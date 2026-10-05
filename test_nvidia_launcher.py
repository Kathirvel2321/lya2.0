"""Launcher checks with fake keys, temporary paths and no live desktop/audio."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from tools import start_nvidia_lya as launcher


class NvidiaLauncherTests(unittest.TestCase):
    def setUp(self):
        self.read_saved_key = launcher.saved_key
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.prefix = self.root / '.venv-asr'
        (self.prefix / 'Lib/site-packages').mkdir(parents=True)
        riva = types.ModuleType('riva')
        riva.client = types.ModuleType('riva.client')
        for context in (patch.object(launcher, 'ROOT', self.root),
                        patch.object(sys, 'prefix', str(self.prefix)),
                        patch.object(sys, 'path', list(sys.path)),
                        patch.dict(sys.modules, {'riva': riva, 'riva.client': riva.client}),
                        patch.dict(os.environ, {'NVIDIA_API_KEY': ''}),
                        patch.object(launcher, 'saved_key', return_value='')):
            context.start()
            self.addCleanup(context.stop)
        desktop_patch = patch.object(launcher.runpy, 'run_path')
        self.desktop = desktop_patch.start()
        self.addCleanup(desktop_patch.stop)

    def run_launcher(self, gui=True):
        argv = ['start_nvidia_lya.py', '--allow-nvidia-questions', '--show-panel']
        if gui:
            argv.append('--gui')
        with patch.object(sys, 'argv', argv):
            return launcher.main()

    def test_gui_key_reaches_desktop_only_in_session_environment(self):
        def desktop(*args, **kwargs):
            self.assertEqual(os.environ['NVIDIA_API_KEY'], 'fake-key')
            self.assertNotIn('fake-key', sys.argv)
            self.assertNotIn('--gui', sys.argv)
            self.assertIn('--cloud-voice', sys.argv)
        self.desktop.side_effect = desktop
        with patch.object(launcher, 'gui_key', return_value='fake-key'), \
             patch.object(launcher.getpass, 'getpass', side_effect=AssertionError('Console input')):
            self.assertEqual(self.run_launcher(), 0)
        self.desktop.assert_called_once()
        self.assertNotIn('NVIDIA_API_KEY', os.environ)
        for file in self.root.rglob('*'):
            if file.is_file():
                self.assertNotIn(b'fake-key', file.read_bytes())

    def test_cancel_exits_before_desktop_launch(self):
        with patch.object(launcher, 'gui_key', return_value=''), \
             patch.object(launcher.getpass, 'getpass', side_effect=AssertionError('Console input')):
            self.assertEqual(self.run_launcher(), 1)
        self.desktop.assert_not_called()

    def test_saved_windows_key_skips_input_and_remains_out_of_arguments(self):
        def desktop(*args, **kwargs):
            self.assertEqual(os.environ['NVIDIA_API_KEY'], 'fake-saved-key')
            self.assertNotIn('fake-saved-key', sys.argv)
        self.desktop.side_effect = desktop
        with patch.object(launcher, 'saved_key', return_value='fake-saved-key'), \
             patch.object(launcher, 'gui_key') as prompt:
            self.assertEqual(self.run_launcher(), 0)
            prompt.assert_not_called()
        self.assertNotIn('NVIDIA_API_KEY', os.environ)

    def test_saved_key_access_failure_keeps_the_existing_prompt(self):
        from security import api_credentials
        with patch.object(api_credentials, 'nvidia_key', side_effect=RuntimeError('fake-private-detail')):
            self.assertEqual(self.read_saved_key(), '')

    def test_existing_session_key_skips_prompt(self):
        with patch.dict(os.environ, {'NVIDIA_API_KEY': 'fake-existing-key'}), \
             patch.object(launcher, 'gui_key') as prompt:
            self.assertEqual(self.run_launcher(), 0)
            prompt.assert_not_called()

    def test_desktop_error_removes_key_and_does_not_display_exception_payload(self):
        self.desktop.side_effect = RuntimeError('fake-key must not be displayed')
        with patch.object(launcher, 'gui_key', return_value='fake-key'), \
             patch.object(launcher, 'launch_error') as error:
            self.assertEqual(self.run_launcher(), 1)
            self.assertNotIn('fake-key', error.call_args.args[0])
        self.assertNotIn('NVIDIA_API_KEY', os.environ)

    def test_gui_password_is_masked_and_cleared_on_accept_and_cancel(self):
        from PySide6.QtWidgets import QLineEdit
        for accepted in (0, 1):
            dialog = Mock()
            dialog.exec.return_value = accepted
            dialog.textValue.return_value = ' fake-key '
            with patch('PySide6.QtWidgets.QInputDialog', return_value=dialog):
                self.assertEqual(launcher.gui_key(), 'fake-key' if accepted else '')
            dialog.setTextEchoMode.assert_called_once_with(QLineEdit.EchoMode.Password)
            dialog.setTextValue.assert_called_once_with('')

    def test_console_diagnostic_mode_keeps_hidden_input(self):
        with patch.object(launcher.getpass, 'getpass', return_value='fake-console-key') as prompt, \
             patch.object(launcher, 'gui_key') as gui, patch('builtins.print'):
            self.assertEqual(self.run_launcher(gui=False), 0)
            prompt.assert_called_once()
            gui.assert_not_called()

    def test_desktop_main_reuses_existing_qt_application(self):
        desktop_dir = Path(__file__).resolve().parent / 'desktop'
        sys.path.insert(0, str(desktop_dir))
        import app
        application = Mock()
        application.exec.return_value = 0
        lock = Mock()
        lock.tryLock.return_value = True
        with patch.object(sys, 'argv', ['app.py', '--no-voice', '--skip-setup']), \
             patch.object(app, 'QApplication') as qt, \
             patch.object(app, 'QLockFile', return_value=lock), \
             patch('experience.OrbDesktop') as desktop:
            qt.instance.return_value = application
            self.assertEqual(app.main(), 0)
            qt.assert_not_called()
            desktop.return_value.start_voice.assert_not_called()
            desktop.assert_called_once_with(application, False)


if __name__ == '__main__':
    unittest.main()
