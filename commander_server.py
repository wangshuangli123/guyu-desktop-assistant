"""Guyu local MCP gateway using the independently copied MIT upstream engine."""
import argparse, asyncio, json, logging, shutil, sys, uuid
from datetime import timedelta
from pathlib import Path
from mcp import ClientSession, types
from mcp.client.stdio import stdio_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import Assistant, init_home
from guyu.safety import AppError
from guyu.commander_backend import backend_parameters
from guyu.commander_policy import CommanderPolicy, UPSTREAM_TOOLS
from guyu.local_extensions import LocalExtensions, NAMES, tool_definitions


def response(data, error=False):
    text = data if isinstance(data,str) else json.dumps(data,ensure_ascii=False)
    return types.CallToolResult(content=[types.TextContent(type='text',text=text)],isError=error)


def public_schema(schema):
    schema = json.loads(json.dumps(schema))
    properties = schema.get('properties',{})
    for key in ('origin','_meta','deviceId'):
        properties.pop(key,None)
    if 'isUrl' in properties:
        properties['isUrl'] = {'type':'boolean','const':False,'default':False}
    return schema


async def main(home):
    init_home(home)
    app = Assistant(home,source='commander-adapter')
    policy = CommanderPolicy(app)
    extensions = LocalExtensions(app,policy)
    params = backend_parameters(ROOT,home)
    gateway = Server('guyu-commander',version='0.5.0')
    lock = asyncio.Lock()
    logging.basicConfig(level=logging.WARNING,stream=sys.stderr)
    with (home/'logs/commander-engine.log').open('a',encoding='utf-8') as errlog:
        async with stdio_client(params,errlog=errlog) as (reader,writer):
            async with ClientSession(reader,writer,read_timeout_seconds=timedelta(seconds=60)) as backend:
                await backend.initialize()
                inventory = await backend.list_tools()
                tools = [types.Tool(name=t.name,description='本地独立引擎；文件仅限授权工作区；终端须本地开启。\n'+(t.description or ''),
                    inputSchema=public_schema(t.inputSchema),annotations=t.annotations,outputSchema=t.outputSchema)
                    for t in inventory.tools if t.name in UPSTREAM_TOOLS and t.name!='write_pdf']
                for tool in tools:
                    if tool.name=='write_pdf':
                        tool.description='PDF 生成暂未开放：渲染资源范围需专项验收。读取现有 PDF 可使用 read_file。'
                names = {t.name for t in tools}
                tools.extend(tool_definitions())
                read = types.ToolAnnotations(readOnlyHint=True,destructiveHint=False,openWorldHint=False)
                for name,description in [('device_status','本地状态、暂停状态和已注册功能；不是网页接通证明。'),
                    ('get_config','查看适配器设置；不返回密钥，不允许模型更改授权。'),
                    ('pause_session','暂停新文件、搜索和命令动作；不撤销已发生的操作。')]:
                    tools.append(types.Tool(name=name,description=description,
                        inputSchema={'type':'object','properties':{},'additionalProperties':False},
                        annotations=read if name!='pause_session' else types.ToolAnnotations(readOnlyHint=False,destructiveHint=False)))

                @gateway.list_tools()
                async def list_tools():
                    return tools

                @gateway.call_tool()
                async def call_tool(name,arguments):
                    async with lock:
                        try:
                            if name in NAMES:
                                return response(extensions.call(name,arguments or {}))
                            if name=='pause_session':
                                return response(app.pause())
                            if name in {'device_status','get_config'}:
                                return response(dict(app.status(),version='0.5.0',adapter_version='0.5.0',upstream_version='0.2.50',
                                    terminal_enabled=policy.terminal_enabled(),tool_count=len(tools),telemetry_enabled=False,pdf_enabled=False))
                            if name not in names:
                                raise AppError('TOOL_DENIED','Tool not available in this adapter.')
                            args = policy.validate(name,arguments or {})
                            backup = None
                            key = {'write_file':'path','edit_block':'file_path','move_file':'source'}.get(name)
                            if key:
                                source = Path(args[key])
                                if source.is_file():
                                    if source.stat().st_size>20*1024*1024:
                                        raise AppError('BACKUP_LIMIT','Existing file exceeds the 20 MiB overwrite-backup limit.')
                                    backup = extensions.versions.snapshot(str(source),'dc:'+name)['id']
                            app._event('dc:'+name,'running')
                            result = await backend.call_tool(name,args)
                            policy.track_result(name,result)
                            app._event('dc:'+name,'blocked' if result.isError else 'succeeded')
                            if backup:
                                result.content.append(types.TextContent(type='text',text='Restorable backup ID: '+str(backup)))
                            return result
                        except AppError as exc:
                            app._event('dc:'+name,'blocked')
                            return response(str(exc),error=True)
                        except Exception as exc:
                            app._event('dc:'+name,'unknown')
                            logging.exception('Upstream operation has an uncertain result')
                            return response('RESULT_UNKNOWN: '+str(exc)+'; inspect the existing result; do not automatically retry writes.',error=True)
                async with stdio_server() as (input_stream,output_stream):
                    await gateway.run(input_stream,output_stream,gateway.create_initialization_options())


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,default=ROOT)
    arguments = parser.parse_args()
    asyncio.run(main(arguments.home.resolve()))
