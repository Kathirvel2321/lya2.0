@echo off
setlocal
call "%~dp0check-t02.cmd" || exit /b 1
"%~dp0.venv-ui\Scripts\python.exe" -B "%~dp0test_answer_verification.py" || exit /b 1
"%~dp0.venv-ui\Scripts\python.exe" -B "%~dp0test_research_adapter.py" || exit /b 1
echo PASS: offline T03 verification and research-adapter checks.