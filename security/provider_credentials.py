"""Windows Credential Manager entries for approved desktop connections."""
import sys


def _target(name):
    return "LYA/Desktop/" + name


def read(name):
    if sys.platform != "win32":
        return ""
    try:
        import win32cred
        credential = win32cred.CredRead(_target(name), win32cred.CRED_TYPE_GENERIC, 0)
        blob = credential["CredentialBlob"]
        return blob.rstrip("\x00") if isinstance(blob, str) else blob.decode("utf-16-le").rstrip("\x00")
    except Exception:
        return ""


def write(name, value):
    import win32cred

    win32cred.CredWrite({
        "Type": win32cred.CRED_TYPE_GENERIC,
        "TargetName": _target(name),
        "CredentialBlob": value,
        "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
    }, 0)


def remove(name):
    import pywintypes
    import win32cred

    try:
        win32cred.CredDelete(_target(name), win32cred.CRED_TYPE_GENERIC, 0)
    except pywintypes.error as error:
        if error.winerror != 1168:  # ERROR_NOT_FOUND
            raise
