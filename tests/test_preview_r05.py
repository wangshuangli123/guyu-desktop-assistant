"""Exercise a real local preview widget without launching user files."""
import importlib, sys, tempfile, tkinter as tk, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import Assistant,init_home
from guyu.commander_policy import CommanderPolicy
from guyu.safety import AppError

class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'temp'); self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name); init_home(self.home)
        self.app=Assistant(self.home); self.policy=CommanderPolicy(self.app)
        self.root=tk.Tk(); self.root.withdraw(); self.addCleanup(self.root.destroy)
        try: self.cls=importlib.import_module('guyu.preview').TextPreview
        except ImportError: self.fail('Preview implementation missing: expected RED')
        self.file=self.home/'workspace/test.txt'; self.file.write_text('原始内容',encoding='utf-8')
    def test_load_edit_save_and_backup(self):
        panel=self.cls(self.root,self.app,self.policy,str(self.file)); self.root.update()
        self.assertEqual(panel.text.get('1.0','end-1c'),'原始内容')
        panel.text.delete('1.0','end'); panel.text.insert('1.0','预览修改')
        result=panel.save()
        self.assertEqual(self.file.read_text(encoding='utf-8'),'预览修改')
        self.assertTrue(result['backup_id'])
    def test_external_edit_is_not_silently_overwritten(self):
        panel=self.cls(self.root,self.app,self.policy,str(self.file))
        self.file.write_text('external change',encoding='utf-8')
        with self.assertRaisesRegex(AppError,'STALE_FILE'): panel.save()
    def test_reload_updates_content_after_conflict(self):
        panel=self.cls(self.root,self.app,self.policy,str(self.file))
        self.file.write_text('new external version',encoding='utf-8')
        self.assertTrue(hasattr(panel,'reload'),'Reload action missing: expected RED')
        panel.reload()
        self.assertEqual(panel.text.get('1.0','end-1c'),'new external version')
    def test_dirty_state_clears_after_save(self):
        panel=self.cls(self.root,self.app,self.policy,str(self.file))
        self.assertTrue(hasattr(panel,'is_dirty'),'Dirty detection missing: expected RED')
        self.assertFalse(panel.is_dirty())
        panel.text.insert('end',' changed'); self.assertTrue(panel.is_dirty())
        panel.save(); self.assertFalse(panel.is_dirty())
