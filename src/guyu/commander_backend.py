"""Launch settings isolated from the user's original Desktop Commander."""
import json, os, shutil
from pathlib import Path
from mcp import StdioServerParameters
from .safety import AppError, atomic_json
BLOCKED = 'mkfs format mount umount fdisk dd parted diskpart sudo su passwd adduser useradd usermod groupadd chsh visudo shutdown reboot halt poweroff init iptables firewall netsh sfc bcdedit reg net sc runas cipher takeown'.split()


def backend_parameters(root, home):
    root, home = Path(root).resolve(), Path(home).resolve()
    node = shutil.which('node')
    if not node:
        raise AppError('NODE_NOT_FOUND','Install or locate Node.js before using this adapter.')
    package = root/'vendor/desktop-commander/node_modules/@wonderwhy-er/desktop-commander'
    manifest = json.loads((package/'package.json').read_text(encoding='utf-8'))
    if manifest.get('version')!='0.2.50' or manifest.get('license')!='MIT':
        raise AppError('UPSTREAM_VERSION_MISMATCH','The reviewed upstream version must be 0.2.50 MIT.')
    profile = home/'runtime/commander-home'
    config_dir = profile/'.claude-server-commander'
    for directory in (profile,config_dir,profile/'AppData/Roaming',profile/'AppData/Local',home/'cache',home/'temp'):
        directory.mkdir(parents=True,exist_ok=True)
    config_path = config_dir/'config.json'
    config = {}
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding='utf-8-sig'))
        if not isinstance(config,dict):
            raise AppError('INVALID_BACKEND_CONFIG','Backend configuration is not an object.')
    config.update(telemetryEnabled=False,allowedDirectories=[str(home/'workspace')],
        blockedCommands=sorted(set(BLOCKED)|set(config.get('blockedCommands',[]))),
        defaultShell='powershell.exe',fileReadLineLimit=1000,fileWriteLineLimit=50,
        pendingWelcomeOnboarding=False,welcomeOnboardingEligible=False)
    atomic_json(config_path,config)
    # Do not pass model/API credentials into the execution engine.
    keys = {'PATH','SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','PROGRAMFILES',
        'PROGRAMFILES(X86)','SYSTEMDRIVE','OS','PROCESSOR_ARCHITECTURE','NUMBER_OF_PROCESSORS'}
    env = {key:value for key,value in os.environ.items() if key.upper() in keys}
    env.update(USERPROFILE=str(profile),HOME=str(profile),
        APPDATA=str(profile/'AppData/Roaming'),LOCALAPPDATA=str(profile/'AppData/Local'),
        TEMP=str(home/'temp'),TMP=str(home/'temp'),
        XDG_CACHE_HOME=str(home/'cache'),npm_config_cache=str(home/'cache/npm'),
        PIP_CACHE_DIR=str(home/'cache/pip'),PUPPETEER_CACHE_DIR=str(home/'cache/chrome'),
        PUPPETEER_SKIP_DOWNLOAD='true',DESKTOP_COMMANDER_DISABLE_TELEMETRY='1',
        PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',UV_THREADPOOL_SIZE='16')
    return StdioServerParameters(command=node,args=[str(root/'scripts/commander-stdio.mjs')],
        env=env,cwd=str(home/'workspace'))
