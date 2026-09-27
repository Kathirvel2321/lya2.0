"""In-process Windows Hello / PIN consent. LYA never sees the PIN or face.

Camera and microphone in LYA only measure presence. Creating an admin still
needs this Windows checkpoint because it proves the person can unlock *this*
Windows account. The unsigned HelloVerifier.exe is not used here, so Smart App
Control does not have a new binary to block.
"""
from __future__ import annotations

import ctypes
import re
import sys
import time
import uuid
from ctypes import HRESULT, POINTER, Structure, byref, c_int32, c_uint32, c_uint16, c_ubyte, c_void_p, c_wchar_p

CLASS_NAME = "Windows.Security.Credentials.UI.UserConsentVerifier"
PROMPT = ("LYA: verify your Windows account for administrator setup. "
          "This does not enroll face or voice.")
NONCE = re.compile(r"^[A-Za-z0-9_-]{32}$")
IID_INTEROP = "39E050C3-4E74-441A-8DC0-B81104DF949C"
IID_ASYNC_VERIFY = "fd596ffd-2318-558f-9dbe-d21df43764a5"
IID_ASYNC_INFO = "00000036-0000-0000-C000-000000000046"
IID_STATICS = "AF4F3F91-564C-4DDC-B8B5-973447627C65"
RPC_E_CHANGED_MODE = -2147417850  # 0x80010106
RO_E_CLOSED = -2147483638

AVAILABILITY = {
    0: "Available",
    1: "DeviceNotPresent",
    2: "NotConfiguredForUser",
    3: "DisabledByPolicy",
    4: "DeviceBusy",
}
RESULTS = {
    0: "Verified",
    1: "DeviceNotPresent",
    2: "NotConfiguredForUser",
    3: "DisabledByPolicy",
    4: "DeviceBusy",
    5: "RetriesExhausted",
    6: "Canceled",
}


class GUID(Structure):
    _fields_ = (("Data1", c_uint32), ("Data2", c_uint16),
                ("Data3", c_uint16), ("Data4", c_ubyte * 8))

    @classmethod
    def from_text(cls, text: str) -> "GUID":
        value = uuid.UUID(text)
        packed = cls()
        packed.Data1 = value.time_low
        packed.Data2 = value.time_mid
        packed.Data3 = value.time_hi_version
        packed.Data4[:] = value.bytes[8:]
        return packed


def _combase():
    dll = ctypes.WinDLL("combase.dll")
    dll.RoInitialize.argtypes = (c_uint32,)
    dll.RoInitialize.restype = HRESULT
    dll.RoUninitialize.argtypes = ()
    dll.RoUninitialize.restype = None
    dll.WindowsCreateString.argtypes = (c_wchar_p, c_uint32, POINTER(c_void_p))
    dll.WindowsCreateString.restype = HRESULT
    dll.WindowsDeleteString.argtypes = (c_void_p,)
    dll.WindowsDeleteString.restype = HRESULT
    dll.RoGetActivationFactory.argtypes = (c_void_p, POINTER(GUID), POINTER(c_void_p))
    dll.RoGetActivationFactory.restype = HRESULT
    return dll


def _vtbl(obj):
    return ctypes.cast(c_void_p(obj), POINTER(POINTER(c_void_p))).contents


def _fn(obj, index, restype, *argtypes):
    return ctypes.WINFUNCTYPE(restype, c_void_p, *argtypes)(_vtbl(obj)[index])


def _release(obj):
    if obj:
        _fn(obj, 2, c_uint32)(obj)


def _hstring(dll, text: str) -> c_void_p:
    handle = c_void_p()
    hr = dll.WindowsCreateString(text, len(text), byref(handle))
    if hr < 0:
        raise OSError(hr, "WindowsCreateString")
    return handle


def _initialize(dll) -> bool:
    hr = dll.RoInitialize(1)
    if hr == RPC_E_CHANGED_MODE:
        return False
    if hr < 0:
        raise OSError(hr, "RoInitialize")
    return True


def _factory(dll, iid_text: str) -> int:
    name = _hstring(dll, CLASS_NAME)
    factory = c_void_p()
    try:
        hr = dll.RoGetActivationFactory(name, byref(GUID.from_text(iid_text)), byref(factory))
        if hr < 0 or not factory.value:
            raise OSError(hr, "RoGetActivationFactory")
        return factory.value
    finally:
        dll.WindowsDeleteString(name)


def _wait_int(operation, pump=None, cancelled=None, timeout=90.0) -> int:
    info = c_void_p()
    hr = _fn(operation, 0, HRESULT, POINTER(GUID), POINTER(c_void_p))(
        operation, byref(GUID.from_text(IID_ASYNC_INFO)), byref(info))
    if hr < 0 or not info.value:
        raise OSError(hr, "IAsyncInfo")
    try:
        deadline = time.monotonic() + timeout
        status = c_int32()
        while True:
            if cancelled and cancelled():
                _fn(info.value, 9, HRESULT)(info.value)
                raise TimeoutError("cancelled")
            hr = _fn(info.value, 7, HRESULT, POINTER(c_int32))(info.value, byref(status))
            if hr < 0:
                raise OSError(hr, "IAsyncInfo.get_Status")
            if status.value != 0:  # AsyncStatus.Started
                break
            if time.monotonic() >= deadline:
                _fn(info.value, 9, HRESULT)(info.value)
                raise TimeoutError("TimedOut")
            if pump:
                pump()
            else:
                time.sleep(0.05)
        if status.value != 1:  # Completed
            raise OSError(status.value, "async failed")
        value = c_int32()
        hr = _fn(operation, 8, HRESULT, POINTER(c_int32))(operation, byref(value))
        if hr < 0:
            raise OSError(hr, "GetResults")
        return int(value.value)
    finally:
        _fn(info.value, 10, HRESULT)(info.value)
        _release(info.value)


def runtime_ready() -> bool:
    if sys.platform != "win32":
        return False
    own = False
    dll = None
    factory = 0
    try:
        dll = _combase()
        own = _initialize(dll)
        factory = _factory(dll, IID_INTEROP)
        return True
    except OSError:
        return False
    finally:
        _release(factory)
        if own and dll is not None:
            dll.RoUninitialize()


def check_availability() -> str:
    """Named Windows availability. This is not authentication."""
    if sys.platform != "win32":
        return "DeviceNotPresent"
    own = False
    dll = None
    factory = 0
    operation = c_void_p()
    try:
        dll = _combase()
        own = _initialize(dll)
        factory = _factory(dll, IID_STATICS)
        hr = _fn(factory, 6, HRESULT, POINTER(c_void_p))(factory, byref(operation))
        if hr < 0 or not operation.value:
            return "Unavailable"
        code = _wait_int(operation.value)
        return AVAILABILITY.get(code, "Unavailable")
    except TimeoutError:
        return "TimedOut"
    except OSError:
        return "Unavailable"
    finally:
        if operation.value:
            _release(operation.value)
        _release(factory)
        if own and dll is not None:
            dll.RoUninitialize()


def verify_for_window(hwnd: int, nonce: str, pump=None, cancelled=None) -> str:
    """Return Verified:<nonce> after a fresh Windows prompt, else a named failure."""
    if not NONCE.fullmatch(nonce or ""):
        return "Unavailable"
    if sys.platform != "win32" or not hwnd:
        return "Unavailable"
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.IsWindow.argtypes = (c_void_p,)
    user32.IsWindow.restype = ctypes.c_bool
    if not user32.IsWindow(c_void_p(int(hwnd))):
        return "Unavailable"
    own = False
    dll = None
    factory = 0
    message = c_void_p()
    operation = c_void_p()
    try:
        dll = _combase()
        own = _initialize(dll)
        factory = _factory(dll, IID_INTEROP)
        message = _hstring(dll, PROMPT)
        iid = GUID.from_text(IID_ASYNC_VERIFY)
        hr = _fn(factory, 6, HRESULT, c_void_p, c_void_p, POINTER(GUID), POINTER(c_void_p))(
            factory, c_void_p(int(hwnd)), message, byref(iid), byref(operation))
        if hr < 0 or not operation.value:
            return "Unavailable"
        code = _wait_int(operation.value, pump=pump, cancelled=cancelled)
        name = RESULTS.get(code, "Unavailable")
        return "Verified:" + nonce if name == "Verified" else name
    except TimeoutError:
        return "TimedOut"
    except OSError:
        return "Unavailable"
    finally:
        if operation.value:
            _release(operation.value)
        if message.value and dll is not None:
            dll.WindowsDeleteString(message)
        _release(factory)
        if own and dll is not None:
            dll.RoUninitialize()
