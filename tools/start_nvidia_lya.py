"""Explicit cloud-voice launch with a hidden, session-only NVIDIA key."""
import argparse
import getpass
import os
from pathlib import Path
import runpy
import site
import sys

ROOT = Path(__file__).resolve().parents[1]


def saved_key():
    from security.api_credentials import nvidia_key
    try:
        return nvidia_key()
    except (ImportError, RuntimeError):
        # Keep the established session prompt available if the vault is unavailable.
        return ''


def gui_application():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName('LYA Desktop')
    app.setQuitOnLastWindowClosed(False)
    return app


def gui_key():
    from PySide6.QtWidgets import QInputDialog, QLineEdit
    dialog = QInputDialog()
    dialog.setWindowTitle('Connect LYA hearing')
    dialog.setLabelText('Paste your NVIDIA API key.\n'
                        'The key stays in this session and is not saved.\n\n'
                        'Completed questions go to NVIDIA while private mode is off.\n'
                        'Use private mode and text before confidential questions.')
    dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
    dialog.setOkButtonText('Start LYA')
    dialog.setCancelButtonText('Cancel')
    dialog.setMinimumWidth(460)
    dialog.setStyleSheet("""
        QDialog { background: #101b23; }
        QLabel { color: #e4edf1; font: 13px 'Segoe UI'; }
        QLineEdit { color: #e4edf1; background: #070f15; border: 1px solid #628b98;
                    border-radius: 6px; padding: 10px; }
        QPushButton { color: #e4edf1; background: #243a46; border: 1px solid #628b98;
                      border-radius: 6px; padding: 8px 18px; }
        QPushButton:focus { border: 2px solid #9de4ee; }
    """)
    try:
        return dialog.textValue().strip() if dialog.exec() else ''
    finally:
        dialog.setTextValue('')


def launch_error(message, gui):
    if gui:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(None, 'LYA could not start', message)
    else:
        print(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-nvidia-questions', action='store_true',
                        help='Allow captured non-private spoken questions to NVIDIA in this session.')
    parser.add_argument('--nvidia-model', choices=('parakeet', 'whisper', 'parakeet-ctc'), default='parakeet',
                        help='Primary hosted recognizer; at most one NVIDIA backup per question.')
    parser.add_argument('--show-panel', action='store_true')
    parser.add_argument('--reduced-motion', action='store_true')
    parser.add_argument('--gui', action='store_true', help='Use a native password dialog; suitable for pythonw.')
    args = parser.parse_args()
    if not args.allow_nvidia_questions:
        parser.error('Cloud voice is disabled without explicit session permission.')
    # Use separate hosted-speech dependencies; do not install them into the desktop.
    if Path(sys.prefix).resolve() != (ROOT / '.venv-asr').resolve():
        parser.error('Run with .venv-asr/Scripts/python.exe.')
    # Child tools use sys.executable too; give them the same existing desktop libraries.
    (Path(sys.prefix) / 'Lib/site-packages/lya_desktop.pth').write_text(
        'import site; site.addsitedir(' + repr(str(ROOT / '.venv-ui/Lib/site-packages')) + ')\n', encoding='utf-8')
    site.addsitedir(str(ROOT / '.venv-ui/Lib/site-packages'))
    sys.path.insert(0, str(ROOT / 'desktop'))
    sys.path.insert(0, str(ROOT))
    application = gui_application() if args.gui else None  # Keep Qt alive through desktop startup.
    if not args.gui:
        print('\nLYA ONLINE - PRIMARY MODEL: ' + args.nvidia_model.upper())
        print('Use the same NVIDIA API key from the successful tests.')
        print('Paste at the hidden prompt and press Enter; no characters will appear.')
    try:
        import riva.client
        key = os.environ.get('NVIDIA_API_KEY', '').strip()
        if not key:
            key = saved_key()
        if not key:
            key = gui_key() if args.gui else getpass.getpass('NVIDIA key (hidden; this session only): ').strip()
    except (KeyboardInterrupt, EOFError):
        if not args.gui:
            print('\nCancelled before LYA launch.')
        return 1
    except ImportError:
        launch_error('NVIDIA speech client missing. Install requirements-nvidia-speech.txt in .venv-asr.', args.gui)
        return 1
    if not key:
        if not args.gui:
            print('Key required. LYA not launched.')
        return 1
    if not args.gui:
        print('NVIDIA receives completed questions while private mode is off.')
        print('Turn private mode on BEFORE confidential speech. Wake/stop stay local.')
        print('Close existing LYA first; its single-instance lock prevents duplicate listeners.')
    os.environ['NVIDIA_API_KEY'] = key
    os.environ['LYA_NVIDIA_ASR'] = args.nvidia_model
    # The key is never written to disk or passed as a command-line argument.
    sys.argv = ['app.py', '--cloud-voice', '--cloud-asr', 'nvidia', '--skip-setup']
    if args.show_panel:
        sys.argv.append('--show-panel')
    if args.reduced_motion:
        sys.argv.append('--reduced-motion')
    try:
        runpy.run_path(str(ROOT / 'desktop/app.py'), run_name='__main__')
    except Exception:
        launch_error('LYA could not finish starting. Check the local desktop setup and try again.', args.gui)
        return 1
    finally:
        os.environ.pop('NVIDIA_API_KEY', None)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        # pythonw has no console for dependency/bootstrap failures. This native
        # fallback also works when Qt itself could not be imported.
        if '--gui' in sys.argv and os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,
                'LYA could not start. Check the local setup in desktop/README.md and try again.',
                'LYA startup', 0x10)
            raise SystemExit(1)
        raise
