"""Local recognition profiles. These cannot create an owner or a verified Session."""
import math

FACE_MODEL = 'sface-int8-2021dec-128d'
VOICE_MODEL = 'resemblyzer-0.1.4-256d'
MODEL_DIMS = {FACE_MODEL: 128, VOICE_MODEL: 256}
CAPTURE_FAILURES = {
    'camera': 'The camera could not provide a usable frame.',
    'face_quality': 'The face view did not meet the lighting, alignment or sharpness check.',
    'face_missing': 'Move your face into the camera view.',
    'face_multiple': 'Keep only your face in the camera view.',
    'face_position': 'Keep your whole face inside the frame and move a little closer.',
    'face_pose': 'Follow the requested face turn, then hold still.',
    'face_light': 'Light your face from the front and avoid a bright light behind you.',
    'face_blur': 'Hold still and clean the camera lens if the preview looks blurred.',
    'voice_device': 'The selected microphone could not provide local voice audio.',
    'audio_overflow': 'The microphone lost audio during capture. That incomplete sample was discarded.',
    'audio_quality': 'The microphone returned invalid audio. That sample was discarded.',
    'voice_no_speech': 'I did not receive two seconds of usable speech. Wait until my guidance finishes, then speak naturally.',
    'voice_quiet': 'The speech sample was too faint for a reliable voice profile.',
    'voice_clipped': 'The speech sample was distorted or clipped. Move the microphone slightly farther away.',
    'voice_short': 'Too little speech remained after the local noise and silence check.',
    'voice_mismatch': 'The voice samples did not match consistently. Use the same microphone and your natural voice for each sample.',
    'face_mismatch': 'The face samples did not match consistently. Keep only your face visible.',
    'expired': 'Your phone proof expired before profile setup finished. Verify with your phone again.',
    'capture_timeout': 'Local capture or processing took too long. The capture worker was stopped.',
    'capture_failed': 'Local profile capture could not finish.',
}
RETRY_FAILURES = frozenset(('face_quality', 'face_missing', 'face_multiple', 'face_position',
    'face_pose', 'face_light', 'face_blur', 'voice_no_speech', 'voice_quiet', 'voice_clipped',
    'voice_short', 'audio_overflow', 'face_mismatch', 'voice_mismatch'))


def checked_vector(vector, model):
    if (type(vector) is not list or len(vector) != MODEL_DIMS.get(model)
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in vector)):
        raise ValueError('Invalid recognition profile.')
    norm = math.sqrt(sum(v*v for v in vector))
    if not .98 <= norm <= 1.02:
        raise ValueError('Recognition profile must have unit length.')
    return [float(v) / norm for v in vector]


def matches(vector, samples, model):
    """Consistency check, not presentation-attack detection or identity authority."""
    vector = checked_vector(vector, model)
    if not samples or len(samples) > 3:
        raise ValueError('Invalid reference samples.')
    scores = [sum(a*b for a, b in zip(vector, checked_vector(s, model))) for s in samples]
    # ponytail: recognition thresholds need live owner/negative-speaker calibration; never grant access.
    threshold = .45 if model == FACE_MODEL else .75
    return min(scores) >= threshold
