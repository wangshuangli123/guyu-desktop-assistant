"""Official-SDK integration test. No model, API key or cloud service."""
import argparse
import asyncio
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import uuid
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import init_home

async def run(desktop=False):
    assert (ROOT/'server.py').is_file(), 'MCP server missing: expected RED before implementation'
    home = ROOT/'temp'/('smoke_'+uuid.uuid4().hex[:12])
    init_home(home)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', TEMP=str(home/'temp'), TMP=str(home/'temp'))
    params = StdioServerParameters(command=sys.executable,args=[str(ROOT/'server.py'),'--home',str(home)],env=env)
    checks = []
    report = {'home':str(home),'started':datetime.now(timezone.utc).isoformat(),'client':'official Python MCP SDK','model_e2e':'NOT_TESTED','web_e2e':'NOT_TESTED'}
    async with stdio_client(params) as (reader,writer):
        async with ClientSession(reader,writer) as client:
            initialized = await client.initialize()
            report['protocol'] = initialized.protocolVersion
            tools = await client.list_tools()
            report['tools'] = [tool.name for tool in tools.tools]
            assert {'device_status','create_text','read_text','pause_session'} <= set(report['tools'])
            checks.append('initialize_and_tools_list')
            async def call(name, args=None, error=False):
                result = await client.call_tool(name,args or {})
                assert bool(result.isError)==error, f'{name}: unexpected result {result}'
                checks.append(name+('_blocked' if error else '_ok'))
                if error:
                    return None
                return json.loads(next(c.text for c in result.content if c.type=='text'))
            content = '谷雨电脑助手连接测试成功\n中文与 emoji 🙂'
            first = await call('create_text',{'path':'protocol.txt','text':content,'request_id':'smoke_create_001'})
            again = await call('create_text',{'path':'protocol.txt','text':content,'request_id':'smoke_create_001'})
            assert first==again
            read = await call('read_text',{'path':'protocol.txt'})
            assert read['text']==content
            await call('create_text',{'path':'../escape.txt','text':'blocked','request_id':'smoke_block_001'},error=True)
            await call('create_text',{'path':'other.txt','text':'blocked','request_id':'smoke_create_001'},error=True)
            await call('replace_text',{'path':'protocol.txt','text':'updated','expected_sha256':first['sha256'],'request_id':'smoke_update_001'})
            if desktop:
                opened = await call('launch_test_editor',{'request_id':'smoke_launch_001'})
                report['editor'] = opened
                await call('type_test_text',{'text':content,'request_id':'smoke_type_001'})
                observed = await call('observe_test_editor')
                assert observed['text'].replace('\r\n','\n')==content
                saved = await call('save_test_document',{'request_id':'smoke_save_001'})
                assert saved['content_verified'] is True
                assert (home/'workspace'/opened['path']).read_text(encoding='utf-8-sig').replace('\r\n','\n')==content
                picture = await client.call_tool('screenshot_test_editor',{})
                assert not picture.isError
                images = [x for x in picture.content if x.type=='image']
                assert images, 'Screenshot did not return image content'
                (ROOT/'evidence').mkdir(exist_ok=True)
                (ROOT/'evidence/notepad_verified.png').write_bytes(base64.b64decode(images[0].data))
                checks.append('single_window_screenshot_ok')
                await call('close_saved_test_editor',{'request_id':'smoke_close_001'})
                report['windows_adapter'] = 'VERIFIED'
            await call('pause_session')
            await call('create_text',{'path':'paused.txt','text':'blocked','request_id':'smoke_pause_001'},error=True)
            status = await call('device_status')
            assert status['paused'] is True
            assert not (home/'workspace/paused.txt').exists()
            assert not (home/'escape.txt').exists()
    report.update(result='LOCAL_PROTOCOL_VERIFIED',checks=checks)
    (ROOT/'evidence').mkdir(exist_ok=True)
    (ROOT/'evidence/protocol_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--desktop',action='store_true')
    args = parser.parse_args()
    asyncio.run(asyncio.wait_for(run(args.desktop),timeout=90))
