@echo off
REM LYA initialization / admin registration walk-through.
REM Opens the camera and microphone only when you press their buttons.
start "LYA" /D "%~dp0" "%~dp0.venv-ui\Scripts\pythonw.exe" "%~dp0desktop\activation.py" %*
