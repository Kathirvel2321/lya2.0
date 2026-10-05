"""Run desktop voice regressions with synthetic stores and all live I/O disabled."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'desktop')]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'


def main():
    from cryptography.fernet import Fernet
    from brain.workflow import Brain
    from security import vault
    with tempfile.TemporaryDirectory(prefix='lya-ui-check-') as folder:
        def isolated_brain(*args, **kwargs):
            kwargs.update(client=Mock(side_effect=AssertionError('Unexpected model request')),
                          db_path=Path(folder) / 'synthetic.db.enc', researcher=None)
            return Brain(*args, **kwargs)
        with patch.dict(os.environ, {'LYA_DATA_DIR': folder, 'LYA_COMMAND_ASR': 'vosk', 'LYA_MICROPHONE': ''}), \
             patch.object(vault, '_F', Fernet(Fernet.generate_key())), \
             patch('brain.workflow.Brain', side_effect=isolated_brain), \
             patch('brain.research.default_researcher', return_value=None), \
             patch('desktop.setup_speech.SetupSpeech.say'), \
             patch('desktop.setup_speech.SetupSpeech.prewarm'), \
             patch('winsound.PlaySound'), \
             patch('sounddevice.RawInputStream', side_effect=AssertionError('Unexpected microphone input')):
            import check_ui
            import check_experience
            loader = unittest.defaultTestLoader
            suite = unittest.TestSuite([loader.loadTestsFromTestCase(check_ui.InterfaceChecks),
                                       loader.loadTestsFromTestCase(check_experience.ExperienceChecks)])
            result = unittest.TextTestRunner(verbosity=1).run(suite)
            return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
