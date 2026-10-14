"""Render two invented lines for listening comparison; sends them to Edge TTS."""
import asyncio
import time
from pathlib import Path

import edge_tts

OUT = Path(__file__).resolve().parent / 'samples'
VOICE = 'en-US-AvaMultilingualNeural'
CASES = {
    'english': "Hey, I'm LYA. I'm right here with you, and your work is ready.",
    'tamil': 'வணக்கம், நான் லயா. நான் உங்களுடன் இருக்கிறேன், வேலை தயாராக உள்ளது.',
}


async def main():
    OUT.mkdir(exist_ok=True)
    for name, text in CASES.items():
        target = OUT / f'edge-ava-{name}.mp3'
        temporary = target.with_suffix('.tmp')
        started = time.perf_counter()
        try:
            await asyncio.wait_for(edge_tts.Communicate(
                text, VOICE, connect_timeout=10, receive_timeout=20
            ).save(str(temporary)), timeout=35)
            if not temporary.exists() or not 1000 < temporary.stat().st_size < 1_000_000:
                raise RuntimeError('empty or unexpectedly large audio')
            temporary.replace(target)
            print(name, target.stat().st_size, round(time.perf_counter() - started, 2))
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    asyncio.run(main())
