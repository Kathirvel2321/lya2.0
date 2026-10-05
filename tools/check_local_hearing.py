"""Fresh offline speech comparison; no files, cloud route or command dispatch."""
import argparse
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard():
    os.environ.update(HF_HUB_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                      DO_NOT_TRACK='1', NEEDLE_TELEMETRY='0', LYA_COMMAND_ASR='vosk')
    def deny_network(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'urllib.Request'):
            raise RuntimeError('Offline hearing check blocks Python networking.')
    sys.addaudithook(deny_network)


def compare(data, *, include_whisper=False, output=print):
    from audio import voice, local_whistle
    # All engines receive the same complete captured WAV, never a separate take.
    local_whistle.validate_audio(data)
    engines = [('LYA CURRENT LOCAL (VOSK)', lambda: voice.transcribe(data, offline_required=True)),
               ('CACTUS WHISTLE (EXPERIMENTAL)', lambda: local_whistle.decode(data)['text'])]
    if include_whisper:
        from audio import local_whisper
        engines.append(('WHISPER SMALL.EN (OPTIONAL)', lambda: local_whisper.transcribe(data)))
    for name, decode in engines:
        output('\nTRANSCRIBING: ' + name)
        started = time.monotonic()
        try:
            text = decode().strip()
            output('RECOGNIZED WORDS - compare with what you said:\n' + (text or '(no words)'))
        except voice.RecognitionUncertain as error:
            output('UNCERTAIN - not accepted as a command. Candidate:\n' + (error.candidate or '(no words)'))
        except KeyboardInterrupt:
            raise
        except Exception:
            output('Local decoder unavailable/failed. No fallback provider or action.')
        output('Decoder time: ' + str(round(time.monotonic() - started, 2)) + ' seconds')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-whisper', action='store_true',
                        help='Also compare the larger already-installed small English model.')
    args = parser.parse_args()
    offline_guard()
    print('OFFLINE SPEECH-TO-TEXT ONLY. No audio saved, cloud calls or LYA actions.')
    print('One question is compared by current local Vosk and tiny Whistle, sequentially.')
    print('Close LYA voice listening first. Speak naturally for under 20 seconds.')
    try:
        from audio import voice, local_whistle
        import vosk
        vosk.SetLogLevel(-1)
        local_whistle.verify_assets()  # Never download missing weights.
        input('Press Enter when ready; pause 3 seconds after your question: ')
        capture = voice._record_stream(max_seconds=30, silence=3.0, use_vad=True,
                                       on_state=lambda state: print('LISTENING' if state == 'listening' else 'HEARING', flush=True))
        if capture is None:
            print('No speech captured. Nothing decoded.')
            return 1
        compare(capture.getvalue(), include_whisper=args.include_whisper,
                output=lambda text: print(text, flush=True))
        print('\nCheck each result against your spoken words. No result was sent to LYA.')
        return 0
    except (KeyboardInterrupt, EOFError):
        print('\nStopped.')
        return 1
    except voice.RecognitionUncertain:
        print('Question reached the capture limit. No truncated question decoded.')
        return 1
    except Exception:
        print('Offline check unavailable. No download or cloud fallback attempted.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
