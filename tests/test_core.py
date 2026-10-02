import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

class CoreTests(unittest.TestCase):
    def setUp(self):
        try:
            self.mod = importlib.import_module('guyu.core')
        except ModuleNotFoundError:
            self.fail('Implementation missing: guyu.core (expected RED before coding)')
        (ROOT / 'temp').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'temp')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.mod.init_home(self.home)
        self.app = self.mod.Assistant(self.home)

    def denied(self, function, *args):
        with self.assertRaises(self.mod.AppError):
            function(*args)

    def create(self):
        return self.app.create_text('中文测试.txt', '谷雨🙂\n测试', 'request_001')

    def test_create_and_read_chinese(self):
        result = self.create()
        self.assertEqual(self.app.read_text('中文测试.txt')['text'], '谷雨🙂\n测试')
        self.assertEqual(result['sha256'], hashlib.sha256('谷雨🙂\n测试'.encode()).hexdigest())

    def test_no_silent_overwrite(self):
        self.create()
        self.denied(self.app.create_text, '中文测试.txt', 'changed', 'request_002')
        self.assertEqual(self.app.read_text('中文测试.txt')['text'], '谷雨🙂\n测试')

    def test_same_request_returns_same_result(self):
        self.assertEqual(self.create(), self.create())
        self.assertEqual(len(list((self.home/'workspace').iterdir())), 1)

    def test_same_request_different_payload_rejected(self):
        self.create()
        self.denied(self.app.create_text, 'other.txt', 'x', 'request_001')
        self.assertFalse((self.home/'workspace/other.txt').exists())

    def test_parent_path_rejected(self):
        self.denied(self.app.create_text, '../escape.txt', 'x', 'request_001')
        self.assertFalse((self.home/'escape.txt').exists())

    def test_windows_parent_path_rejected(self):
        self.denied(self.app.create_text, '..\\escape.txt', 'x', 'request_001')

    def test_absolute_path_rejected(self):
        self.denied(self.app.read_text, str(self.home/'control.json'))

    def test_ads_rejected(self):
        self.denied(self.app.create_text, 'file.txt:stream', 'x', 'request_001')

    def test_reserved_names_rejected(self):
        for name in ['CON.txt', 'nul', 'LPT1.txt', 'AUX.json', 'foo. ', 'foo.txt.']:
            with self.subTest(name=name):
                self.denied(self.app.create_text, name, 'x', 'request_001')

    def test_executable_extensions_rejected(self):
        for name in ['a.exe','a.cmd','a.ps1','a.py','a.lnk','a.url']:
            with self.subTest(name=name):
                self.denied(self.app.create_text, name, 'x', 'request_001')

    def test_pause_blocks_new_writes(self):
        self.app.pause()
        self.denied(self.create)
        self.assertTrue(self.app.status()['paused'])
        self.assertFalse((self.home/'workspace/中文测试.txt').exists())

    def test_pause_keeps_status_available(self):
        self.app.pause()
        self.assertEqual(self.app.status()['web_e2e'], 'NOT_TESTED')

    def test_missing_control_fails_closed(self):
        (self.home/'runtime/control.json').unlink()
        self.denied(self.create)

    def test_corrupt_control_fails_closed(self):
        (self.home/'runtime/control.json').write_text('{broken', encoding='utf-8')
        self.denied(self.create)

    def test_replace_requires_hash_and_creates_backup(self):
        original = self.create()
        changed = self.app.replace_text('中文测试.txt', '更新后的内容', original['sha256'], 'request_002')
        self.assertEqual(self.app.read_text('中文测试.txt')['text'], '更新后的内容')
        self.assertEqual((self.home/changed['backup']).read_text(encoding='utf-8'), '谷雨🙂\n测试')

    def test_stale_hash_rejected(self):
        self.create()
        self.denied(self.app.replace_text, '中文测试.txt', 'x', '0'*64, 'request_002')
        self.assertEqual(self.app.read_text('中文测试.txt')['text'], '谷雨🙂\n测试')

    def test_large_input_rejected(self):
        self.denied(self.app.create_text, 'big.txt', 'x'*300000, 'request_001')

    def test_nul_text_rejected(self):
        self.denied(self.app.create_text, 'x.txt', 'a\0b', 'request_001')

    def test_search_and_listing(self):
        self.create()
        self.assertEqual(self.app.search_files('中文')['files'], ['中文测试.txt'])
        self.assertEqual(self.app.list_files()['entries'][0]['name'], '中文测试.txt')

    def test_hardlinks_rejected(self):
        outside = self.home/'outside.txt'
        outside.write_text('private',encoding='utf-8')
        os.link(outside,self.home/'workspace/linked.txt')
        self.denied(self.app.read_text,'linked.txt')
        self.denied(self.app.replace_text,'linked.txt','x',hashlib.sha256(b'private').hexdigest(),'request_003')
        self.assertEqual(outside.read_text(), 'private')

    def test_audit_does_not_store_text_payload(self):
        self.app.create_text('a.txt', 'PRIVATE_PAYLOAD_ABC', 'request_001')
        self.assertNotIn('PRIVATE_PAYLOAD_ABC', json.dumps(self.app.recent_events()))
        self.assertGreater(len(self.app.recent_events()), 0)

    def test_id_validation(self):
        self.denied(self.app.create_text, 'a.txt', 'x', '../bad')

if __name__ == '__main__':
    unittest.main(verbosity=2)
