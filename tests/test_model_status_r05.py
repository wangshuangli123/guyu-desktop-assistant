"""Display separately verified local read/write results without claiming web access."""
import sys,tempfile,tkinter as tk,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from guyu.core import init_home
from guyu.safety import atomic_json
from guyu.ui import Panel

class ModelStatusTests(unittest.TestCase):
    def test_verified_write_report_is_shown_but_web_remains_unverified(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'temp') as tmp:
            home=Path(tmp); init_home(home)
            atomic_json(home/'evidence/model-read-report.json',{'result':'MODEL_READ_E2E_VERIFIED'})
            atomic_json(home/'evidence/model-write-report.json',{'result':'MODEL_FILE_E2E_VERIFIED'})
            root=tk.Tk(); root.withdraw()
            try:
                panel=Panel(root,home)
                self.assertIn('读写已通过',panel.model_var.get())
                self.assertIn('网页：未验证',panel.model_var.get())
            finally: root.destroy()
    def test_write_approval_requirement_does_not_erase_read_success(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'temp') as tmp:
            home=Path(tmp); init_home(home)
            atomic_json(home/'evidence/model-read-report.json',{'result':'MODEL_READ_E2E_VERIFIED'})
            atomic_json(home/'evidence/model-write-report.json',{'result':'BLOCKED_CLIENT_APPROVAL_REQUIRED'})
            root=tk.Tk(); root.withdraw()
            try:
                panel=Panel(root,home)
                self.assertIn('只读已通过',panel.model_var.get())
                self.assertIn('写入待本机确认',panel.model_var.get())
            finally: root.destroy()
