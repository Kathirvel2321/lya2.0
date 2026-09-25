import json
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alya_voice import audiofile, privacy
from alya_voice.audit import Auditor
from alya_voice.cache import AudioCache
from alya_voice.engines.base import Chunk, EngineError
from alya_voice.persona import load_persona
from alya_voice.runtime import Voice

SR = 22050


class FakeEngine:
    kind = 'local'

    def __init__(self, name, fail=False, delay=0.0, path_only=False, limit=None,
                 unavailable=False):
        self.name = name
        self.fail = fail
        self.delay = delay
        self.path_only = path_only
        self.limit = limit
        self.unavailable = unavailable
        self.closed = False
        self.stopped = False

    def available(self, *args, **kwargs):
        # `fail` simulates an engine that loads fine but errors during synthesis;
        # `unavailable` simulates one that reports itself unusable up front.
        if getattr(self, 'unavailable', False):
            return (False, 'fake engine unavailable')
        return (True, 'fake engine')

    def render(self, plan, seed=0, **kwargs):
        if self.fail:
            raise EngineError('fake failure in %s' % self.name)
        spans = plan.spans if self.limit is None else plan.spans[:self.limit]
        for span in spans:
            if self.stopped:
                return
            if self.delay:
                time.sleep(self.delay)
            if self.path_only:
                yield Chunk(index=span.index, engine=self.name, text=span.text,
                            path='C:/fake/span-%d.mp3' % span.index, seconds=0.3,
                            paused_after_ms=span.pause_after_ms, language=span.language,
                            emotion=span.emotion, first_audio_ms=1.0)
            else:
                samples = (np.sin(np.linspace(0, 60, int(SR * 0.2))) * 0.2).astype(np.float32)
                yield Chunk(index=span.index, engine=self.name, text=span.text, samples=samples,
                            sample_rate=SR, seconds=0.2, paused_after_ms=span.pause_after_ms,
                            language=span.language, emotion=span.emotion, first_audio_ms=1.0,
                            synth_ms=2.0)

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


def make_voice(folder, policy=None, keep_warm=False):
    persona = load_persona()
    return Voice(persona, policy=policy, keep_warm=keep_warm,
                 auditor=Auditor(Path(folder) / 'audit', enabled=True),
                 cache=AudioCache(Path(folder) / 'cache', enabled=False))


class VoiceRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='alya-voice-test-')
        self.voice = make_voice(self.folder)
        self.voice._engines['offline_piper'] = FakeEngine('offline_piper')
        self.voice._engines['offline_sapi'] = FakeEngine('offline_sapi')

    def test_offline_render_writes_audio_and_reports_honestly(self):
        target = Path(self.folder) / 'say.wav'
        report = self.voice.speak('The backup finished. Everything is fine.',
                                  engine='auto', play=False, wav=target, allow_interjections=False)
        self.assertEqual(report.engine, 'offline_piper')
        self.assertEqual(report.chunks, report.spans)
        self.assertGreater(report.audio_seconds, 0.0)
        self.assertGreater(report.first_audio_ms, 0.0)
        self.assertEqual(report.sensitivity, 'public')
        self.assertTrue(Path(report.wav).exists())
        samples, rate = audiofile.read_wav(report.wav)
        self.assertEqual(rate, SR)
        self.assertGreater(audiofile.duration_seconds(samples, rate), report.audio_seconds * 0.8)
        self.assertTrue(any('remote voice was not offered' in note for note in report.notes))
        self.voice.close()

    def test_caption_callback_precedes_each_chunk_playback(self):
        order = []
        self.voice._play = lambda chunk: order.append(('play', chunk.text)) or True
        report = self.voice.speak(
            'First phrase. Second phrase.', engine='auto', play=True,
            allow_interjections=False,
            on_chunk=lambda chunk: order.append(('caption', chunk.text)))
        self.assertGreaterEqual(report.chunks, 2)
        self.assertEqual(len(order), report.chunks * 2)
        for index in range(0, len(order), 2):
            self.assertEqual(order[index][0], 'caption')
            self.assertEqual(order[index + 1][0], 'play')
            self.assertEqual(order[index][1], order[index + 1][1])
        self.voice.close()

    def test_auto_never_selects_the_remote_engine(self):
        self.assertNotIn('cloud_edge', self.voice.resolve('auto', 'public'))
        self.assertEqual(self.voice.resolve('auto', 'public'), ['offline_piper', 'offline_sapi'])

    def test_pcm_reply_reuses_device_including_pauses_and_drains_final_audio(self):
        stream = Mock(samplerate=SR)
        events = []
        stream.write.side_effect = lambda data: events.append(('audio', len(data)))
        stream.stop.side_effect = lambda: events.append(('drain', 0))
        stream.close.side_effect = lambda: events.append(('close', 0))
        with patch('sounddevice.OutputStream', return_value=stream) as open_stream:
            report = self.voice.speak('First phrase. Second phrase.', play=True,
                                      allow_interjections=False,
                                      on_chunk=lambda chunk: events.append(('caption', chunk.text)))
        open_stream.assert_called_once()
        stream.start.assert_called_once()
        stream.stop.assert_called_once()
        stream.close.assert_called_once()
        stream.abort.assert_not_called()
        self.assertEqual(len([e for e in events if e[0] == 'caption']), report.chunks)
        self.assertEqual(events[-2:], [('drain', 0), ('close', 0)])
        self.assertGreater(sum(e[1] for e in events if e[0] == 'audio'), report.audio_seconds * SR)
        self.assertLessEqual(max(e[1] for e in events if e[0] == 'audio'), round(SR * 0.02))
        self.assertIsNone(self.voice._pcm_stream)

    def test_pcm_cancel_aborts_without_playing_remaining_blocks(self):
        stream = Mock(samplerate=SR)
        stream.write.side_effect = lambda data: self.voice._cancel.set()
        with patch('sounddevice.OutputStream', return_value=stream):
            report = self.voice.speak('First phrase. Second phrase.', play=True,
                                      allow_interjections=False)
        self.assertTrue(report.cancelled)
        stream.write.assert_called_once()
        stream.abort.assert_called_once()
        stream.close.assert_called_once()
        stream.stop.assert_not_called()

    def test_stop_during_pcm_write_closes_without_reusing_closed_stream(self):
        writing = threading.Event()
        release = threading.Event()
        stopped = threading.Event()
        stream = Mock(samplerate=SR)

        def write(_data):
            writing.set()
            self.assertTrue(release.wait(2))

        stream.write.side_effect = write

        def cancel():
            self.assertTrue(writing.wait(2))
            self.voice.stop()
            stopped.set()

        canceller = threading.Thread(target=cancel)
        canceller.start()
        timer = threading.Timer(0.1, release.set)
        timer.start()
        try:
            with patch('sounddevice.OutputStream', return_value=stream):
                report = self.voice.speak('First phrase. Second phrase.', play=True,
                                          allow_interjections=False)
        finally:
            release.set()
            canceller.join(2)
            timer.join(2)
        self.assertTrue(stopped.is_set())
        self.assertTrue(report.cancelled)
        stream.abort.assert_called_once()
        stream.close.assert_called_once()
        stream.write.assert_called_once()

    def test_pcm_device_error_closes_stream_and_stops_producer(self):
        stream = Mock(samplerate=SR)
        stream.write.side_effect = RuntimeError('fake disconnected device')
        plan = self.voice.plan('One. Two. Three. Four. Five. Six.')
        with patch('sounddevice.OutputStream', return_value=stream):
            with self.assertRaisesRegex(RuntimeError, 'disconnected'):
                self.voice._consume(self.voice._engines['offline_piper'], plan,
                                    play=True, collected=None, allow_remote=False)
        stream.abort.assert_called_once()
        stream.close.assert_called_once()
        self.assertFalse(any(t.name == 'alya-voice-render' for t in threading.enumerate()))

    def test_private_text_cannot_be_sent_remotely(self):
        with self.assertRaises(RuntimeError):
            self.voice.speak('my password is hunter2', engine='cloud_edge', allow_remote=True)
        self.voice.close()

    def test_engine_failure_falls_back_to_the_next_local_engine(self):
        self.voice._engines['offline_piper'] = FakeEngine('offline_piper', fail=True)
        report = self.voice.speak('Hello there.', engine='auto', play=False)
        self.assertEqual(report.engine, 'offline_sapi')
        self.assertTrue(any('offline_piper failed' in note for note in report.notes))
        self.voice.close()

    def test_all_engines_failing_is_an_error_not_silence(self):
        self.voice._engines['offline_piper'] = FakeEngine('offline_piper', fail=True)
        self.voice._engines['offline_sapi'] = FakeEngine('offline_sapi', fail=True)
        with self.assertRaises(RuntimeError):
            self.voice.speak('Hello there.', engine='auto', play=False)
        self.voice.close()

    def test_audit_never_stores_the_spoken_text(self):
        self.voice.speak('The secret meeting is at nine.', engine='auto', play=False)
        rows = self.voice.auditor.tail(5)
        self.assertTrue(rows)
        row = rows[-1]
        self.assertEqual(row['kind'], 'speak')
        self.assertEqual(len(row['text']), 16)
        self.assertNotIn('secret', json.dumps(row))
        self.voice.close()

    def test_stop_cancels_and_returns_quickly(self):
        self.voice._engines['offline_piper'] = FakeEngine('offline_piper', delay=0.25, limit=20)
        self.voice._engines['offline_sapi'] = FakeEngine('offline_sapi', delay=0.25, limit=20)
        reports = []

        def run():
            reports.append(self.voice.speak('One. Two. Three. Four. Five. Six. Seven. Eight.',
                                            engine='auto', play=False, allow_interjections=False))

        worker = threading.Thread(target=run)
        started = time.perf_counter()
        worker.start()
        time.sleep(0.3)
        self.voice.stop()
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertLess(time.perf_counter() - started, 4.0)
        self.assertTrue(reports[0].cancelled)
        self.voice.close()

    def test_remote_engine_needs_opt_in_and_skips_wav_export(self):
        payload = json.loads(Path(privacy.Policy().source).read_text(encoding='utf-8'))
        payload['remote'] = 'opt_in'
        policy_path = Path(self.folder) / 'policy.json'
        policy_path.write_text(json.dumps(payload), encoding='utf-8')
        self.voice.policy = privacy.Policy(policy_path)
        self.voice._engines['cloud_edge'] = FakeEngine('cloud_edge', path_only=True)
        with self.assertRaises(RuntimeError):
            self.voice.speak('Hello from the cloud.', engine='cloud_edge', allow_remote=False)
        report = self.voice.speak('Hello from the cloud.', engine='cloud_edge', allow_remote=True,
                                  play=False, wav=Path(self.folder) / 'unused.wav')
        self.assertEqual(report.engine, 'cloud_edge')
        self.assertEqual(report.wav, '')
        self.assertTrue(any('WAV export skipped' in note for note in report.notes))
        self.voice.close()

    def test_private_text_stays_local_even_with_opt_in(self):
        payload = json.loads(Path(privacy.Policy().source).read_text(encoding='utf-8'))
        payload['remote'] = 'opt_in'
        policy_path = Path(self.folder) / 'policy.json'
        policy_path.write_text(json.dumps(payload), encoding='utf-8')
        policy = privacy.Policy(policy_path)
        self.assertEqual(policy.decide('cloud_edge', 'private', allow_remote=True).allowed, False)
        self.assertEqual(policy.ladder('cloud_edge', 'private', allow_remote=True),
                         ['offline_piper', 'offline_sapi'])

    def test_report_is_json_serialisable(self):
        report = self.voice.speak('A short answer.', engine='auto', play=False)
        json.dumps(report.to_dict())
        self.voice.close()

    def test_close_releases_engines_and_blocks_nothing(self):
        self.voice.close()
        self.assertTrue(self.voice._engines == {})

    def test_close_aborts_any_open_pcm_stream(self):
        stream = Mock(samplerate=SR)
        self.voice._pcm_stream = stream
        self.voice.close()
        stream.abort.assert_called_once()
        stream.close.assert_called_once()
        self.assertIsNone(self.voice._pcm_stream)


if __name__ == '__main__':
    unittest.main()
