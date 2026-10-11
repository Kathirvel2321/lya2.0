"""Fake public responses/audio and temporary auth metadata only."""
import base64
import io
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_mobile as fixtures
from test_mobile_voice import sound


class ConversationChecks(unittest.TestCase):
    setUp=fixtures.MobileChecks.setUp
    response=fixtures.MobileChecks.response
    start_pair=fixtures.MobileChecks.start_pair
    pair=fixtures.MobileChecks.pair

    def test_same_voice_is_bounded_and_private_state_not_exposed(self):
        token=self.pair();calls=[]
        audio=base64.b64encode(sound(rate=22050)).decode()
        self.app.speaker=lambda text,cancel:calls.append(text) or audio
        result=self.app.chat(token,'1'*32,'Public question',spoken=True)
        self.assertEqual(result['audio'],audio);self.assertEqual(calls,['Synthetic reply.'])
        self.assertNotIn(audio.encode(),self.store.path.read_bytes())
        self.assertNotIn('audio',self.app.chat(token,'2'*32,'Text only'))
        with self.assertRaises(ValueError):self.app.chat(token,'3'*32,'Invalid flag',spoken='true')

    def test_voice_failure_preserves_text_and_cancel_discards_both(self):
        token=self.pair()
        self.app.speaker=lambda text,cancel:'invalid base64'
        result=self.app.chat(token,'1'*32,'hello',spoken=True)
        self.assertEqual(result['text'],'Synthetic reply.');self.assertTrue(result['voice_unavailable'])
        def speak(text,cancel):cancel.set();return base64.b64encode(sound(rate=22050)).decode()
        self.app.speaker=speak
        with self.assertRaises(InterruptedError):self.app.chat(token,'2'*32,'cancel',spoken=True)
        self.assertEqual(len(self.app.session(token)['history']),2)

    def test_heavy_audio_cannot_overlap_and_long_question_is_not_truncated(self):
        token=self.pair();calls=[]
        self.app.transcriber=lambda data,cancel:calls.append(len(data)) or 'Long synthetic question'
        self.app.audio_slots.acquire()
        try:
            with self.assertRaises(ValueError):self.app.transcribe(token,'1'*32,sound())
            self.assertEqual(calls,[])
        finally:self.app.audio_slots.release()
        data=sound(frames=16000*70)
        self.assertEqual(self.app.transcribe(token,'2'*32,data)['text'],'Long synthetic question')
        self.assertEqual(calls,[len(data)])

    def test_reply_runtime_uses_fixed_unprivileged_command_and_larger_bounded_output(self):
        from cloud import mobile_runtime
        with patch.object(mobile_runtime,'exchange',return_value=SimpleNamespace(returncode=0,stdout='{"audio":"FAKE_AUDIO"}')) as exchange:
            self.assertEqual(mobile_runtime.speak('Public text',threading.Event()),'FAKE_AUDIO')
        args,kwargs=exchange.call_args
        self.assertEqual(args[0],['/opt/lya-connect/tts-venv/bin/python','-I','/opt/lya-connect/reply.py'])
        self.assertEqual(kwargs['output_limit'],11000000);self.assertTrue(kwargs['close_stdin'])

    def test_transport_default_and_new_output_limits(self):
        from cloud.ssh_session import exchange
        class Pipe(io.BytesIO):
            def read(self,size=-1):self.size=size;return super().read(size)
        class Process:
            def __init__(self):self.stdin=io.BytesIO();self.stdout=Pipe(b'public');self.returncode=0
            def poll(self):return 0
            def wait(self,timeout=None):return 0
        for limit in (65536,11000000):
            process=Process();self.assertEqual(exchange(['fake'],'{}',popen=lambda *a,**kw:process,output_limit=limit).stdout,'public')
            self.assertEqual(process.stdout.size,limit+1)
        for limit in (0,12000001,True):
            with self.assertRaises(ValueError):exchange(['fake'],'{}',output_limit=limit)

    def test_tts_rejects_oversize_or_arbitrary_packet_before_model_load(self):
        from cloud import mobile_tts
        with self.assertRaises(ValueError):mobile_tts.synthesize('x'*4001)
        with patch.object(mobile_tts.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(b'{"text":"hello","path":"bad"}'))),patch.object(mobile_tts,'synthesize') as synth:
            with self.assertRaises(ValueError):mobile_tts.main()
            synth.assert_not_called()

    def test_tts_bounds_unpunctuated_model_spans(self):
        import numpy as np
        from cloud import mobile_tts
        from unittest.mock import MagicMock
        spans=[]
        def generate(text,config):
            spans.append(text)
            yield SimpleNamespace(audio_float_array=np.zeros(2205,dtype=np.float32),sample_rate=22050)
        options=SimpleNamespace(add_session_config_entry=lambda *args:None)
        model=MagicMock();model.with_suffix.return_value.read_text.return_value='{}'
        modules={'onnxruntime':SimpleNamespace(SessionOptions=lambda:options,InferenceSession=lambda *a,**kw:None),
                 'piper':SimpleNamespace(PiperVoice=lambda *a:SimpleNamespace(synthesize=generate)),
                 'piper.config':SimpleNamespace(PiperConfig=SimpleNamespace(from_dict=lambda value:None),SynthesisConfig=lambda **kw:None)}
        trim=MagicMock()
        with patch.dict('sys.modules',modules),patch.object(mobile_tts,'MODEL',model), \
             patch.object(mobile_tts.ctypes,'CDLL',return_value=SimpleNamespace(malloc_trim=trim)):
            audio=mobile_tts.synthesize('public words without punctuation '*40)
        self.assertTrue(all(len(span)<=81 and span.endswith('.') for span in spans))
        self.assertEqual(trim.call_count,len(spans));self.assertTrue(audio.startswith(b'RIFF'))
        self.assertFalse(options.enable_cpu_mem_arena)
