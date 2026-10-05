"""Opt-in NVIDIA speech with one bounded model backup; no audio persistence."""
import io
import os
import threading
import wave

ENDPOINT = 'grpc.nvcf.nvidia.com:443'
FUNCTION_ID = 'd3fe9151-442b-4204-a70d-5fcc597fd610'
MODELS = {
    'parakeet': (FUNCTION_ID, 'en-US', 'Parakeet TDT v2'),
    'whisper': ('b702f636-f60c-4a3d-a6f4-f3568c13bd7d', 'en', 'Whisper Large v3'),
    'parakeet-ctc': ('1598d209-5e27-4d3c-8079-4751568b1081', 'en-US', 'Parakeet CTC 1.1B'),
}
TIMEOUT = 15.0
MAX_SECONDS = 120


def pcm_audio(data):
    """Validate the complete question; never silently trim a longer input."""
    if len(data) > MAX_SECONDS * 32000 + 65536:
        raise ValueError('Question exceeds the 120-second speech-check limit.')
    try:
        with wave.open(io.BytesIO(data), 'rb') as sound:
            if (sound.getframerate(), sound.getnchannels(), sound.getsampwidth(), sound.getcomptype()) != (16000, 1, 2, 'NONE'):
                raise ValueError('Speech check needs mono 16 kHz PCM16 audio.')
            frames = sound.getnframes()
            if not 0 < frames <= MAX_SECONDS * 16000:
                raise ValueError('Question is empty or exceeds the speech-check limit.')
            pcm = sound.readframes(frames)
            if len(pcm) != frames * 2:
                raise ValueError('Incomplete audio; nothing sent.')
            return pcm
    except (wave.Error, EOFError):
        raise ValueError('Invalid audio; nothing sent.') from None


class SpeechUnavailable(RuntimeError):
    def __init__(self, message, *, switch_model=False):
        super().__init__(message)
        self.switch_model = switch_model


def transcribe(data, *, remote_allowed=False, api_key=None, cancelled=None,
               model=None, allow_backup=True, on_model=None):
    allowed = remote_allowed if callable(remote_allowed) else lambda: remote_allowed
    if not allowed():
        raise PermissionError('NVIDIA speech requires explicit permission to send audio.')
    key = (api_key if api_key is not None else os.environ.get('NVIDIA_API_KEY', '')).strip()
    if not key:
        raise RuntimeError('NVIDIA speech key is not configured. Nothing sent.')
    pcm = pcm_audio(data)
    stopped = cancelled if cancelled is not None else threading.Event()
    if stopped.is_set():
        raise InterruptedError('Cancelled; nothing sent.')
    selected = model or os.environ.get('LYA_NVIDIA_ASR', 'parakeet')
    if selected not in MODELS:
        raise ValueError('Unknown NVIDIA speech model. Nothing sent.')
    backup = 'parakeet-ctc' if selected == 'whisper' else 'whisper'
    attempts = [selected, backup] if allow_backup else [selected]
    from audio.voice import RecognitionUncertain
    for index, name in enumerate(attempts):
        if stopped.is_set():
            raise InterruptedError('Cancelled.')
        if not allowed():
            raise PermissionError('Private mode blocks cloud speech; no next model contacted.')
        if on_model:
            on_model(MODELS[name][2], bool(index))
        try:
            return _recognize(pcm, key, name, stopped)
        except SpeechUnavailable as error:
            if not error.switch_model or index == len(attempts) - 1:
                raise
        except RecognitionUncertain:
            if index == len(attempts) - 1:
                raise


def _recognize(pcm, key, model, stopped):
    try:
        import riva.client
        from riva.client.proto import riva_asr_pb2 as asr
        import grpc
    except ImportError:
        raise RuntimeError('Optional NVIDIA speech client is not installed. Nothing sent.') from None
    auth = None
    future = None
    try:
        auth = riva.client.Auth(uri=ENDPOINT, use_ssl=True, metadata_args=[
            ['function-id', MODELS[model][0]], ['authorization', 'Bearer ' + key]])
        service = riva.client.ASRService(auth)
        config = riva.client.RecognitionConfig(
            encoding=riva.client.AudioEncoding.LINEAR_PCM, sample_rate_hertz=16000,
            language_code=MODELS[model][1], max_alternatives=1,
            enable_automatic_punctuation=model != 'whisper')
        if stopped.is_set():
            raise InterruptedError('Cancelled; nothing sent.')
        future = service.stub.Recognize.future(
            asr.RecognizeRequest(config=config, audio=pcm),
            metadata=auth.get_auth_metadata(), timeout=TIMEOUT)
        while True:
            if stopped.is_set():
                raise InterruptedError('Cancelled.')
            try:
                response = future.result(timeout=0.1)
                break
            except grpc.FutureTimeoutError:
                continue  # gRPC's RPC deadline bounds the entire request.
        if stopped.is_set():
            raise InterruptedError('Cancelled.')
        text = ' '.join(result.alternatives[0].transcript.strip()
                        for result in response.results if result.alternatives).strip()
        if not text:
            from audio.voice import RecognitionUncertain
            raise RecognitionUncertain('No clear words recognized by NVIDIA.')
        return text
    except InterruptedError:
        raise
    except Exception as error:
        from audio.voice import RecognitionUncertain
        if isinstance(error, RecognitionUncertain):
            raise
        # Never echo provider payloads. Auth/quota/bad-input failures stop here;
        # only model retirement or transient service failures try one other model.
        code = error.code().name if isinstance(error, grpc.RpcError) else 'UNKNOWN'
        switch = code in ('NOT_FOUND', 'UNIMPLEMENTED', 'UNAVAILABLE', 'DEADLINE_EXCEEDED', 'INTERNAL')
        raise SpeechUnavailable('NVIDIA speech unavailable (' + code + ').', switch_model=switch) from None
    finally:
        if future is not None:
            future.cancel()
        if auth is not None:
            auth.channel.close()
