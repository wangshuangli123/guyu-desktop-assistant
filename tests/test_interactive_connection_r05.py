"""The interactive connection must request human approval rather than suppress it."""
import importlib,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))

class InteractiveConnectionTests(unittest.TestCase):
    def test_real_client_arguments_preserve_sandbox_and_ask_for_approval(self):
        module=importlib.import_module('codex_connection')
        self.assertTrue(hasattr(module,'interactive_command'),'Interactive command builder missing')
        command=module.interactive_command('test prompt')
        self.assertEqual(command[command.index('--sandbox')+1],'read-only')
        self.assertEqual(command[command.index('--ask-for-approval')+1],'on-request')
        self.assertFalse(any('dangerously' in value for value in command))
        self.assertNotIn('exec',command)
        self.assertEqual(command[-1],'test prompt')
        self.assertTrue(Path(command[0]).is_file())
