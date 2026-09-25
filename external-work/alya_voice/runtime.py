"""Runtime: policy -> plan -> engine ladder -> playback, with cancellation.

Defaults are deliberately offline-first and fail-closed:
  * 'auto' resolves to the best LOCAL engine; the remote voice is only used when
    a caller asks for it and the policy plus an explicit opt-in allow it.
  * Private or personal text can never reach a remote engine.
  * Neural model memory is released after each utterance unless keep_warm=True.
"""
from __future__ import annotations

import ctypes
import queue
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import audiofile, dsp, engines, privacy
from .audit import Auditor
from .cache import AudioCache
from .director import Director
from .emotions import EmotionTable
from .persona import load_persona

OUT_DIR = Path(__file__).resolve().parents[1] / 'out'


@dataclass
class Report:
    text: str
    engine: str
    spans: int
    chunks: int
    first_audio_ms: float
    total_ms: float
    audio_seconds: float
    sensitivity: str
    findings: tuple = ()
    wav: str = ''
    notes: tuple = field(default_factory=tuple)
    cancelled: bool = False

    def to_dict(self):
        return {
            'text': self.text, 'engine': self.engine, 'spans': self.spans, 'chunks': self.chunks,
            'first_audio_ms': round(self.first_audio_ms, 1), 'total_ms': round(self.total_ms, 1),
            'audio_seconds': round(self.audio_seconds, 3), 'sensitivity': self.sensitivity,
            'findings': [f.kind for f in self.findings], 'wav': self.wav,
            'notes': list(self.notes), 'cancelled': self.cancelled,
        }


def _mci(command, buffer_size=0):
    buffer = ctypes.create_unicode_buffer(buffer_size) if buffer_size else None
    ctypes.windll.winmm.mciSendStringW(command, buffer, buffer_size, None)
    return buffer.value if buffer is not None else ''


class Voice:
    """The single entry point the rest of the world should use."""

    def __init__(self, persona=None, table=None, policy=None, auditor=None, cache=None,
                 models_dir=None, timbre='unified', seed=None, keep_warm=False, log=None,
                 remote_cache_bytes=0, keep_remote_files=False):
        self.persona = persona or load_persona()
        self.table = table or EmotionTable()
        self.policy = policy or privacy.Policy()
        self.director = Director(self.persona, self.table)
        self.models_dir = models_dir
        self.timbre = timbre
        self.seed = None if seed is None else int(seed)
        self.keep_warm = bool(keep_warm)
        self.remote_cache_bytes = int(remote_cache_bytes)
        self.keep_remote_files = bool(keep_remote_files)
        self.log = log
        audit = self.policy.audit or {}
        self.auditor = auditor if auditor is not None else Auditor(
            OUT_DIR / 'audit', enabled=audit.get('enabled', True),
            store_text=audit.get('store_text', False))
        cache = self.policy.cache or {}
        self.cache = cache if isinstance(cache, AudioCache) else AudioCache(
            OUT_DIR / 'cache', enabled=cache.get('enabled', False),
            max_bytes=cache.get('max_bytes', 32 * 1024 * 1024))
        self._engines = {}
        self._cancel = threading.Event()
        self._mci = 0
        self._mci_alias = ''
        self._pcm_stream = None
        self._pcm_lock = threading.Lock()

    # -- planning -------------------------------------------------------
    def plan(self, text, **kwargs):
        return self.director.build(text, **{k: v for k, v in kwargs.items()
                                            if k in ('emotion', 'style', 'language', 'seed',
                                                     'allow_interjections')})

    def available(self, allow_remote=False):
        out = {}
        for name in engines.ENGINE_NAMES:
            try:
                engine = self._engine(name, allow_remote=allow_remote)
                out[name] = (engine.available(allow_remote) if engine.kind == 'remote'
                             else engine.available())
            except Exception as error:
                out[name] = (False, 'construction failed (%s)' % error)
        return out

    def _engine(self, name, allow_remote=False):
        if name not in self._engines:
            if name == 'offline_piper':
                self._engines[name] = engines.build(name, self.persona, models_dir=self.models_dir,
                                                    mode=self.timbre)
            elif name == 'neural_edge':
                self._engines[name] = engines.build(
                    name, self.persona, policy=self.policy, mode=self.timbre,
                    cache_bytes=self.remote_cache_bytes, keep_files=self.keep_remote_files)
            elif name == 'cloud_edge':
                self._engines[name] = engines.build(name, self.persona, policy=self.policy,
                                                    mode=self.timbre)
            else:
                self._engines[name] = engines.build(name, self.persona)
        return self._engines[name]

    def resolve(self, engine='auto', sensitivity=privacy.PUBLIC, allow_remote=False):
        """Ordered engine names to try. 'auto' never selects a remote engine."""
        preferred = 'offline_piper' if engine == 'auto' else engine
        ladder = self.policy.ladder(preferred, sensitivity, allow_remote)
        if engine == 'auto':
            ladder = [name for name in ladder
                      if self.policy.engines.get(name, {}).get('kind') == 'local']
        if not ladder:
            raise RuntimeError('no engine is allowed for sensitivity %r' % sensitivity)
        return ladder

    def _play(self, chunk):
        """Play one chunk. True if audio was actually emitted."""
        if chunk.decoded:
            return self._play_pcm(chunk)
        if chunk.path:
            return self._play_file(chunk.path)
        return False

    def _play_pcm(self, chunk):
        import sounddevice as sd
        rate = int(chunk.sample_rate)
        with self._pcm_lock:
            if self._cancel.is_set():
                return False
            if self._pcm_stream is not None and self._pcm_stream.samplerate != rate:
                self._pcm_stream.stop()
                self._pcm_stream.close()
                self._pcm_stream = None
            if self._pcm_stream is None:
                # Keep one device stream through the reply, including pauses.
                stream = sd.OutputStream(samplerate=rate, channels=1,
                                         dtype='float32', latency=0.06)
                try:
                    stream.start()
                except Exception:
                    stream.close()
                    raise
                self._pcm_stream = stream
        self._write_pcm(chunk.samples)
        return not self._cancel.is_set()

    def _write_pcm(self, samples):
        samples = dsp.as_float(samples)
        # Small blocking writes bound cancellation delay and avoid busy polling.
        with self._pcm_lock:
            stream = self._pcm_stream
            if stream is None or self._cancel.is_set():
                return
            frames = max(1, round(stream.samplerate * 0.02))
        for offset in range(0, len(samples), frames):
            with self._pcm_lock:
                if self._cancel.is_set() or self._pcm_stream is not stream:
                    break
                stream.write(samples[offset:offset + frames])

    def _close_pcm(self, abort=False):
        with self._pcm_lock:
            stream, self._pcm_stream = self._pcm_stream, None
            if stream is not None:
                try:
                    if abort or self._cancel.is_set():
                        stream.abort()
                    else:
                        stream.stop()  # Drain the final words before reporting done.
                finally:
                    stream.close()

    def _play_file(self, path):
        """Compressed audio goes through Windows MCI, so no decoder is needed."""
        self._mci += 1
        alias = 'alya%d' % self._mci
        _mci('open "%s" type mpegvideo alias %s' % (path, alias))
        self._mci_alias = alias
        try:
            _mci('play %s' % alias)
            while True:
                mode = _mci('status %s mode' % alias, 64)
                if mode not in ('playing', 'seeking'):
                    break
                if self._cancel.is_set():
                    _mci('stop %s' % alias)
                    break
                time.sleep(0.02)
        finally:
            _mci('close %s' % alias)
            self._mci_alias = ''
        return True

    @staticmethod
    def _as_pcm(chunk):
        return [dsp.as_float(chunk.samples)] if chunk.decoded else []

    def stop(self):
        """Cancel speech as soon as possible."""
        self._cancel.set()
        self._close_pcm(abort=True)
        if getattr(self, '_mci_alias', ''):
            _mci('stop %s' % self._mci_alias)

    def close(self):
        self._cancel.set()
        self._close_pcm(abort=True)
        for instance in self._engines.values():
            try:
                instance.stop()
                instance.close()
            except Exception:
                continue
        self._engines.clear()

    # -- speaking -------------------------------------------------------
    def speak(self, text, emotion=None, style=None, language='auto', engine='auto',
              allow_remote=False, play=True, wav=None, allow_interjections=True, seed=None,
              on_chunk=None):
        started = time.perf_counter()
        self._cancel.clear()
        plan = self.plan(text, emotion=emotion, style=style, language=language,
                         seed=self.seed if seed is None else seed,
                         allow_interjections=allow_interjections)
        sensitivity, findings = privacy.classify(text)
        notes = []
        if engine != 'auto':
            # An explicitly named engine is a contract: if policy refuses it, say so
            # instead of silently speaking the text through a different voice.
            decision = self.policy.decide(engine, sensitivity, allow_remote)
            if not decision.allowed:
                raise RuntimeError('engine %s refused: %s' % (engine, decision.reason))
        ladder = self.resolve(engine, sensitivity, allow_remote)
        if engine == 'auto':
            notes.append('auto selected the local engine; the remote voice was not offered')
        report = Report(text=plan.text, engine='', spans=len(plan.spans), chunks=0,
                        first_audio_ms=0.0, total_ms=0.0, audio_seconds=0.0,
                        sensitivity=sensitivity, findings=findings, notes=tuple(notes))
        if not plan.spans:
            report.notes = tuple(notes + ['nothing to say'])
            return report
        collected, played, speech_seconds = [], False, 0.0
        first_audio = None
        for name in ladder:
            instance = self._engine(name, allow_remote)
            try:
                usable, reason = (instance.available(allow_remote) if instance.kind == 'remote'
                                  else instance.available())
            except Exception as error:
                usable, reason = False, 'availability check failed (%s)' % error
            if not usable:
                notes.append('%s unavailable: %s' % (name, reason))
                continue
            try:
                speech_seconds, first_audio, played = self._consume(
                    instance, plan, play=play, collected=None if not wav else collected,
                    allow_remote=allow_remote, on_chunk=on_chunk, sensitivity=sensitivity)
                report.engine = name
                break
            except Exception as error:
                notes.append('%s failed: %s' % (name, error))
                instance.stop()
                continue
        else:
            raise RuntimeError('every engine failed: %s' % '; '.join(notes))
        report.chunks = len(plan.spans)
        report.first_audio_ms = first_audio or 0.0
        report.audio_seconds = speech_seconds
        report.cancelled = self._cancel.is_set()
        if wav and collected:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            target = (OUT_DIR / ('say-%d.wav' % time.time_ns())
                      if wav is True or str(wav) in ('', 'auto') else Path(wav))
            target.parent.mkdir(parents=True, exist_ok=True)
            report.wav = audiofile.write_wav(target, dsp.concat(collected), 22050)
        elif wav:
            notes.append('WAV export skipped: this engine returns compressed audio')
        report.notes = tuple(notes)
        report.total_ms = (time.perf_counter() - started) * 1000.0
        self.auditor.record('speak', text=plan.text, engine=report.engine,
                            spans=report.spans, audio_seconds=round(report.audio_seconds, 3),
                            first_audio_ms=round(report.first_audio_ms, 1),
                            total_ms=round(report.total_ms, 1),
                            sensitivity=sensitivity, played=played,
                            findings=[f.kind for f in findings])
        if not self.keep_warm:
            self._engines.get(report.engine, _Null()).close()
        return report

    def _consume(self, instance, plan, play, collected, allow_remote, on_chunk=None,
                 sensitivity=privacy.PUBLIC):
        """Render in a worker thread, play in this thread. Bounded queue, cancellable."""
        pending = queue.Queue(maxsize=2)
        finished = threading.Event()
        consumer_closed = threading.Event()
        failed = []

        def produce():
            try:
                if instance.kind == 'remote':
                    stream = instance.render(plan, seed=self.seed, allow_remote=allow_remote,
                                             sensitivity=sensitivity)
                else:
                    stream = instance.render(plan, seed=self.seed)
                for chunk in stream:
                    if self._cancel.is_set() or consumer_closed.is_set():
                        break
                    while not self._cancel.is_set() and not consumer_closed.is_set():
                        try:
                            pending.put(chunk, timeout=0.1)
                            break
                        except queue.Full:
                            continue
            except Exception as error:                    # surfaced to the caller
                failed.append(error)
            finally:
                finished.set()

        worker = threading.Thread(target=produce, daemon=True, name='alya-voice-render')
        worker.start()
        speech_seconds, first_audio, played = 0.0, None, False
        try:
            while True:
                if self._cancel.is_set():
                    break
                try:
                    chunk = pending.get(timeout=0.1)
                except queue.Empty:
                    if finished.is_set() and pending.empty():
                        break
                    continue
                first_audio = first_audio if first_audio is not None else chunk.first_audio_ms
                speech_seconds += chunk.seconds
                if on_chunk is not None:
                    on_chunk(chunk)
                if play:
                    played = self._play(chunk) or played
                pcm = self._as_pcm(chunk)
                if collected is not None:
                    collected.extend(pcm)
                if chunk.paused_after_ms and not self._cancel.is_set():
                    pause = chunk.paused_after_ms / 1000.0
                    # Only pad a pause into the PCM buffer when this chunk actually
                    # produced decoded audio. Path-only engines (e.g. the remote MP3
                    # stream) must not turn a silent gap into an exported WAV.
                    if collected is not None and pcm:
                        collected.append(dsp.silence(chunk.paused_after_ms, 22050))
                    if play:
                        if self._pcm_stream is not None and chunk.decoded:
                            self._write_pcm(dsp.silence(min(chunk.paused_after_ms, 1200),
                                                       chunk.sample_rate))
                        else:
                            self._cancel.wait(min(pause, 1.2))
        finally:
            consumer_closed.set()
            try:
                self._close_pcm(abort=sys.exc_info()[0] is not None)
            finally:
                if self._cancel.is_set():
                    instance.stop()
                worker.join(timeout=3)
                if worker.is_alive():
                    instance.stop()
        if failed:
            raise failed[0]
        return speech_seconds, first_audio, played


class _Null:
    def close(self):
        pass
