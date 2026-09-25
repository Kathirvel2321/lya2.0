"""On-demand aggregate device readings; no files, process list or network calls."""
import ctypes
import os
import shutil


def _windows_snapshot():
    if os.name != "nt":
        raise OSError("Windows device readings are unavailable on this platform.")

    class Memory(ctypes.Structure):
        _fields_ = [("length", ctypes.c_uint32), ("load", ctypes.c_uint32)] + [
            (name, ctypes.c_uint64) for name in
            ("total", "available", "page_total", "page_available",
             "virtual_total", "virtual_available", "extended")]

    class Power(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ubyte) for name in
                    ("ac", "flag", "percent", "saver")] + [
                        ("remaining", ctypes.c_uint32), ("full", ctypes.c_uint32)]

    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    power = Power()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise OSError("Windows could not read memory status.")
    power_ok = bool(kernel.GetSystemPowerStatus(ctypes.byref(power)))
    battery = (None if not power_ok or power.flag == 255 or power.flag & 128
               or power.percent > 100 else power.percent)
    ac = None if not power_ok or power.ac not in (0, 1) else bool(power.ac)
    return memory.total, memory.available, battery, ac


def report():
    total, available, battery, ac = _windows_snapshot()
    disk = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
    gib = 1024 ** 3
    power = "plugged in" if ac is True else "on battery" if ac is False else "power source unknown"
    charge = f"{battery}%" if battery is not None else "unavailable or no battery"
    return (f"Battery: {charge} ({power})\n"
            f"Memory: {available/gib:.1f} GiB available / {total/gib:.1f} GiB total\n"
            f"System disk: {disk.free/gib:.1f} GiB free / {disk.total/gib:.1f} GiB total\n"
            f"Logical CPUs: {os.cpu_count() or 'unavailable'}\n"
            "Current snapshot; CPU utilization and battery runtime are not measured.")
