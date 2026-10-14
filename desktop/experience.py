"""Compact native presentation. No sensors, persistence or inference changes."""
import re
import wave
from PySide6.QtCore import Qt, QEvent, QRect, QPoint, QTimer, QElapsedTimer, QPropertyAnimation, QVariantAnimation, QEasingCurve, Signal, QProcess
from PySide6.QtGui import QTextCursor, QPixmap
from PySide6.QtWidgets import QLabel, QApplication, QDialog, QVBoxLayout, QTextBrowser
from app import Desktop, GlassPanel, WINDOW_FLAGS, HERE, DOCUMENTS, read_project_document
from layout import Box, place_panel


def is_owner_access_request(text):
    command = ' '.join(text.casefold().split()).strip(' .,!?:;')
    return re.fullmatch(
        r'(?:lya[, ]+)?(?:please )?(?:open |start )?'
        r'(?:register (?:admin|administrator|admijn)|(?:admin|administrator) (?:setup|registration)|'
        r'setup admin|set up admin|sign in|unlock lya)(?: please)?', command) is not None


class CompactPanel(GlassPanel):
    resized_mode = Signal()
    drag_started = Signal()

    def __init__(self):
        self.mode = 'answer'
        self.reduced = True
        super().__init__()
        self.reveal = QTimer(self)
        self.reveal.setInterval(40)
        self.reveal.timeout.connect(self.reveal_next)
        self.full_text = ''
        self.reveal_offset = 0
        self.spoken_tokens = []
        self.spoken_original = ''
        self.spoken_prefix = ''
        self.preserve_chat = False
        self.detached = False
        self.drag_offset = None
        self.answer.installEventFilter(self)

    def eventFilter(self, watched, event):
        if (watched is self.answer and self.mode == 'answer' and
                not self.reveal.isActive() and event.type() == QEvent.Type.KeyPress):
            modifiers = event.modifiers()
            blocked = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier
            text = event.text() if not modifiers & blocked else ''
            if (text and not text.isspace()) or event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.set_mode('input')
                self.entry.setText(text)
                self.entry.setFocus()
                self.entry.setCursorPosition(len(text))
                return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 48:
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self.detached = True
            self.drag_started.emit()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and not self.isFullScreen():
            self.move(event.globalPosition().toPoint() - self.drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_offset = None
        super().mouseReleaseEvent(event)

    def set_mode(self, mode):
        self.mode = mode
        layout = self.layout()
        # Reuse existing widgets; only the composer is visible in input mode.
        def visible(item, show):
            if item.widget():
                item.widget().setVisible(show)
            elif item.layout():
                for i in range(item.layout().count()):
                    visible(item.layout().itemAt(i), show)
        for i in range(layout.count()):
            visible(layout.itemAt(i), mode != 'input' or i == 5)
        self.eyebrow.hide()
        if mode == 'answer':
            visible(layout.itemAt(5), False)
        if mode == 'files':
            visible(layout.itemAt(5), False)
        if mode != 'chat':
            visible(layout.itemAt(4), False)
        layout.setContentsMargins(30, 22, 30, 24)
        layout.setSpacing(18)
        self.title_label.setStyleSheet('font-size: 23px; font-weight: 600; color: #f1f4f3;')
        self.resized_mode.emit()

    def show_answer(self, title, message):
        if hasattr(self, 'reveal'):
            self.reveal.stop()
        if self.mode == 'chat' and self.preserve_chat:
            return
        super().show_answer(title, message)
        if hasattr(self, 'reveal'):
            self.set_mode('chat' if self.mode == 'chat' else 'answer')
            if title == 'Working on your request…':
                self.answer.setPlainText('Thinking…')
            else:
                self.animate_answer(message)

    def animate_answer(self, text):
        self.reveal.stop()
        if self.reduced or not self.isVisible():
            self.answer.setPlainText(text)
            return
        self.full_text, self.reveal_offset = text, 0
        self.answer.clear()
        self.reveal.start()

    def show_transcript(self, text):
        self.reveal.stop()
        self.full_text = ''
        self.reveal_offset = 0
        self.answer.setPlainText(text)
        self.answer.moveCursor(QTextCursor.MoveOperation.End)

    def animate_append(self, history, text, separator='\n\n'):
        self.reveal.stop()
        prefix = history + (separator if history and text else '')
        self.answer.setPlainText(prefix)
        self.answer.moveCursor(QTextCursor.MoveOperation.End)
        if self.reduced or not self.isVisible():
            cursor = self.answer.textCursor()
            cursor.insertText(text)
            self.answer.setTextCursor(cursor)
            return
        self.full_text, self.reveal_offset = text, 0
        self.reveal.start()

    def reveal_next(self):
        if self.spoken_tokens:
            cursor = self.answer.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(self.spoken_tokens.pop(0))
            self.answer.setTextCursor(cursor)
            self.answer.ensureCursorVisible()
            if not self.spoken_tokens:
                self.reveal.stop()
            return
        # Finish long replies promptly without adding another repaint timer.
        end = min(len(self.full_text), self.reveal_offset + max(2, (len(self.full_text) + 29) // 30))
        cursor = self.answer.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(self.full_text[self.reveal_offset:end])
        self.answer.setTextCursor(cursor)
        self.answer.ensureCursorVisible()
        self.reveal_offset = end
        if self.reveal_offset >= len(self.full_text):
            self.reveal.stop()

    def begin_spoken(self, original, prefix=''):
        self.reveal.stop()
        self.spoken_tokens = []
        self.spoken_original = str(original)
        self.spoken_prefix = prefix
        self.answer.setPlainText(prefix)

    def sync_caption(self, phrase, duration_ms):
        if not self.spoken_original:
            return
        tokens = re.findall(r'\S+\s*', phrase)
        if not tokens:
            return
        self.spoken_tokens.extend(tokens)
        self.reveal.setInterval(max(45, min(350, int(duration_ms / len(tokens)))))
        if not self.reveal.isActive():
            self.reveal.start()

    def finish_spoken(self):
        if not self.spoken_original:
            return
        self.reveal.stop()
        self.answer.setPlainText(self.spoken_prefix + self.spoken_original)
        self.spoken_original = ''
        self.spoken_prefix = ''
        self.spoken_tokens = []

    def hideEvent(self, event):
        if hasattr(self, 'reveal'):
            self.reveal.stop()
            self.full_text = ''
            self.spoken_original = ''
            self.spoken_tokens = []
        super().hideEvent(event)


class OrbDesktop(Desktop):
    panel_type = CompactPanel

    def prepare_system_dictation(self):
        super().prepare_system_dictation()
        self.command('open chat')
        self.panel.entry.setFocus()
        self.panel.footnote.setText('WINDOWS VOICE ACCESS INPUT · SAY PRESS ENTER TO SEND')

    def __init__(self, application, reduced_motion=False):
        super().__init__(application, reduced_motion)
        from desktop.setup_speech import SetupSpeech
        self.speech = SetupSpeech(self)
        self.wake_timer = QTimer(self)
        self.wake_timer.setSingleShot(True)
        self.wake_timer.timeout.connect(
            lambda: self._speaking_changed(False) if not self.speech.busy else None)
        self.spoken = True
        self.listener_phase = 'off'
        self.voice_dispatch = False
        self.speech_language = 'auto'
        self.speech_style = 'everyday'
        self.speech_engine = 'offline_piper'
        self.speech.unavailable.connect(lambda: self.panel.footnote.setText('VOICE UNAVAILABLE · ANSWER ON SCREEN'))
        self.speech.speaking.connect(self._speaking_changed)
        self.speech.caption.connect(self.panel.sync_caption)
        self.speech.completed.connect(self.panel.finish_spoken)
        self.vision_tour = []
        self.vision_reply_generation = None
        self.vision_step_request = None
        self.camera_panel_text = None
        self.speech.completed.connect(self._vision_completed)
        self.speech.unavailable.connect(self.cancel_vision)
        # The original fixed-size silhouette mask clipped the resized circle.
        self.orb.clearMask()
        self.orb.relocated.disconnect(self.position_panel)
        self.keep_crystal = False
        self.file_windows = []
        self.spin_frames = []
        self.spin_index = 0
        self.spin_timer = QTimer(self)
        self.spin_clock = QElapsedTimer()
        self.spin_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.spin_timer.setInterval(50)
        self.spin_timer.timeout.connect(self.spin_next)
        self.panel.reduced = reduced_motion
        self.panel.resized_mode.connect(self.position_panel)
        self.orb.motion_changed.connect(self.set_motion_mode)
        self.intro_timer = QTimer(self)
        self.intro_timer.setSingleShot(True)
        self.intro_timer.timeout.connect(self.dock)
        self.docking = QPropertyAnimation(self.orb, b'geometry', self)
        self.docking.setDuration(1100)
        self.docking.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.morph = QVariantAnimation(self)
        self.morph.setDuration(1100)
        self.morph.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.morph.valueChanged.connect(self.set_circle)
        self.motion.setDuration(450)
        self.fade.setDuration(450)
        self.panel_geometry = QPropertyAnimation(self.panel, b'geometry', self)
        self.panel_geometry.setDuration(450)
        self.panel_geometry.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.panel.drag_started.connect(self.panel_geometry.stop)
        self.panel.drag_started.connect(self.motion.stop)
        self.greeting = QLabel('LYA online · Guest mode', None, WINDOW_FLAGS)
        self.greeting.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.greeting.setStyleSheet('color: #eaf8ff; background: rgba(12,24,36,235); border: 1px solid #658594; border-radius: 16px; padding: 12px; font: 14px "Segoe UI";')
        self.greeting.resize(290, 52)
        self.orb.setMinimumSize(1, 1)
        self.orb.setMaximumSize(16777215, 16777215)
        self.transcript = []
        self.first_run_setup = False
        self.pending_question = ''
        self.quitting=False
        self.startup_observation_done=False
        self.face_observation=None
        self.camera_badge=None
        self.visitor_expiry=QTimer(self)
        self.visitor_expiry.setSingleShot(True)
        self.visitor_expiry.timeout.connect(self.brain.visitors.end_presence)
        self.panel.set_mode('input')

    def spin_next(self):
        self.spin_index = self.spin_clock.elapsed() // 50
        if self.spin_index >= len(self.spin_frames):
            self.spin_timer.stop()
            self.orb.spin_frame = None
            self.orb.update()
            if not self.keep_crystal:
                self.intro_timer.start(700)
            return
        self.orb.spin_frame = self.spin_frames[self.spin_index]
        self.orb.update()

    def greet(self):
        self.greeting.show()
        if not self.orb.reduced_motion and self.orb.using_model:
            if not self.spin_frames:
                paths = sorted((HERE / 'assets' / 'rotation').glob('frame-*.png'))
                if len(paths) == 48:
                    self.spin_frames = [QPixmap(str(path)) for path in paths]
            if self.spin_frames:
                self.spin_index = 0
                self.spin_clock.start()
                self.spin_timer.start()
                return
        if not self.keep_crystal:
            self.intro_timer.start(2200)

    def set_circle(self, value):
        self.orb.circle_mix = value
        self.orb.update()

    def set_motion_mode(self, reduced):
        self.panel.reduced = reduced
        if reduced:
            spinning = self.spin_timer.isActive()
            self.spin_timer.stop()
            self.orb.spin_frame = None
            self.position_panel()
            self.motion.stop()
            self.fade.stop()
            self.panel.setWindowOpacity(1)
            if self.panel.reveal.isActive():
                self.panel.answer.setPlainText(self.panel.full_text)
                self.panel.reveal.stop()
            if self.docking.state() == self.docking.State.Running:
                if self.keep_crystal:
                    self.orb.setGeometry(self.docking.endValue())
                    self.docking.stop()
                    self.morph.stop()
                    self.set_circle(0.0)
                else:
                    self.dock(False)
            elif spinning and not self.keep_crystal:
                self.dock(False)

    def start_intro(self):
        if not self.startup_observation_done:
            self.startup_observation_done=True
            QTimer.singleShot(0,self.startup_recognition)
        self.close_panel()
        self.docking.stop()
        self.morph.stop()
        self.spin_timer.stop()
        self.orb.spin_frame = None
        area = self.app.primaryScreen().availableGeometry()
        self.orb.setMinimumSize(1, 1)
        self.orb.setMaximumSize(16777215, 16777215)
        target = QRect(area.center().x() - 115, area.center().y() - 157, 230, 315)
        self.orb.show()
        self.greeting.move(area.center().x() - 145, target.top() - 60)
        if self.orb.reduced_motion:
            self.orb.setGeometry(target)
            self.set_circle(0.0)
            self.greet()
        else:
            self.docking.setStartValue(self.orb.geometry())
            self.docking.setEndValue(target)
            self.docking.start()
            self.morph.setStartValue(1.0)
            self.morph.setEndValue(0.0)
            self.morph.start()
            self.intro_timer.timeout.disconnect()
            self.intro_timer.timeout.connect(self.finish_expansion)
            self.intro_timer.start(1150)

    def startup_recognition(self):
        if (self.quitting or not self.orb.isVisible() or self.brain._identified()
                or (hasattr(self,'owner_dialog') and self.owner_dialog.isVisible())):
            return
        try:
            from storage.visitors import recognition_people
            people=recognition_people(self.brain.db_path)
            if not people:
                return
            if hasattr(self,'vision_dialog') and self.vision_dialog.process.state()!=QProcess.ProcessState.NotRunning:
                return
            from desktop.familiarity import FaceObservation
            self.face_observation=FaceObservation(self)
            self.face_observation.camera.connect(self.show_camera_badge)
            self.face_observation.result.connect(lambda vector:self.observed_person(vector,people))
            self.show_camera_badge(preparing=True)
            self.face_observation.start()
        except Exception:
            self.stop_observation()
            self.brain.visitors.end_presence()

    def show_camera_badge(self,preparing=False):
        if self.quitting:
            return
        if self.camera_badge is None:
            self.camera_badge=QLabel('',None,WINDOW_FLAGS)
        self.camera_badge.setText('CAMERA CHECK · PREPARING' if preparing else 'CAMERA · ONE LOCAL CHECK')
        self.camera_badge.setAccessibleName('Preparing local camera check' if preparing else 'Camera active for one local recognition check')
        self.camera_badge.setStyleSheet(self.greeting.styleSheet())
        self.camera_badge.resize(280,44)
        area=(self.app.screenAt(self.orb.geometry().center()) or self.app.primaryScreen()).availableGeometry()
        self.camera_badge.move(max(area.left(),min(self.orb.x()-108,area.right()-280)),
                               max(area.top(),self.orb.y()-54))
        self.camera_badge.show()

    def observed_person(self,vector,people):
        if self.camera_badge is not None:
            self.camera_badge.close()
            self.camera_badge=None
        if self.quitting or (hasattr(self,'owner_dialog') and self.owner_dialog.isVisible()):
            return
        try:
            person=self.brain.visitors.observe(vector,people)
        except Exception:
            self.brain.visitors.end_presence()
            return
        self.visitor_expiry.start(600000)
        if person is not None:
            address = person['display_name']
            self.greeting.setText('Welcome back, '+address+'.')
            self.orb.set_state(person='admin' if person['role']=='admin' else 'friend',task='idle')
            if (not self.brain_busy and not self.speech.busy
                    and self.listener_phase not in ('hearing','transcribing')):
                self.speak_reply('Welcome back, '+address+'. What shall we work on?' if person['role']=='admin' else 'Hi, '+address+'.')

    def stop_observation(self):
        if self.face_observation is not None:
            self.face_observation.stop()
        if self.camera_badge is not None:
            self.camera_badge.close()
            self.camera_badge=None

    def review_visitors(self):
        try:
            from storage import store,visitors
            session=self.brain.session
            if getattr(self,'passkey_session_id',None)!=session.id:
                raise PermissionError('Phone proof required.')
            with store.store_connection(self.brain.db_path,read_only=True) as db:
                visitors.owner_check(db,session)
        except Exception:
            self.open_owner_access()
            return
        from desktop.familiarity import VisitorReview
        if not hasattr(self,'visitor_review') or not self.visitor_review.isVisible():
            self.visitor_review=VisitorReview(self)
        self.visitor_review.show()
        self.visitor_review.raise_()

    def finish_expansion(self):
        self.intro_timer.timeout.disconnect()
        self.intro_timer.timeout.connect(self.dock)
        self.greet()

    def dock(self, animated=True):
        self.intro_timer.stop()
        self.intro_timer.timeout.disconnect()
        self.intro_timer.timeout.connect(self.dock)
        self.spin_timer.stop()
        self.orb.spin_frame = None
        if self.keep_crystal:
            return
        self.greeting.hide()
        self.docking.stop()
        self.morph.stop()
        area = (self.app.screenAt(self.orb.geometry().center()) or self.app.primaryScreen()).availableGeometry()
        width, height = (96, 112) if self.orb.body_enabled else (64, 64)
        target = QRect(area.center().x() - width // 2, area.bottom() - height - 20, width, height)
        if animated and not self.orb.reduced_motion:
            self.docking.setStartValue(self.orb.geometry())
            self.docking.setEndValue(target)
            self.docking.start()
            self.morph.setStartValue(getattr(self.orb, 'circle_mix', 0.0))
            self.morph.setEndValue(1.0)
            self.morph.start()
        else:
            self.orb.setGeometry(target)
            self.set_circle(1.0)
        self.orb.timer.stop()
        self.orb.refresh_effects()

    def panel_target(self):
        screen = self.app.screenAt(self.orb.geometry().center()) or self.app.primaryScreen()
        size = {'input': (460, 100), 'answer': (500, 320), 'chat': (560, 590), 'files': (520, 470)}[self.panel.mode]
        area = screen.availableGeometry()
        width = min(size[0], area.width() - 24)
        height = min(size[1], area.height() - 24)
        x = max(area.left() + 12, min(self.orb.geometry().center().x() - width // 2, area.right() - width - 12))
        if self.panel.detached:
            return Box(self.panel.x(), self.panel.y(), width, height)
        if self.orb.y() - height - 12 >= area.top() + 12:
            return Box(x, self.orb.y() - height - 12, width, height)
        # Keep the full card beside the crystal when there is no room above it.
        return place_panel(Box(self.orb.x(), self.orb.y(), self.orb.width(), self.orb.height()),
                           Box(area.x(), area.y(), area.width(), area.height()), (width, height))

    def _speaking_changed(self, active):
        from audio import voice
        if active:
            voice._SPEAKING.set()
        else:
            voice._SPEAKING.clear()
        if hasattr(self, 'listener_phase'):
            if not active:
                self.listener_phase = 'standby' if self.voice_thread and self.voice_thread.is_alive() else 'off'
            self.refresh_voice_phase()

    def refresh_voice_phase(self):
        from audio import voice
        phase = ('speaking' if voice._SPEAKING.is_set() else 'thinking'
                 if self.brain_busy else self.listener_phase)
        self.orb.set_voice_phase(phase)
        labels = {'listening': 'LISTENING', 'hearing': 'HEARING YOU', 'thinking': 'THINKING',
                  'speaking': 'SPEAKING · SAY STOP', 'uncertain': 'WORDS UNCERTAIN',
                  'standby': 'VOICE ON', 'off': 'VOICE OFF'}
        if phase in labels:
            self.panel.state_label.setText(labels[phase])

    def on_voice_phase(self, phase):
        self.listener_phase = 'thinking' if phase == 'transcribing' else phase
        self.refresh_voice_phase()
        approval = getattr(self, 'passkey_approval', None)
        dialog = (approval.dialog if approval and approval.dialog and approval.dialog.isVisible()
                  else getattr(self, 'owner_dialog', None))
        if dialog is not None and dialog.isVisible():
            dialog.set_input_phase(phase)

    def on_voice_retry(self, candidate='', paused=False):
        from audio import voice
        self.listener_phase = 'uncertain'
        message = super().on_voice_retry(candidate, paused)
        if not voice.QUIET['on']:
            self.speak_reply(message)

    def speak_reply(self, text):
        if self.spoken:
            self.speech.say(text, language=self.speech_language, style=self.speech_style, engine=self.speech_engine)

    def on_voice(self, text, quiet=False):
        low = ' '.join(text.casefold().split())
        phone_approval = getattr(self, 'passkey_approval', None)
        owner_dialog = (phone_approval.dialog if phone_approval and phone_approval.dialog
                        and phone_approval.dialog.isVisible() else getattr(self, 'owner_dialog', None))
        if owner_dialog is not None and owner_dialog.isVisible():
            owner_dialog.handle_voice(text)
            return
        from vision.answers import camera_control, is_visual_question
        if camera_control(text) or is_visual_question(text):
            self.quiet_reply = quiet
            self.command(text)
            return
        if low in ('open vision', 'look around', 'scan room'):
            self.command(text)
            return
        if is_owner_access_request(text):
            self.command(text)
            return
        if hasattr(self, 'registration_dialog') and self.registration_dialog.isVisible():
            if low in ('stop', 'cancel', 'close', 'close panel'):
                self.registration_dialog.reject()
            return
        if hasattr(self, 'activation_dialog') and self.activation_dialog.isVisible():
            if low in ('stop', 'cancel', 'close', 'close panel'):
                self.activation_dialog.reject()
            return
        if quiet:
            self.speech.stop()
        self.quiet_reply = quiet
        self.voice_dispatch = True
        try:
            super().on_voice(text, quiet)
        finally:
            self.voice_dispatch = False

    def needs_owner_setup(self):
        """True when the encrypted store is readable and holds no administrator."""
        try:
            from storage.store import get_primary_admin
            return get_primary_admin(self.brain.db_path) is None
        except Exception:
            return False   # An unreadable store must never silently open owner setup.

    def begin_owner_setup(self):
        """First run: the owner is set up before the orb opens, like a new phone."""
        if not self.needs_owner_setup():
            self.start_intro()
            return
        self.first_run_setup = True
        self.close_panel()
        self.orb.hide()
        self.open_owner_access()

    def open_owner_access(self):
        self.stop_observation()
        from desktop.owner_setup import OwnerSetupDialog
        approval = getattr(self, 'passkey_approval', None)
        if approval and approval.dialog and approval.dialog.isVisible():
            approval.dialog.raise_()
            return
        if not hasattr(self, 'owner_dialog') or not self.owner_dialog.isVisible():
            self.owner_dialog = OwnerSetupDialog(
                reduced_motion=self.orb.reduced_motion, db_path=self.brain.db_path,
                profile_setup=True, listener=self)
            self.owner_dialog.speech.speaking.connect(self._speaking_changed)
            self.owner_dialog.authenticated.connect(self.on_passkey_authenticated)
            self.owner_dialog.rejected.connect(self.on_setup_dismissed)
            screen = self.app.screenAt(self.orb.geometry().center()) or self.app.primaryScreen()
            area = screen.availableGeometry()
            if self.orb.isVisible():
                target = place_panel(Box(self.orb.x(), self.orb.y(), self.orb.width(), self.orb.height()),
                                     Box(area.x(), area.y(), area.width(), area.height()), (460, 390))
                self.owner_dialog.setGeometry(target.x, target.y, target.width, target.height)
            else:
                self.owner_dialog.move(area.center() - self.owner_dialog.rect().center())
        self.owner_dialog.show()
        self.owner_dialog.raise_()
        self.owner_dialog.activateWindow()

    def start_voice(self, allow_cloud=False):
        dialog = getattr(self, 'owner_dialog', None)
        if dialog is not None and dialog.private_capture:
            return  # A tray toggle or queued restart cannot overlap private enrollment.
        super().start_voice(allow_cloud)

    def on_passkey_authenticated(self, session):
        from desktop.owner_setup import PasskeyApproval
        if not hasattr(self, 'passkey_approval'):
            self.passkey_approval = PasskeyApproval(self)
        self.brain.approve.verifier = self.passkey_approval.verify
        self.passkey_session_id = session.id
        self.on_admin_authenticated(session)

    def on_setup_dismissed(self):
        """Closing setup leaves a usable guest orb, never a locked window."""
        if not getattr(self, 'first_run_setup', False):
            return
        self.first_run_setup = False
        self.orb.show()
        self.dock(False)
        self.panel.footnote.setText('SETUP NOT FINISHED · SAY "REGISTER ADMIN" TO CONTINUE')

    def on_admin_authenticated(self, session):
        self.brain.bind_session(session)
        self.orb.set_state(person='admin', task='idle')
        self.greeting.setText(f'LYA online · {session.person}')
        def welcome():
            if getattr(self, 'passkey_session_id', None) == session.id:
                if getattr(self, 'first_run_setup', False):
                    self.first_run_setup = False
                    self.orb.show()
                    self.start_intro()
                self.panel.set_mode('answer')
                message = (f'Welcome back, {session.person}. Your phone passkey verified owner access for five minutes. '
                           'Private actions still require separate phone approval of the exact request.')
                self.panel.show_answer('Owner verified', message)
                self.open_panel()
                self.speak_reply(f'Welcome back, {session.person}. I am ready. What shall we work on?')
                return
            if hasattr(self, 'activation_dialog') and self.activation_dialog.isVisible():
                return  # The activation's ONLINE act already greets the owner.
            self.panel.set_mode('answer')
            if getattr(self, 'first_run_setup', False):
                self.first_run_setup = False
                dialog = getattr(self, 'activation_dialog', None)
                if dialog is not None:
                    dialog.finished.connect(lambda _: self.start_intro())
                else:
                    QTimer.singleShot(0, self.start_intro)
                return
            self.panel.show_answer('Admin verified',
                f'Welcome, {session.person}. This Windows account has a local admin profile. '
                'Face and voice are not enrolled. Private actions still need separate phone approval.')
            self.open_panel()
        QTimer.singleShot(0, welcome)
        if getattr(self,'passkey_session_id',None)==session.id and any(self.brain.visitors.counts.values()):
            QTimer.singleShot(0,self.review_visitors)

    def open_panel(self):
        if hasattr(self, 'owner_dialog') and self.owner_dialog.isVisible():
            self.owner_dialog.raise_()
            return
        if hasattr(self, 'activation_dialog') and self.activation_dialog.isVisible():
            self.activation_dialog.raise_()
            return
        if hasattr(self, 'registration_dialog') and self.registration_dialog.isVisible():
            self.registration_dialog.raise_()
            return
        was_visible = self.panel.isVisible()
        super().open_panel()
        if self.panel.mode == 'answer':
            self.panel.answer.setFocus()
        if not was_visible and not self.orb.reduced_motion:
            self.motion.stop()
            destination = QPoint(self.panel_target().x, self.panel_target().y)
            self.motion.setStartValue(destination + QPoint(0, 12))
            self.motion.setEndValue(destination)
            self.motion.start()

    def position_panel(self):
        if self.panel.isFullScreen():
            return
        if not hasattr(self, 'panel_geometry'):
            return super().position_panel()
        target = self.panel_target()
        rect = QRect(target.x, target.y, target.width, target.height)
        if not self.panel.reduced and self.panel_geometry.state() == self.panel_geometry.State.Running and self.panel_geometry.endValue() == rect:
            return
        self.panel_geometry.stop()
        if self.panel.isVisible() and not self.panel.reduced:
            self.motion.stop()
            self.panel_geometry.setStartValue(self.panel.geometry())
            self.panel_geometry.setEndValue(rect)
            self.panel_geometry.start()
        else:
            self.panel.setGeometry(rect)

    def toggle_panel(self):
        if self.panel.mode == 'answer':
            self.panel.set_mode('input')
            self.open_panel()
            return
        if self.panel.isVisible():
            self.close_panel()
        else:
            self.dock(False)
            self.panel.set_mode('input')
            self.open_panel()

    def wake(self):
        # Voice wake stays in the compact circle instead of replaying the
        # crystal introduction while the owner waits to ask their question.
        self.close_panel()
        self.dock(False)
        self.orb.show()
        if self.spoken:
            self.speech.prewarm()
        if self.spoken:
            try:
                import winsound
                path = HERE / 'assets' / 'wake-greeting.wav'
                with wave.open(str(path), 'rb') as sound:
                    duration_ms = round(1000 * sound.getnframes() / sound.getframerate())
                self._speaking_changed(True)
                winsound.PlaySound(str(path),
                                   winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                self.wake_timer.start(duration_ms + 100)
            except (ImportError, RuntimeError, OSError, wave.Error):
                self._speaking_changed(False)
                self.speak_reply("I'm here. What can I help you with?")

    def stop_wake_greeting(self):
        if hasattr(self, 'wake_timer') and self.wake_timer.isActive():
            import winsound
            self.wake_timer.stop()
            winsound.PlaySound(None, 0)
            self._speaking_changed(False)

    def close_panel(self):
        self.cancel_vision()
        self.stop_wake_greeting()
        if hasattr(self, 'speech'):
            self.speech.stop(keep_warm=True)
        if hasattr(self, 'intro_timer'):
            self.panel_geometry.stop()
            self.intro_timer.stop()
            self.docking.stop()
            self.greeting.hide()
            self.transcript.clear()
        if self.panel.isFullScreen():
            self.panel.showNormal()
        super().close_panel()
        self.panel.reveal.stop()
        self.panel.set_mode('input')
        if hasattr(self, 'intro_timer'):
            self.dock(False)

    def command(self, text):
        low = ' '.join(text.casefold().split())
        if low in ('visitor review','review visitors',"i'm back",'i am back'):
            self.review_visitors()
            return
        if low in ('sleep','guest mode'):
            self.stop_observation()
            self.brain.visitors.end_presence()
            if low=='guest mode':
                from security.policy import Session
                self.brain.bind_session(Session(id='guest'))
                self.transcript.clear()
                self.panel.show_answer('Ready.','Private access is locked.')
                return
        self.cancel_vision(stop_speech=False)
        self.stop_wake_greeting()
        self.speech.stop(keep_warm=low not in ('voice off', 'stop speaking'))
        from vision.answers import camera_control, is_visual_question
        camera_action = camera_control(text)
        if camera_action == 'close':
            if hasattr(self, 'vision_dialog'):
                self.vision_dialog.close()
            return
        camera_active = (hasattr(self, 'vision_dialog') and
                         self.vision_dialog.process.state() != QProcess.ProcessState.NotRunning)
        if is_visual_question(text, camera_active=camera_active):
            if self.brain_busy:
                return
            self.generation += 1
            self.brain_cancel.clear()
            self.pending_question = text
            self.request_quiet = getattr(self, 'quiet_reply', False)
            self.quiet_reply = False
            self.ensure_vision()
            self.vision_dialog.show()
            self.vision_dialog.ask(text, self.generation)
            return
        if low in ('voice on', 'voice off', 'stop speaking'):
            if low != 'stop speaking':
                self.spoken = low == 'voice on'
            if low == 'voice on':
                self.speak_reply("I'm ready. I'll speak my answers aloud.")
            return
        if low in ('voice economy', 'voice natural'):
            self.speech_engine = 'offline_sapi' if low.endswith('economy') else 'offline_piper'
            self.panel.footnote.setText('VOICE · ' + self.speech_engine.upper())
            return
        if low.startswith('voice language '):
            language = low.removeprefix('voice language ')
            if language in ('auto', 'en', 'ta'):
                self.speech_language = language
                self.panel.footnote.setText('VOICE LANGUAGE · ' + language.upper())
            return
        if low.startswith('voice style '):
            style = low.removeprefix('voice style ')
            if style in ('everyday', 'joyful', 'storyteller', 'hacker', 'hype', 'whisper', 'night'):
                self.speech_style = style
            return
        if low in ('open recovery', 'memory recovery', 'backup notes', 'restore notes'):
            from desktop.recovery import RecoveryDialog
            if not hasattr(self, 'recovery_dialog'):
                self.recovery_dialog = RecoveryDialog(get_session=lambda: self.brain.session,
                    approve=self.brain.approve, db_path=self.brain.db_path, clock=self.brain.clock)
                self.recovery_dialog.signals.done.connect(
                    lambda *_: self.quit() if getattr(self, '_quit_after_recovery', False) else None)
            self.recovery_dialog.show()
            self.recovery_dialog.raise_()
            self.recovery_dialog.activateWindow()
            if low == 'restore notes':
                self.recovery_dialog.tabs.setCurrentIndex(1)
            return
        if camera_action == 'open' or low in ('open vision', 'look around', 'scan room'):
            self.ensure_vision()
            self.vision_dialog.show()
            self.vision_dialog.raise_()
            self.vision_dialog.activateWindow()
            if (camera_action == 'open' or low in ('look around', 'scan room')) and self.vision_dialog.process.state() == self.vision_dialog.process.ProcessState.NotRunning:
                self.vision_dialog.toggle_live()
            return
        if is_owner_access_request(text):
            self.close_panel()
            self.open_owner_access()
            return
        if low in ('stay as a crystal', 'stay as crystal', 'stay crystal', 'show crystal'):
            self.keep_crystal = True
            self.start_intro()
            return
        if low in ('become a circle', 'become circle', 'circle', 'hide crystal'):
            self.keep_crystal = False
            self.dock()
            return
        if low in ('close chat', 'close chat box'):
            self.close_panel()
            return
        if low in ('full screen', 'fullscreen', 'make it full screen', 'maximize chat'):
            self.panel.set_mode('chat')
            self.panel_geometry.stop()
            self.motion.stop()
            self.panel.showFullScreen()
            return
        if low in ('exit full screen', 'restore chat', 'small chat'):
            self.panel.showNormal()
            self.position_panel()
            return
        names = [name for name in DOCUMENTS if name.casefold() in low]
        if low.startswith(('show ', 'open ')) and names:
            for name in names:
                self.read_document(name)
            return
        if low in ('show two files', 'show 2 files', 'show three files', 'show 3 files'):
            for name in DOCUMENTS[:2 if ('two' in low or '2' in low) else 3]:
                self.read_document(name)
            return
        if low in ('chat', 'open chat', 'chat box', 'open chat box'):
            self.panel.set_mode('chat')
            self.panel.show_transcript('\n\n'.join(self.transcript) or 'Ask LYA below.')
            self.open_panel()
            return
        if low not in ('stop', 'cancel', 'close', 'close panel', 'sleep', 'quit', 'exit'):
            if self.panel.mode != 'chat':
                self.panel.set_mode('answer')
            self.open_panel()
        if not self.brain_busy:
            self.pending_question = text
        super().command(text)
        if low in ('time', 'what time is it', 'date', 'what date is it', 'day',
                   'status', 'system status', 'check', 'help', 'commands', 'what can you do'):
            quiet = getattr(self, 'quiet_reply', False)
            self.quiet_reply = False
            if not quiet:
                reply = (self.panel.full_text if self.panel.reveal.isActive()
                         else self.panel.answer.toPlainText())
                title = self.panel.title_label.text()
                if title.endswith((' AM', ' PM')):
                    reply = title + '\n' + reply
                self.speak_reply(reply)

    def ensure_vision(self):
        if not hasattr(self, 'vision_dialog'):
            from camera_eyes import VisionDialog
            self.vision_dialog = VisionDialog(access_check=self.camera_owner)
            self.vision_dialog.answer_ready.connect(self.on_vision_answer)
            self.vision_dialog.session_ended.connect(self.end_vision_session)
            self.vision_dialog.focus_cleared.connect(self.cancel_vision)

    def camera_owner(self):
        try:
            self.brain._authorize('camera_view', 'Local camera view')
            return self.brain.session
        except Exception:
            return None  # Guest, expired, revoked, changed role or unreadable store: fail closed.

    def end_vision_session(self):
        self.cancel_vision()
        current = (self.panel.spoken_original or
                   (self.panel.full_text if self.panel.reveal.isActive() else self.panel.answer.toPlainText()))
        if self.camera_panel_text and current.endswith(self.camera_panel_text):
            self.panel.spoken_original = self.panel.spoken_prefix = ''
            self.panel.spoken_tokens = []
            self.panel.show_answer('Camera off', 'Camera view and observations cleared.')
        self.camera_panel_text = None

    def cancel_vision(self, stop_speech=True):
        was_active = self.vision_reply_generation is not None
        self.vision_tour = []
        self.vision_reply_generation = None
        self.vision_step_request = None
        if hasattr(self, 'vision_dialog'):
            self.vision_dialog.pending_question = None
            self.vision_dialog.clear_focus()
        if was_active and stop_speech:
            self.speech.stop(keep_warm=True)  # Clear state first: stop also emits completion.

    def _vision_completed(self):
        if self.vision_step_request is not None:
            expected = self.vision_step_request
            # An error completion precedes its unavailable signal; let both arrive first.
            QTimer.singleShot(0, lambda: self._next_vision_item(expected))

    def _next_vision_item(self, expected=None):
        if expected is not None and expected != self.vision_step_request:
            return
        if expected is not None and expected[1] != self.speech.request:
            self.cancel_vision()
            return
        if (self.vision_reply_generation is None or self.vision_reply_generation != self.generation or
                self.brain_cancel.is_set() or (expected is not None and self.speech.cancelled) or not self.spoken or
                not self.vision_dialog.focus_active or not self.vision_dialog.authorized()):
            self.cancel_vision()
            return
        self.vision_step_request = None
        if not self.vision_tour:
            self.vision_reply_generation = None
            self.vision_dialog.focus_item(None)
            self.vision_dialog.status.setText('Checked frame · tour complete · local only')
            return
        item = self.vision_tour.pop(0)
        self.vision_dialog.focus_item(item)
        self.speak_reply(item['text'])
        self.vision_step_request = (self.generation, self.speech.request)

    def on_vision_answer(self, generation, text):
        if generation != self.generation or self.brain_cancel.is_set():
            return
        from brain.workflow import Answer
        details = getattr(self.vision_dialog, 'answer_details', None)
        tour = bool(details and details['request_id'] == generation and details['tour'] and
                    self.spoken and not getattr(self, 'request_quiet', False))
        quiet = getattr(self, 'request_quiet', False)
        self.vision_reply_generation = generation if self.spoken and not quiet else None
        if tour:
            self.request_quiet = True  # Render the inventory once; narrate each item through the warm worker.
        history = list(self.transcript)
        try:
            self.on_brain(generation, Answer(text, 'local-vision'))
        finally:
            self.request_quiet = quiet
            self.transcript = history  # Camera observations never become chat history or model context.
        self.panel.footnote.setText('LOCAL CAMERA · NO IMAGE UPLOADS')
        self.camera_panel_text = text
        self.open_panel()
        if tour:
            self.vision_tour = list(details['items'])
            self._next_vision_item()

    def sleep(self):
        self.stop_observation()
        self.visitor_expiry.stop()
        self.brain.visitors.end_presence()
        self.cancel_vision()
        if hasattr(self, 'vision_dialog'):
            self.vision_dialog.close()
        super().sleep()

    def show_files(self):
        self.panel.set_mode('files')
        super().show_files()

    def ask_brain(self, text):
        if not self.brain_busy:
            self.request_quiet = getattr(self, 'quiet_reply', False)
            self.quiet_reply = False
        if self.panel.mode == 'chat' and not self.brain_busy:
            self.transcript.append('You: ' + text)
            self.transcript = self.transcript[-12:]
            self.panel.show_transcript('\n\n'.join(self.transcript))
            self.panel.preserve_chat = True
            try:
                super().ask_brain(text)
            finally:
                self.panel.preserve_chat = False
            return
        super().ask_brain(text)
        if self.voice_dispatch:
            self.panel.hide()

    def read_document(self, name):
        # Preserve the existing four-document allowlist and bounded local reader.
        if name not in DOCUMENTS:
            return
        for old in self.file_windows[:]:
            if not old.isVisible():
                self.file_windows.remove(old)
                old.deleteLater()
        for window in self.file_windows:
            if window.windowTitle() == name and window.isVisible():
                window.raise_()
                return
        window = QDialog(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        window.setWindowTitle(name)
        layout = QVBoxLayout(window)
        content = QTextBrowser(window)
        content.setOpenExternalLinks(False)
        opened = True
        try:
            content.setPlainText(read_project_document(name))
        except (OSError, PermissionError):
            opened = False
            content.setPlainText('This project document could not be opened.')
        layout.addWidget(content)
        window.setStyleSheet('background: #12202d; color: #eaf4fa; font: 14px "Segoe UI";')
        area = (self.app.screenAt(self.orb.geometry().center()) or self.app.primaryScreen()).availableGeometry()
        width, height = min(420, area.width()//2), min(430, area.height()-40)
        occupied = [w.frameGeometry() for w in self.file_windows if w.isVisible()]
        if self.panel.isVisible():
            occupied.append(self.panel.geometry())
        occupied.append(self.orb.geometry())
        candidates = [QRect(x,y,width,height) for y in range(area.top()+12,area.bottom()-height+1,40)
                      for x in range(area.left()+12,area.right()-width+1,40)]
        def overlap(rect):
            return sum(rect.intersected(other).width()*rect.intersected(other).height()
                       for other in occupied if rect.intersects(other))
        target = min(candidates, key=overlap) if candidates else QRect(area.topLeft(), self.panel.size())
        window.setGeometry(target)
        window.show()
        self.file_windows.append(window)
        self.set_state(task='files')
        self.speak_reply('Your document is open.' if opened else 'I could not open that document.')

    def on_brain(self, generation, answer):
        valid = generation == self.generation and not self.brain_cancel.is_set()
        if valid and answer.route=='mobile-pairing':
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(answer.evidence[0]['url']))
        in_chat = valid and self.panel.mode == 'chat'
        self.panel.preserve_chat = in_chat
        try:
            super().on_brain(generation, answer)
        finally:
            self.panel.preserve_chat = False
        if valid:
            self.listener_phase = 'standby' if self.voice_thread and self.voice_thread.is_alive() else 'off'
            self.refresh_voice_phase()
            self.open_panel()
        spoken_now = valid and self.spoken and not getattr(self, 'request_quiet', False)
        if in_chat:
            reply = 'LYA: ' + answer.text[:8000]
            self.transcript.append(reply)
            self.transcript = self.transcript[-12:]
            history = '\n\n'.join(self.transcript[:-1]) + '\n\nLYA: '
            if spoken_now:
                self.panel.begin_spoken(answer.text[:8000], history)
                self.speak_reply(answer.text)
            else:
                self.panel.animate_append(history, answer.text[:8000], '')
        elif valid:
            self.transcript.extend(['You: ' + self.pending_question, 'LYA: ' + answer.text[:8000]])
            self.transcript = self.transcript[-12:]
            context = ('You asked: ' + self.pending_question + '\n\nLYA: '
                       if self.pending_question else '')
            if spoken_now:
                self.panel.begin_spoken(answer.text, context)
                self.speak_reply(answer.text)
            else:
                self.panel.animate_answer(context + answer.text)

    def quit(self):
        self.quitting = True
        self.stop_observation()
        self.visitor_expiry.stop()
        self.brain.visitors.discard()
        self.brain.visitors.end_presence()
        if hasattr(self,'visitor_review'):
            self.visitor_review.reject()
        if hasattr(self, 'owner_dialog'):
            self.owner_dialog.reject()
        if hasattr(self, 'passkey_approval'):
            self.passkey_approval.close()
        self.cancel_vision()
        self.stop_wake_greeting()
        self.speech.stop()
        if hasattr(self, 'recovery_dialog'):
            if self.recovery_dialog.busy:
                self._quit_after_recovery = True
                self.recovery_dialog.reject()
                return  # Finish cancellation without blocking Qt or destroying its worker signals.
            self.recovery_dialog.reject()
        if hasattr(self, 'vision_dialog'):
            self.vision_dialog.close()
        if hasattr(self, 'registration_dialog'):
            self.registration_dialog.reject()
        self.spin_timer.stop()
        for window in self.file_windows:
            window.close()
            window.deleteLater()
        self.file_windows.clear()
        self.spin_frames.clear()
        self.panel_geometry.stop()
        self.intro_timer.stop()
        self.docking.stop()
        self.morph.stop()
        self.greeting.close()
        self.panel.reveal.stop()
        self.transcript.clear()
        super().quit()



