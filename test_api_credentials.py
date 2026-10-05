"""Fake Windows credential reads only; never opens the owner's credential store."""
import unittest
from unittest.mock import patch
import pywintypes
import win32cred
from security import api_credentials


class ApiCredentialTests(unittest.TestCase):
    def test_windows_password_and_ascii_blob_are_supported(self):
        for blob in ('fake-key', b'fake-key', 'fake-key'.encode('utf-16-le'),
                     'fake-key\0'.encode('utf-16-le')):
            with patch.object(win32cred, 'CredRead', return_value={'CredentialBlob': blob}) as read:
                self.assertEqual(api_credentials.nvidia_key(), 'fake-key')
                read.assert_called_once_with('LYA/NVIDIA_API_KEY', win32cred.CRED_TYPE_GENERIC, 0)

    def test_missing_credential_preserves_prompt(self):
        error = pywintypes.error(1168, 'CredRead', 'synthetic missing entry')
        with patch.object(win32cred, 'CredRead', side_effect=error):
            self.assertEqual(api_credentials.nvidia_key(), '')

    def test_access_failure_has_no_private_payload(self):
        error = pywintypes.error(5, 'CredRead', 'fake-private-detail')
        with patch.object(win32cred, 'CredRead', side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                api_credentials.nvidia_key()
            self.assertNotIn('fake-private-detail', str(caught.exception))

    def test_bad_or_empty_credential_is_not_used(self):
        for blob in (b'', b'x\0y', b'\xff', 'fake-key\nother-key', '\0fake-key', 'x' * 513):
            with patch.object(win32cred, 'CredRead', return_value={'CredentialBlob': blob}):
                with self.assertRaises(RuntimeError):
                    api_credentials.nvidia_key()


if __name__ == '__main__':
    unittest.main()
