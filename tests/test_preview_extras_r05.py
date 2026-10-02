"""Native image preview and visible backup catalog use real widgets and files."""
import importlib,sys,tempfile,tkinter as tk,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from guyu.core import Assistant,init_home
from guyu.commander_policy import CommanderPolicy
from guyu.versions import Versions

class ExtraPreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'temp'); self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name); init_home(self.home)
        self.app=Assistant(self.home); self.policy=CommanderPolicy(self.app)
        self.root=tk.Tk(); self.root.withdraw(); self.addCleanup(self.root.destroy)
        self.module=importlib.import_module('guyu.preview')
    def test_image_is_loaded_and_scaled_locally(self):
        self.assertTrue(hasattr(self.module,'ImagePreview'),'ImagePreview missing: expected RED')
        p=self.home/'workspace/test.png'; Image.new('RGB',(1800,1000),'white').save(p)
        view=self.module.ImagePreview(self.root,self.app,self.policy,str(p)); self.root.update()
        self.assertLessEqual(view.display_size[0],900)
        self.assertLessEqual(view.display_size[1],600)
    def test_backup_catalog_shows_recorded_file(self):
        self.assertTrue(hasattr(self.module,'BackupBrowser'),'BackupBrowser missing: expected RED')
        p=self.home/'workspace/test.txt'; p.write_text('old',encoding='utf-8')
        item=Versions(self.app,self.policy).snapshot(str(p),'test')
        view=self.module.BackupBrowser(self.root,self.app,self.policy); self.root.update()
        self.assertIn(item['id'],view.tree.get_children())
