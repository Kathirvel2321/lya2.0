"""Bounded local wake diagnostic. No recordings, transcripts, stores or network."""
import json
from pathlib import Path
import sys
import threading
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check(seconds=20, output=print):
    import numpy as np
    import sounddevice as sd
    import vosk
    import winsound
    from audio import voice

    result = dict(microphone_opened=False, sound_received=False,
                  name_detected=False, double_clap_detected=False,
                  greeting_playback_started=False, error=None)
    stopped = threading.Event()
    timer = threading.Timer(seconds, stopped.set)
    original_stream = sd.RawInputStream
    original_clap = voice.DoubleClap.feed
    clap_detected = False

    def open_metered(*args, **kwargs):
        stream = original_stream(*args, **kwargs)
        original_read = stream.read

        def read(frames):
            data, overflow = original_read(frames)
            samples = np.frombuffer(data, np.int16).astype(np.float32)
            if samples.size and np.sqrt(np.mean(samples * samples)) >= 100:
                if not result['sound_received']:
                    output('Sound is reaching the microphone.', flush=True)
                result['sound_received'] = True
            return data, overflow

        stream.read = read
        return stream

    def feed(detector, pcm):
        nonlocal clap_detected
        detected = original_clap(detector, pcm)
        clap_detected = clap_detected or detected
        return detected

    def ready():
        result['microphone_opened'] = True
        if not timer.is_alive():
            timer.start()
        output(f'LISTENING NOW: say Laya after the beep, or clap twice. Stops after {seconds} seconds.', flush=True)
        winsound.Beep(900, 120)

    def detected(_text, _quiet):
        stopped.set()  # End before command capture/transcription can start.
        result['double_clap_detected' if clap_detected else 'name_detected'] = True
        output('Wake detected. Playing the local greeting now.', flush=True)
        try:
            winsound.PlaySound(str(ROOT / 'desktop/assets/wake-greeting.wav'),
                               winsound.SND_FILENAME | winsound.SND_NODEFAULT)
            result['greeting_playback_started'] = True
        except (RuntimeError, OSError):
            result['error'] = 'Greeting playback failed'

    vosk.SetLogLevel(-1)
    try:
        with patch.object(sd, 'RawInputStream', side_effect=open_metered), \
             patch.object(voice.DoubleClap, 'feed', feed):
            voice.wake_loop(detected, clap_enabled=True, stop_event=stopped,
                            offline_required=True, on_ready=ready,
                            on_error=lambda kind: output('Input error: ' + kind, flush=True))
    except Exception as error:
        result['error'] = type(error).__name__
    finally:
        stopped.set()
        timer.cancel()
    return result


if __name__ == '__main__':
    print('Local microphone -> wake -> greeting check. Nothing is saved or uploaded.', flush=True)
    result = check()
    print(json.dumps(result, indent=2), flush=True)
    print('Playback success does not prove you heard it. Report whether the greeting was audible.', flush=True)
    sys.exit(0 if result['greeting_playback_started'] else 1)
