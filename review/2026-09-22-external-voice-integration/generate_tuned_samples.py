"""Generate public, offline-only acceptance samples for the tuned LYA persona."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'external work'))

from alya_voice.audit import Auditor
from alya_voice.runtime import Voice

OUT = Path(__file__).resolve().parent / 'samples'
OUT.mkdir(exist_ok=True)

CASES = (
    ('english-everyday', 'en', 'everyday', 'warm',
     "Hey, I'm LYA. I'm right here with you, and your work is ready."),
    ('english-joyful', 'en', 'joyful', 'cheerful',
     "That worked beautifully! The task is complete, and everything looks good."),
    ('tamil-everyday', 'ta', 'everyday', 'warm',
     'வணக்கம், நான் லயா. நான் உங்களுடன் இருக்கிறேன், வேலை தயாராக உள்ளது.'),
    ('tamil-joyful', 'ta', 'joyful', 'cheerful',
     'சூப்பர்! வேலை அழகாக முடிந்தது, எல்லாம் சரியாக இருக்கிறது.'),
)

voice = Voice(timbre='unified', keep_warm=True,
              auditor=Auditor(OUT / 'audit', enabled=False))
results = []
try:
    for name, language, style, emotion, text in CASES:
        target = OUT / (name + '.wav')
        report = voice.speak(text, language=language, style=style, emotion=emotion,
                             engine='offline_piper', allow_remote=False, play=False,
                             wav=target, allow_interjections=False, seed=21)
        results.append({'name': name, 'engine': report.engine,
                        'audio_seconds': round(report.audio_seconds, 3),
                        'first_audio_ms': round(report.first_audio_ms, 1),
                        'chunks': report.chunks})
finally:
    voice.close()

(OUT / 'metrics.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print(json.dumps(results))
