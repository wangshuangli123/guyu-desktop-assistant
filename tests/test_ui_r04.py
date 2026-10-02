"""R04 panel truthfulness and terminal state regression."""
import sys, tempfile, tkinter as tk, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import init_home
from guyu.safety import atomic_json
from guyu.ui import Panel

class R04PanelTests(unittest.TestCase):
    def test_terminal_state_is_visible_and_refreshes(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'temp') as tmp:
            home = Path(tmp)
            init_home(home)
            root = tk.Tk()
            root.withdraw()
            try:
                panel = Panel(root,home)
                self.assertTrue(hasattr(panel,'terminal_var'),'R04 terminal status is missing')
                self.assertIn('关闭',panel.terminal_var.get())
                atomic_json(home/'runtime/commander-control.json',{'version':1,'terminal_enabled':True})
                panel.refresh()
                self.assertIn('开启',panel.terminal_var.get())
            finally:
                root.destroy()

    def test_account_limit_is_not_reported_as_a_tool_failure(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'temp') as tmp:
            home = Path(tmp)
            init_home(home)
            root = tk.Tk()
            root.withdraw()
            try:
                panel = Panel(root,home)
                self.assertTrue(hasattr(panel,'model_var'),'Model verification status is missing')
                atomic_json(home/'evidence/model-read-report.json',{'result':'BLOCKED_ACCOUNT_USAGE_LIMIT'})
                panel.refresh()
                self.assertIn('额度',panel.model_var.get())
                self.assertIn('未验证',panel.model_var.get())
            finally:
                root.destroy()
