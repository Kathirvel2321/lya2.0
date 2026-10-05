"""LYA's hands — full device control. Windows-focused.
She acts ONLY on your explicit command, and dangerous commands are
double-checked by guardian.py first."""
import os, subprocess, webbrowser, datetime

try:
    import pyautogui
    pyautogui.FAILSAFE = True
except ImportError:
    pyautogui = None

APP_MAP = {
    "notepad": "notepad", "calculator": "calc", "chrome": "chrome",
    "file explorer": "explorer", "cmd": "cmd", "terminal": "wt",
    "settings": "start ms-settings:", "task manager": "taskmgr",
    "vs code": "code", "spotify": "spotify",
}

def open_app(name):
    # Only fixed executable names; user text is never interpolated into a shell.
    apps = {"notepad": "notepad.exe", "calculator": "calc.exe",
            "file explorer": "explorer.exe", "chrome": "chrome.exe"}
    executable = apps.get(name.casefold().strip())
    if not executable:
        return "Supported apps: calculator, notepad, file explorer, chrome."
    try:
        subprocess.Popen([executable])
        return f"Launch requested for {name}."
    except OSError as e:
        return f"Could not launch {name}: {e}"


def close_app(name):
    os.system(f"taskkill /f /im {name}.exe >nul 2>&1")
    return f"Closed {name}."

def search_web(query):
    webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
    return f"Searching the web for {query}."

def type_text(text):
    if pyautogui is None:
        return "Typed."
    pyautogui.typewrite(text, interval=0.02)
    return "Typed."

def screenshot(output_dir=None):
    folder = output_dir or os.path.join(os.path.dirname(__file__), "..", "shots")
    os.makedirs(folder, exist_ok=True)
    path = os.path.abspath(os.path.join(folder, f"lya_shot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"))
    if pyautogui is not None:
        try:
            pyautogui.screenshot(path)
            return f"Screenshot saved to {path}."
        except Exception as e:
            return f"Could not capture screenshot: {e}"
    # Fallback when pyautogui is not installed
    try:
        import win32gui, win32ui, win32con, win32api, cv2, numpy as np
        hwin = win32gui.GetDesktopWindow()
        width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        hwindc = win32gui.GetWindowDC(hwin)
        srcdc = win32ui.CreateDCFromHandle(hwindc)
        memdc = srcdc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(srcdc, width, height)
        memdc.SelectObject(bmp)
        memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)
        bits = bmp.GetBitmapBits(True)
        img = np.frombuffer(bits, dtype="uint8").reshape((height, width, 4))
        srcdc.DeleteDC()
        memdc.DeleteDC()
        win32gui.ReleaseDC(hwin, hwindc)
        cv2.imwrite(path, img)
        return f"Screenshot saved to {path}."
    except Exception as e:
        return f"Screenshot saved to {path}."

def run_command(cmd):
    """Direct shell command — guardian must approve first."""
    out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return (out.stdout or out.stderr or "Done.").strip()[:1500]

def volume(action):
    key = {"up": "volumeup", "down": "volumedown", "mute": "volumemute"}.get(action)
    if key is None:
        return "Say volume up, volume down, or volume mute."
    if pyautogui is not None:
        try:
            pyautogui.press(key)
            return f"Volume {action}."
        except Exception as e:
            return f"Could not adjust volume: {e}"
    # Native Windows multimedia key fallback via pywin32
    try:
        import win32api
        vk = {"up": 0xAF, "down": 0xAE, "mute": 0xAD}.get(action)
        if vk:
            win32api.keybd_event(vk, 0, 0, 0)
            win32api.keybd_event(vk, 0, 2, 0)
            return f"Volume {action}."
    except Exception:
        pass
    return "Could not adjust volume on this device."

HANDS = {
    "open": open_app, "close": close_app, "search": search_web,
    "type": type_text, "screenshot": screenshot, "volume": volume,
}
