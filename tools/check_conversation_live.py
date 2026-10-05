"""Owner-ready local voice trial. No files, cloud, enrollment or protected stores.

Only run while the owner is ready and the desktop listener is not running.
"""
import os
import argparse
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio import voice
from desktop.setup_speech import _load_voice


def say(renderer, text):
    voice._SPEAKING.set()
    try:
        renderer.speak(text, engine='offline_piper', play=True, allow_interjections=False)
    finally:
        voice._SPEAKING.clear()


def main():
    import vosk
    import winsound
    vosk.SetLogLevel(-1)
    parser = argparse.ArgumentParser()
    parser.add_argument('--command-model', type=Path)
    parser.add_argument('--skip-wake', action='store_true', help='Isolate question/interrupt after owner readiness')
    args = parser.parse_args()
    path = Path.home() / 'AppData/Local/LYA/models/vosk-model-small-en-us-0.15'
    os.environ['LYA_VOSK_MODEL'] = str(path)
    model = vosk.Model(str(path))
    command_model = vosk.Model(str(args.command_model)) if args.command_model else model
    voice._local = model
    renderer = _load_voice(keep_warm=True)
    stopped = threading.Event()
    timer = threading.Timer(20, stopped.set)
    try:
        renderer._engine('offline_piper')._voice('en')
        def ready():
            print('WAKE WINDOW OPEN: say LYA or clap twice now.', flush=True)
            winsound.Beep(850, 180)
        woke = True
        if not args.skip_wake:
            timer.start()
            woke = voice._wait_for_wake(model, True, stopped, ready)
            timer.cancel()
        print('Wake bypassed for isolated question test.' if args.skip_wake
              else 'Wake detected: ' + str(woke), flush=True)
        if not woke:
            return 1
        say(renderer, 'We will count down with five low beeps. After the high beep, please ask what time is it. Keep the headset microphone close to your mouth.')
        for _ in range(5):
            winsound.Beep(450, 100)
            time.sleep(0.7)
        voice._local = command_model
        os.environ['LYA_VOSK_MODEL'] = str(args.command_model or path)
        print('QUESTION WINDOW OPEN: ask what time is it.', flush=True)
        def capture_state(state):
            print('Capture: ' + state, flush=True)
            if state == 'listening':
                winsound.Beep(1200, 250)
        captured = voice._record_stream(max_seconds=30, silence=1.2, endpoint_model=command_model,
                                        on_state=capture_state, use_vad=True)
        text = ''
        if captured is not None and captured is not voice._CLAP_WAKE:
            try:
                text = voice.transcribe(captured.getvalue(), offline_required=True)
                print('You asked: ' + text, flush=True)
            except voice.RecognitionUncertain as error:
                if error.candidate:
                    print('Uncertain candidate (not answered): ' + error.candidate, flush=True)
                print('Question recognition uncertain; not forwarded to the brain.', flush=True)
        captured = None
        correct = text.casefold().strip(' .?!') in ('what time is it', 'time', 'what is the time')
        print('Clock question matched: ' + str(correct), flush=True)
        if not correct:
            say(renderer, 'I did not catch the clock question clearly. We will check interruption separately.')
        say(renderer, 'In the next reply, please say stop while I am still speaking.')
        interrupted = threading.Event()
        errors = []
        answer = ('The time is ' + time.strftime('%I:%M %p') + '. ' if correct else '')
        answer += ('This is the interruption test. I will keep speaking for a short moment. '
                   'You can interrupt this reply whenever you are ready. '
                   'We are checking the local microphone and the local voice together.')
        voice._SPEAKING.set()
        def speak():
            try:
                say(renderer, answer)
            except Exception as error:
                errors.append(type(error).__name__)
            finally:
                voice._SPEAKING.clear()
        thread = threading.Thread(target=speak, daemon=True)
        print('INTERRUPTION WINDOW: say stop during the reply.', flush=True)
        def interrupt(*_):
            interrupted.set()
            renderer.stop()
            voice._SPEAKING.clear()
        timer = threading.Timer(25, lambda: (stopped.set(), renderer.stop(), voice._SPEAKING.clear()))
        timer.start()
        # Open input before beginning the reply so an early stop is not missed.
        voice._wait_for_interrupt(command_model, stopped, interrupt, on_ready=thread.start)
        timer.cancel()
        thread.join(5)
        print('Spoken interruption detected: ' + str(interrupted.is_set()), flush=True)
        print('Output worker ended: ' + str(not thread.is_alive()), flush=True)
        if errors:
            print('Output error: ' + errors[0], flush=True)
        return 0 if correct and interrupted.is_set() and not errors and not thread.is_alive() else 1
    except voice.RecognitionUncertain:
        print('Capture reached its limit; no fragment answered.', flush=True)
        return 1
    finally:
        timer.cancel()
        stopped.set()
        voice._SPEAKING.clear()
        renderer.close()


if __name__ == '__main__':
    sys.exit(main())
