@echo off
cd /d "%~dp0"
if exist ".venv-ui\Scripts\python.exe" (
    ".venv-ui\Scripts\python.exe" -B -m desktop.linked
) else (
    py -3 -B -m desktop.linked
)
