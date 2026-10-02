"""Versioned file editing within the existing, fixed workspace."""
import json, os, re, uuid
from pathlib import Path
from .core import now
from .safety import AppError, atomic_json, decode_text, digest, text_bytes, reject_link
TEXT_TYPES={'.txt','.md','.log','.json','.csv','.py','.js','.ts','.tsx','.jsx','.css',
    '.html','.xml','.yaml','.yml','.toml','.ini','.c','.h','.cpp','.rs'}
MAX_BACKUP=20*1024*1024

class Versions:
    def __init__(self,app,policy):
        self.app=app; self.policy=policy
        self.folder=app.home/'backups/versions'
        self.folder.mkdir(parents=True,exist_ok=True)
    def _path(self,value):
        return Path(self.policy.path(str(value)))
    def _bytes(self,path):
        reject_link(path)
        with path.open('rb') as f: data=f.read(MAX_BACKUP+1)
        if len(data)>MAX_BACKUP: raise AppError('BACKUP_LIMIT','File exceeds 20 MiB.')
        return data
    def read_text(self,path):
        self.app._enabled(); p=self._path(path)
        if p.suffix.lower() not in TEXT_TYPES:
            raise AppError('TEXT_PREVIEW_UNSUPPORTED','Not an editable text type.')
        data=self._bytes(p)
        if len(data)>262144: raise AppError('LIMIT_EXCEEDED','Text preview is limited to 256 KiB.')
        return {'path':str(p),'text':decode_text(data),'sha256':digest(data),'bytes':len(data)}
    def snapshot(self,path,action):
        self.app._enabled(); p=self._path(path); data=self._bytes(p)
        key=uuid.uuid4().hex
        item={'id':key,'path':str(p),'sha256':digest(data),'bytes':len(data),'time':now(),'action':action}
        with (self.folder/(key+'.bin')).open('xb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        atomic_json(self.folder/(key+'.json'),item)
        return item
    def _load(self,key):
        if not isinstance(key,str) or not re.fullmatch('[0-9a-f]{32}',key):
            raise AppError('INVALID_BACKUP','Choose a recorded backup identifier.')
        try:
            meta=self.folder/(key+'.json'); reject_link(meta)
            item=json.loads(meta.read_text(encoding='utf-8'))
            if not isinstance(item,dict) or item.get('id')!=key: raise ValueError('Invalid metadata')
            p=self._path(item['path'])
            data=self._bytes(self.folder/(key+'.bin'))
            if digest(data)!=item.get('sha256'): raise ValueError('Backup hash mismatch')
        except (OSError,ValueError,KeyError) as exc:
            raise AppError('BACKUP_DAMAGED','Backup metadata or content failed validation.') from exc
        return item,p,data
    def list_backups(self):
        self.app._enabled(); entries=[]; damaged=0
        files=sorted(self.folder.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
        for p in files[:100]:
            try: entries.append(self._load(p.stem)[0])
            except AppError: damaged+=1
        return {'backups':entries,'truncated':len(files)>100,'unreadable':damaged}
    def _replace(self,p,data,expected):
        if digest(self._bytes(p))!=expected:
            raise AppError('STALE_FILE','The file changed; refresh before saving or restoring.')
        temp=p.with_name('.guyu-version-'+uuid.uuid4().hex+'.tmp')
        try:
            with temp.open('xb') as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
            self.app._enabled(); self._path(p)
            if digest(self._bytes(p))!=expected:
                raise AppError('STALE_FILE','The file changed during preparation.')
            os.replace(temp,p)
        finally: temp.unlink(missing_ok=True)
    def save_text(self,path,text,expected_sha256,request_id):
        p=self._path(path); data=text_bytes(text)
        if p.suffix.lower() not in TEXT_TYPES: raise AppError('TEXT_PREVIEW_UNSUPPORTED','Not a text type.')
        def work():
            if digest(self._bytes(p))!=expected_sha256: raise AppError('STALE_FILE','Refresh before saving.')
            backup=self.snapshot(str(p),'preview_save')
            self._replace(p,data,expected_sha256)
            return {'path':str(p),'sha256':digest(data),'backup_id':backup['id']}
        return self.app._mutate('preview_save',{'path':str(p),'new':digest(data),'old':expected_sha256},request_id,work)
    def restore(self,backup_id,expected_sha256,request_id):
        def work():
            item,p,data=self._load(backup_id)
            if digest(self._bytes(p))!=expected_sha256: raise AppError('STALE_FILE','Refresh before restoring.')
            recovery=self.snapshot(str(p),'before_restore')
            self._replace(p,data,expected_sha256)
            return {'path':str(p),'sha256':digest(data),'restored_backup_id':backup_id,'recovery_backup_id':recovery['id']}
        return self.app._mutate('restore_backup',{'id':backup_id,'old':expected_sha256},request_id,work)
