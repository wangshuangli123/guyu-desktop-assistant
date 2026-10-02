"""Do not allow unreviewed PDF rendering to bypass file/terminal permissions."""
import sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import Assistant, init_home
from guyu.commander_policy import CommanderPolicy
from guyu.safety import AppError

class PdfGateTests(unittest.TestCase):
    def test_unverified_pdf_renderer_is_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'temp') as tmp:
            home = Path(tmp)
            init_home(home)
            policy = CommanderPolicy(Assistant(home))
            with self.assertRaisesRegex(AppError,'PDF_NOT_ENABLED'):
                policy.validate('write_pdf',{'path':'test.pdf','content':'# Test'})
