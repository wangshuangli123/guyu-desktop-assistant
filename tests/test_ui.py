import importlib
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import init_home

class PanelTests(unittest.TestCase):
    def test_local_pause_and_resume_are_visible(self):
        try:
            module = importlib.import_module('guyu.ui')
        except ModuleNotFoundError:
            self.fail('Control panel missing: expected RED before implementation')
        with tempfile.TemporaryDirectory(dir=ROOT/'temp') as tmp:
            home = Path(tmp)
            init_home(home)
            root = tk.Tk()
            root.withdraw()
            try:
                panel = module.Panel(root,home)
                entries = [child for group in panel.winfo_children() for child in group.winfo_children() if child.winfo_class()=="TEntry"]
                self.assertEqual(len(entries),1)
                self.assertEqual(entries[0].get(),str(home/"workspace"))
                panel.pause()
                self.assertIn('已暂停',panel.status_var.get())
                panel.resume()
                self.assertIn('可用',panel.status_var.get())
            finally:
                root.destroy()
