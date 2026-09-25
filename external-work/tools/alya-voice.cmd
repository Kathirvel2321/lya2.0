@echo off
rem Run the isolated ALYA voice lab CLI from any directory.
rem Uses the workspace virtual environment; nothing in the LYA app is touched.
setlocal
set "HEREDIR=%~dp0"
set "LABDIR=%HEREDIR%.."
set "PYTHON=%LABDIR%\..\.venv-ui\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
set "PYTHONPATH=%LABDIR%"
"%PYTHON%" -m alya_voice.cli %*
endlocal
