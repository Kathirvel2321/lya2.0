"""Launch LYA with saved Windows credentials or an explicit session key."""
import argparse
import getpass
import os
from pathlib import Path
import runpy
import site
import sys

ROOT = Path(__file__).resolve().parents[1]


def configured_key():
    try:
        from security import bitwarden_secrets
        key = bitwarden_secrets.get_password('NVIDIA_API_KEY')
        if key:
            return key
    except Exception:
        pass
    return os.environ.get('NVIDIA_API_KEY', '').strip()


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


def gui_bitwarden_password():
    from PySide6.QtWidgets import QInputDialog, QLineEdit
    dialog = QInputDialog()
    dialog.setWindowTitle('Unlock Bitwarden for LYA')
    dialog.setLabelText('Enter your Bitwarden master password to unlock the CLI for this LYA session.\n'
                        'It is not saved. Cancel to use another configured key source.')
    dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
    dialog.setOkButtonText('Unlock')
    dialog.setCancelButtonText('Cancel')
    dialog.setMinimumWidth(460)
    try:
        return dialog.textValue() if dialog.exec() else ''
    finally:
        dialog.setTextValue('')


def unlock_bitwarden(gui):
    try:
        from security import bitwarden_secrets
        if not bitwarden_secrets.take_environment_session():
            if bitwarden_secrets.status() != 'locked':
                return False
            password = (gui_bitwarden_password() if gui else
                        getpass.getpass('Bitwarden master password (hidden; this session only): '))
            if not password:
                return False
            try:
                session = bitwarden_secrets.unlock(password)
            finally:
                password = ''
            if not session:
                launch_error('Bitwarden could not unlock. Check that the CLI is logged in; '
                             'LYA can still use the NVIDIA session prompt.', gui)
                return False
            bitwarden_secrets.set_session(session)
        if bitwarden_secrets.sync():
            return True
        bitwarden_secrets.clear()
        launch_error('Bitwarden could not sync. LYA will continue without vault credentials.', gui)
    except Exception:
        return False
    return False


def clear_bitwarden_session():
    try:
        from security import bitwarden_secrets
        bitwarden_secrets.clear()
    except Exception:
        pass


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
    parser.add_argument('--bitwarden', action='store_true',
                        help='Use the previous Bitwarden unlock flow for this session.')
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
    from security import provider_credentials
    saved = ""
    session_key = ""
    try:
        import riva.client
        if args.bitwarden:
            unlock_bitwarden(args.gui)
        else:
            os.environ.pop('BW_SESSION', None)
        saved = provider_credentials.read('NVIDIA_API_KEY')
        if not saved:
            session_key = configured_key()
        if not (saved or session_key):
            if args.gui and not args.bitwarden:
                from desktop.connections import ConnectionsDialog
                dialog = ConnectionsDialog(nvidia_model=args.nvidia_model)
                dialog.exec()
                saved = provider_credentials.read('NVIDIA_API_KEY')
            else:
                session_key = (gui_key() if args.gui else
                               getpass.getpass('NVIDIA key (hidden; this session only): ').strip())
    except (KeyboardInterrupt, EOFError):
        clear_bitwarden_session()
        if not args.gui:
            print('\nCancelled before LYA launch.')
        return 1
    except ImportError:
        clear_bitwarden_session()
        launch_error('NVIDIA speech client missing. Install requirements-nvidia-speech.txt in .venv-asr.', args.gui)
        return 1
    if not (saved or session_key):
        clear_bitwarden_session()
        if not args.gui:
            print('Key required. LYA not launched.')
        return 1
    if not args.gui:
        print('NVIDIA receives completed questions while private mode is off.')
        print('Turn private mode on BEFORE confidential speech. Wake/stop stay local.')
        print('Close existing LYA first; its single-instance lock prevents duplicate listeners.')
    # Saved keys are read where used. Only the legacy session fallback uses the environment.
    if session_key:
        os.environ['NVIDIA_API_KEY'] = session_key
    os.environ['LYA_NVIDIA_ASR'] = args.nvidia_model
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
        clear_bitwarden_session()
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
