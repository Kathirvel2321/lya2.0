@echo off
setlocal
set "LYA_PY=%~dp0.venv-ui\Scripts\python.exe"

if not exist "%LYA_PY%" (
  echo FAIL: LYA Python was not found at "%LYA_PY%"
  exit /b 2
)

echo LYA T01 safe offline baseline
echo No live provider, camera, microphone, enrollment, or real memory is used.

"%LYA_PY%" -B "%~dp0test_router.py" || exit /b 1
"%LYA_PY%" -B "%~dp0test_oracle.py" || exit /b 1
"%LYA_PY%" -B "%~dp0test_provider_setup.py" || exit /b 1
"%LYA_PY%" -B "%~dp0test_brain_workflow.py" || exit /b 1

set "QT_QPA_PLATFORM=offscreen"
set "PYTHONPATH=%~dp0desktop;%~dp0"
"%LYA_PY%" -B -m unittest desktop.check_ui.InterfaceChecks || exit /b 1
"%LYA_PY%" -B -m unittest desktop.check_experience.ExperienceChecks || exit /b 1

echo.
echo PASS: LYA offline baseline and compact interface checks completed.
exit /b 0
