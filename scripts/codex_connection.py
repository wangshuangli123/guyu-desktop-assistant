"""Local client entry with invocation-only settings; no global config edits."""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def executable():
    base = Path(os.environ['LOCALAPPDATA'])/'OpenAI/Codex/bin'
    matches = sorted(base.glob('*/codex.exe'),key=lambda p:p.stat().st_mtime,reverse=True)
    if not matches:
        raise RuntimeError('未找到已有 Codex 客户端；不自动下载安装或购买服务。')
    return str(matches[0])


def settings(home=ROOT):
    return {'forced_login_method':'chatgpt','model_provider':'openai',
        'log_dir':str(ROOT/'logs/codex'),'sqlite_home':str(ROOT/'runtime/codex-state'),
        'history.persistence':'none',
        'mcp_servers.guyu_commander.command':str(ROOT/'runtime/venv/Scripts/python.exe'),
        'mcp_servers.guyu_commander.args':[str(ROOT/'commander_server.py'),'--home',str(home)],
        'mcp_servers.guyu_commander.cwd':str(ROOT),
        'mcp_servers.guyu_commander.env':{'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','TEMP':str(home/'temp'),'TMP':str(home/'temp')},
        'mcp_servers.guyu_commander.startup_timeout_sec':30,
        'mcp_servers.guyu_commander.tool_timeout_sec':65,
        'mcp_servers.guyu_commander.required':True,
        'mcp_servers.guyu_commander.default_tools_approval_mode':'writes'}


def toml_value(value):
    if isinstance(value,dict):
        return '{'+', '.join(json.dumps(k)+' = '+toml_value(v) for k,v in value.items())+'}'
    return json.dumps(value,ensure_ascii=False)


def arguments(home=ROOT):
    result = []
    for key,value in settings(home).items():
        result.extend(['-c',key+'='+toml_value(value)])
    return result


def environment():
    env = dict(os.environ)
    for key in ('OPENAI_API_KEY','OPENAI_BASE_URL','AZURE_OPENAI_API_KEY'):
        env.pop(key,None)
    env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(ROOT/'temp'),TMP=str(ROOT/'temp'))
    return env


def check():
    config = Path.home()/'.codex/config.toml'
    before = hashlib.sha256(config.read_bytes()).hexdigest() if config.exists() else None
    result = subprocess.run([executable(),*arguments(),'mcp','get','guyu_commander','--json'],
        cwd=ROOT,env=environment(),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
    after = hashlib.sha256(config.read_bytes()).hexdigest() if config.exists() else None
    if before!=after:
        raise RuntimeError('Client inspection unexpectedly changed global configuration.')
    report = {'result':'CLIENT_CONFIG_ACCEPTED' if result.returncode==0 else 'CLIENT_CONFIG_FAILED',
        'exit_code':result.returncode,'global_config_unchanged':True,
        'model_e2e':'NOT_TESTED','web_e2e':'NOT_TESTED',
        'configuration':json.loads(result.stdout) if result.returncode==0 else None,
        'diagnostic':result.stderr}
    (ROOT/'evidence/client-recognition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return result.returncode


def interactive_command(prompt):
    return [executable(),*arguments(),'--sandbox','read-only','--ask-for-approval','on-request','-C',str(ROOT),prompt]


def launch():
    exe = executable()
    status = subprocess.run([exe,'-c','forced_login_method="chatgpt"','login','status'],
        capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=20,env=environment())
    if status.returncode!=0 or 'Logged in using ChatGPT' not in status.stdout+status.stderr:
        raise RuntimeError('请先在已有官方 Codex 客户端登录 ChatGPT 账号；不会改用付费 API。')
    prompt = ('请使用 guyu_commander 的本地 MCP 工具处理我接下来交给你的任务。'
        '先调用 device_status 告诉我真实状态。文件操作仅限显示的 workspace。'
        '工具暂停时让我在控制窗口恢复，不要自己修改授权文件。'
        '终端默认关闭，必须由我在本地明确开启。不要购买服务或切换付费 API。')
    print('使用现有 ChatGPT 账号；不会新增 API 密钥或云服务。关闭此窗口即结束本次客户端。')
    return subprocess.call(interactive_command(prompt),
        cwd=ROOT,env=environment())


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    opts = parser.parse_args()
    for directory in ('logs/codex','runtime/codex-state','temp','evidence'):
        (ROOT/directory).mkdir(parents=True,exist_ok=True)
    try:
        sys.exit(check() if opts.check else launch())
    except (OSError,RuntimeError,subprocess.TimeoutExpired,ValueError) as exc:
        print('连接未完成：'+str(exc),file=sys.stderr)
        sys.exit(1)
