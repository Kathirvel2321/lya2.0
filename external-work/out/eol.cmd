@echo off
cd /d "%~dp0.."
"..\.venv-ui\Scripts\python.exe" out\normalize_eol.py alya_voice\runtime.py alya_voice\engines\base.py alya_voice\engines\cloud_edge.py alya_voice\engines\offline_piper.py alya_voice\engines\offline_sapi.py alya_voice\cli.py alya_voice\persona.py alya_voice\director.py config\policy.json config\persona.json > out\eol.txt 2>&1
