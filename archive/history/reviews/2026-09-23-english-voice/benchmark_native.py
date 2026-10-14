"""Public, silent comparison of pinned English and Tamil local Piper voices."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'external-work'))

import win32api
import win32process
from alya_voice.audit import Auditor
from alya_voice.runtime import Voice

OUT = Path(__file__).resolve().parent
CASES = (
    ('english-everyday', 'en', 'everyday',
     "Hey, I'm LYA. I'm right here with you, and your work is ready."),
    ('english-joyful', 'en', 'joyful',
     'That worked beautifully! The task is complete, and everything looks good.'),
    ('tamil-everyday', 'ta', 'everyday',
     'வணக்கம், நான் லயா. நான் உங்களுடன் இருக்கிறேன், வேலை தயாராக உள்ளது.'),
)

voice = Voice(timbre='native', keep_warm=True,
              auditor=Auditor(OUT / 'audit', enabled=False))
results = []
try:
    for name, language, style, text in CASES:
        target = OUT / f'{name}.wav'
        report = voice.speak(text, language=language, style=style,
                             engine='offline_piper', allow_interjections=False,
                             play=False, wav=target)
        memory = win32process.GetProcessMemoryInfo(win32api.GetCurrentProcess())
        results.append({'name': name, 'total_ms': round(report.total_ms),
                        'first_audio_ms': round(report.first_audio_ms),
                        'audio_s': round(report.audio_seconds, 2),
                        'peak_mb': round(memory['PeakWorkingSetSize'] / 1048576),
                        'bytes': target.stat().st_size})
finally:
    voice.close()
print(json.dumps(results, ensure_ascii=False))
