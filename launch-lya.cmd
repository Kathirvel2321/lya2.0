@echo off
start "LYA" /D "%~dp0" "%~dp0.venv-ui\Scripts\pythonw.exe" "%~dp0desktop\app.py" --show-panel %*
