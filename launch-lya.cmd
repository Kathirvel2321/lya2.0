@echo off
start "LYA Online" /D "%~dp0" "%~dp0.venv-asr\Scripts\pythonw.exe" "%~dp0tools\start_nvidia_lya.py" --gui --allow-nvidia-questions --show-panel %*
