"""Isolated Connections checks: fake provider and fake credential store."""
import os
import sys
import time
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from desktop import connections
from security import provider_credentials

app = QApplication.instance() or QApplication([])
saved = {}

# Simulate the Windows API's Unicode credential round trip without touching its store.
api = types.SimpleNamespace(CRED_TYPE_GENERIC=1, CRED_PERSIST_LOCAL_MACHINE=2)
api.CredWrite = lambda credential, flags: saved.update(credential)
api.CredRead = lambda target, kind, flags: {'CredentialBlob': saved['CredentialBlob'].encode('utf-16-le')}
with patch.dict(sys.modules, {'win32cred': api}):
    provider_credentials.write('fake', 'fake-key')
    assert saved['CredentialBlob'] == 'fake-key'
    assert provider_credentials.read('fake') == 'fake-key'
saved.clear()


def wait_until(predicate):
    end = time.monotonic() + 5
    while not predicate() and time.monotonic() < end:
        app.processEvents()
        time.sleep(.01)
    assert predicate(), 'Timed out waiting for dialog'


def slow_check(name, key, model, cancelled):
    while not cancelled.wait(.01):
        pass


with patch.object(provider_credentials, 'read', side_effect=lambda name: saved.get(name, '')), \
     patch.object(provider_credentials, 'write', side_effect=lambda name, value: saved.update({name: value})), \
     patch.object(connections, 'check_key', side_effect=slow_check):
    dialog = connections.ConnectionsDialog()
    dialog.show()
    dialog.key.setText('fake-key')
    dialog.check.click()
    assert dialog.worker is not None
    dialog.done_button.click()
    wait_until(lambda: dialog.worker is None)
    assert not dialog.isVisible() and not saved

with patch.object(provider_credentials, 'read', side_effect=lambda name: saved.get(name, '')), \
     patch.object(provider_credentials, 'write', side_effect=lambda name, value: saved.update({name: value})), \
     patch.object(connections, 'check_key', return_value=None):
    dialog = connections.ConnectionsDialog()
    dialog.show()
    dialog.key.setText('fake-key')
    dialog.check.click()
    wait_until(lambda: dialog.worker is None)
    assert saved['NVIDIA_API_KEY'] == 'fake-key'
    dialog.done_button.click()
    assert not dialog.isVisible()

with patch.object(provider_credentials, 'read', return_value=''):
    dialog = connections.ConnectionsDialog()
    dialog.show()
    dialog.close()
    assert not dialog.isVisible()

print('Cancellation, close and simulated save passed.')
