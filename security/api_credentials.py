"""Read the owner's NVIDIA key from Windows Credential Manager, never a file."""
TARGET = 'LYA/NVIDIA_API_KEY'


def nvidia_key():
    import win32cred
    import pywintypes
    try:
        credential = win32cred.CredRead(TARGET, win32cred.CRED_TYPE_GENERIC, 0)
    except pywintypes.error as error:
        if error.winerror == 1168:  # No such credential: retain the existing prompt.
            return ''
        raise RuntimeError('Windows could not read the saved NVIDIA key.') from None
    blob = credential.get('CredentialBlob', b'')
    try:
        if isinstance(blob, bytes):
            # Windows' generic password UI uses UTF-16; accept ASCII credentials too.
            blob = blob.decode('utf-16-le' if b'\0' in blob else 'utf-8')
        key = blob.rstrip('\0').strip()
        if not key or len(key) > 512 or any(ord(char) < 33 or ord(char) > 126 for char in key):
            raise ValueError()
        return key
    except (AttributeError, UnicodeError, ValueError):
        raise RuntimeError('The saved NVIDIA credential is not a usable API key.') from None
