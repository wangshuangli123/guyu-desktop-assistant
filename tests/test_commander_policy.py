"""Regression tests for the local adapter's boundaries."""
import os, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import Assistant, init_home
from guyu.safety import AppError, atomic_json
from guyu.commander_policy import CommanderPolicy
from guyu.commander_backend import backend_parameters

class CommanderPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'temp')
        self.home = Path(self.temp.name)
        init_home(self.home)
        self.app = Assistant(self.home)
        self.policy = CommanderPolicy(self.app)
    def tearDown(self):
        self.temp.cleanup()
    def test_absolute_inside_workspace_accepted(self):
        p = self.home/'workspace/code.py'
        self.assertEqual(self.policy.path(str(p)),str(p))
    def test_parent_and_absolute_outside_rejected(self):
        for path in ['../secrets.txt',str(self.home/'outside.txt'),'C:\\Windows\\win.ini']:
            with self.subTest(path=path), self.assertRaises(AppError):
                self.policy.path(path)
    def test_prefix_sibling_rejected(self):
        with self.assertRaises(AppError):
            self.policy.path(str(self.home/'workspace_other/test.txt'))
    def test_model_cannot_change_configuration(self):
        with self.assertRaises(AppError):
            self.policy.validate('set_config_value',{'key':'allowedDirectories','value':[]})
    def test_model_cannot_forge_ui_origin(self):
        with self.assertRaises(AppError):
            self.policy.validate('read_file',{'path':'test.txt','origin':'ui'})
    def test_terminal_disabled_by_default(self):
        with self.assertRaises(AppError):
            self.policy.validate('start_process',{'command':'echo ok','timeout_ms':1000})
    def test_corrupt_terminal_setting_fails_closed(self):
        self.policy.control.write_text('[]',encoding='utf-8')
        self.assertFalse(self.policy.terminal_enabled())
    def test_non_owned_pid_rejected(self):
        with self.assertRaises(AppError):
            self.policy.validate('force_terminate',{'pid':12345})
    def test_owned_process_can_be_stopped_when_paused(self):
        self.policy.owned_pids.add(12345)
        self.app.pause()
        self.assertEqual(self.policy.validate('force_terminate',{'pid':12345})['pid'],12345)
    def test_paused_read_rejected(self):
        self.app.pause()
        with self.assertRaises(AppError):
            self.policy.validate('read_file',{'path':'test.txt'})
    def test_all_paths_in_batch_are_checked(self):
        with self.assertRaises(AppError):
            self.policy.validate('read_multiple_files',{'paths':['ok.txt','../outside.txt']})
    def test_remote_url_rejected(self):
        with self.assertRaises(AppError):
            self.policy.validate('read_file',{'path':'https://example.com','isUrl':True})
    def test_backend_isolated_and_telemetry_off(self):
        import json
        params = backend_parameters(ROOT,self.home)
        self.assertEqual(params.env['DESKTOP_COMMANDER_DISABLE_TELEMETRY'],'1')
        self.assertEqual(params.env['USERPROFILE'],str(self.home/'runtime/commander-home'))
        self.assertNotIn('OPENAI_API_KEY',params.env)
        cfg = json.loads((self.home/'runtime/commander-home/.claude-server-commander/config.json').read_text())
        self.assertFalse(cfg['telemetryEnabled'])
        self.assertEqual(cfg['allowedDirectories'],[str(self.home/'workspace')])
        self.assertIn('format',cfg['blockedCommands'])
    def test_pid_tracking_uses_successful_start_only(self):
        from mcp import types
        result = types.CallToolResult(content=[types.TextContent(type='text',text='Process started with PID 24680')])
        self.policy.track_result('start_process',result)
        self.assertIn(24680,self.policy.owned_pids)
    def test_source_pdf_path_cannot_escape(self):
        with self.assertRaises(AppError):
            self.policy.validate('write_pdf',{'path':'a.pdf','outputPath':'b.pdf',
                'content':[{'type':'insert','pageIndex':0,'sourcePdfPath':'../private.pdf'}]})

if __name__=='__main__':
    unittest.main()
