@echo off
setlocal
call "%~dp0check-t01.cmd" || exit /b 1
"%~dp0.venv-ui\Scripts\python.exe" -B "%~dp0test_t02.py" || exit /b 1
echo PASS: offline T02 checks. Live independent backup is a separate acceptance gate.
