"""Conservative validation; this is not an operating-system sandbox."""
from pathlib import Path, PureWindowsPath
import hashlib
import json
import os
import stat
import re
import uuid

MAX_BYTES = 262144
TEXT_SUFFIXES = {'.txt', '.md', '.json', '.csv', '.log'}
RESERVED = {'CON','PRN','AUX','NUL','CONIN$','CONOUT$'} | {f'{p}{i}' for p in ('COM','LPT') for i in range(1,10)}

class AppError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(f'{code}: {message}')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def atomic_json(path, data):
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with tmp.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)

def text_bytes(text):
    if not isinstance(text,str) or '\x00' in text:
        raise AppError('INVALID_TEXT','Text must be a string without NUL.')
    try:
        data = text.encode('utf-8')
    except UnicodeEncodeError as exc:
        raise AppError('INVALID_TEXT','Invalid Unicode.') from exc
    if len(data) > MAX_BYTES:
        raise AppError('LIMIT_EXCEEDED','Maximum text size is 256 KiB.')
    return data

def decode_text(data):
    try:
        return data.decode('utf-16') if data[:2] in (b'\xff\xfe',b'\xfe\xff') else data.decode('utf-8-sig')
    except UnicodeError as exc:
        raise AppError('ENCODING_UNSUPPORTED','Use UTF-8 or BOM-marked UTF-16.') from exc

def request_key(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{6,80}',value):
        raise AppError('INVALID_REQUEST_ID','Use 6-80 letters, digits, underscore or hyphen.')
    return value

def reject_link(path):
    try:
        st = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0) & 0x400:
        raise AppError('LINK_DENIED','Symlinks and reparse points are forbidden.')
    if stat.S_ISREG(st.st_mode) and st.st_nlink > 1:
        raise AppError('LINK_DENIED','Hard-linked files are forbidden.')

def safe_path(root, relative, directory=False):
    reject_link(root)
    if directory and relative in ('','.'):
        return root
    if not isinstance(relative,str) or not relative or len(relative)>220:
        raise AppError('INVALID_PATH','Supply a short relative workspace path.')
    win = PureWindowsPath(relative)
    if win.drive or win.root or Path(relative).is_absolute():
        raise AppError('SCOPE_DENIED','Absolute and network paths are forbidden.')
    parts = relative.replace('\\','/').split('/')
    for part in parts:
        if part in ('','.','..') or part.rstrip(' .') != part:
            raise AppError('SCOPE_DENIED','Traversal or ambiguous name.')
        if any(ord(c)<32 or c in '<>:"|?*' for c in part):
            raise AppError('INVALID_PATH','Invalid path characters.')
        if part.split('.')[0].upper() in RESERVED:
            raise AppError('INVALID_PATH','Reserved Windows device name.')
    candidate = root.joinpath(*parts)
    current = root
    for part in parts:
        current = current / part
        reject_link(current)
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise AppError('SCOPE_DENIED','Path is outside the workspace.')
    if not directory and candidate.suffix.lower() not in TEXT_SUFFIXES:
        raise AppError('FILE_TYPE_DENIED','Only .txt .md .json .csv .log are enabled.')
    return candidate
