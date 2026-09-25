@echo off
rem Run the voice-lab test suite. Offline: no microphone, no network, no LYA changes.
setlocal
set "HEREDIR=%~dp0"
set "LABDIR=%HEREDIR%.."
set "PYTHON=%LABDIR%\..\.venv-ui\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
pushd "%LABDIR%"
"%PYTHON%" -m unittest discover -s tests -t . -v
set "CODE=%ERRORLEVEL%"
popd
endlocal & exit /b %CODE%
