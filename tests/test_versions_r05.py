"""Version restore stays inside the already approved workspace."""
import importlib, json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import Assistant, init_home
from guyu.safety import AppError, digest
from guyu.commander_policy import CommanderPolicy

class VersionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'temp'); self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name); init_home(self.home)
        self.app=Assistant(self.home); self.policy=CommanderPolicy(self.app)
        try: cls=importlib.import_module('guyu.versions').Versions
        except ImportError: self.fail('Versions implementation missing: expected RED')
        self.store=cls(self.app,self.policy)
        self.path=self.home/'workspace/note.txt'; self.path.write_text('original',encoding='utf-8')
    def test_save_preview_creates_backup(self):
        info=self.store.read_text(str(self.path))
        result=self.store.save_text(str(self.path),'中文修改',info['sha256'],'save_test_001')
        self.assertEqual(self.path.read_text(encoding='utf-8'),'中文修改')
        self.assertEqual(self.store.list_backups()['backups'][0]['id'],result['backup_id'])
    def test_stale_save_rejected(self):
        old=self.store.read_text(str(self.path))['sha256']
        self.path.write_text('other editor',encoding='utf-8')
        with self.assertRaisesRegex(AppError,'STALE_FILE'):
            self.store.save_text(str(self.path),'bad',old,'stale_test_001')
    def test_restore_checks_current_and_retains_recovery_version(self):
        item=self.store.snapshot(str(self.path),'test')
        self.path.write_text('changed',encoding='utf-8')
        result=self.store.restore(item['id'],digest(b'changed'),'restore_test_001')
        self.assertEqual(self.path.read_text(encoding='utf-8'),'original')
        self.assertTrue(result['recovery_backup_id'])
        self.assertEqual(len(self.store.list_backups()['backups']),2)
    def test_restore_refuses_unexpected_current_content(self):
        item=self.store.snapshot(str(self.path),'test')
        self.path.write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(AppError,'STALE_FILE'):
            self.store.restore(item['id'],digest(b'original'),'restore_stale_001')
    def test_pause_prevents_save_and_restore(self):
        item=self.store.snapshot(str(self.path),'test'); self.app.pause()
        with self.assertRaises(AppError): self.store.restore(item['id'],digest(b'original'),'pause_restore_001')
        with self.assertRaises(AppError): self.store.save_text(str(self.path),'x',digest(b'original'),'pause_save_001')
    def test_restore_is_idempotent(self):
        item=self.store.snapshot(str(self.path),'test')
        one=self.store.restore(item['id'],digest(b'original'),'repeat_restore_001')
        two=self.store.restore(item['id'],digest(b'original'),'repeat_restore_001')
        self.assertEqual(one,two)
    def test_invalid_backup_identifier(self):
        with self.assertRaises(AppError): self.store.restore('invalid',digest(b'original'),'invalid_restore_001')
    def test_binary_not_editable_as_text(self):
        p=self.home/'workspace/data.bin'; p.write_bytes(bytes([0,255,23]))
        with self.assertRaises(AppError): self.store.read_text(str(p))

if __name__=='__main__': unittest.main()
