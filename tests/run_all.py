"""Repeatable local verification. Does not invoke a model or buy any service."""
from datetime import datetime, timezone
import io, json, os, subprocess, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',TEMP=str(ROOT/'temp'),TMP=str(ROOT/'temp'))
sys.dont_write_bytecode = True
sys.path.insert(0,str(ROOT/'src'))
for directory in ('evidence','logs','temp'):
    (ROOT/directory).mkdir(exist_ok=True)
stream = io.StringIO()
suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
result = unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
unit_log = stream.getvalue()
(ROOT/'logs/tests-final.log').write_text(unit_log,encoding='utf-8')
print(unit_log)
protocols = {}
for name,script,evidence in [('legacy','mcp_smoke.py','protocol_report.json'),('commander','r04_smoke.py','r04-protocol.json'),('extensions','r05_smoke.py','r05-protocol.json')]:
    try:
        run = subprocess.run([sys.executable,str(ROOT/'tests'/script)],cwd=ROOT,
            capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=160)
        (ROOT/'logs'/('r05-'+name+'-final.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
        report = json.loads((ROOT/'evidence'/evidence).read_text(encoding='utf-8')) if run.returncode==0 else {}
        protocols[name] = {'exit_code':run.returncode,'checks':len(report.get('checks',[]))}
        print(name,run.returncode,run.stdout[-1400:])
    except subprocess.TimeoutExpired:
        protocols[name] = {'exit_code':124,'checks':0,'error':'Test timed out; not a pass.'}

def read_report(name):
    try:
        report = json.loads((ROOT/'evidence'/name).read_text(encoding='utf-8'))
        return report if isinstance(report,dict) else {}
    except (OSError,ValueError):
        return {}

ok = result.wasSuccessful() and all(p['exit_code']==0 for p in protocols.values())
commander = read_report('r05-protocol.json')
model = read_report('model-read-report.json')
client = read_report('client-recognition.json')
status = {'project':'Guyu Desktop Assistant','version':'0.5.0-dev','root':str(ROOT),
    'verified_at_utc':datetime.now(timezone.utc).isoformat(),
    'overall':'LOCAL_VERSION_WORKFLOW_VERIFIED' if ok else 'VERIFICATION_FAILED',
    'unit_tests':{'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)},
    'protocol_tests':protocols,'registered_tools':commander.get('tools',[]),
    'registered_tool_count':len(commander.get('tools',[])),
    'tested_features':['text_and_source_files','create_directories','rename_files','recursive_content_search',
        'multi_file_read','file_metadata','backup_before_edit','xlsx_read_write','docx_read_write_edit',
        'powershell_output','python_interactive_process','owned_process_termination','pause_and_scope_checks','native_control_panel','version_catalog','sha256_checked_preview_save',
        'verified_restore_with_recovery_backup','native_text_preview','native_image_preview','process_listing','search_stop','negative_offset_read','image_mcp_read'],
    'untested_registered_features':[],
    'blocked_unimplemented_tests':{'workspace_grants':2,'pdf_integration':9},
    'additional_workspaces':'BLOCKED_NOT_IMPLEMENTED','pdf_creation':'BLOCKED_NOT_IMPLEMENTED',
    'terminal_default':'DISABLED_REQUIRES_LOCAL_CONFIRMATION',
    'desktop_input_control':'NOT_IMPLEMENTED','browser_control':'NOT_IMPLEMENTED',
    'client_configuration':client.get('result','NOT_TESTED'),
    'model_read_e2e':model.get('result','NOT_TESTED'),'model_write_e2e':read_report('model-write-report.json').get('result','NOT_TESTED'),'web_e2e':'NOT_TESTED',
    'paid_api_used':False,'cloud_service_deployed':False,'upstream_package_version':'0.2.50',
    'limitations':['Not an operating-system sandbox','Not the commercial remote service','Source backup is not a standalone installer','Existing Python and Node installations remain dependencies']}
(ROOT/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(status,ensure_ascii=False,indent=2))
sys.exit(0 if ok else 1)
