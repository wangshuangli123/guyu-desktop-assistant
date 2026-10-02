"""Local tools: workspace restrictions, audit, pause and durable request IDs."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sqlite3
import uuid
from .safety import AppError, MAX_BYTES, atomic_json, decode_text, digest, request_key, safe_path, text_bytes
VERSION = '0.5.0'

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def init_home(home):
    home = Path(home)
    for name in ('workspace','runtime','logs','backups','temp','evidence'):
        (home/name).mkdir(parents=True,exist_ok=True)
    marker = home/'runtime/initialized.json'
    if not marker.exists():
        if not (home/'runtime/control.json').exists():
            atomic_json(home/'runtime/control.json',{'paused':False,'version':1})
        atomic_json(marker,{'created':now(),'version':VERSION})

class Assistant:
    def __init__(self, home, source='local'):
        self.home = Path(home).resolve()
        self.workspace = self.home/'workspace'
        self.runtime = self.home/'runtime'
        self.source = source
        self.database = self.runtime/'audit.sqlite3'
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,fingerprint TEXT,status TEXT,result TEXT,error TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS events(n INTEGER PRIMARY KEY,time TEXT,source TEXT,action TEXT,status TEXT,job_id TEXT)')
        db = sqlite3.connect(self.runtime/'operation-lock.sqlite3')
        db.execute('CREATE TABLE IF NOT EXISTS guard(id INTEGER)')
        db.commit()
        db.close()

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.database,timeout=3)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @contextmanager
    def _serial(self):
        db = sqlite3.connect(self.runtime/'operation-lock.sqlite3',timeout=3)
        try:
            db.execute('BEGIN IMMEDIATE')
            yield
        except sqlite3.OperationalError as exc:
            raise AppError('BUSY','Another action is running; check its result.') from exc
        finally:
            db.rollback()
            db.close()

    def _enabled(self):
        try:
            control = json.loads((self.runtime/'control.json').read_text(encoding='utf-8-sig'))
        except (OSError,ValueError) as exc:
            raise AppError('PAUSED','Control state is missing or damaged.') from exc
        if not isinstance(control,dict) or control.get('paused') is not False or control.get('version') != 1:
            raise AppError('PAUSED','Resume from the local control window.')

    def _event(self,action,status,job_id=''):
        with self._db() as db:
            db.execute('INSERT INTO events(time,source,action,status,job_id) VALUES(?,?,?,?,?)',(now(),self.source,action,status,job_id))

    def _mutate(self,action,payload,key,function):
        key = request_key(key)
        fingerprint = digest(json.dumps([action,payload],ensure_ascii=False,sort_keys=True).encode())
        with self._serial():
            self._enabled()
            with self._db() as db:
                old = db.execute('SELECT * FROM jobs WHERE id=?',(key,)).fetchone()
                if old:
                    if old['fingerprint'] != fingerprint:
                        raise AppError('IDEMPOTENCY_CONFLICT','Request ID was used for a different operation.')
                    if old['status'] == 'succeeded':
                        return json.loads(old['result'])
                    raise AppError('RESULT_UNKNOWN','Previous result is uncertain; do not replay blindly.')
                db.execute('INSERT INTO jobs VALUES(?,?,?,?,?)',(key,fingerprint,'running',None,None))
            self._event(action,'running',key)
            try:
                result = function()
            except Exception as exc:
                code = exc.code if isinstance(exc,AppError) else 'INTERNAL_ERROR'
                with self._db() as db:
                    db.execute('UPDATE jobs SET status=?,error=? WHERE id=?',('unknown',code,key))
                self._event(action,'blocked' if isinstance(exc,AppError) else 'unknown',key)
                if isinstance(exc,AppError):
                    raise
                raise AppError('RESULT_UNKNOWN','Operation failed; inspect its result before retrying.') from exc
            with self._db() as db:
                db.execute('UPDATE jobs SET status=?,result=? WHERE id=?',('succeeded',json.dumps(result,ensure_ascii=False),key))
            self._event(action,'succeeded',key)
            return result

    def status(self):
        try:
            self._enabled()
            paused = False
        except AppError:
            paused = True
        return {'version':VERSION,'paused':paused,'workspace':str(self.workspace),'transport':'stdio','network_listener':False,'paid_api_configured':False,'model_e2e':'NOT_TESTED','web_e2e':'NOT_TESTED'}

    def pause(self):
        atomic_json(self.runtime/'control.json',{'paused':True,'version':1})
        self._event('pause','succeeded')
        return {'paused':True,'note':'Stops later actions; cannot undo completed actions.'}

    def resume_local(self):
        # Deliberately not exposed as a model-callable tool.
        atomic_json(self.runtime/'control.json',{'paused':False,'version':1})
        self._event('resume_local','succeeded')

    def recent_events(self):
        with self._db() as db:
            return [dict(r) for r in db.execute('SELECT time,source,action,status,job_id FROM events ORDER BY n DESC LIMIT 60')]

    def get_job(self,request_id):
        with self._db() as db:
            row = db.execute('SELECT id,status,result,error FROM jobs WHERE id=?',(request_key(request_id),)).fetchone()
        if not row:
            raise AppError('NOT_FOUND','No such request.')
        result = dict(row)
        result['result'] = json.loads(result['result']) if result['result'] else None
        return result

    def _read(self,path):
        if not path.is_file():
            raise AppError('NOT_FOUND','Text file not found.')
        with path.open('rb') as stream:
            data = stream.read(MAX_BYTES+1)
        if len(data)>MAX_BYTES:
            raise AppError('LIMIT_EXCEEDED','File exceeds 256 KiB.')
        return data

    def read_text(self,path):
        self._enabled()
        data = self._read(safe_path(self.workspace,path))
        self._event('read_text','succeeded')
        return {'path':path,'text':decode_text(data),'sha256':digest(data),'bytes':len(data)}

    def list_files(self,path='.'):
        self._enabled()
        p = safe_path(self.workspace,path,directory=True)
        if not p.is_dir():
            raise AppError('NOT_FOUND','Directory not found.')
        entries = []
        truncated = False
        with os.scandir(p) as scan:
            for item in scan:
                if len(entries)>=200:
                    truncated = True
                    break
                try:
                    safe_path(self.workspace,str(Path(item.path).relative_to(self.workspace)),directory=True)
                    entries.append({'name':item.name,'directory':item.is_dir(follow_symlinks=False)})
                except AppError:
                    continue
        self._event('list_files','succeeded')
        return {'entries':sorted(entries,key=lambda e:e['name']),'truncated':truncated}

    def search_files(self,query):
        self._enabled()
        if not isinstance(query,str) or not 1<=len(query)<=120:
            raise AppError('INVALID_QUERY','Use a name fragment of 1-120 characters.')
        listing = self.list_files()
        return {'files':[i['name'] for i in listing['entries'] if query.casefold() in i['name'].casefold()],'truncated':listing['truncated'],'recursive':False}

    def create_text(self,path,text,request_id):
        data = text_bytes(text)
        safe_path(self.workspace,path)
        def work():
            p = safe_path(self.workspace,path)
            if not p.parent.is_dir():
                raise AppError('NOT_FOUND','Parent directory does not exist.')
            self._enabled()
            try:
                with p.open('xb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError as exc:
                raise AppError('ALREADY_EXISTS','Create never overwrites an existing file.') from exc
            return {'path':path,'sha256':digest(data),'bytes':len(data)}
        return self._mutate('create_text',{'path':path,'sha256':digest(data)},request_id,work)

    def replace_text(self,path,text,expected_sha256,request_id):
        data = text_bytes(text)
        safe_path(self.workspace,path)
        def work():
            p = safe_path(self.workspace,path)
            old = self._read(p)
            if digest(old)!=expected_sha256:
                raise AppError('STALE_FILE','File changed; read again before editing.')
            backup = self.home/'backups'/f'{uuid.uuid4().hex}.bak'
            with backup.open('xb') as stream:
                stream.write(old)
                stream.flush()
                os.fsync(stream.fileno())
            tmp = p.with_name(f'.guyu-{uuid.uuid4().hex}.txt')
            try:
                with tmp.open('xb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                self._enabled()
                safe_path(self.workspace,path)
                if digest(self._read(p))!=expected_sha256:
                    raise AppError('STALE_FILE','File changed during preparation.')
                os.replace(tmp,p)
            finally:
                tmp.unlink(missing_ok=True)
            return {'path':path,'sha256':digest(data),'backup':backup.relative_to(self.home).as_posix()}
        return self._mutate('replace_text',{'path':path,'sha256':digest(data),'expected_sha256':expected_sha256},request_id,work)
