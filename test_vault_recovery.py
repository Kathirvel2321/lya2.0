"""Portable recovery checks using only a disposable fake DPAPI key."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
import win32crypt


SCRIPT = Path(__file__).parent / "lya-external-work/lya-brain/recovery/vault_recovery.py"


class PortableRecoveryTests(unittest.TestCase):
    def test_bundle_and_verify_fake_encrypted_stores(self):
        spec = importlib.util.spec_from_file_location("lya_test_recovery_bundle", SCRIPT)
        recovery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recovery)
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            base = Path(temporary)
            root = base / "project"
            runtime = base / "runtime"
            backup_parent = base / "offdevice"
            (root / "security").mkdir(parents=True)
            runtime.mkdir()
            backup_parent.mkdir()
            recovery.ROOT = str(root)
            recovery.VAULT_DIR = str(root / "security")
            recovery.KEY_PATH = str(root / "security" / ".lya_key")
            key = Fernet.generate_key()
            Path(recovery.KEY_PATH).write_bytes(win32crypt.CryptProtectData(
                key, "LYA test", recovery.ENTROPY, None, None, 0))
            (runtime / "lya.db.enc").write_bytes(Fernet(key).encrypt(b"fake sqlite bytes"))
            (root / "security" / "private.lya").write_bytes(
                Fernet(key).encrypt(b"fake vault bytes"))
            (root / ".env").write_text("FAKE_SECRET=do-not-copy")
            destination = backup_parent / "LYA-backup"
            phrase = "test only portable backup phrase 2026"
            with patch.dict(os.environ, {"LYA_DATA_DIR": str(runtime)}):
                with patch.object(recovery.getpass, "getpass", side_effect=[phrase, phrase]):
                    self.assertEqual(recovery.cmd_bundle(types.SimpleNamespace(
                        output_dir=str(destination))), 0)
                self.assertTrue((destination / "lya_recovery.key").is_file())
                manifest = (destination / "manifest.lya").read_bytes()
                self.assertNotIn(b"lya.db.enc", manifest)
                self.assertNotIn(b"private.lya", manifest)
                self.assertEqual(sorted(p.name for p in (destination / "data").iterdir()),
                                 ["0001.enc", "0002.enc"])
                self.assertNotIn(b"FAKE_SECRET", b"".join(
                    p.read_bytes() for p in destination.rglob("*") if p.is_file()))
                with patch.object(recovery.getpass, "getpass", return_value=phrase), \
                     patch.object(recovery, "_dpapi_unwrap", side_effect=AssertionError(
                         "bundle verification must not depend on the old Windows account")):
                    self.assertEqual(recovery.cmd_verify_bundle(types.SimpleNamespace(
                        bundle_dir=str(destination))), 0)
                original_key_file = Path(recovery.KEY_PATH).read_bytes()
                extracted = backup_parent / "extracted"
                with patch.object(recovery.getpass, "getpass", return_value=phrase):
                    self.assertEqual(recovery.cmd_extract_bundle(types.SimpleNamespace(
                        bundle_dir=str(destination), output_dir=str(extracted))), 0)
                self.assertEqual((extracted / "runtime" / "lya.db.enc").read_bytes(),
                                 (runtime / "lya.db.enc").read_bytes())
                self.assertEqual((extracted / "project" / "security" / "private.lya").read_bytes(),
                                 (root / "security" / "private.lya").read_bytes())
                self.assertEqual(Path(recovery.KEY_PATH).read_bytes(), original_key_file)
                self.assertFalse((extracted / ".env").exists())
                with patch.object(recovery.getpass, "getpass", return_value=phrase):
                    self.assertEqual(recovery.cmd_extract_bundle(types.SimpleNamespace(
                        bundle_dir=str(destination), output_dir=str(root / "unsafe"))), 2)
                with patch.object(recovery.getpass, "getpass", return_value="wrong phrase"):
                    self.assertEqual(recovery.cmd_verify_bundle(types.SimpleNamespace(
                        bundle_dir=str(destination))), 1)
                copied = destination / "data" / "0001.enc"
                copied.write_bytes(copied.read_bytes() + b"tampered")
                with patch.object(recovery.getpass, "getpass", return_value=phrase):
                    self.assertEqual(recovery.cmd_verify_bundle(types.SimpleNamespace(
                        bundle_dir=str(destination))), 1)

    def test_bundle_rejects_bad_source_without_partial_output(self):
        spec = importlib.util.spec_from_file_location("lya_test_recovery_bad_bundle", SCRIPT)
        recovery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recovery)
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            base = Path(temporary)
            root = base / "project"
            runtime = base / "runtime"
            backup_parent = base / "offdevice"
            (root / "security").mkdir(parents=True)
            runtime.mkdir()
            backup_parent.mkdir()
            recovery.ROOT = str(root)
            recovery.VAULT_DIR = str(root / "security")
            recovery.KEY_PATH = str(root / "security" / ".lya_key")
            key = Fernet.generate_key()
            Path(recovery.KEY_PATH).write_bytes(win32crypt.CryptProtectData(
                key, "LYA test", recovery.ENTROPY, None, None, 0))
            (runtime / "lya.db.enc").write_bytes(
                Fernet(Fernet.generate_key()).encrypt(b"wrong-key store"))
            destination = backup_parent / "LYA-backup"
            phrase = "test only portable backup phrase 2026"
            with patch.dict(os.environ, {"LYA_DATA_DIR": str(runtime)}):
                self.assertEqual(recovery.cmd_bundle(types.SimpleNamespace(
                    output_dir=str(root / "unsafe"))), 2)
                with patch.object(recovery.getpass, "getpass", side_effect=[phrase, phrase]):
                    self.assertEqual(recovery.cmd_bundle(types.SimpleNamespace(
                        output_dir=str(destination))), 1)
                self.assertFalse(destination.exists())
                self.assertEqual(list(backup_parent.glob("LYA-backup.tmp.*")), [])

    def test_fake_vault_export_verify_and_restore(self):
        spec = importlib.util.spec_from_file_location("lya_test_recovery", SCRIPT)
        recovery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recovery)
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temporary)
            recovery.ROOT = temporary
            recovery.VAULT_DIR = temporary
            recovery.KEY_PATH = str(root / "fake_dpapi_key")
            key = Fernet.generate_key()
            key_path = Path(recovery.KEY_PATH)
            key_path.write_bytes(win32crypt.CryptProtectData(key, "LYA test", recovery.ENTROPY,
                                                             None, None, 0))
            blob = root / "portable.key"
            phrase = "test only recovery phrase 2026"
            with patch.object(recovery.getpass, "getpass", side_effect=[phrase, phrase]):
                self.assertEqual(recovery.cmd_export(types.SimpleNamespace(output=str(blob), force=False)), 0)
            original_blob = blob.read_bytes()
            with patch.object(recovery.getpass, "getpass", side_effect=[phrase, phrase]), \
                 patch.object(recovery.os, "replace", side_effect=OSError("fake disk failure")), \
                 self.assertRaises(OSError):
                recovery.cmd_export(types.SimpleNamespace(output=str(blob), force=True))
            self.assertEqual(blob.read_bytes(), original_blob)
            self.assertEqual(list(root.glob(".lya-recovery-*.tmp")), [])
            with patch.object(recovery.getpass, "getpass", return_value=phrase):
                self.assertEqual(recovery.cmd_verify(types.SimpleNamespace(blob=str(blob))), 0)
            encrypted_store = root / "fake_store.enc"
            encrypted_store.write_bytes(Fernet(key).encrypt(b"disposable encrypted store"))
            with patch.object(recovery.getpass, "getpass", return_value=phrase):
                self.assertEqual(recovery.cmd_verify(types.SimpleNamespace(
                    blob=str(blob), encrypted_store=str(encrypted_store))), 0)
            wrapped = key_path.read_bytes()
            with patch.object(recovery.getpass, "getpass", return_value="wrong phrase"):
                self.assertEqual(recovery.cmd_restore(types.SimpleNamespace(blob=str(blob))), 1)
            self.assertEqual(key_path.read_bytes(), wrapped)
            key_path.unlink()
            with patch.object(recovery.getpass, "getpass", return_value=phrase):
                self.assertEqual(recovery.cmd_restore(types.SimpleNamespace(blob=str(blob))), 0)
            self.assertEqual(recovery._dpapi_unwrap(), key)

    def test_wrong_valid_vault_cannot_replace_working_key(self):
        spec = importlib.util.spec_from_file_location("lya_test_recovery_replace", SCRIPT)
        recovery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recovery)
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temporary)
            recovery.ROOT = temporary
            recovery.VAULT_DIR = temporary
            recovery.KEY_PATH = str(root / "fake_dpapi_key")
            current = Fernet.generate_key()
            key_path = Path(recovery.KEY_PATH)
            key_path.write_bytes(win32crypt.CryptProtectData(current, "LYA test",
                                                             recovery.ENTROPY, None, None, 0))
            original = key_path.read_bytes()
            encrypted_store = root / "fake_store.enc"
            encrypted_store.write_bytes(Fernet(current).encrypt(b"disposable encrypted store"))
            phrase = "test only recovery phrase 2026"
            wrong = root / "wrong.key"
            wrong.write_bytes(recovery._make_blob(Fernet.generate_key(), phrase))
            with patch.object(recovery.getpass, "getpass", return_value=phrase):
                self.assertEqual(recovery.cmd_restore(types.SimpleNamespace(
                    blob=str(wrong), encrypted_store=str(encrypted_store),
                    replace_existing=True)), 1)
            self.assertEqual(key_path.read_bytes(), original)
            with patch.object(recovery.getpass, "getpass", return_value=phrase):
                self.assertEqual(recovery.cmd_restore(types.SimpleNamespace(
                    blob=str(wrong), replace_existing=True)), 2)
            self.assertEqual(key_path.read_bytes(), original)

            right = root / "right.key"
            right.write_bytes(recovery._make_blob(current, phrase))
            key_path.write_bytes(b"unreadable old-account DPAPI blob")
            args = types.SimpleNamespace(blob=str(right), encrypted_store=str(encrypted_store),
                                         replace_existing=True)
            with patch.object(recovery.getpass, "getpass", return_value=phrase), \
                 patch.object(recovery.os, "replace", side_effect=OSError("fake disk failure")), \
                 self.assertRaises(OSError):
                recovery.cmd_restore(args)
            self.assertEqual(key_path.read_bytes(), b"unreadable old-account DPAPI blob")
            self.assertEqual(list(root.glob(".lya-key-*.tmp")), [])
            with patch.object(recovery.getpass, "getpass", return_value=phrase):
                self.assertEqual(recovery.cmd_restore(args), 0)
            self.assertEqual(recovery._dpapi_unwrap(), current)
            self.assertTrue(list(root.glob("fake_dpapi_key.pre-restore.*")))


if __name__ == "__main__":
    unittest.main()
