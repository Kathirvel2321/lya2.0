"""Fresh speech -> visible text only. Never accepts/uploads a saved recording."""
import argparse
import getpass
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Reuse installed microphone/VAD libraries without changing the desktop environment.
# The pilot's own Riva/protobuf packages retain precedence.
if Path(sys.prefix).name == '.venv-asr':
    sys.path.append(str(ROOT / '.venv-ui/Lib/site-packages'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-fresh-audio-to-nvidia', action='store_true',
                        help='Explicitly allow fresh ordinary speech to NVIDIA for this check.')
    parser.add_argument('--model', choices=('parakeet', 'whisper', 'parakeet-ctc'), default='parakeet',
                        help='Test this specific hosted model without fallback.')
    args = parser.parse_args()
    if not args.allow_fresh_audio_to_nvidia:
        parser.error('Disabled: explicit fresh-audio permission is required.')
    print('\nLYA - NVIDIA ' + args.model.upper() + ' SPEECH TEST')
    print('Speech-to-text check only. No LYA replies or device actions. No audio saved.')
    print('NVIDIA receives this fresh audio. Use ordinary, non-confidential speech.')
    print('Use the SAME NVIDIA API key from your successful Parakeet test.')
    print('Paste the key at the hidden prompt. No characters will appear; then press Enter.')
    print('No file upload is needed. Do not put the key in chat.')
    print('Close LYA voice listening first to avoid competing microphone access.')
    try:
        key = os.environ.get('NVIDIA_API_KEY', '').strip() or getpass.getpass('Paste NVIDIA API key here (hidden), then Enter: ').strip()
    except (KeyboardInterrupt, EOFError):
        print('\nStopped before microphone access.')
        return 1
    if not key:
        print('No key configured. Microphone not opened.')
        return 1
    try:
        import riva.client  # Check optional dependency before collecting audio.
        from audio import voice, nvidia_asr
        input('Press Enter when ready. Speak naturally; pause 3 seconds when finished: ')
        capture = voice._record_stream(max_seconds=120, silence=3.0, use_vad=True,
                                       on_state=lambda state: print('LISTENING' if state == 'listening' else 'HEARING', flush=True))
        if capture is None:
            print('No speech captured. Nothing sent.')
            return 1
        print('TRANSCRIBING', flush=True)
        text = nvidia_asr.transcribe(capture.getvalue(), remote_allowed=True, api_key=key,
                                    model=args.model, allow_backup=False)
        print('\nRECOGNIZED WORDS (check against what you actually said):\n' + text)
        return 0
    except KeyboardInterrupt:
        print('\nStopped.')
        return 1
    except ImportError:
        print('Optional client missing. Install requirements-nvidia-speech.txt before this check.')
        return 1
    except Exception:
        print('Speech check failed. No answer or device action executed; no model fallback in this diagnostic.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
