@echo off
rem Run the voice-lab suite in the background and write full output to out\tests.txt
cd /d "%~dp0.."
"..\.venv-ui\Scripts\python.exe" -m unittest discover -s tests -t . -v > out\tests.txt 2>&1
