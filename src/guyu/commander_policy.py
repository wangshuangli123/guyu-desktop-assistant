"""Capability boundary for the local upstream adapter, not an OS sandbox."""
import json, re
from pathlib import Path, PureWindowsPath
from .safety import AppError, safe_path, atomic_json

FILE_TOOLS = {'read_file','read_multiple_files','write_file','edit_block',
    'create_directory','list_directory','move_file','get_file_info','write_pdf'}
SEARCH_TOOLS = {'start_search','get_more_search_results','stop_search','list_searches'}
PROCESS_TOOLS = {'start_process','read_process_output','interact_with_process',
    'force_terminate','list_sessions','list_processes'}
EXTRA_TOOLS = {'get_usage_stats','get_recent_tool_calls'}
UPSTREAM_TOOLS = FILE_TOOLS | SEARCH_TOOLS | PROCESS_TOOLS | EXTRA_TOOLS
PATH_KEYS = {'read_file':('path',),'write_file':('path',),'edit_block':('file_path',),
    'create_directory':('path',),'list_directory':('path',),'move_file':('source','destination'),
    'get_file_info':('path',),'start_search':('path',),'write_pdf':('path','outputPath')}
CLEANUP_TOOLS = {'read_process_output','force_terminate','list_sessions',
    'stop_search','list_searches','get_more_search_results'}

class CommanderPolicy:
    def __init__(self, app):
        self.app = app
        self.control = app.runtime/'commander-control.json'
        self.owned_pids = set()
        if not self.control.exists():
            atomic_json(self.control,{'version':1,'terminal_enabled':False})

    def terminal_enabled(self):
        try:
            value = json.loads(self.control.read_text(encoding='utf-8-sig'))
            return isinstance(value,dict) and value.get('version')==1 and value.get('terminal_enabled') is True
        except (OSError,ValueError):
            return False

    def path(self, value):
        if not isinstance(value,str) or not value or len(value)>1000:
            raise AppError('INVALID_PATH','A nonempty local workspace path is required.')
        root = self.app.workspace.resolve()
        candidate = Path(value)
        if candidate.is_absolute():
            try:
                relative = candidate.relative_to(root)
            except ValueError as exc:
                raise AppError('SCOPE_DENIED','Only the workspace is authorized.') from exc
        else:
            if PureWindowsPath(value).drive or value.startswith(('//','\\\\')):
                raise AppError('SCOPE_DENIED','Network and drive-relative paths are not allowed.')
            relative = candidate
        return str(safe_path(root,str(relative),directory=True))

    def validate(self, name, arguments):
        if name not in UPSTREAM_TOOLS:
            raise AppError('TOOL_DENIED','This tool is not exposed by the local adapter.')
        if name=='write_pdf':
            raise AppError('PDF_NOT_ENABLED','PDF rendering is disabled until resource-scope verification is complete.')
        if name not in CLEANUP_TOOLS:
            self.app._enabled()
        if not isinstance(arguments,dict):
            raise AppError('INVALID_ARGUMENTS','Arguments must be an object.')
        args = dict(arguments)
        if any(key in args for key in ('origin','_meta','deviceId')):
            raise AppError('INVALID_ARGUMENTS','Remote/UI control fields are not accepted.')
        if args.get('isUrl'):
            raise AppError('URL_DISABLED','This adapter does not fetch remote URLs through file tools.')
        for key in PATH_KEYS.get(name,()):
            if key in args and args[key] is not None:
                args[key] = self.path(args[key])
        if name=='read_multiple_files':
            paths = args.get('paths')
            if not isinstance(paths,list) or not 1<=len(paths)<=100:
                raise AppError('LIMIT_EXCEEDED','Read 1-100 workspace files per call.')
            args['paths'] = [self.path(p) for p in paths]
        if name=='write_pdf' and isinstance(args.get('content'),list):
            for operation in args['content']:
                if isinstance(operation,dict) and 'sourcePdfPath' in operation:
                    operation['sourcePdfPath'] = self.path(operation['sourcePdfPath'])
        if name in {'start_process','interact_with_process'} and not self.terminal_enabled():
            raise AppError('TERMINAL_DISABLED','Enable terminal access explicitly in the local control window.')
        if name in {'read_process_output','interact_with_process','force_terminate'}:
            if type(args.get('pid')) is not int or args['pid'] not in self.owned_pids:
                raise AppError('PROCESS_NOT_OWNED','Only a process started by this adapter may be controlled.')
        if name in {'start_process','interact_with_process','read_process_output'}:
            timeout = args.get('timeout_ms',1000)
            if type(timeout) is not int or not 0<=timeout<=30000:
                raise AppError('INVALID_TIMEOUT','Use timeout_ms between 0 and 30000.')
        return args

    def track_result(self,name,result):
        if name=='start_process' and not result.isError:
            for block in result.content:
                if block.type=='text':
                    self.owned_pids.update(int(pid) for pid in re.findall(r'PID[: ]+(\d+)',block.text))
