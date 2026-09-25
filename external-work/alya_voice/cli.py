"""Command line: a small toolkit for inspecting, speaking, benchmarking and
auditing the voice. Nothing here changes LYA or any project file."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import privacy, realism, __version__
from .persona import load_persona
from .runtime import OUT_DIR, Voice


def _use_utf8_stdout():
    """Tamil must not crash on a cp1252 Windows console.

    Python inherits the console code page; a legacy code page cannot encode
    Tamil, so printing any Tamil plan or transcript raises UnicodeEncodeError.
    Reconfiguring the streams keeps the CLI usable without changing the console.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            continue


_use_utf8_stdout()

_COLOURS = {'red': '31', 'green': '32', 'yellow': '33', 'blue': '34', 'magenta': '35',
            'cyan': '36', 'grey': '90', 'bold': '1'}


def paint(text, colour=None):
    if colour is None or not sys.stdout.isatty():
        return str(text)
    return '\033[%sm%s\033[0m' % (_COLOURS[colour], text)


def ok(flag):
    return paint('OK', 'green') if flag else paint('MISSING', 'red')


def make_voice(args):
    persona = load_persona(getattr(args, 'persona', None))
    return Voice(persona, models_dir=getattr(args, 'models', None),
                 timbre=getattr(args, 'timbre', 'unified'),
                 seed=getattr(args, 'seed', None), keep_warm=getattr(args, 'keep_warm', False))


def resolve_delivery(args):
    """(--emotion, --style) honouring the owner's mood vocabulary as a fallback."""
    emotion, style = getattr(args, 'emotion', None), getattr(args, 'style', None)
    mood = getattr(args, 'mood', None)
    if mood:
        from .emotions import resolve_mood
        mood_emotion, mood_style = resolve_mood(mood)
        emotion = emotion or mood_emotion
        style = style or mood_style
    return emotion, style


def cmd_doctor(args):
    voice = make_voice(args)
    print(paint('ALYA voice lab %s' % __version__, 'bold'))
    print('persona     %s, %d, %s, base f0 %.0f Hz, languages %s' % (
        voice.persona.name, voice.persona.age, voice.persona.gender, voice.persona.base_f0_hz,
        '/'.join(voice.persona.languages)))
    print('styles      %s' % ', '.join(voice.persona.style_names))
    print('emotions    %d defined' % len(voice.table.names))
    print('moods       %s' % ', '.join(sorted(__import__('alya_voice.emotions',
                                                         fromlist=['MOOD_PRESETS']).MOOD_PRESETS)))
    print('policy      remote=%s, fallback=%s' % (voice.policy.remote, ' -> '.join(voice.policy.fallback_order)))
    print('audit       %s (raw text stored: %s)' % (voice.auditor.path, voice.auditor.store_text))
    print('cache       enabled=%s at %s' % (voice.cache.enabled, voice.cache.directory))
    print('timbre      %s' % voice.timbre)
    print('realism     %s' % (realism.available()[1] if True else ''))
    print('')
    for name, (usable, reason) in voice.available(allow_remote=args.remote).items():
        print('%-14s %-6s %s' % (name, ok(usable), reason))
    print('')
    print('hint        ' + paint("engine 'auto' is always local; the neural voice needs "
                                "--engine neural_edge --remote and policy remote=opt_in", 'grey'))
    print('hint        ' + paint('phone/studio polish: tools/render_realistic.py --realism phone',
                                'grey'))
    voice.close()
    return 0


def cmd_plan(args):
    voice = make_voice(args)
    emotion, style = resolve_delivery(args)
    plan = voice.plan(' '.join(args.text), emotion=emotion, style=style,
                      language=args.language, seed=args.seed)
    print(paint('%d span(s), dominant emotion %s, style %s' % (
        len(plan.spans), plan.emotion, plan.style), 'bold'))
    for line in plan.lines():
        print(line)
    print('')
    print(paint(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)[:4000], 'grey'))
    return 0


def cmd_say(args):
    if getattr(args, 'realism', 'none') != 'none':
        # Polished output needs ffmpeg assembly, which lives in the tool (never in the
        # desktop runtime path). Delegate so there is still one command to remember.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
        import render_realistic
        argv = ['--text', *args.text, '--engine', args.engine, '--realism', args.realism,
                '--personality', args.personality, '--timbre', args.timbre,
                '--language', args.language]
        if args.mood:
            argv += ['--mood', args.mood]
        if args.style:
            argv += ['--style', args.style]
        if args.remote:
            argv += ['--remote']
        if args.seed is not None:
            argv += ['--seed', str(args.seed)]
        if not args.ambience:
            argv += ['--no-ambience']
        if args.wav not in (None, True):
            argv += ['--out', str(args.wav)]
        return render_realistic.main(argv)
    voice = make_voice(args)
    emotion, style = resolve_delivery(args)
    report = voice.speak(' '.join(args.text), emotion=emotion, style=style,
                         language=args.language, engine=args.engine,
                         allow_remote=args.remote, play=not args.silent,
                         wav=args.wav, allow_interjections=not args.no_interjections,
                         seed=args.seed)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    voice.close()
    return 0


def cmd_redact(args):
    text = ' '.join(args.text)
    level, findings = privacy.classify(text)
    policy = privacy.Policy()
    print('sensitivity %s' % paint(level, 'yellow' if level != 'public' else 'green'))
    for finding in findings:
        print('  %-16s %-9s -> %s' % (finding.kind, finding.sensitivity, finding.preview))
    redacted, _ = privacy.redact(text)
    print('redacted   %s' % redacted)
    for engine in ('offline_piper', 'offline_sapi', 'cloud_edge'):
        decision = policy.decide(engine, level, allow_remote=True)
        print('  %-14s %-6s %s' % (engine, ok(decision.allowed), decision.reason))
    return 0


def cmd_voices(args):
    voice = make_voice(args)
    print(json.dumps(voice.persona.voices, ensure_ascii=False, indent=2))
    if args.list_remote:
        import asyncio
        import edge_tts
        entries = asyncio.run(edge_tts.list_voices())
        print('')
        print(paint('remote voices matching %s (live list, network used)' % args.list_remote, 'grey'))
        for entry in entries:
            if args.list_remote.lower() in entry['ShortName'].lower():
                print('  %-40s %s' % (entry['ShortName'], entry['Gender']))
    return 0


REEL = (
    ('warm', "Hey, I'm Alya. I'm right here whenever you need me, and I'll keep it short."),
    ('cheerful', "Good news. The backup finished, and all 1,204 files are safe."),
    ('playful', "You told me to be quieter at night. So, fine, I'll whisper. Sort of."),
    ('serious', "Careful. That page asks for your password. I will not open it."),
    ('worried', "The battery is at 8 percent, and the charger is not connected."),
    ('sympathetic', "You sound tired. That was a hard day. We can finish this tomorrow."),
    ('tired', "It is 2:40 in the morning. Even I want to sleep."),
    ('surprised', "Wait, really? You already fixed it yourself?"),
    ('warm', "வணக்கம், நான் அல்யா. உங்களுக்கு என்ன உதவி வேண்டும்?"),
    ('cheerful', "சூப்பர்! உங்கள் கோப்புகள் எல்லாம் தயாராக உள்ளன."),
    ('serious', "முக்கியம். அந்த இணைப்பை திறக்காதீர்கள்."),
    ('curious', "இன்னிக்கு எப்படி இருக்கிறீர்கள்? சொல்லுங்க."),
)

BENCH = {
    'en-neutral': ('neutral', "Good evening. Your laptop finished the backup four minutes ago, "
                              "and nothing needs your attention right now."),
    'en-cheerful': ('cheerful', "That worked. The report is ready, and every number matches."),
    'en-serious': ('serious', "Important. Do not open that link until I check it."),
    'ta-warm': ('warm', "வணக்கம். உங்கள் கோப்புகள் தயாராக உள்ளன."),
    'ta-cheerful': ('cheerful', "சூப்பர்! வேலை முடிந்தது."),
    'private-block': (None, "My password is hunter2 and my card is 4111 1111 1111 1111."),
}


def peak_working_set_mb():
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]

    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    current_process = ctypes.windll.kernel32.GetCurrentProcess
    current_process.restype = wintypes.HANDLE
    get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    get_memory.restype = wintypes.BOOL
    if not get_memory(current_process(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    return round(counters.PeakWorkingSetSize / (1024.0 * 1024.0), 1)


def cmd_demo(args):
    voice = make_voice(args)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(paint('voice reel -> %s' % OUT_DIR, 'bold'))
    mood_emotion, mood_style = (resolve_mood(args.mood) if args.mood else (None, None))
    made = []
    try:
        for index, (emotion, text) in enumerate(REEL):
            target = OUT_DIR / ('reel-%02d-%s.wav' % (index + 1, emotion))
            report = voice.speak(
                text,
                emotion=mood_emotion if args.mood else (None if args.infer else emotion),
                style=mood_style or args.style,
                engine=args.engine, allow_remote=args.remote, play=not args.silent,
                wav=target, seed=None if args.seed is None else args.seed + index)
            made.append(report.wav)
            print('%2d %-14s %-12s %7.0f ms  %5.2f s audio  %s' % (
                index + 1, report.engine, emotion, report.total_ms, report.audio_seconds,
                Path(report.wav).name if report.wav else report.notes))
    finally:
        voice.close()
    print(paint('%d file(s) written. Listen to them before trusting any claim about naturalness.'
                % len(made), 'cyan'))
    return 0


def cmd_bench(args):
    voice = make_voice(args)
    results = {}
    print(paint('benchmarking %s (timbre %s)' % (args.engine, args.timbre), 'bold'))
    try:
        for name, (emotion, text) in BENCH.items():
            target = OUT_DIR / ('bench-%s-%s.wav' % (args.engine, name))
            started = time.perf_counter()
            report = voice.speak(text, emotion=emotion, engine=args.engine,
                                 allow_remote=args.remote, play=False, wav=target, seed=args.seed)
            results[name] = dict(report.to_dict(),
                                 rtf=round(report.total_ms / max(report.audio_seconds * 1000.0, 1.0), 3),
                                 wall_ms=round((time.perf_counter() - started) * 1000.0, 1))
            print('%-15s %-14s %7.0f ms  %5.2f s audio  rtf %5.3f  %s' % (
                name, report.engine, report.total_ms, report.audio_seconds,
                results[name]['rtf'], report.notes if report.notes else ''))
    finally:
        voice.close()
    payload = {'engine': args.engine, 'timbre': args.timbre,
               'when': time.strftime('%Y-%m-%dT%H:%M:%S'),
               'peak_working_set_mb': peak_working_set_mb(), 'results': results}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / ('bench-%s-%s.json' % (args.engine, time.strftime('%Y%m%d-%H%M%S')))
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(paint('wrote %s (peak working set %s MB)' % (target, payload['peak_working_set_mb']), 'cyan'))
    return 0


def cmd_remote_probe(args):
    from .engines import build
    policy = privacy.Policy()
    if policy.remote == 'disabled':
        print(paint('refusing: config/policy.json has remote=disabled.', 'red'))
        print(paint('Change it to "opt_in" deliberately, then re-run with --remote. '
                    'Speech text would leave this laptop.', 'grey'))
        return 2
    if not args.remote:
        print(paint('refusing: re-run with --remote to acknowledge that text leaves the device.', 'red'))
        return 2
    engine = build('cloud_edge', load_persona(args.persona), policy=policy, mode=args.timbre)
    results = []
    try:
        for language, text in (('en', 'Hey, this is a remote voice quality check.'),
                               ('ta', 'வணக்கம், இது ஒரு குரல் சோதனை.')):
            results.append(engine.probe(text, language))
            print(json.dumps(results[-1], ensure_ascii=False))
    finally:
        engine.close()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / ('remote-probe-%s.json' % time.strftime('%Y%m%d-%H%M%S'))
    target.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(paint('wrote %s - listen to the MP3s; this probe proves delivery, not quality.' % target,
                'cyan'))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog='alya-voice',
                                     description='ALYA voice lab (isolated from the LYA app)')
    parser.add_argument('--version', action='version', version='alya-voice %s' % __version__)
    parser.add_argument('--persona', help='path to a persona JSON override')
    parser.add_argument('--models', help='directory holding the Piper .onnx models')
    parser.add_argument('--timbre', choices=('unified', 'native'), default='unified',
                        help='one timbre for both languages (default) or one model per language')
    parser.add_argument('--seed', type=int, help='reproducible prosody when set')
    parser.add_argument('--keep-warm', action='store_true', help='keep model memory between calls')
    subs = parser.add_subparsers(dest='command', required=True)

    doctor = subs.add_parser('doctor', help='environment, engines and policy')
    doctor.add_argument('--remote', action='store_true', help='also check remote usability')
    doctor.set_defaults(func=cmd_doctor)

    plan = subs.add_parser('plan', help='show the prosody plan without speaking')
    plan.add_argument('text', nargs='+')
    plan.add_argument('--emotion')
    plan.add_argument('--style')
    plan.add_argument('--mood', help='owner vocabulary (warm, happy, excited, caring, calm, '
                                     'shy, teasing, serious, sad, whisper)')
    plan.add_argument('--language', default='auto')
    plan.set_defaults(func=cmd_plan)

    say = subs.add_parser('say', help='speak text')
    say.add_argument('text', nargs='+')
    say.add_argument('--emotion')
    say.add_argument('--style')
    say.add_argument('--mood', help='owner vocabulary (see plan --help)')
    say.add_argument('--realism', default='none', choices=realism.MODES,
                     help='none = speak now (default); studio/phone/raw write a polished file '
                          'through ffmpeg via tools/render_realistic.py')
    say.add_argument('--personality', default='lya', choices=sorted(realism.PERSONALITIES))
    say.add_argument('--no-ambience', dest='ambience', action='store_false')
    say.add_argument('--language', default='auto')
    say.add_argument('--engine', default='auto')
    say.add_argument('--remote', action='store_true')
    say.add_argument('--silent', action='store_true', help='render without playing')
    say.add_argument('--wav', nargs='?', const=True, default=None)
    say.add_argument('--no-interjections', action='store_true')
    say.set_defaults(func=cmd_say)

    redact = subs.add_parser('redact', help='classify text and show routing decisions')
    redact.add_argument('text', nargs='+')
    redact.set_defaults(func=cmd_redact)

    voices = subs.add_parser('voices', help='voice mapping per engine')
    voices.add_argument('--list-remote', nargs='?', const='ta-IN', default=None,
                        help='query the live Edge voice list (network used)')
    voices.set_defaults(func=cmd_voices)

    demo = subs.add_parser('demo', help='write the multi-emotion bilingual voice reel')
    demo.add_argument('--engine', default='auto')
    demo.add_argument('--style')
    demo.add_argument('--mood', help='force one mood from the owner vocabulary for every line')
    demo.add_argument('--remote', action='store_true')
    demo.add_argument('--silent', action='store_true')
    demo.add_argument('--infer', action='store_true', help='use cue inference instead of fixed tags')
    demo.set_defaults(func=cmd_demo)

    bench = subs.add_parser('bench', help='measure latency, audio seconds and memory')
    bench.add_argument('--engine', default='offline_piper')
    bench.add_argument('--remote', action='store_true')
    bench.set_defaults(func=cmd_bench)

    probe = subs.add_parser('remote-probe', help='opt-in live remote check (text leaves the device)')
    probe.add_argument('--remote', action='store_true')
    probe.set_defaults(func=cmd_remote_probe)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print(paint('cancelled', 'yellow'))
        return 130


if __name__ == '__main__':                                # pragma: no cover
    sys.exit(main())
