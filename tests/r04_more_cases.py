"""Additional acceptance against the real upstream engine and test files."""
import asyncio, json, re, sys
from pathlib import Path

async def more_cases(call, home):
    workspace = home/'workspace'
    directory = workspace/'中文项目'
    target = directory/'hello.py'
    moved = directory/'renamed.py'
    await call('move_file',{'source':str(target),'destination':str(moved)})
    assert moved.exists() and not target.exists()
    search = await call('start_search',{'path':str(workspace),'pattern':'GUYU_NEW',
        'searchType':'content','literalSearch':True,'timeout_ms':10000})
    match = re.search(r'search_\d+_\d+',search)
    assert match, search
    combined = search
    for attempt in range(10):
        combined += await call('get_more_search_results',{'sessionId':match.group(0),'offset':0,'length':100})
        if 'GUYU_NEW' in combined and 'renamed.py' in combined:
            break
        await asyncio.sleep(0.25)
    assert 'renamed.py' in combined and 'GUYU_NEW' in combined, combined
    await call('list_searches')
    excel = directory/'test.xlsx'
    data = [['项目','数值'],['中文测试',123]]
    await call('write_file',{'path':str(excel),'content':json.dumps(data,ensure_ascii=False)})
    assert '中文测试' in await call('read_file',{'path':str(excel),'range':'A1:B2'})
    document = directory/'test.docx'
    await call('write_file',{'path':str(document),'content':'# GUYU\n\n中文文档测试 BEFORE'})
    assert 'BEFORE' in await call('read_file',{'path':str(document)})
    await call('edit_block',{'file_path':str(document),
        'old_string':'中文文档测试 BEFORE','new_string':'中文文档测试 AFTER'})
    assert 'AFTER' in await call('read_file',{'path':str(document)})
    output = await call('start_process',{'command':f'& "{sys.executable}" -u -i',
        'timeout_ms':1000,'shell':'powershell.exe'})
    match = re.search(r'PID[: ]+(\d+)',output)
    assert match, output
    pid = int(match.group(1))
    try:
        interactive = await call('interact_with_process',{'pid':pid,
            'input':'print("GUYU_INTERACTIVE_" + str(6 * 7))', 'timeout_ms':5000})
        assert 'GUYU_INTERACTIVE_42' in interactive, interactive
        await call('read_process_output',{'pid':pid,'offset':0,'length':100,'timeout_ms':1000})
        assert str(pid) in await call('list_sessions')
    finally:
        await call('force_terminate',{'pid':pid})
    await call('get_recent_tool_calls')
    await call('get_usage_stats')
