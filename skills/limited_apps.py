"""Fixed visitor app launches; no arbitrary paths, URLs, shells or signed-in browser."""
import os
from pathlib import Path
import subprocess


def launch(name):
    if name=='calculator':
        command=[str(Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/calc.exe')]
    elif name=='youtube':
        roots=[os.environ.get(key,'') for key in ('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA')]
        browser=next((Path(root)/'Google/Chrome/Application/chrome.exe' for root in roots
                      if root and (Path(root)/'Google/Chrome/Application/chrome.exe').is_file()),None)
        if browser is None:
            raise ValueError('A Chrome guest browser is not available. No signed-in browser was opened.')
        command=[str(browser),'--guest','--new-window','--no-first-run','https://www.youtube.com/']
    else:
        raise ValueError('Only calculator and YouTube guest browsing are permitted here.')
    subprocess.Popen(command)
    return 'Opened '+name+'.'
