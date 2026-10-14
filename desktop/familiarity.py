"""Consent-gated one-shot worker and owner-only review, no continuous sensors."""
import base64
import json
import os
from pathlib import Path
import time

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QVBoxLayout)
from security.owner_profiles import FACE_MODEL, checked_vector

ROOT = Path(__file__).resolve().parents[1]


class FaceObservation(QObject):
    camera = Signal()
    result = Signal(object)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.process=QProcess(self)
        self.buffer=b''
        self.vector=None
        self.photo=None
        self.seen_camera=self.seen_result=self.closed=False
        self.process.readyReadStandardOutput.connect(self.read)
        self.process.readyReadStandardError.connect(lambda:self.process.readAllStandardError())
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(lambda _:self.stop())
        self.lease=QTimer(self)
        self.lease.setInterval(750)
        self.lease.timeout.connect(lambda:self.process.write(b'lease\n'))
        self.timeout=QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.stop)

    def start(self):
        python=ROOT/'.venv-owner/Scripts/python.exe'
        if not python.is_file():
            self.stop()
            return
        env=QProcessEnvironment()
        for name in ('SystemRoot','WINDIR','PATH','TEMP','TMP'):
            if name in os.environ:
                env.insert(name,os.environ[name])
        for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
            env.insert(name,'2')
        env.insert('PYTHONDONTWRITEBYTECODE','1')
        env.insert('PYTHONNOUSERSITE','1')
        self.process.setProcessEnvironment(env)
        self.process.start(str(python),['-B',str(ROOT/'security/familiar_capture.py'),str(time.time()+22)])
        self.lease.start()
        self.timeout.start(22000)

    def packet(self,data):
        if type(data) is not dict:
            raise ValueError('Invalid observation.')
        if data==dict(kind='camera') and not self.seen_camera and not self.seen_result:
            self.seen_camera=True
            self.camera.emit()
        elif (set(data) in ({'kind','vector'},{'kind','vector','image'}) and
              data['kind']=='result' and self.seen_camera and not self.seen_result):
            self.vector=checked_vector(data['vector'],FACE_MODEL) if data['vector'] is not None else None
            image = data.get('image')
            if image is not None:
                if type(image) is not str or len(image) > 220000:
                    raise ValueError('Invalid visitor image.')
                self.photo = base64.b64decode(image, validate=True)
                if (not 32 <= len(self.photo) <= 160000 or
                        not self.photo.startswith(b'\xff\xd8') or not self.photo.endswith(b'\xff\xd9')):
                    raise ValueError('Invalid visitor image.')
            self.seen_result=True
        else:
            raise ValueError('Invalid observation sequence.')

    def read(self):
        self.buffer+=bytes(self.process.readAllStandardOutput())
        if len(self.buffer)>16384:
            self.stop()
            return
        while b'\n' in self.buffer and not self.closed:
            line,self.buffer=self.buffer.split(b'\n',1)
            try:
                self.packet(json.loads(line))
            except Exception:
                self.stop()

    def finished(self,code,_):
        if self.closed:
            return
        self.read()
        vector=self.vector if code==0 and self.seen_result and not self.buffer else None
        photo=self.photo if vector is not None else None
        if not self.closed:
            self.close()
            self.result.emit(dict(vector=vector,photo=photo) if photo is not None else vector)

    def close(self):
        self.closed=True
        self.lease.stop()
        self.timeout.stop()
        self.vector=None
        self.photo=None
        self.buffer=b''

    def stop(self):
        if self.closed:
            return
        self.close()
        self.process.kill()
        self.result.emit(None)


class VisitorReview(QDialog):
    """Owner-only activity summary and encrypted unknown-photo review."""
    def __init__(self,desktop):
        super().__init__()
        self.desktop=desktop
        self.counts=dict(desktop.brain.visitors.counts)
        self.pending_id=None
        self.setWindowTitle('LYA · visitor review')
        self.setMinimumWidth(420)
        self.setStyleSheet('QDialog{background:#0b1820;color:#d6eaeb;} QLabel{color:#d6eaeb;font:14px "Segoe UI";} QPushButton{color:#a9e4e8;background:#142b35;border:1px solid #50717c;border-radius:10px;padding:12px;}')
        layout=QVBoxLayout(self)
        layout.setContentsMargins(24,24,24,24)
        layout.addWidget(QLabel('Temporary visitor activity'))
        layout.addWidget(QLabel(f"Requests: {self.counts['requests']}\nLimited app launches: {self.counts['limited_apps']}\nBlocked actions: {self.counts['blocked']}"))
        self.status=QLabel('Counts only · no recordings or conversation text in this report.\nSaving the summary does not register anyone.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        from storage import visitors
        try:
            pending=visitors.pending(self.desktop.brain.db_path)
        except Exception:
            pending=[]
        if pending:
            self.pending_id=pending[0]['pending_id']
            layout.addWidget(QLabel('Unrecognized face · encrypted local photo'))
            self.photo=QLabel('Photo unavailable or expired')
            self.photo.setMinimumSize(220,160)
            self.photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            photo=visitors.pending_photo(self.pending_id,self.desktop.brain.db_path)
            if photo:
                pixmap=QPixmap()
                if pixmap.loadFromData(photo,b'JPG'):
                    self.photo.setPixmap(pixmap.scaled(300,220,Qt.AspectRatioMode.KeepAspectRatio,
                                                       Qt.TransformationMode.SmoothTransformation))
            layout.addWidget(self.photo)
            self.name=QLineEdit()
            self.name.setPlaceholderText('Name after you confirm who this is')
            self.name.setMaxLength(80)
            layout.addWidget(self.name)
            self.category=QComboBox()
            self.category.addItems(['friend','family'])
            layout.addWidget(self.category)
            visitor_controls=QHBoxLayout()
            save_visitor=QPushButton('Save visitor')
            save_visitor.clicked.connect(self.promote)
            delete_photo=QPushButton('Delete photo')
            delete_photo.clicked.connect(self.delete_pending)
            visitor_controls.addWidget(save_visitor)
            visitor_controls.addWidget(delete_photo)
            layout.addLayout(visitor_controls)
        controls=QHBoxLayout()
        for label,save in (('Save summary',True),('Discard',False)):
            button=QPushButton(label)
            button.clicked.connect(lambda _,save=save:self.choose(save))
            controls.addWidget(button)
        layout.addLayout(controls)

    def promote(self):
        try:
            from storage import visitors
            if not self.name.text().strip():
                self.status.setText('Enter a name, then choose friend or family. Nothing was saved.')
                return
            visitors.register_pending(self.desktop.brain.session,self.pending_id,self.name.text(),
                                      self.desktop.brain.db_path,category=self.category.currentText())
            self.status.setText('Saved. The encrypted photo was deleted; the person can now be recognized by name.')
            self.accept()
        except Exception as exc:
            self.status.setText(str(exc))

    def delete_pending(self):
        try:
            from storage import visitors
            visitors.discard_pending(self.desktop.brain.session,self.pending_id,self.desktop.brain.db_path)
            self.status.setText('The encrypted visitor photo and pending profile were deleted.')
            self.accept()
        except Exception:
            self.status.setText('Owner proof expired or changed. Nothing was deleted.')

    def choose(self,save):
        try:
            from storage import visitors,store
            session=self.desktop.brain.session
            with store.store_connection(self.desktop.brain.db_path,read_only=True) as db:
                visitors.owner_check(db,session)
            if save:
                visitors.save_summary(session,self.counts,self.desktop.brain.db_path)
            self.desktop.brain.visitors.discard()
            self.accept()
        except Exception:
            self.status.setText('Owner proof expired or changed. Sign in again. Nothing was saved or discarded.')
