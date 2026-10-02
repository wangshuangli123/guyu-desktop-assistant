"""Real local protocol acceptance: no model, credentials or cloud calls."""
import asyncio, json, os, re, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from guyu.core import init_home
from guyu.safety import atomic_json

async def run():
    assert (ROOT/'commander_server.py').is_file(), 'R04 gateway missing: expected RED'
    home = ROOT/'temp'/('r04_'+uuid.uuid4().hex[:12])
    init_home(home)
    checks = []
    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT/'commander_server.py'),'--home',str(home)],
        env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as client:
            initialized = await client.initialize()
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {'read_file','write_file','edit_block','start_search','start_process','device_status','pause_session'} <= names
            assert not {'set_config_value','give_feedback_to_desktop_commander','get_prompts','kill_process'} & names
            for tool in tools.tools:
                assert 'origin' not in tool.inputSchema.get('properties',{}), 'Rejected UI-origin field must not be advertised'
            checks.append('tool_inventory_and_protected_tools')
            (ROOT/'evidence/r04-tools.json').write_text(json.dumps([t.model_dump(mode='json') for t in tools.tools],ensure_ascii=False,indent=2),encoding='utf-8')
            async def call(name, args=None, error=False):
                result = await client.call_tool(name,args or {})
                text = '\n'.join(c.text for c in result.content if c.type=='text')
                assert bool(result.isError)==error, f'{name}: {text}'
                checks.append(name+('_blocked' if error else '_ok'))
                return text
            workspace = home/'workspace'
            directory = workspace/'中文项目'
            target = directory/'hello.py'
            await call('create_directory',{'path':str(directory)})
            await call('write_file',{'path':str(target),'content':'# 谷雨测试\nprint("GUYU_OLD")\n'})
            assert '谷雨测试' in await call('read_file',{'path':str(target)})
            await call('edit_block',{'file_path':str(target),'old_string':'GUYU_OLD','new_string':'GUYU_NEW'})
            assert 'GUYU_NEW' in target.read_text(encoding='utf-8')
            assert 'hello.py' in await call('list_directory',{'path':str(workspace),'depth':3})
            await call('get_file_info',{'path':str(target)})
            await call('read_multiple_files',{'paths':[str(target)]})
            await call('write_file',{'path':str(home/'outside.txt'),'content':'blocked'},error=True)
            await call('read_file',{'path':'https://example.com','isUrl':True},error=True)
            await call('start_process',{'command':'Write-Output GUYU_TERMINAL_OK','timeout_ms':1000},error=True)
            atomic_json(home/'runtime/commander-control.json',{'version':1,'terminal_enabled':True})
            output = await call('start_process',{'command':'Write-Output GUYU_TERMINAL_OK','timeout_ms':1000,'shell':'powershell.exe'})
            assert 'GUYU_TERMINAL_OK' in output, output
            from r04_more_cases import more_cases
            await more_cases(call,home)
            await call('force_terminate',{'pid':999999},error=True)
            await call('list_sessions')
            await call('pause_session')
            await call('write_file',{'path':str(directory/'paused.txt'),'content':'blocked'},error=True)
            await call('start_process',{'command':'Write-Output PAUSED','timeout_ms':1000},error=True)
            assert json.loads(await call('device_status'))['paused'] is True
            assert not (home/'outside.txt').exists()
            assert not (directory/'paused.txt').exists()
    report = {'result':'R04_LOCAL_PROTOCOL_VERIFIED','at':datetime.now(timezone.utc).isoformat(),
        'home':str(home),'protocol':initialized.protocolVersion,'tool_count':len(names),
        'tools':sorted(names),'checks':checks,'model_e2e':'NOT_TESTED','web_e2e':'NOT_TESTED'}
    (ROOT/'evidence/r04-protocol.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    asyncio.run(asyncio.wait_for(run(),timeout=120))
