"""Render an emotional reply, then apply the measured ffmpeg realism pass.

This is the merged workflow: the shared persona + emotion director and the
safety/offline ladder from `alya_voice`, plus the telephone-band / studio polish
and pitch analysis that the owner's `lya-voice` engine proved were needed.

It is a tool, not part of the runtime, because LYA's desktop path must not spawn a
subprocess per answer. Use it to produce voice notes, call-mode audio and
acceptance samples.

Examples:
  python tools/render_realistic.py --mood warm --engine neural_edge --remote \
      --text "வணக்கம், நான் லியா. Work முடிஞ்சது."
  python tools/render_realistic.py --engine offline_piper --realism phone \
      --file script.txt --out out/call.mp3
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / 'tools') not in sys.path:
    sys.path.insert(0, str(ROOT / 'tools'))

from alya_voice import audiofile, dsp, privacy, realism          # noqa: E402
from alya_voice.emotions import EmotionTable, resolve_mood       # noqa: E402
from alya_voice.persona import load_persona                      # noqa: E402
from alya_voice.runtime import Voice                             # noqa: E402

WORK_SR = 24000
DELIVERY = ROOT / 'out' / 'realism'


def decode_to_pcm(path, sample_rate=WORK_SR):
    """MP3 -> float PCM through ffmpeg (only needed for remote engines)."""
    ffmpeg = realism.ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError('ffmpeg is required to assemble compressed speech')
    with tempfile.TemporaryDirectory(prefix='alya-decode-') as tmp:
        target = Path(tmp) / 'decoded.wav'
        result = subprocess.run(
            [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(path),
             '-ar', str(sample_rate), '-ac', '1', '-c:a', 'pcm_s16le', str(target)],
            capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError('ffmpeg decode failed: %s' % (result.stderr or '')[:200])
        return audiofile.read_wav(target)


def assemble(chunks, sample_rate=WORK_SR):
    """Chunks -> one PCM buffer, honouring the director's pause lengths."""
    pieces, seconds = [], 0.0
    for chunk in chunks:
        if chunk.decoded:
            samples = dsp.as_float(chunk.samples)
            rate = int(chunk.sample_rate)
            if rate != sample_rate:
                samples = dsp.resample_linear(samples, rate / float(sample_rate))
        else:
            samples, _ = decode_to_pcm(chunk.path, sample_rate)
        pieces.append(samples)
        seconds += len(samples) / float(sample_rate)
        if chunk.paused_after_ms:
            pieces.append(dsp.silence(chunk.paused_after_ms, sample_rate))
            seconds += chunk.paused_after_ms / 1000.0
    return dsp.concat(pieces), seconds


def render(args):
    persona = load_persona()
    emotion, style = None, args.style
    if args.mood:
        emotion, style = resolve_mood(args.mood)
    policy = privacy.Policy()
    remote = args.engine in ('neural_edge', 'cloud_edge')
    if remote and policy.remote == 'disabled':
        print('refusing: config/policy.json has remote=disabled. The speech text would leave '
              'this laptop. Set it to "opt_in" deliberately, then re-run with --remote.')
        return 2
    if remote and not args.remote:
        print('refusing: pass --remote to acknowledge that the text leaves this device.')
        return 2

    voice = Voice(persona, timbre=args.timbre, keep_warm=True, keep_remote_files=True)
    try:
        text = ' '.join(args.text) if args.text else Path(args.file).read_text(encoding='utf-8')
        plan = voice.plan(text, emotion=emotion, style=style, language=args.language,
                          seed=args.seed, allow_interjections=args.interjections)
        engine = voice._engine(args.engine, allow_remote=args.remote)
        usable, reason = (engine.available(args.remote) if engine.kind == 'remote'
                          else engine.available())
        if not usable:
            print('engine %s unavailable: %s' % (args.engine, reason))
            return 2
        started = time.perf_counter()
        if engine.kind == 'remote':
            sensitivity = privacy.classify(plan.text)[0]
            chunks = list(engine.render(plan, seed=args.seed, allow_remote=args.remote,
                                        sensitivity=sensitivity))
        else:
            chunks = list(engine.render(plan, seed=args.seed))
        render_ms = (time.perf_counter() - started) * 1000.0
        samples, speech_seconds = assemble(chunks)
    finally:
        voice.close()
    if not chunks:
        print('nothing was rendered')
        return 2

    DELIVERY.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime('%H%M%S')
    raw = DELIVERY / ('%s-%s-raw.wav' % (args.name or 'take', stamp))
    audiofile.write_wav(raw, samples, WORK_SR)
    final = Path(args.out) if args.out else DELIVERY / (
        '%s-%s-%s.mp3' % (args.name or 'take', args.realism, stamp))
    if args.realism == 'none':
        final = raw
    else:
        realism.apply(raw, final, mode=args.realism, personality=args.personality,
                      ambience=args.ambience,
                      seed=args.seed if args.seed is not None else -1,
                      sample_rate=WORK_SR)
    if not args.keep_raw and final != raw:
        raw.unlink(missing_ok=True)

    from f0_probe import measure
    metrics = {
        'engine': args.engine, 'realism': args.realism, 'personality': args.personality,
        'mood': args.mood, 'emotion': emotion, 'style': style, 'spans': len(plan.spans),
        'seed': args.seed, 'network': remote, 'render_ms': round(render_ms, 1),
        'first_audio_ms': round(chunks[0].first_audio_ms, 1), 'cached': chunks[0].cached,
        'speech_seconds': round(speech_seconds, 3), 'file': str(final),
        'pitch': measure(final),
    }
    final.with_suffix('.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    print(json.dumps(metrics, indent=2))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description='Emotional speech + realism pass (offline by default)')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--text', nargs='+')
    source.add_argument('--file')
    parser.add_argument('--mood', help='owner vocabulary: warm, happy, excited, caring, calm, shy, '
                                       'teasing, serious, sad, whisper')
    parser.add_argument('--style', help='style name (see config/persona.json)')
    parser.add_argument('--language', default='auto', choices=('auto', 'en', 'ta'))
    parser.add_argument('--engine', default='offline_piper',
                        choices=('offline_piper', 'offline_sapi', 'neural_edge', 'cloud_edge'))
    parser.add_argument('--remote', action='store_true', help='acknowledge that text leaves the device')
    parser.add_argument('--timbre', default='unified', choices=('unified', 'native'))
    parser.add_argument('--realism', default='studio', choices=realism.MODES)
    parser.add_argument('--personality', default='lya', choices=sorted(realism.PERSONALITIES))
    parser.add_argument('--no-ambience', dest='ambience', action='store_false')
    parser.add_argument('--interjections', action='store_true',
                        help='allow Tamil/English discourse markers (off by default)')
    parser.add_argument('--keep-raw', action='store_true', help='keep the unprocessed take too')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--name', help='label used in the output file name')
    parser.add_argument('--out', help='final file path')
    return parser


def main(argv=None):
    return render(build_parser().parse_args(argv))


if __name__ == '__main__':
    raise SystemExit(main())
