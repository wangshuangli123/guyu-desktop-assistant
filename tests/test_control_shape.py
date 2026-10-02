import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import Assistant, init_home
from guyu.safety import AppError

class ControlShapeTests(unittest.TestCase):
    def test_non_object_control_is_treated_as_paused(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'temp') as tmp:
            home = Path(tmp)
            init_home(home)
            app = Assistant(home)
            for value in ([],None,'enabled',42):
                with self.subTest(value=value):
                    (home/'runtime/control.json').write_text(json.dumps(value),encoding='utf-8')
                    with self.assertRaises(AppError) as caught:
                        app.create_text('blocked.txt','must not write','shape_test_001')
                    self.assertEqual(caught.exception.code,'PAUSED')
                    self.assertTrue(app.status()['paused'])
                    self.assertFalse((home/'workspace/blocked.txt').exists())
