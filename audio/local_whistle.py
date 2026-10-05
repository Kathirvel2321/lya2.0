"""Bounded Windows Whistle pilot. No microphone, cloud route or implicit setup."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'models/speech/whistle'
TIMEOUT = 30.0
MEMORY_BYTES = 512 * 1024 * 1024
MAX_WAV_BYTES = 16000 * 2 * 30 + 65536
HASHES = {
    'client.whl': '4101e693757d969782ce1d0d6aac9756bfca80a163a26f13c39e5c5aacecea68',
    'libneedle3.dll': 'de2e2c39cd311fbd9971fad4736abc329ed970653674c203e149c4ef27fd1c62',
    'whistle.cact': 'b6e02f048568ac5d01a2042556c658061e699acbc0aa2a1439f52f3d461dffeb',
}


def verify_assets(folder=MODEL):
    for name, expected in HASHES.items():
        path = Path(folder) / name
        if not path.is_file():
            raise RuntimeError('Whistle pilot is not installed. Run tools/setup_whistle.py explicitly.')
        with path.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        if digest != expected:
            raise RuntimeError('Whistle asset integrity check failed. Inference not started.')


def validate_audio(data):
    from audio.voice import RecognitionUncertain
    if len(data) > MAX_WAV_BYTES:
        raise RecognitionUncertain('Whistle pilot supports complete questions up to 30 seconds; no part was transcribed.')
    try:
        with wave.open(io.BytesIO(data), 'rb') as sound:
            if (sound.getframerate(), sound.getnchannels(), sound.getsampwidth(), sound.getcomptype()) != (16000, 1, 2, 'NONE'):
                raise ValueError('Unsupported audio format')
            frames = sound.getnframes()
            if not 0 < frames <= 30 * 16000:
                raise RecognitionUncertain('Whistle pilot supports complete questions up to 30 seconds; no part was transcribed.')
            if len(sound.readframes(frames)) != frames * 2:
                raise ValueError('Incomplete WAV')
    except (wave.Error, EOFError, ValueError) as error:
        raise RuntimeError('Whistle requires a complete mono 16 kHz PCM16 WAV.') from error


def _limit_worker(process):
    import win32api
    import win32con
    import win32job
    import win32process
    job = win32job.CreateJobObject(None, '')
    handle = None
    try:
        limits = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
        limits['BasicLimitInformation']['LimitFlags'] |= (win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY |
                                                         win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
        limits['ProcessMemoryLimit'] = MEMORY_BYTES
        win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, limits)
        handle = win32api.OpenProcess(win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE |
                                     win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_SET_INFORMATION,
                                     False, process.pid)
        win32job.AssignProcessToJobObject(job, handle)
        mask, _ = win32process.GetProcessAffinityMask(handle)
        slots = [1 << bit for bit in range(mask.bit_length()) if mask & (1 << bit)]
        win32process.SetProcessAffinityMask(handle, sum(slots[:2]))
        return job
    except Exception:
        job.Close()
        raise RuntimeError('Whistle resource controls unavailable. Inference not started.') from None
    finally:
        if handle is not None:
            handle.Close()


def decode(wav_bytes, *, cancelled=None):
    """Return an experimental candidate and transient metrics; never execute it."""
    validate_audio(wav_bytes)
    if sys.platform != 'win32':
        raise RuntimeError('This resource-limited Whistle pilot supports Windows only.')
    verify_assets()
    if cancelled is not None and cancelled.is_set():
        raise InterruptedError('Cancelled.')
    # Only OS necessities reach the speech worker, never inherited provider keys.
    environment = {key: value for key, value in os.environ.items()
                   if key.upper() in ('SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'USERPROFILE', 'LOCALAPPDATA')}
    environment.update(NEEDLE_TELEMETRY='0', DO_NOT_TRACK='1', HF_HUB_OFFLINE='1',
                       HF_HUB_DISABLE_TELEMETRY='1', PYTHONIOENCODING='utf-8',
                       NEEDLE3_LIB_PATH=str(MODEL / 'libneedle3.dll'), OMP_NUM_THREADS='2')
    executable = Path(sys.executable)
    if executable.name.lower() == 'pythonw.exe':
        executable = executable.with_name('python.exe')
    started = time.monotonic()
    process = subprocess.Popen([str(executable), '-I', '-B', str(ROOT / 'tools/whistle_worker.py'), str(MODEL)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=environment, creationflags=subprocess.CREATE_NO_WINDOW |
                               subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    job = None
    try:
        job = _limit_worker(process)  # Worker waits for stdin before importing/loading the engine.
        pending = wav_bytes
        while True:
            if cancelled is not None and cancelled.is_set():
                raise InterruptedError('Cancelled.')
            if time.monotonic() - started >= TIMEOUT:
                raise RuntimeError('Whistle exceeded its time budget. Worker stopped; no question dispatched.')
            try:
                output, _ = process.communicate(pending, timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                pending = None
        if cancelled is not None and cancelled.is_set():
            raise InterruptedError('Cancelled.')
        if process.returncode or len(output) > 65536:
            raise RuntimeError('Whistle worker failed. No question dispatched.')
        try:
            result = json.loads(output)
            if not isinstance(result, dict) or not isinstance(result.get('text'), str):
                raise ValueError('Invalid result')
        except (ValueError, TypeError):
            raise RuntimeError('Whistle returned an invalid result. No question dispatched.') from None
        import win32job
        limits = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
        result['wall_seconds'] = time.monotonic() - started
        result['peak_worker_mib'] = limits['PeakProcessMemoryUsed'] / (1024 * 1024)
        return result
    finally:
        if process.poll() is None:
            process.kill()
        if job is not None:
            job.Close()
        process.communicate()
