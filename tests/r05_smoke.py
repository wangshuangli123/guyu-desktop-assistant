"""Exercise restore through the real local MCP process; no model usage."""
import asyncio,json,os,sys,uuid
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import init_home,now

async def run():
    home=ROOT/'temp'/('r05_'+uuid.uuid4().hex[:10]); init_home(home)
    params=StdioServerParameters(command=sys.executable,args=[str(ROOT/'commander_server.py'),'--home',str(home)],
        env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(home/'temp'),TMP=str(home/'temp')))
    checks=[]
    async with stdio_client(params) as (reader,writer):
        async with ClientSession(reader,writer) as client:
            await client.initialize(); tools=await client.list_tools()
            names={t.name for t in tools.tools}
            assert {'preview_text','save_text_with_backup','list_backups','restore_backup'}<=names,'R05 tools are missing: expected RED'
            async def call(name,args=None,error=False,parse=False):
                result=await client.call_tool(name,args or {})
                text='\n'.join(c.text for c in result.content if c.type=='text')
                assert bool(result.isError)==error,(name,text)
                checks.append(name+('_blocked' if error else '_ok'))
                return json.loads(text) if parse and not error else text
            p=home/'workspace/test.txt'
            await call('write_file',{'path':str(p),'content':'Original 中文'})
            preview=await call('preview_text',{'path':str(p)},parse=True)
            saved=await call('save_text_with_backup',{'path':str(p),'text':'Updated 中文',
                'expected_sha256':preview['sha256'],'request_id':'protocol_save_001'},parse=True)
            listed=await call('list_backups',parse=True)
            assert saved['backup_id'] in {x['id'] for x in listed['backups']}
            args={'backup_id':saved['backup_id'],'expected_sha256':saved['sha256'],'request_id':'protocol_restore_001'}
            restored=await call('restore_backup',args,parse=True)
            again=await call('restore_backup',args,parse=True); assert restored==again
            assert p.read_text(encoding='utf-8')=='Original 中文'
            await call('edit_block',{'file_path':str(p),'old_string':'Original','new_string':'Patched'})
            listed=await call('list_backups',parse=True)
            assert any(x['action']=='dc:edit_block' for x in listed['backups'])
            stale={'path':str(p),'text':'wrong','expected_sha256':preview['sha256'],'request_id':'protocol_stale_001'}
            await call('save_text_with_backup',stale,error=True)
            config=await call('get_config',parse=True)
            assert config['network_listener'] is False and config['pdf_enabled'] is False
            tail=home/'workspace/tail.txt'
            await call('write_file',{'path':str(tail),'content':'FIRST_LINE\nSECOND_LINE\nLAST_LINE'})
            ending=await call('read_file',{'path':str(tail),'offset':-1,'length':1})
            assert 'LAST_LINE' in ending and 'FIRST_LINE' not in ending
            from PIL import Image
            image_path=home/'workspace/local-image.png'
            Image.new('RGB',(160,90),'white').save(image_path)
            image_result=await client.call_tool('read_file',{'path':str(image_path)})
            assert not image_result.isError and any(c.type=='image' for c in image_result.content)
            checks.append('image_read_verified')
            await call('list_processes')
            search=await call('start_search',{'path':str(home/'workspace'),'pattern':'test','searchType':'files'})
            import re
            match=re.search(r'(search_\d+_\d+)',search)
            if not match: raise AssertionError('No search session returned: '+search)
            await call('stop_search',{'sessionId':match[1]})
            await call('pause_session')
            await call('restore_backup',dict(args,request_id='protocol_paused_001'),error=True)
            await call('preview_text',{'path':str(p)},error=True)
    report={'result':'R05_LOCAL_PROTOCOL_VERIFIED','at':now(),'home':str(home),'checks':checks,
        'tools':sorted(names),'model_e2e':'NOT_TESTED','web_e2e':'NOT_TESTED',
        'additional_workspaces':'BLOCKED_NOT_IMPLEMENTED','pdf':'BLOCKED_NOT_IMPLEMENTED'}
    (ROOT/'evidence/r05-protocol.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': asyncio.run(asyncio.wait_for(run(),timeout=120))
