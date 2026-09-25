"""Authenticated encryption for callers that explicitly use this module.

Fernet uses AES-128-CBC plus HMAC-SHA256; its key is protected with Windows
DPAPI. This does not encrypt unrelated files/logs or isolate data from malware
running as the same unlocked Windows user. Independent recovery is required
before moving encrypted data to a different Windows account or device.
"""
import os, base64, threading
from cryptography.fernet import Fernet

import win32crypt  # from pywin32 — Windows Data Protection API

_LEGACY_KEY_PATH = os.path.join(os.path.dirname(__file__), ".lya_key")
_NEW_KEY_PATH = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                             "LYA", "master.key.dpapi")
# Keep existing vaults on their original key until a verified recovery copy exists.
KEY_PATH = _LEGACY_KEY_PATH if os.path.exists(_LEGACY_KEY_PATH) else _NEW_KEY_PATH
ENTROPY = b"LYA-ultron-project-2026"   # extra salt bound to this app

def _get_fernet() -> Fernet:
    """Load or create the DPAPI-protected key. Transparent to callers."""
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            blob = f.read()
    else:
        raw = Fernet.generate_key()
        blob = win32crypt.CryptProtectData(raw, "LYA", ENTROPY, None, None, 0)
        os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
        try:
            with open(KEY_PATH, "xb") as f:
                f.write(blob)
        except FileExistsError:
            with open(KEY_PATH, "rb") as f:
                blob = f.read()
    _, raw = win32crypt.CryptUnprotectData(blob, ENTROPY, None, None, 0)
    return Fernet(raw)

_F = None  # Importing a brain module must not read/create the user's key.
_F_LOCK = threading.Lock()

def _fernet():
    global _F
    if _F is None:
        with _F_LOCK:
            if _F is None:
                _F = _get_fernet()
    return _F

def encrypt(data: bytes) -> bytes:
    return _fernet().encrypt(data)

def decrypt(token: bytes) -> bytes:
    return _fernet().decrypt(token)

def encrypt_text(text: str) -> str:
    return encrypt(text.encode()).decode()

def decrypt_text(token: str) -> str:
    return decrypt(token.encode()).decode()

def encrypt_file(path: str):
    """Encrypt a file in place."""
    if not os.path.exists(path) or path.endswith(".lya"):
        return
    with open(path, "rb") as f:
        data = f.read()
    with open(path + ".lya", "wb") as f:
        f.write(encrypt(data))
    os.remove(path)   # plaintext gone

def decrypt_file(path: str) -> bytes:
    """Decrypt .lya file to bytes (never touches the disk as plaintext)."""
    with open(path, "rb") as f:
        return decrypt(f.read())

def secure_delete(path: str):
    """Best-effort overwrite/delete; SSDs, snapshots and backups may retain copies."""
    if not os.path.exists(path):
        return
    size = os.path.getsize(path)
    with open(path, "wb") as f:
        f.write(os.urandom(size))
    os.remove(path)
