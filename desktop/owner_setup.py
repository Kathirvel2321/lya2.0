"""Voice-guided owner setup and exact-action phone approval, with no OS identity prompt."""
import math
import re
import threading
import time
import webbrowser

from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal, QPointF, QRectF, QRect, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from desktop.setup_speech import SetupSpeech
from desktop.layout import TASK_COLORS
from desktop.owner_scan import FaceScan


class OwnerMark(QWidget):
    """A bounded native dot sculpture driven by voice state, never biometric progress."""
    def __init__(self, reduced_motion=False, parent=None):
        super().__init__(parent)
        self.setAccessibleName('LYA voice state')
        self.phase, self.active, self.verified = 0, False, False
        self.mode, self.checkpoint = 'ready', 0
        self.preview, self.level = None, 0.0
        self.reduced_motion = reduced_motion
        self.timer = QTimer(self)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self.tick)

    def tick(self):
        if self.isVisible() and self.active:
            self.phase += .12
            self.update()

    def showEvent(self, event):
        if not self.reduced_motion:
            self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.preview is not None:
            width = min(288, self.width()-24, (self.height()-48)*4/3)
            rect = QRectF((self.width()-width)/2, (self.height()-width*.75)/2-8, width, width*.75)
            clip = QPainterPath()
            clip.addRoundedRect(rect, 16, 16)
            painter.setClipPath(clip)
            painter.drawImage(rect, self.preview)
            painter.setClipping(False)
            painter.setPen(QPen(QColor(TASK_COLORS['listening']), 1.5))
            for x, y, dx, dy in ((rect.left(), rect.top(), 1, 1), (rect.right(), rect.top(), -1, 1),
                                 (rect.left(), rect.bottom(), 1, -1), (rect.right(), rect.bottom(), -1, -1)):
                painter.drawLine(QPointF(x+dx*6, y), QPointF(x+dx*20, y))
                painter.drawLine(QPointF(x, y+dy*6), QPointF(x, y+dy*20))
            return
        painter.translate(self.width()/2, self.height()/2-8)
        painter.setPen(Qt.PenStyle.NoPen)
        side = min(290, self.width()*.85, (self.height()-36)*.92)
        t = self.phase if self.active and not self.reduced_motion else 0
        palette = (TASK_COLORS['listening'], TASK_COLORS['thinking'], TASK_COLORS['success'])
        if self.mode == 'phone':
            palette = (TASK_COLORS['approval'], '#ada7d3', '#b9d4cf')
        elif self.mode == 'thinking':
            palette = (TASK_COLORS['thinking'], '#8f9bd9', '#b8d5df')
        elif self.mode == 'blocked':
            palette = (TASK_COLORS['error'], '#68737d', '#68737d')
        # Same voice-state colours as LYA; depth comes from dot size, without blur or 3D assets.
        for strand in range(3):
            color = QColor(palette[strand])
            for index in range(48):
                u = index/48
                angle = math.tau*u
                if self.mode == 'speaking':
                    envelope = math.sin(math.pi*u)**1.4
                    x = (u-.5)*side*.9
                    y = (math.sin(angle*1.8-t*2.8+strand*.6)*side*.18*envelope
                         + (strand-1)*side*.065)
                    brightness = .45+.55*envelope
                elif self.mode == 'thinking':
                    angle += t*.65+strand*.18
                    x = math.sin(angle)*side*(.32+strand*.025)
                    y = math.sin(2*angle)*side*(.15+strand*.016)
                    brightness = .25+.75*((u+t*.17)%1)**2
                elif self.mode == 'phone':
                    angle += t*.22+strand*.28
                    radius = side*(.29+strand*.045)
                    x = math.cos(angle)*radius
                    y = math.sin(angle)*radius*(.45+strand*.12)
                    brightness = .3+.7*((u-t*.12+strand*.16)%1)**2
                else:
                    point = strand*48+index
                    latitude = 1-2*(point+.5)/144
                    angle = point*2.3999632297+t*.18
                    ring = math.sqrt(1-latitude*latitude)
                    depth = ring*math.cos(angle)
                    breath = 1+.018*math.sin(t*1.5) if self.active else 1
                    x = ring*math.sin(angle)*side*.37*breath
                    y = latitude*side*.37*breath
                    brightness = .2+.8*(depth+1)/2
                    if self.mode == 'hearing':
                        x *= 1+.04*math.sin(latitude*8+t*3)
                dot = .9+1.1*brightness
                if self.mode == 'microphone':
                    y *= .35 + self.level * 2
                    dot += self.level
                color.setAlpha(round((235 if self.active else 160)*brightness))
                painter.setBrush(color)
                painter.drawEllipse(QRectF(x-dot, y-dot, dot*2, dot*2))
        if self.mode == 'phone':
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor('#d4c3a7'), 1.5))
            painter.drawRoundedRect(QRectF(-10, -18, 20, 36), 5, 5)
            painter.drawLine(QPointF(-3, 12), QPointF(3, 12))
        painter.resetTransform()
        # Checkpoints indicate walkthrough stages, never biometric accuracy or security strength.
        for index in range(6):
            color = QColor(TASK_COLORS['success'] if self.verified else '#9cdfe8' if index <= self.checkpoint else '#34454f')
            painter.setBrush(color)
            dot = 2 if index == self.checkpoint else 1.5
            painter.drawEllipse(QPointF(self.width()/2+(index-2.5)*14, self.height()-10), dot, dot)


class SetupControl(QPushButton):
    """Icon-only controls retain keyboard and screen-reader names."""
    def __init__(self, kind, name, parent, *, registration=True):
        super().__init__(parent)
        self.kind = kind
        self.registration = registration
        self.setObjectName('primary' if kind == 'continue' else 'secondary')
        side = (56 if kind == 'continue' else 44) if registration else 38
        self.setFixedSize(side, side)
        self.setText(name)
        self.setIconSize(QSize(24, 24) if registration else QSize(16, 16))
        self.draw_icon(kind)

    def draw_icon(self, kind):
        image = QPixmap(24, 24)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = ('#b9e6e6' if self.kind == 'continue' else '#939ea7') if self.registration else '#a1a7ad'
        painter.setPen(QPen(QColor(color), 1.6 if self.registration else 1.5,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        if kind == 'cancel':
            painter.drawLine(7, 7, 17, 17)
            painter.drawLine(7, 17, 17, 7)
        elif kind == 'repeat':
            painter.drawArc(QRectF(5, 5, 14, 14), 45*16, 275*16)
            painter.drawLine(18, 4, 18, 9)
            painter.drawLine(18, 9, 13, 8)
        elif kind == 'camera':
            painter.drawRoundedRect(QRectF(3, 7, 18, 13), 3, 3)
            painter.drawEllipse(QRectF(9, 10, 6, 6))
            painter.drawLine(8, 7, 10, 4)
            painter.drawLine(10, 4, 15, 4)
            painter.drawLine(15, 4, 17, 7)
        elif kind == 'microphone':
            painter.drawRoundedRect(QRectF(9, 3, 6, 12), 3, 3)
            painter.drawArc(QRectF(6, 7, 12, 11), 180*16, 180*16)
            painter.drawLine(12, 18, 12, 21)
            painter.drawLine(8, 21, 16, 21)
        elif kind == 'phone':
            painter.drawRoundedRect(QRectF(7, 2, 10, 20), 3, 3)
            painter.drawLine(10, 18, 14, 18)
        elif kind == 'check':
            painter.drawLine(5, 12, 10, 17)
            painter.drawLine(10, 17, 19, 7)
        else:
            path = QPainterPath()
            path.moveTo(9, 6)
            path.lineTo(17, 12)
            path.lineTo(9, 18)
            painter.drawPath(path)
        painter.end()
        self.setIcon(QIcon(image))

    def setText(self, text):
        self.setAccessibleName(text)
        self.setToolTip(text)


class OwnerSetupDialog(QDialog):
    authenticated = Signal(object)
    approved = Signal(object)

    def __init__(self, *, db_path=None, reduced_motion=False, approval=None, parent=None,
                 ceremony_factory=None, open_browser=webbrowser.open, approval_valid=None,
                 profile_setup=False, listener=None, capture_factory=None):
        super().__init__(parent)
        self.db_path, self.approval = db_path, approval
        self.ceremony_factory, self.open_browser = ceremony_factory, open_browser
        self.approval_valid = approval_valid
        self.ceremony, self.name, self.stage = None, 'Owner', 'intro'
        self.started, self.closed = False, False
        self.confirm_guided = False
        self.profile_setup = profile_setup and approval is None
        self.listener, self.capture_factory = listener, capture_factory
        self.capture_worker, self.profile_session = None, None
        self.profile_credential = None
        self.private_capture, self.resume_listener = False, False
        self.capture_step, self.awaiting_guidance = 0, False
        self.resume_samples, self.resume_owner, self.resume_until = None, None, 0.
        self.compact_geometry = None
        self.setWindowTitle('LYA owner access')
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(320, 280)
        self.resize(460, 390)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, approval is None)
        self.setStyleSheet("""QDialog{background:transparent;}
            QPushButton#secondary{background:transparent;border:1px solid transparent;border-radius:12px;}
            QPushButton#primary{background:#172c35;border:1px solid #658594;border-radius:16px;}
            QPushButton#secondary:hover{background:#1c2c36;border-color:#465d6a;}
            QPushButton#primary:hover{background:#224153;border-color:#9cdfe8;}
            QPushButton:pressed{background:#0c141e;border-color:#b0d8dc;}
            QPushButton:focus{border:2px solid #9cdfe8;}
            QPushButton:disabled{background:transparent;border-color:transparent;}""")
        if approval is not None:
            self.resize(440, 400)
            self.setStyleSheet("""QDialog{background:#101214;border:1px solid #22262a;}
                QPushButton{background:transparent;border:1px solid transparent;border-radius:19px;}
                QPushButton:hover{background:#1b1f23;}
                QPushButton:focus{border:1px solid #89939c;} QPushButton:disabled{opacity:.4;}""")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        self.mark = OwnerMark(reduced_motion, self)
        layout.addWidget(self.mark, 1)
        self.scan = FaceScan(reduced_motion, self)
        layout.addWidget(self.scan, 1)
        self.fade_effect = QGraphicsOpacityEffect(self.mark)
        self.fade_effect.setOpacity(1)
        self.mark.setGraphicsEffect(self.fade_effect)
        self.fade = QPropertyAnimation(self.fade_effect, b'opacity', self)
        self.fade.setDuration(180 if not reduced_motion else 0)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        # Keep guidance as accessibility/state data; none is rendered as routine text.
        for field in ('step', 'title', 'body', 'status', 'footer'):
            label = QLabel(self)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.hide()
            setattr(self, field, label)
        controls = QHBoxLayout()
        controls.setSpacing(16)
        controls.addStretch()
        self.repeat = SetupControl('repeat', 'Repeat voice guidance', self, registration=approval is None)
        self.repeat.clicked.connect(lambda: self.speech.say(self.prompt))
        self.next = SetupControl('continue', 'Begin setup', self, registration=approval is None)
        self.next.clicked.connect(self.advance)
        self.next.setDefault(True)
        self.cancel = SetupControl('cancel', 'Cancel setup', self, registration=approval is None)
        self.cancel.clicked.connect(self.reject)
        for control in (self.repeat, self.next, self.cancel):
            controls.addWidget(control)
        controls.addStretch()
        layout.addLayout(controls)
        self.speech = SetupSpeech(self)
        self.speech.speaking.connect(self._speaking)
        self.speech.completed.connect(self.guidance_finished)
        self.speech.unavailable.connect(self.voice_unavailable)
        self.pause_poll = QTimer(self)
        self.pause_poll.setInterval(100)
        self.pause_poll.timeout.connect(self.wait_listener)
        self.poll = QTimer(self)
        self.poll.setInterval(150)
        self.poll.timeout.connect(self.check_result)
        self.expire = QTimer(self)
        self.expire.setSingleShot(True)
        self.expire.timeout.connect(self.expired)
        self.watch = QTimer(self)
        self.watch.setInterval(250)
        self.watch.timeout.connect(self.check_approval)
        self.finished.connect(self.cleanup)
        self.configure()

    def paintEvent(self, event):
        if self.approval is not None:
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        body = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        path = QPainterPath()
        path.moveTo(body.left()+22, body.top())
        path.lineTo(body.right()-40, body.top())
        path.lineTo(body.right(), body.top()+40)
        path.lineTo(body.right(), body.bottom()-22)
        path.lineTo(body.right()-22, body.bottom())
        path.lineTo(body.left()+22, body.bottom())
        path.lineTo(body.left(), body.bottom()-22)
        path.lineTo(body.left(), body.top()+22)
        path.closeSubpath()
        fill = QLinearGradient(body.topLeft(), body.bottomRight())
        fill.setColorAt(0, QColor('#06121a' if self.stage=='face' else '#1c272f'))
        fill.setColorAt(.45, QColor('#0e181f'))
        fill.setColorAt(1, QColor('#091016'))
        painter.setBrush(fill)
        painter.setPen(QPen(QColor(166, 201, 213, 100), 1))
        painter.drawPath(path)
        painter.setPen(QPen(QColor('#9cdfe8'), 1.5))
        painter.drawLine(QPointF(34, 10), QPointF(100, 10))
        painter.setPen(QPen(QColor(156, 223, 232, 48), .8))
        painter.drawLine(QPointF(body.right()-64, body.top()), QPointF(body.right(), body.top()+64))
        painter.setPen(QPen(QColor(212, 193, 151, 140), 1.2))
        painter.drawLine(QPointF(body.right()-22, body.bottom()), QPointF(body.right(), body.bottom()-22))

    def mousePressEvent(self, event):
        if self.approval is None and event.button() == Qt.MouseButton.LeftButton and event.position().y() < 40:
            if self.windowHandle():
                self.windowHandle().startSystemMove()
        super().mousePressEvent(event)

    def configure(self):
        try:
            from storage.store import get_owner_passkey
            owner = get_owner_passkey(self.db_path)
            self.returning = owner is not None
            if self.approval:
                self.stage = 'approval'
                self.set_step('ONE ACTION', 'Review this exact request',
                    self.approval.action.replace('_', ' ').capitalize() + '\n\n' + self.approval.parameters,
                    'Continue with your phone. Review the exact request in your browser before approving only that action.',
                    'Approve with phone')
            elif self.returning:
                self.stage = 'phone'
                self.set_step('OWNER PROOF', 'Welcome back.',
                    'Use the enrolled passkey on your phone. Owner access lasts five minutes; private actions require fresh, separate approval.',
                    'Welcome back. Say continue with phone. Your phone verifies you; private actions still need separate approval.',
                    'Continue with phone')
            else:
                profile_prompt = (' After phone verification, I will ask permission to create local face and voice profiles. '
                    'Those profiles stay encrypted here; photos or voices never replace your phone proof.'
                    if self.profile_setup else ' No laptop face or voice scan is needed.')
                self.set_step('01 / ARRIVE', 'Make LYA\nyours.',
                    'I will guide you, one step at a time. Choose a name, keep a way back, and let your phone verify you.\n\n'
                    'Your existing hearing service may receive ordinary setup words. The camera and biometric recording stay off.',
                    'I will guide your owner setup. Ordinary setup words use your existing hearing mode. '
                    + profile_prompt + ' Say I agree to begin, or cancel.', 'I agree · Begin')
        except Exception as exc:
            self.stage = 'blocked'
            message = str(exc) if isinstance(exc, PermissionError) else 'The protected owner store is unavailable. No setup or sign-in is allowed.'
            self.set_step('LOCKED', 'Owner review required.', message,
                          'Owner access is locked. An existing profile needs trusted migration, or its protected store is unavailable. Nothing was replaced.', 'Locked')
            self.next.setEnabled(False)

    def set_step(self, step, title, body, prompt, button):
        self.show_face_stage(self.stage == 'face')
        self.step.setText(step)
        self.title.setText(title)
        self.body.setText(body)
        self.prompt = prompt
        self.setAccessibleDescription(prompt)
        self.next.setText(button)
        icon = ('camera' if self.stage in ('profile_consent', 'face') else 'microphone' if self.stage == 'voice' else
                'check' if self.stage == 'profile_review' else 'phone' if self.stage in ('phone', 'waiting', 'approval', 'profile_refresh') else 'continue')
        if self.approval is None:
            self.next.draw_icon(icon)
        self.status.setText('LYA WILL GUIDE YOU · SAY CANCEL TO EXIT')
        self.mark.mode = 'phone' if self.stage == 'waiting' else 'blocked' if self.stage == 'blocked' else 'ready'
        self.mark.checkpoint = {'name':1, 'confirm_name':1, 'recovery':2, 'phone':3, 'waiting':3,
                               'profile_consent':4, 'face':4, 'voice':4, 'profile_review':5}.get(self.stage, 0)
        self.mark.setAccessibleDescription(self.mark.mode)
        self.mark.active = self.stage == 'waiting'
        self.mark.update()
        if self.started and not self.closed:
            self.fade.stop()
            self.fade.setStartValue(.25)
            self.fade.setEndValue(1)
            self.fade.start()
            self.speech.say(prompt)

    def show_face_stage(self, visible):
        if visible and self.compact_geometry is None:
            self.compact_geometry = QRect(self.geometry())
            available = (self.screen() or QApplication.primaryScreen()).availableGeometry()
            width, height = min(1280, available.width()-24), min(760, available.height()-24)
            self.setGeometry(available.center().x()-width//2, available.center().y()-height//2, width, height)
        elif not visible and self.compact_geometry is not None:
            self.setGeometry(self.compact_geometry)
            self.compact_geometry = None
            self.mark.preview = None
        self.mark.setVisible(not visible)
        self.scan.setVisible(visible)
        self.next.setVisible(not visible)
        self.repeat.setVisible(not visible)
        if visible:
            self.scan.set_capture(self.capture_step, self.awaiting_guidance)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.started:
            self.started = True
            duration = min(240, max(0, self.approval.deadline - time.monotonic())) if self.approval else 240
            self.expire.start(max(1, int(duration * 1000)))
            if self.approval_valid:
                self.watch.start()
            QTimer.singleShot(0, lambda: self.speech.say(self.prompt) if not self.closed else None)

    def _speaking(self, active):
        if self.private_capture and self.stage in ('face', 'voice') and not self.awaiting_guidance:
            return
        self.mark.active = active or self.stage == 'waiting'
        self.mark.mode = ('speaking' if active else 'phone' if self.stage == 'waiting' else
                          'blocked' if self.stage == 'blocked' else 'ready')
        self.mark.setAccessibleDescription(self.mark.mode)
        self.mark.update()
        if self.stage != 'blocked':
            self.status.setText('LYA IS SPEAKING · SAY STOP / CANCEL' if active else
                                'WAITING FOR PHONE PROOF' if self.stage == 'waiting' else 'YOUR TURN · ' + self.next.accessibleName().upper())

    def set_input_phase(self, phase):
        if self.closed or self.private_capture or self.stage in ('waiting', 'blocked') or self.speech.busy:
            return
        self.mark.mode = {'transcribing':'thinking', 'hearing':'hearing', 'listening':'listening'}.get(phase, 'ready')
        self.mark.setAccessibleDescription(self.mark.mode)
        self.mark.active = self.mark.mode != 'ready'
        labels = {'thinking':'TRANSCRIBING YOUR WORDS', 'hearing':'HEARING YOUR WORDS', 'listening':'LISTENING'}
        self.status.setText(labels.get(self.mark.mode, 'YOUR TURN · ' + self.next.accessibleName().upper()))
        self.mark.update()

    def handle_voice(self, text):
        low = ' '.join(text.casefold().split()).strip(' .!?')
        if low in ('stop', 'cancel', 'close', 'close panel'):
            self.reject()
            return
        if self.speech.busy or self.stage in ('blocked', 'waiting', 'done'):
            return
        if self.stage == 'name':
            match = re.fullmatch(r'(?:my name is|call me) (.{1,80})', text.strip(), re.I)
            if match:
                name = match.group(1).strip().rstrip('.!?')
                if name and not any(ord(c) < 32 for c in name):
                    self.name = name
                    self.stage = 'confirm_name'
                    self.set_step('02 / IDENTITY', f'Call you {self.name}?',
                        'Say “yes, that is my name”, “try again”, or use Owner.',
                        f'I heard {self.name}. Say yes, that is my name, or try again.', 'Yes · Confirm name')
                    return
            if low in ('use owner', 'owner', 'continue'):
                self.name = 'Owner'
                self.recovery_step()
                return
            self.speech.say('Say my name is, followed by your name, or say use Owner.')
            return
        if self.stage == 'confirm_name' and low in ('try again', 'no', 'wrong name'):
            self.stage = 'name'
            self.set_step('02 / IDENTITY', 'What should I call you?', 'Say “my name is …”, or use Owner.',
                          'What should I call you? Say my name is, followed by your name, or use Owner.', 'Use Owner')
            return
        accepted = {
            'intro': ('i agree', 'agree', 'begin setup'),
            'confirm_name': ('yes that is my name', 'yes, that is my name', 'yes', 'confirm name'),
            'recovery': ('i understand', 'continue with phone', 'continue'),
            'phone': ('continue with phone', 'sign in', 'continue'),
            'approval': ('approve with phone', 'continue with phone', 'approve'),
            'failed': ('retry', 'try again'),
            'profile_consent': ('i agree', 'agree', 'start my profiles', 'start profiles'),
            'profile_review': ('save my profiles', 'save profiles', 'confirm profiles'),
            'profile_refresh': ('continue with phone', 'verify again', 'continue'),
        }
        if low in accepted.get(self.stage, ()):
            self.advance()

    def recovery_step(self):
        self.stage = 'recovery'
        self.set_step('03 / RECOVERY', 'Keep a way back.',
            'Keep your iPhone passkey available through your chosen password manager and its recovery method. '
            'LYA cannot reset owner access from a photo, voice, name or secret phrase. '
            'Passkey recovery and your encrypted LYA data backup are separate; losing the laptop encryption key can still lose your data.',
            'Keep your phone passkey and its recovery method safe. LYA cannot reset access from your voice or photo. '
            'Your LYA data also needs a separate encrypted backup. Say I understand to continue.', 'I understand · Continue with phone')

    def advance(self):
        if self.closed:
            return
        if self.stage == 'profile_consent':
            self.start_profiles()
            return
        if self.stage == 'profile_review':
            self.save_profiles()
            return
        if self.private_capture:
            return
        self.speech.stop(keep_warm=True)
        if self.stage == 'intro':
            self.stage = 'name'
            self.set_step('02 / IDENTITY', 'What should I call you?',
                'Say “my name is …”. I will read it back for confirmation. Or continue with the name Owner.',
                'What should I call you? Say my name is, followed by your name, or say use Owner.', 'Use Owner')
        elif self.stage in ('name', 'confirm_name'):
            self.recovery_step()
        elif self.stage in ('recovery', 'phone', 'approval', 'failed', 'profile_refresh'):
            self.start_phone()

    def start_phone(self):
        try:
            if self.ceremony_factory is None:
                from security.passkeys import PasskeyCeremony
                factory = PasskeyCeremony
            else:
                factory = self.ceremony_factory
            self.ceremony = factory(db_path=self.db_path, name=self.name, approval=self.approval,
                                   approval_valid=self.approval_valid)
            self.confirm_guided = False
            self.stage = 'waiting'
            prompt = ('Verify with your existing phone passkey to continue the paused local profile setup. '
                      'The camera and enrollment microphone remain off while you verify.' if self.resume_samples is not None else
                      'Select the phone symbol in your browser. Choose another device and scan its QR with your iPhone. '
                      'After creation, verify your new passkey once more. I am waiting for signed proof.')
            self.set_step('PHONE PROOF', 'Your phone holds the key.',
                'A local browser window will offer a phone / tablet or “Use another device” option. '
                'Scan the browser QR with your iPhone; keep Bluetooth on and the phone nearby. '
                'After creating a passkey, verify it once more. LYA saves the profile only after that signed proof.',
                prompt, 'Waiting for phone…')
            self.next.setEnabled(False)
            self.poll.start()
            if self.open_browser(self.ceremony.url) is False:
                raise RuntimeError('Browser unavailable.')
        except Exception:
            self.fail('Could not start phone verification. Use a current Chrome or Edge browser. Existing owner profiles may require trusted migration.')

    def check_result(self):
        if self.ceremony is None:
            return
        if not self.isVisible() or time.monotonic() >= self.ceremony.deadline:
            self.fail('Phone verification expired or the setup screen was hidden. Nothing was unlocked.')
            return
        if not self.ceremony.done.is_set():
            if (getattr(self.ceremony, 'phase', None) == 'confirm'
                    and not self.confirm_guided and not self.speech.busy):
                self.confirm_guided = True
                self.prompt = 'Your passkey was created. Select the phone symbol once more to verify it before I save your owner profile.'
                self.setAccessibleDescription(self.prompt)
                self.speech.say(self.prompt)
            return
        result, error = self.ceremony.result, self.ceremony.error
        if self.profile_setup and not error and result is not None:
            from fido2.utils import websafe_encode
            credential = websafe_encode(bytes(self.ceremony.credential))
            if self.resume_samples is not None and (time.monotonic()>=self.resume_until
                    or (result.person_id,credential)!=self.resume_owner):
                self.ceremony.close()
                self.ceremony = None
                self.fail('The paused samples expired or belong to a different owner credential. Nothing was saved.')
                return
            self.profile_credential = credential
        self.ceremony.close()
        self.ceremony = None
        self.poll.stop()
        if error or result is None:
            self.fail(error or 'Phone verification failed. Nothing was unlocked.')
            return
        if self.approval:
            self.approved.emit(result)
            self.accept()
            return
        if self.profile_setup:
            try:
                from storage import store
                profiles = store.owner_profiles(result, self.db_path, expected_credential=self.profile_credential)
                if self.resume_samples is not None and profiles['face']:
                    self.fail('Saved profiles changed while setup was paused. Nothing was replaced.')
                    return
                if not profiles['face']:
                    self.profile_session = result
                    self.expire.start(max(1, int((result.verified_until-time.time())*1000)))
                    if self.resume_samples is not None:
                        self.start_profiles()
                        return
                    self.stage = 'profile_consent'
                    self.next.setEnabled(True)
                    self.set_step('LOCAL PROFILES', 'Your choice. Your device.', '',
                        'Your phone credential is registered and its proof is verified. Next I can store three face profiles and three voice profiles, '
                        'your confirmed name, public passkey and consent record, encrypted on this laptop. '
                        'Lya never receives your private passkey. I save no photos or recordings. '
                        'I will stop online hearing before any capture. With your consent, future launches will make one brief, visible local face check, '
                        'then close the camera. Recognition personalizes greetings and limited everyday tools only; no photos are saved. '
                        'Unknown face observations stay in RAM for ten minutes and are never automatically registered. '
                        'Visitor activity counts stay in RAM until you save or discard them, or quit Lya. A webcam and voice can be copied, '
                        'so recognition never replaces your phone. Say I agree to start, or cancel.', 'Start local face and voice profiles')
                    return
            except Exception:
                self.fail('Recognition profiles could not be checked. Access stays locked.')
                return
        self.finish_owner(result)

    def finish_owner(self, session):
        from storage import store
        try:
            owner = store.get_owner_passkey(self.db_path)
            valid = (session.verified_until > time.time() and owner['person_id'] == session.person_id
                     and (self.profile_credential is None or owner['credential'] == self.profile_credential))
        except Exception:
            valid = False
        if not valid:
            self.fail('Phone proof expired or owner changed. Verify again.')
            return
        self.stage = 'done'
        self.mark.verified = True
        self.authenticated.emit(session)
        self.accept()

    def start_profiles(self):
        if self.listener is None or self.profile_session.verified_until <= time.time():
            self.fail('Private capture requires a stopped listener and fresh phone proof.')
            return
        self.speech.stop()
        self.private_capture = True
        self.resume_listener = bool(self.listener.voice_thread and self.listener.voice_thread.is_alive())
        self.listener.stop_voice()
        if hasattr(self.listener, 'cancel_vision'):
            self.listener.cancel_vision()
        self.pause_deadline = time.monotonic()+12
        self.next.setEnabled(False)
        self.repeat.setEnabled(False)
        self.stage = 'pausing'
        self.mark.mode, self.mark.active = 'thinking', True
        self.pause_poll.start()
        self.wait_listener()

    def wait_listener(self):
        if self.closed:
            return
        previous = self.capture_worker
        if previous is not None and hasattr(previous,'process'):
            from PySide6.QtCore import QProcess
            if previous.process.state()!=QProcess.ProcessState.NotRunning:
                if time.monotonic()>=self.pause_deadline:
                    self.pause_poll.stop()
                    self.fail('The previous capture worker did not stop. No new capture was started.')
                return
        if self.listener.voice_thread and self.listener.voice_thread.is_alive():
            if time.monotonic() >= self.pause_deadline:
                self.pause_poll.stop()
                self.fail('Online hearing did not stop. No biometric capture was started.')
            return
        self.pause_poll.stop()
        try:
            from desktop.owner_biometrics import OwnerCapture
            self.capture_worker = (self.capture_factory or OwnerCapture)(self.profile_session, self)
            self.capture_worker.ready.connect(self.guide_capture)
            self.capture_worker.sample.connect(self.sample_captured)
            self.capture_worker.preview.connect(self.show_preview)
            self.capture_worker.tracking.connect(self.show_tracking)
            self.capture_worker.meter.connect(self.show_meter)
            self.capture_worker.failed.connect(self.capture_failed)
            self.capture_worker.retry.connect(self.retry_capture)
            self.capture_worker.hint.connect(self.show_capture_hint)
            worker = self.capture_worker
            self.capture_worker.stopped.connect(lambda worker=worker:self.capture_stopped(worker))
            if self.resume_samples is not None:
                self.capture_worker.samples = self.resume_samples
                self.resume_samples,self.resume_owner,self.resume_until = None,None,0.
            self.capture_step = sum(len(v) for v in self.capture_worker.samples.values())
            if self.capture_step==6:
                self.stage = 'profiles_stopping'
                self.capture_worker.stop(clear=False)
                return
            self.stage = 'loading_profiles'
            self.capture_worker.start()
        except Exception:
            self.fail('Local profile worker unavailable. Nothing was saved.')

    def guide_capture(self, correction=''):
        prompts = (
            'Online hearing is off. Look at the lens with only your face visible, in good light. Escape or the close symbol cancels. Spoken commands are paused.',
            'Now turn your face slightly to one side. Stay inside the preview.',
            'Now turn slightly to the other side. This checks sample consistency, not certified liveness.',
            'The camera is off. After I finish, speak naturally, then pause. I will listen locally for up to twenty seconds. Say: This is my own Lya assistant, and this is my natural voice.',
            'Another local sample. After I finish, say: Tomorrow I would like to study at college and finish my work calmly. Then pause.',
            'Last local sample. After I finish, say: My voice may be soft or slow, and I want my assistant to understand me. Then pause.',
        )
        self.stage = 'face' if self.capture_step < 3 else 'voice'
        self.awaiting_guidance = True
        self.scan.feedback = ''
        self.set_step('LOCAL CAPTURE', '', '', correction+prompts[self.capture_step],
            'Local camera active' if self.stage == 'face' else 'Local microphone active')

    def retry_capture(self, code):
        if self.closed or not self.private_capture:
            return
        if self.profile_session.verified_until <= time.time():
            self.expired()
            return
        from security.owner_profiles import CAPTURE_FAILURES
        sample = 'view' if self.capture_step<3 else 'voice sample'
        self.guide_capture(CAPTURE_FAILURES[code]+f' Your completed samples are kept. Let us retry this {sample}. ')

    def show_capture_hint(self, hint):
        if not self.closed and self.private_capture and self.stage=='face':
            self.scan.feedback = hint
            self.scan.setAccessibleDescription(hint)
            self.scan.update()

    def guidance_finished(self):
        request, step = self.speech.request, self.capture_step
        QTimer.singleShot(0, lambda: self.begin_capture(request, step))

    def begin_capture(self, request, step):
        if (self.closed or not self.private_capture or not self.awaiting_guidance or self.speech.cancelled
                or self.speech.busy or request != self.speech.request or step != self.capture_step):
            return
        self.awaiting_guidance = False
        self.mark.mode = 'camera' if self.capture_step < 3 else 'microphone'
        self.mark.active = True
        self.mark.setAccessibleDescription('Local '+self.mark.mode+' capture active')
        if self.stage == 'face':
            self.scan.set_capture(self.capture_step, False)
        self.capture_worker.capture('face' if self.capture_step < 3 else 'voice', self.capture_step % 3)

    def voice_unavailable(self):
        if self.private_capture:
            self.fail('Voice guidance unavailable. No further capture is allowed.')
        else:
            self.status.setText('Voice unavailable. Use the accessible buttons; access remains locked.')

    def expired(self):
        if self.resume_samples is not None:
            self.reject()
        elif self.profile_session is not None and self.stage in (
                'pausing','loading_profiles','face','voice','profiles_stopping','profile_review'):
            self.pause_profiles()
        elif self.profile_session is not None:
            self.fail('Your phone proof expired before profile setup finished. Verify with your phone again.')
        else:
            self.reject()

    def capture_failed(self):
        if getattr(self.capture_worker,'failure_code',None)=='expired':
            self.expired()
        else:
            self.fail(getattr(self.capture_worker,'failure_reason','Local profile capture failed.')+
                      ' No face or voice profiles were saved. Your phone credential remains registered.')

    def pause_profiles(self):
        self.awaiting_guidance = False
        self.pause_poll.stop()
        samples = self.capture_worker.samples if self.capture_worker is not None else {'face':[],'voice':[]}
        # Partial face views cannot restore the worker's side-turn state; restart only that group.
        self.resume_samples = {kind:[v[:] for v in samples[kind]] if len(samples['face'])==3 else []
                               for kind in ('face','voice')}
        self.resume_owner = (self.profile_session.person_id,self.profile_credential)
        self.resume_until = time.monotonic()+180
        self.stage = 'profile_refresh'
        if self.capture_worker is not None:
            self.capture_worker.stop()
        else:
            self.release_listener()
        self.expire.start(180000)
        self.next.setEnabled(True)
        self.repeat.setEnabled(True)
        self.set_step('PHONE REFRESH','','',
            'Your phone proof expired. Capture is stopped. Completed samples stay only in memory for three minutes. '
            'Say continue with phone to verify the same owner and resume. Closing or cancelling discards them.',
            'Continue with phone')

    def show_preview(self, image):
        if self.closed:
            return
        self.mark.preview = image
        self.mark.update()
        self.scan.image = image
        if image is None:
            self.scan.tracking = None
        self.scan.update()

    def show_tracking(self, tracking):
        if self.closed:
            return
        self.scan.tracking = tracking
        if tracking is not None:
            self.scan.setAccessibleDescription(f"{self.scan.instruction()}. Faces detected: {tracking['faces']}. "
                f"Face views captured: {self.capture_step} of 3. Local profile only; phone proof remains required.")
        self.scan.update()

    def show_meter(self, level):
        self.mark.level = level
        self.mark.update()

    def sample_captured(self, kind, index):
        if self.closed:
            return
        if (kind, index) != ('face' if self.capture_step < 3 else 'voice', self.capture_step % 3):
            self.fail('Unexpected capture result. Nothing was saved.')
            return
        self.capture_step += 1
        if self.capture_step < 6:
            self.guide_capture()
        else:
            self.stage = 'profiles_stopping'

    def capture_stopped(self, worker=None):
        if worker is not None and worker is not self.capture_worker:
            return
        if self.stage=='pausing' and self.resume_samples is not None:
            return
        self.release_listener()
        if self.closed or self.stage != 'profiles_stopping':
            return
        self.stage = 'profile_review'
        self.next.setEnabled(True)
        self.repeat.setEnabled(True)
        self.set_step('REVIEW', '', '',
            'Both sets of samples are consistent. The camera and enrollment microphone are off. '
            'Ordinary hearing has resumed. I will save three face and three voice profiles with their model versions and consent date, '
            'inside your encrypted local owner store. Saving also enables the one brief startup face check you consented to. '
            'Your signed phone proof remains required for admin access, '
            'and private actions still need fresh approval. Say save my profiles to finish, or cancel to discard them.', 'Save my profiles')

    def release_listener(self):
        self.private_capture = False
        if self.resume_listener and self.listener is not None:
            self.resume_listener = False
            if not getattr(self.listener, 'quitting', False):
                self.listener.start_voice(self.listener.cloud_voice)

    def save_profiles(self):
        if self.profile_session.verified_until <= time.time():
            self.expired()
            return
        try:
            from storage import store
            store.save_owner_profiles(self.profile_session, self.profile_credential, self.capture_worker.samples,
                                      consent=True, db_path=self.db_path, startup_recognition=True)
            self.capture_worker.samples = {'face': [], 'voice': []}
            self.finish_owner(self.profile_session)
        except Exception:
            self.fail('Profiles could not be saved. Verify with your phone and try again.')

    def fail(self, message):
        self.resume_samples,self.resume_owner,self.resume_until = None,None,0.
        self.awaiting_guidance = False
        self.pause_poll.stop()
        self.stage = 'failed'
        if self.capture_worker:
            self.capture_worker.stop()
        else:
            self.release_listener()
        if self.ceremony is not None:
            self.ceremony.close()
            self.ceremony = None
        self.poll.stop()
        self.next.setEnabled(True)
        self.repeat.setEnabled(True)
        self.set_step('STILL LOCKED', 'Let’s try that again.', message,
                      message+' Access stays locked. Say retry or cancel.', 'Retry')

    def hideEvent(self, event):
        # Even before phone proof, hidden setup must not keep speaking or waiting.
        self.cleanup()
        super().hideEvent(event)

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            self.reject()
        super().changeEvent(event)

    def check_approval(self):
        if self.approval_valid is not None and self.approval_valid() is not True:
            self.reject()

    def cleanup(self, *_):
        if self.closed:
            return
        self.closed = True
        self.awaiting_guidance = False
        self.pause_poll.stop()
        if self.capture_worker:
            self.capture_worker.stop()
        else:
            self.release_listener()
        self.profile_session = None
        self.resume_samples,self.resume_owner,self.resume_until = None,None,0.
        self.speech.stop()
        self.fade.stop()
        self.mark.timer.stop()
        self.scan.timer.stop()
        self.scan.image = self.scan.tracking = None
        self.mark.preview = None
        self.poll.stop()
        self.expire.stop()
        self.watch.stop()
        if self.ceremony is not None:
            self.ceremony.close()
            self.ceremony = None


class PasskeyApproval(QObject):
    """The Brain worker requests UI approval; signed proof returns its exact Challenge."""
    requested = Signal(object)

    def __init__(self, desktop):
        super().__init__(desktop)
        self.desktop, self.dialog = desktop, None
        self.requested.connect(self.show_request, Qt.ConnectionType.QueuedConnection)

    def verify(self, challenge):
        if QThread.currentThread() == self.thread():
            return None  # Never block the UI waiting for its own event loop.
        request = dict(challenge=challenge, event=threading.Event(), result=None)
        self.requested.emit(request)
        request['event'].wait(max(0, min(120, challenge.deadline - time.monotonic())))
        return request['result'] if request['event'].is_set() else None

    def show_request(self, request):
        challenge = request['challenge']
        if (request['event'].is_set() or time.monotonic() >= challenge.deadline
                or self.desktop.brain.session != challenge.session
                or (hasattr(self.desktop, 'owner_dialog') and self.desktop.owner_dialog.isVisible())
                or (self.dialog is not None and self.dialog.isVisible())):
            request['event'].set()
            return
        dialog = OwnerSetupDialog(db_path=self.desktop.brain.db_path,
            reduced_motion=self.desktop.orb.reduced_motion, approval=challenge,
            approval_valid=lambda: (self.desktop.brain.session == challenge.session
                                   and self.desktop.brain.approve.is_pending(challenge)))
        self.dialog = dialog
        dialog.speech.speaking.connect(self.desktop._speaking_changed)
        def approved(result):
            if (result == challenge and self.desktop.brain.session == challenge.session
                    and time.monotonic() < challenge.deadline):
                request['result'] = result
        dialog.approved.connect(approved)
        dialog.finished.connect(lambda _: request['event'].set())
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def close(self):
        if self.dialog is not None:
            self.dialog.reject()
