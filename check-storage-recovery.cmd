@echo off
setlocal
"%~dp0.venv-ui\Scripts\python.exe" -B "%~dp0test_recovery.py" || exit /b 1
"%~dp0.venv-ui\Scripts\python.exe" -B "%~dp0test_brain_workflow.py" || exit /b 1
"%~dp0.venv-ui\Scripts\python.exe" -B "%~dp0test_approval.py" || exit /b 1
"%~dp0.venv-ui\Scripts\python.exe" -B "%~dp0test_recovery_ui.py" || exit /b 1
echo PASS: isolated recovery core, file and native UI checks. Real owner verification and cloud sync remain pending.
