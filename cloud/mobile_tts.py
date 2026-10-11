"""Public Amy voice, one CPU thread, RAM-only audio. No credentials or network."""
import base64
import ctypes
import io
import json
from pathlib import Path
import sys
import textwrap
import wave

MODEL=Path('/opt/lya-connect/models/en_US-amy-medium.onnx')
MAX_WAV=180*22050*2+44


def synthesize(text):
    if type(text) is not str or not 1<=len(text.strip())<=4000:raise ValueError('Reply too long for voice.')
    import numpy as np
    import onnxruntime as ort
    from piper import PiperVoice
    from piper.config import PiperConfig,SynthesisConfig
    options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
    options.enable_cpu_mem_arena=False;options.enable_mem_pattern=False
    options.add_session_config_entry('session.intra_op.allow_spinning','0')
    options.add_session_config_entry('session.inter_op.allow_spinning','0')
    session=ort.InferenceSession(str(MODEL),sess_options=options,providers=['CPUExecutionProvider'])
    config=PiperConfig.from_dict(json.loads(MODEL.with_suffix('.onnx.json').read_text()))
    voice=PiperVoice(session,config)
    trim=ctypes.CDLL('libc.so.6').malloc_trim
    chunks=[];size=0
    # Bound a sentence without punctuation before it reaches the neural model.
    for span in textwrap.wrap(text,80):
        # Return freed neural buffers between spans on this Linux-only worker.
        trim(0)
        if span[-1] not in '.!?;:':span+='.'
        for chunk in voice.synthesize(span,SynthesisConfig(length_scale=1.0,noise_scale=.55,noise_w_scale=.7)):
            samples=np.asarray(chunk.audio_float_array,dtype=np.float32)
            # Match the desktop's everyday loudness target; keep the same Amy model.
            rms=float(np.sqrt(np.mean(samples*samples))) if samples.size else 0
            if rms>1e-6:samples=samples*min(4.,10**(-16/20)/rms)
            pcm=(np.clip(samples,-1,1)*32767).astype('<i2').tobytes()
            size+=len(pcm)
            if chunk.sample_rate!=22050 or size>MAX_WAV-44:raise ValueError('Reply audio exceeds limit.')
            chunks.append(pcm)
    if not chunks:raise ValueError('No reply audio.')
    out=io.BytesIO()
    with wave.open(out,'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(22050);f.writeframes(b''.join(chunks))
    return out.getvalue()


def main():
    raw=sys.stdin.buffer.read(24001)
    if len(raw)>24000:raise ValueError('Oversize voice request.')
    packet=json.loads(raw)
    if type(packet) is not dict or set(packet)!={'text'}:raise ValueError('Invalid voice request.')
    audio=synthesize(packet['text'])
    print(json.dumps({'audio':base64.b64encode(audio).decode('ascii')}),flush=True)


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('LYA reply voice unavailable; details withheld.')
