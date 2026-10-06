"""Isolated ASR checks: synthetic PCM, fake key/client, no microphone or network."""
import io
import os
from pathlib import Path
import tempfile
import threading
import types
import unittest
from unittest.mock import MagicMock, patch
import wave

from audio import local_whistle, nvidia_asr


def wav(seconds=1, rate=16000):
    result = io.BytesIO()
    with wave.open(result, 'wb') as sound:
        sound.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        sound.writeframes(b'\x00\x00' * int(seconds * rate))
    return result.getvalue()


class WhistleSafetyTests(unittest.TestCase):
    def test_missing_asset_does_not_download(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError):
                local_whistle.verify_assets(folder)

    def test_bad_hash_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in local_whistle.HASHES:
                (Path(folder) / name).write_bytes(b'fake')
            with self.assertRaises(RuntimeError):
                local_whistle.verify_assets(folder)

    def test_complete_audio_and_no_long_turn_trimming(self):
        local_whistle.validate_audio(wav())
        from audio.voice import RecognitionUncertain
        with self.assertRaises(RecognitionUncertain):
            local_whistle.validate_audio(wav(31))
        with self.assertRaises(RuntimeError):
            local_whistle.validate_audio(wav(rate=8000))
        with self.assertRaises(RuntimeError):
            local_whistle.validate_audio(wav()[:-20])

    def test_cancelled_before_worker(self):
        stopped = threading.Event()
        stopped.set()
        with patch.object(local_whistle, 'verify_assets'), patch.object(local_whistle.subprocess, 'Popen') as start:
            with self.assertRaises(InterruptedError):
                local_whistle.decode(wav(), cancelled=stopped)
            start.assert_not_called()

    def test_limits_fail_before_audio_and_cleanup(self):
        process = MagicMock()
        process.poll.return_value = None
        with patch.object(local_whistle, 'verify_assets'), patch.object(local_whistle.subprocess, 'Popen', return_value=process) as start, patch.object(local_whistle, '_limit_worker', side_effect=RuntimeError('limits unavailable')), patch.dict(os.environ, {'NVIDIA_API_KEY': 'fake-secret'}):
            with self.assertRaises(RuntimeError):
                local_whistle.decode(wav())
            self.assertNotIn('NVIDIA_API_KEY', start.call_args.kwargs['env'])
            self.assertEqual(start.call_args.kwargs['env']['NEEDLE_TELEMETRY'], '0')
            process.kill.assert_called_once()
            process.communicate.assert_called_once_with()

    def test_timeout_kills_worker_and_closes_job(self):
        process = MagicMock()
        process.poll.return_value = None
        job = MagicMock()
        with patch.object(local_whistle, 'verify_assets'), patch.object(local_whistle.subprocess, 'Popen', return_value=process), patch.object(local_whistle, '_limit_worker', return_value=job), patch.object(local_whistle.time, 'monotonic', side_effect=[0, 31]):
            with self.assertRaises(RuntimeError):
                local_whistle.decode(wav())
        process.kill.assert_called_once()
        job.Close.assert_called_once()
        process.communicate.assert_called_once_with()

    def test_cancel_after_limits_discards_audio(self):
        stopped = threading.Event()
        process = MagicMock()
        process.poll.return_value = None
        job = MagicMock()
        def limits(child):
            stopped.set()
            return job
        with patch.object(local_whistle, 'verify_assets'), patch.object(local_whistle.subprocess, 'Popen', return_value=process), patch.object(local_whistle, '_limit_worker', side_effect=limits):
            with self.assertRaises(InterruptedError):
                local_whistle.decode(wav(), cancelled=stopped)
        job.Close.assert_called_once()
        process.communicate.assert_called_once_with()


class NvidiaSpeechTests(unittest.TestCase):
    def setUp(self):
        settings = patch.dict(os.environ, {'LYA_NVIDIA_ASR': 'parakeet'})
        settings.start()
        self.addCleanup(settings.stop)
        self.future = MagicMock()
        self.future.result.return_value = types.SimpleNamespace(results=[
            types.SimpleNamespace(alternatives=[types.SimpleNamespace(transcript='First clause.')]),
            types.SimpleNamespace(alternatives=[]),
            types.SimpleNamespace(alternatives=[types.SimpleNamespace(transcript='Second clause.')])])
        self.auth = MagicMock()
        self.auth.get_auth_metadata.return_value = [('authorization', 'Bearer fake')]
        self.service = MagicMock()
        self.service.stub.Recognize.future.return_value = self.future
        client = types.ModuleType('riva.client')
        client.Auth = MagicMock(return_value=self.auth)
        client.ASRService = MagicMock(return_value=self.service)
        client.RecognitionConfig = MagicMock()
        client.AudioEncoding = types.SimpleNamespace(LINEAR_PCM=1)
        proto = types.ModuleType('riva.client.proto')
        proto.riva_asr_pb2 = types.SimpleNamespace(RecognizeRequest=MagicMock())
        riva = types.ModuleType('riva')
        riva.client = client
        class FutureTimeoutError(Exception):
            pass
        grpc = types.ModuleType('grpc')
        grpc.FutureTimeoutError = FutureTimeoutError
        class RpcError(Exception):
            def __init__(self, code):
                self.status = code
            def code(self):
                return types.SimpleNamespace(name=self.status)
        grpc.RpcError = RpcError
        self.client = client
        self.proto = proto
        self.grpc = grpc
        mocked = patch.dict('sys.modules', {'riva': riva, 'riva.client': client, 'riva.client.proto': proto, 'grpc': grpc})
        mocked.start()
        self.addCleanup(mocked.stop)

    def run_asr(self, **kwargs):
        return nvidia_asr.transcribe(wav(), remote_allowed=True, api_key='fake', **kwargs)

    def test_explicit_permission_and_key_required(self):
        with self.assertRaises(PermissionError):
            nvidia_asr.transcribe(wav(), api_key='fake')
        with self.assertRaises(RuntimeError):
            nvidia_asr.transcribe(wav(), remote_allowed=True, api_key='')
        self.client.Auth.assert_not_called()

    def test_full_question_tls_deadline_and_cleanup(self):
        self.assertEqual(self.run_asr(), 'First clause. Second clause.')
        self.assertTrue(self.client.Auth.call_args.kwargs['use_ssl'])
        self.assertEqual(self.client.Auth.call_args.kwargs['uri'], nvidia_asr.ENDPOINT)
        self.assertEqual(self.service.stub.Recognize.future.call_args.kwargs['timeout'], 15.0)
        self.assertEqual(len(self.proto.riva_asr_pb2.RecognizeRequest.call_args.kwargs['audio']), 32000)
        self.auth.channel.close.assert_called_once()

    def test_invalid_long_or_truncated_audio_never_connects(self):
        for data in (b'invalid', wav(121), wav()[:-20], wav(rate=8000)):
            with self.assertRaises(ValueError):
                nvidia_asr.transcribe(data, remote_allowed=True, api_key='fake')
        self.client.Auth.assert_not_called()

    def test_cancel_before_connect(self):
        stopped = threading.Event()
        stopped.set()
        with self.assertRaises(InterruptedError):
            self.run_asr(cancelled=stopped)
        self.client.Auth.assert_not_called()

    def test_cancel_pending_result(self):
        stopped = threading.Event()
        def pending(timeout):
            stopped.set()
            raise self.grpc.FutureTimeoutError()
        self.future.result.side_effect = pending
        with self.assertRaises(InterruptedError):
            self.run_asr(cancelled=stopped)
        self.future.cancel.assert_called_once()
        self.auth.channel.close.assert_called_once()

    def test_failure_redacted_no_fallback(self):
        self.future.result.side_effect = RuntimeError('fake-secret payload')
        with self.assertRaises(RuntimeError) as caught:
            self.run_asr()
        self.assertNotIn('fake-secret', str(caught.exception))
        self.service.stub.Recognize.future.assert_called_once()
        self.auth.channel.close.assert_called_once()

    def test_empty_result_rejected(self):
        from audio.voice import RecognitionUncertain
        self.future.result.return_value = types.SimpleNamespace(results=[])
        with self.assertRaises(RecognitionUncertain):
            self.run_asr()

    def test_retired_primary_switches_once_to_whisper_with_correct_language(self):
        result = self.future.result.return_value
        self.future.result.side_effect = [self.grpc.RpcError('NOT_FOUND'), result]
        models = []
        self.assertEqual(self.run_asr(on_model=lambda *args: models.append(args)), 'First clause. Second clause.')
        self.assertEqual(models, [('Parakeet TDT v2', False), ('Whisper Large v3', True)])
        self.assertEqual(self.client.Auth.call_args.kwargs['metadata_args'][0][1], nvidia_asr.MODELS['whisper'][0])
        self.assertEqual(self.client.RecognitionConfig.call_args.kwargs['language_code'], 'en')
        self.assertEqual(self.client.Auth.call_count, 2)

    def test_auth_quota_bad_input_do_not_try_another_model(self):
        for code in ('UNAUTHENTICATED', 'PERMISSION_DENIED', 'RESOURCE_EXHAUSTED', 'INVALID_ARGUMENT'):
            with self.subTest(code=code):
                self.client.Auth.reset_mock()
                self.future.result.side_effect = self.grpc.RpcError(code)
                with self.assertRaises(nvidia_asr.SpeechUnavailable):
                    self.run_asr()
                self.assertEqual(self.client.Auth.call_count, 1)

    def test_all_services_unavailable_stops_at_two_requests(self):
        self.future.result.side_effect = self.grpc.RpcError('UNAVAILABLE')
        with self.assertRaises(nvidia_asr.SpeechUnavailable):
            self.run_asr()
        self.assertEqual(self.client.Auth.call_count, 2)

    def test_privacy_enabled_before_backup_sends_no_second_request(self):
        allowed = [True]
        def unavailable(timeout):
            allowed[0] = False
            raise self.grpc.RpcError('UNAVAILABLE')
        self.future.result.side_effect = unavailable
        with self.assertRaises(PermissionError):
            nvidia_asr.transcribe(wav(), remote_allowed=lambda: allowed[0], api_key='fake')
        self.assertEqual(self.client.Auth.call_count, 1)

    def test_cancel_before_backup_sends_no_second_request(self):
        stopped = threading.Event()
        def unavailable(timeout):
            stopped.set()
            raise self.grpc.RpcError('UNAVAILABLE')
        self.future.result.side_effect = unavailable
        with self.assertRaises(InterruptedError):
            self.run_asr(cancelled=stopped)
        self.assertEqual(self.client.Auth.call_count, 1)

    def test_specific_backup_diagnostic_does_not_fallback(self):
        self.future.result.side_effect = self.grpc.RpcError('UNAVAILABLE')
        with self.assertRaises(nvidia_asr.SpeechUnavailable):
            self.run_asr(model='whisper', allow_backup=False)
        self.assertEqual(self.client.Auth.call_count, 1)
        self.assertEqual(self.client.Auth.call_args.kwargs['metadata_args'][0][1], nvidia_asr.MODELS['whisper'][0])

    def test_spare_model_request_has_verified_function_id(self):
        self.run_asr(model='parakeet-ctc')
        self.assertEqual(self.client.Auth.call_args.kwargs['metadata_args'][0][1], nvidia_asr.MODELS['parakeet-ctc'][0])
        self.assertEqual(self.client.RecognitionConfig.call_args.kwargs['language_code'], 'en-US')

    def test_unknown_model_never_opens_channel(self):
        with self.assertRaises(ValueError):
            self.run_asr(model='unknown')
        self.client.Auth.assert_not_called()


class HearingIntegrationTests(unittest.TestCase):
    def test_vad_warms_before_wake_readiness_and_missing_vad_keeps_fallback(self):
        from audio import voice
        for unavailable in (False, True):
            with self.subTest(unavailable=unavailable):
                warmed = []
                def warm():
                    warmed.append(True)
                    if unavailable:
                        raise RuntimeError('Synthetic unavailable VAD')
                def wake(*args):
                    self.assertEqual(warmed, [True])
                    return False
                with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
                        'LYA_VOSK_MODEL': folder, 'LYA_COMMAND_ASR': 'vosk'}), patch.object(
                        voice, '_local', object()), patch.object(voice, 'SpeechActivity', side_effect=warm), patch.object(
                        voice, '_wait_for_wake', side_effect=wake):
                    voice.wake_loop(lambda *a: None, offline_required=False,
                                    cloud_provider='nvidia', cloud_only=True)

    def test_online_service_failure_stops_without_repeated_question_capture(self):
        from audio import voice
        stopped = threading.Event()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LYA_VOSK_MODEL': folder, 'LYA_COMMAND_ASR': 'vosk'}), patch.object(voice, '_local', object()), patch.object(voice, '_wait_for_wake', return_value=True), patch.object(voice, '_record_stream', return_value=io.BytesIO(wav())) as capture, patch.object(voice, 'transcribe', side_effect=nvidia_asr.SpeechUnavailable('UNAUTHENTICATED')):
            with self.assertRaisesRegex(RuntimeError, 'Online hearing'):
                voice.wake_loop(lambda *a: None, stop_event=stopped, offline_required=False,
                                cloud_provider='nvidia', cloud_only=True)
        capture.assert_called_once()

    def test_online_only_does_not_warm_large_local_command_model(self):
        from audio import voice, local_whisper
        stopped = threading.Event()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LYA_VOSK_MODEL': folder, 'LYA_COMMAND_ASR': 'whisper'}), patch.object(voice, '_local', object()), patch.object(voice, '_wait_for_wake', return_value=False), patch.object(local_whisper, 'load', side_effect=AssertionError('unneeded local model')):
            voice.wake_loop(lambda *a: None, stop_event=stopped, offline_required=False,
                            cloud_provider='nvidia', cloud_only=True)

    def test_online_only_mode_private_capture_never_uses_local_decoder(self):
        from audio import voice
        stopped = threading.Event()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LYA_VOSK_MODEL': folder, 'LYA_COMMAND_ASR': 'vosk'}), patch.object(voice, '_local', object()), patch.object(voice, '_wait_for_wake', return_value=True), patch.object(voice, '_record_stream', return_value=io.BytesIO(wav())), patch.object(voice, 'transcribe', side_effect=AssertionError('no local substitution')):
            voice.wake_loop(lambda *a: None, stop_event=stopped, offline_required=lambda: True,
                            cloud_provider='nvidia', cloud_only=True, on_retry=lambda *a: stopped.set())
    def test_unknown_provider_never_starts_listener(self):
        from audio import voice
        with patch.object(voice, '_wait_for_wake', side_effect=AssertionError('unexpected listener')):
            with self.assertRaises(RuntimeError):
                voice.wake_loop(lambda *a: None, offline_required=False, cloud_provider='unknown')

    def test_explicit_nvidia_route_forwards_cancellation_without_groq(self):
        from audio import voice
        stopped = threading.Event()
        with patch.object(nvidia_asr, 'transcribe', return_value='Synthetic full question') as nvidia, patch.object(voice, '_transcribe_groq', side_effect=AssertionError('wrong provider')):
            self.assertEqual(voice.transcribe(wav(), offline_required=False, cloud_provider='nvidia', cancelled=stopped), 'Synthetic full question')
        self.assertTrue(nvidia.call_args.kwargs['remote_allowed'])
        self.assertIs(nvidia.call_args.kwargs['cancelled'], stopped)

    def test_offline_policy_never_calls_nvidia(self):
        from audio import voice, local_whisper
        with patch.dict(os.environ, {'LYA_COMMAND_ASR': 'whisper'}), patch.object(local_whisper, 'transcribe', return_value='Local only') as local, patch.object(nvidia_asr, 'transcribe', side_effect=AssertionError('private audio upload')):
            self.assertEqual(voice.transcribe(wav(), offline_required=True, cloud_provider='nvidia'), 'Local only')
            local.assert_called_once()

    def test_nvidia_failure_never_uses_another_provider(self):
        from audio import voice
        with patch.object(nvidia_asr, 'transcribe', side_effect=RuntimeError('unavailable')), patch.object(voice, '_transcribe_groq', side_effect=AssertionError('fallback')):
            with self.assertRaises(RuntimeError):
                voice.transcribe(wav(), offline_required=False, cloud_provider='nvidia')

    def test_private_mode_changed_during_capture_blocks_remote_route(self):
        from audio import voice
        stopped = threading.Event()
        private = [False]
        def record(**kwargs):
            self.assertEqual(kwargs['silence'], 2.0)
            self.assertEqual(kwargs['continuation_silence'], 3.0)
            private[0] = True
            return io.BytesIO(wav())
        def decoded(*args, **kwargs):
            self.assertTrue(kwargs['offline_required'])
            stopped.set()
            return 'Synthetic question'
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LYA_VOSK_MODEL': folder, 'LYA_COMMAND_ASR': 'vosk'}), patch.object(voice, '_local', object()), patch.object(voice, '_wait_for_wake', return_value=True), patch.object(voice, '_record_stream', side_effect=record), patch.object(voice, 'transcribe', side_effect=decoded):
            voice.wake_loop(lambda *a: None, stop_event=stopped,
                            offline_required=lambda: private[0], cloud_provider='nvidia')

    def test_wake_and_full_nvidia_question_route(self):
        from audio import voice
        stopped = threading.Event()
        events = []
        def callback(text, quiet):
            events.append(text)
            if len(events) > 1:
                stopped.set()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LYA_VOSK_MODEL': folder, 'LYA_COMMAND_ASR': 'vosk'}), patch.object(voice, '_local', object()), patch.object(voice, '_wait_for_wake', return_value=True), patch.object(voice, '_record_stream', return_value=io.BytesIO(wav())), patch.object(voice, 'transcribe', return_value='Synthetic full question') as decode:
            voice.wake_loop(callback, stop_event=stopped,
                            offline_required=lambda: False, cloud_provider='nvidia')
        self.assertEqual(events, ['wake up lya', 'Synthetic full question'])
        self.assertEqual(decode.call_args.kwargs['cloud_provider'], 'nvidia')
        self.assertIs(decode.call_args.kwargs['cancelled'], stopped)


if __name__ == '__main__':
    unittest.main()
