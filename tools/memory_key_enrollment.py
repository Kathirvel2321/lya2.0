"""Explicit native owner key-custody window; no automatic startup or memory cutover."""
import argparse
import os
from pathlib import Path
import secrets
import sys
import time
import webbrowser

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QDialog,QLabel,QLineEdit,QPushButton,QVBoxLayout
from brain import memory_owner_keys as keys
from security.approval import Challenge
from security.policy import Session


class EnrollmentWindow(QDialog):
    def __init__(self,directory,*,db_path=None):
        super().__init__();self.directory,self.db_path=directory,db_path
        self.session=None;self.ceremony=None;self.challenge=None;self.pending=None
        self.setWindowTitle('LYA · Recovery-key custody');self.setMinimumWidth(560)
        layout=QVBoxLayout(self)
        self.status=QLabel('Use your existing LYA owner passkey. Save the new unlock in Bitwarden and a separate offline copy. '
            'No memory data is uploaded and production memory stays disconnected.')
        self.status.setWordWrap(True);layout.addWidget(self.status)
        self.unlock=QLineEdit();self.unlock.setReadOnly(True);self.unlock.setEchoMode(QLineEdit.EchoMode.Password)
        self.unlock.setAccessibleName('Private recovery unlock key');layout.addWidget(self.unlock)
        self.reveal=QPushButton('Reveal / hide unlock key');self.reveal.clicked.connect(self.toggle_key);layout.addWidget(self.reveal)
        self.reference=QLabel('');self.reference.setWordWrap(True);layout.addWidget(self.reference)
        self.vault=QLineEdit();self.vault.setEchoMode(QLineEdit.EchoMode.Password)
        self.vault.setPlaceholderText('Read the unlock back from your saved Bitwarden note')
        self.vault.setAccessibleName('Unlock retrieved from Bitwarden');layout.addWidget(self.vault)
        self.offline=QLineEdit();self.offline.setEchoMode(QLineEdit.EchoMode.Password)
        self.offline.setPlaceholderText('Read the unlock back from the separate offline copy')
        self.offline.setAccessibleName('Unlock retrieved from offline copy');layout.addWidget(self.offline)
        self.prepare_button=QPushButton('Verify owner and prepare / reopen keys')
        self.prepare_button.clicked.connect(lambda:self.start('prepare'));layout.addWidget(self.prepare_button)
        self.confirm_button=QPushButton('Verify owner and confirm both saved copies')
        self.confirm_button.clicked.connect(lambda:self.start('confirm'));layout.addWidget(self.confirm_button)
        self.confirm_button.setEnabled(False)
        self.timer=QTimer(self);self.timer.setInterval(100);self.timer.timeout.connect(self.poll)

    def toggle_key(self):
        mode=QLineEdit.EchoMode
        self.unlock.setEchoMode(mode.Normal if self.unlock.echoMode()==mode.Password else mode.Password)

    def start(self,operation):
        if self.ceremony is not None:return
        self.pending=operation;self.unlock.setEchoMode(QLineEdit.EchoMode.Password)
        try:
            from storage import store
            if store.get_owner_passkey(self.db_path) is None:raise PermissionError('An existing owner passkey is required.')
            self._authenticate()
        except Exception:self.fail()

    def _authenticate(self):
        from security.passkeys import PasskeyCeremony
        self.prepare_button.setEnabled(False);self.confirm_button.setEnabled(False)
        if self.session is None or self.session.verified_until<=time.time():
            self.challenge=None;self.ceremony=PasskeyCeremony(db_path=self.db_path)
        else:
            parameters=keys.PREPARE if self.pending=='prepare' else keys.CONFIRM
            self.challenge=Challenge(secrets.token_urlsafe(32),self.session,'memory_backup',parameters,time.monotonic()+120)
            self.ceremony=PasskeyCeremony(db_path=self.db_path,approval=self.challenge,
                approval_valid=lambda:self.isVisible() and self.pending is not None)
        self.status.setText('Approve the exact recovery-key action in your browser using your existing phone passkey. '
            'Keep passwords and recovery keys out of chat.')
        if not webbrowser.open(self.ceremony.url):raise OSError('Browser unavailable.')
        self.timer.start()

    def poll(self):
        if self.ceremony is None or not self.ceremony.done.is_set():return
        ceremony=self.ceremony;self.ceremony=None;self.timer.stop()
        result=ceremony.result;ceremony.close()
        try:
            if self.challenge is None:
                if type(result) is not Session or result.role!='admin' or result.verified_until<=time.time():raise PermissionError()
                self.session=result;self._authenticate();return
            if type(result) is not Challenge or result!=self.challenge:raise PermissionError()
            if self.pending=='prepare':
                view=keys.prepare(self.directory,result,db_path=self.db_path)
                self.unlock.setText(view.unlock_key.decode('ascii'))
                self.reference.setText('Recovery reference: '+view.lineage+'\nCapsule fingerprint: '+view.capsule_sha256+
                    '\nKeep this reference with the owner-held unlock. It does not prove today\'s latest memory state.')
                self.status.setText('Keys are protected on this Windows account. Reveal the unlock only to save it privately in '
                    'Bitwarden and a separate offline copy, then retrieve each copy into the two fields. '
                    'Custody already acknowledged.' if view.custody_acknowledged else
                    'Keys are protected on this Windows account. Save the unlock privately in Bitwarden and a separate offline copy, '
                    'then retrieve each saved copy into its field. Closing this window keeps the pending protected keys for a fresh verified reopening.')
            else:
                keys.confirm(self.directory,result,self.vault.text(),self.offline.text(),db_path=self.db_path)
                self.unlock.clear();self.vault.clear();self.offline.clear()
                self.status.setText('Both retrieved copies matched and your custody acknowledgement is protected locally. '
                    'External survival has not been independently inspected. Production memory remains disconnected; '
                    'the server installation and private recovery rehearsal are separate steps.')
            self.pending=None;self.prepare_button.setEnabled(True);self.confirm_button.setEnabled(bool(self.unlock.text()))
        except Exception:self.fail()

    def fail(self):
        self.timer.stop()
        if self.ceremony is not None:self.ceremony.close();self.ceremony=None
        self.pending=None;self.session=None;self.challenge=None
        self.unlock.clear();self.vault.clear();self.offline.clear()
        self.status.setText('Setup stopped. Existing protected files were preserved. Verify the same owner and retry; '
            'do not delete keys or paste secret details into chat.')
        self.prepare_button.setEnabled(True);self.confirm_button.setEnabled(False)

    def closeEvent(self,event):
        self.timer.stop()
        if self.ceremony is not None:self.ceremony.close();self.ceremony=None
        self.unlock.clear();self.vault.clear();self.offline.clear();self.pending=None
        super().closeEvent(event)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    if sys.platform!='win32':raise SystemExit('Windows owner setup required; no plaintext or synthetic-key fallback.')
    if args.check_only:
        import win32crypt
        from security.passkeys import PasskeyCeremony
        print('Owner setup dependencies available. No owner store, key, browser or enrollment opened.');return 0
    parent=os.environ.get('LOCALAPPDATA')
    if not parent:raise SystemExit('Windows local application-data directory required.')
    app=QApplication(sys.argv[:1]);window=EnrollmentWindow(Path(parent)/'LYA/memory-recovery');window.show()
    return app.exec()


if __name__=='__main__':raise SystemExit(main())
