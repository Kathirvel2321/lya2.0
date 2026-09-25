@echo off
setlocal
call "%~dp0check-t03.cmd" || exit /b 1
"%~dp0.venv-ui\Scripts\python.exe" -B "%~dp0test_approval.py" || exit /b 1
"%~dp0.venv-ui\Scripts\python.exe" -B "%~dp0test_registration.py" || exit /b 1
"%~dp0.venv-ui\Scripts\python.exe" -B "%~dp0test_registration_ui.py" || exit /b 1
echo PASS: T04 policy and registration foundation. Real device verification remains pending.
