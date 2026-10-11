"""Native-only bridge for consented owner profiles; never a session verifier."""
import base64
import json
import os
from pathlib import Path
import time

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal, QBuffer, QByteArray
from PySide6.QtGui import QImageReader
from security.owner_profiles import FACE_MODEL, VOICE_MODEL, CAPTURE_FAILURES, RETRY_FAILURES, checked_vector, matches

ROOT = Path(__file__).resolve().parents[1]


class OwnerCapture(QObject):
    ready = Signal()
    sample = Signal(str, int)
    preview = Signal(object)
    tracking = Signal(object)
    meter = Signal(float)
    failed = Signal()
    stopped = Signal()
    retry = Signal(str)
    hint = Signal(str)

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.samples = {'face': [], 'voice': []}
        self.buffer = b''
        self.pending = None
        self.closing = False
        self.prepared = False
        self.failure_reason = CAPTURE_FAILURES['capture_failed']
        self.failure_code = None
        self.initial_step = 0
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read)
        self.process.readyReadStandardError.connect(lambda: self.process.readAllStandardError())
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(lambda _: self.abort() if not self.closing else None)
        self.lease = QTimer(self)
        self.lease.setInterval(750)
        self.lease.timeout.connect(self.renew)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(lambda: self.abort('capture_timeout'))

    def start(self):
        python = ROOT / '.venv-owner/Scripts/python.exe'
        if not python.is_file() or self.session.verified_until <= time.time():
            self.abort()
            return
        try:
            faces,voices = self.samples['face'],self.samples['voice']
            if len(faces) not in (0,3) or len(voices)>2 or (voices and len(faces)!=3):
                raise ValueError('Invalid resumed capture.')
            for kind,model in (('face',FACE_MODEL),('voice',VOICE_MODEL)):
                checked = [checked_vector(v,model) for v in self.samples[kind]]
                if any(not matches(v,checked[:i],model) for i,v in enumerate(checked) if i):
                    raise ValueError('Inconsistent resumed capture.')
            self.initial_step = len(faces)+len(voices)
        except Exception:
            self.abort()
            return
        environment = QProcessEnvironment()
        for name in ('SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'LYA_MICROPHONE'):
            if name in os.environ:
                environment.insert(name, os.environ[name])
        for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
            environment.insert(name, '2')
        for name in ('PYTHONNOUSERSITE', 'PYTHONDONTWRITEBYTECODE', 'NUMBA_DISABLE_JIT'):
            environment.insert(name, '1')
        self.process.setProcessEnvironment(environment)
        self.process.start(str(python), [str(ROOT / 'security/owner_capture.py'), str(self.session.verified_until),str(self.initial_step)])
        self.lease.start()
        self.timeout.start(90000)

    def renew(self):
        if self.session.verified_until <= time.time():
            self.abort('expired')
        elif self.process.state() == QProcess.ProcessState.Running:
            self.process.write(b'lease\n')

    def capture(self, kind, index):
        expected_kind = 'face' if len(self.samples['face']) < 3 else 'voice'
        if (self.closing or not self.prepared or type(index) is not int or kind != expected_kind
                or index != len(self.samples[expected_kind]) or index >= 3 or self.pending is not None
                or self.process.state() != QProcess.ProcessState.Running):
            self.abort()
            return
        self.pending = (kind, index)
        self.process.write(json.dumps(dict(kind=kind, index=index)).encode('ascii')+b'\n')
        self.timeout.start(25000)

    def read(self):
        self.buffer += bytes(self.process.readAllStandardOutput())
        if len(self.buffer) > 262144:
            self.abort()
            return
        while b'\n' in self.buffer and not self.closing:
            line, self.buffer = self.buffer.split(b'\n', 1)
            try:
                self.handle_packet(json.loads(line))
            except Exception:
                self.abort()
                return

    def handle_packet(self, data):
        if self.session.verified_until <= time.time():
            self.abort('expired')
            return
        if type(data) is not dict:
            raise ValueError('Invalid capture event.')
        kind = data.get('kind')
        if (kind == 'ready' and not self.prepared and self.pending is None
                and sum(len(v) for v in self.samples.values())==self.initial_step):
            self.prepared = True
            self.timeout.stop()
            self.ready.emit()
        elif kind == 'preview' and self.pending and self.pending[0] == 'face':
            tracking = data.get('tracking')
            if (type(tracking) is not dict or set(tracking) != {'faces', 'box', 'points'}
                    or type(tracking['faces']) is not int or tracking['faces'] not in (0, 1, 2)
                    or type(tracking['box']) is not list or type(tracking['points']) is not list):
                raise ValueError('Invalid face tracking.')
            box, points = tracking['box'], tracking['points']
            if tracking['faces'] == 1:
                if len(box) != 4 or len(points) != 5 or any(type(p) is not list or len(p) != 2 for p in points):
                    raise ValueError('Invalid landmarks.')
                if any(type(v) not in (int, float) or not 0 <= v <= 1 for v in box + [v for p in points for v in p]):
                    raise ValueError('Invalid coordinates.')
                if box[0]+box[2] > 1.000001 or box[1]+box[3] > 1.000001:
                    raise ValueError('Invalid face bounds.')
            elif box or points:
                raise ValueError('Unexpected landmarks.')
            raw = base64.b64decode(data['image'], validate=True)
            if len(raw) > 100000:
                raise ValueError('Oversize preview.')
            buffer = QBuffer()
            buffer.setData(QByteArray(raw))
            buffer.open(QBuffer.OpenModeFlag.ReadOnly)
            reader = QImageReader(buffer, b'JPG')
            if (reader.size().width(), reader.size().height()) not in ((320,240),(640,480)):
                raise ValueError('Invalid preview.')
            image = reader.read()
            if image.isNull():
                raise ValueError('Invalid preview.')
            self.preview.emit(image)
            self.tracking.emit(tracking)
        elif kind == 'meter' and self.pending and self.pending[0] == 'voice':
            level = data.get('level')
            if type(level) not in (int, float) or not 0 <= level <= 1:
                raise ValueError('Invalid microphone meter.')
            self.meter.emit(float(level))
        elif (kind == 'hint' and self.pending and self.pending[0] == 'face' and set(data)=={'kind','code'}
                and type(data['code']) is str and data['code'] in (
                    'face_missing','face_multiple','face_position','face_pose','face_light','face_blur','face_hold')):
            self.hint.emit('Hold still — capturing this view.' if data['code']=='face_hold' else CAPTURE_FAILURES[data['code']])
        elif (kind == 'retry' and self.pending and set(data)=={'kind','code'} and type(data['code']) is str
                and data['code'] in RETRY_FAILURES and data['code'].startswith('face' if self.pending[0]=='face' else ('voice','audio'))):
            self.retry_sample(data['code'])
        elif kind == 'sample' and type(data.get('index')) is int and (data.get('profile'), data.get('index')) == self.pending:
            profile, index = self.pending
            model = FACE_MODEL if profile == 'face' else VOICE_MODEL
            vector = checked_vector(data['vector'], model)
            samples = self.samples[profile]
            if samples and not matches(vector, samples, model):
                self.retry_sample(profile+'_mismatch')
                return
            if len(samples) != index:
                raise ValueError('Inconsistent recognition samples.')
            samples.append(vector)
            self.process.write(json.dumps(dict(accept=index if profile=='face' else index+3)).encode('ascii')+b'\n')
            self.pending = None
            self.timeout.stop()
            self.preview.emit(None)
            self.tracking.emit(None)
            self.meter.emit(0)
            self.sample.emit(profile, index)
        elif kind == 'done' and len(self.samples['face']) == len(self.samples['voice']) == 3:
            self.stop(clear=False)
        elif kind == 'error' and set(data) == {'kind','code'} and type(data['code']) is str and data['code'] in CAPTURE_FAILURES:
            self.abort(data['code'])
        else:
            raise ValueError('Unexpected capture event.')

    def retry_sample(self, code):
        self.pending = None
        self.timeout.stop()
        self.preview.emit(None)
        self.tracking.emit(None)
        self.meter.emit(0)
        self.retry.emit(code)

    def abort(self, code=None):
        if self.closing:
            return
        if self.session.verified_until <= time.time():
            code = 'expired'
        self.failure_code = code
        if code in CAPTURE_FAILURES:
            self.failure_reason = CAPTURE_FAILURES[code]
        self.stop(clear=code!='expired')
        self.failed.emit()

    def stop(self, *, clear=True):
        self.closing = True
        self.lease.stop()
        self.timeout.stop()
        self.pending = None
        self.buffer = b''
        if clear:
            self.samples = {'face': [], 'voice': []}
        self.preview.emit(None)
        self.tracking.emit(None)
        self.meter.emit(0)
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
        else:
            self.stopped.emit()

    def finished(self, code, _):
        if not self.closing:
            if code != 0 or any(len(v) != 3 for v in self.samples.values()):
                self.abort()
                return
            self.stop(clear=False)
        else:
            self.stopped.emit()
