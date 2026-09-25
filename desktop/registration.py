"""Native owner setup with a brief, battery-conscious identity-core reveal."""
from pathlib import Path
import secrets
import time

from PySide6.QtCore import (QElapsedTimer, QPointF, QProcess, QRectF, QTimer, Qt,
                            QUrl, QVariantAnimation, QEasingCurve, Signal)
from PySide6.QtGui import (QColor, QDesktopServices, QFont, QPainter, QPen,
                           QPixmap, QPolygonF)
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFrame,
                               QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea,
                               QStackedWidget, QVBoxLayout, QWidget)

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "security" / "HelloVerifier.exe"
MESSAGES = {
    "DeviceNotPresent": "Windows verification is unavailable here. Set up Windows Hello PIN, then retry from your normal desktop.",
    "NotConfiguredForUser": "Set up Windows Hello PIN in Settings > Accounts > Sign-in options, then retry.",
    "DisabledByPolicy": "Windows verification is blocked by policy. Setup remains locked.",
    "DeviceBusy": "Windows verification is busy. Close the other prompt and retry.",
    "RetriesExhausted": "Windows paused verification after too many attempts. Try again later.",
    "Canceled": "Verification cancelled. You remain a guest.",
    "TimedOut": "Verification timed out. You remain a guest.",
}


class HologramDialog(QDialog):
    """Paint one intact core and a one-shot connected reveal; never animate at idle."""
    STAGES = ("IDENTITY", "DEVICE", "SIGNALS", "REVIEW")

    def __init__(self, reduced_motion=False):
        super().__init__()
        self.reduced_motion, self.progress, self.drag_offset = reduced_motion, 1.0, None
        self.current_step = 0
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(700, 650)
        self.sprite = QPixmap(str(ROOT / "desktop/assets/obsidian-baked.png")).scaled(
            220, 250, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.body = QScrollArea(self)
        self.body.setObjectName("contentArea")
        self.body.setFrameShape(QFrame.Shape.NoFrame)
        self.body.setWidgetResizable(True)
        self.body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.form = QWidget()
        self.form.setObjectName("contentSurface")
        self.body.setWidget(self.form)
        self.fade = None
        self.skip = QPushButton("Skip", self)
        self.skip.setObjectName("skipIntro")
        self.skip.setAutoDefault(False)
        self.skip.setAccessibleName("Skip introduction animation")
        self.skip.clicked.connect(self.finish_intro)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(1050)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self.animate_frame)
        self.animation.finished.connect(self.finish_intro)
        self.paint_clock = QElapsedTimer()
        self.paint_clock.start()
        self.scan_progress = -1.0
        self.scan = QVariantAnimation(self)
        self.scan.setDuration(720)
        self.scan.setStartValue(0.0)
        self.scan.setEndValue(1.0)
        self.scan.valueChanged.connect(self.scan_frame)
        self.scan.finished.connect(self.finish_scan)

    def scan_frame(self, value):
        self.scan_progress = float(value)
        self.update()

    def finish_scan(self):
        self.scan_progress = -1.0
        self.update()

    def start_scan(self):
        if not self.reduced_motion:
            self.scan.stop()
            self.scan.start()

    def animate_frame(self, value):
        if self.paint_clock.elapsed() < 33 and float(value) < 1.0:
            return
        self.paint_clock.restart()
        self.set_progress(float(value))

    def set_progress(self, value):
        self.progress = max(0.0, min(1.0, value))
        self.body.setVisible(self.progress >= 0.34)
        if self.fade:
            self.fade.setOpacity(max(0.0, min(1.0, (self.progress - 0.34) / 0.40)))
        self.update()

    def finish_intro(self):
        self.animation.stop()
        self.set_progress(1.0)
        self.skip.hide()
        self.body.setGraphicsEffect(None)
        self.fade = None

    def showEvent(self, event):
        super().showEvent(event)
        if self.reduced_motion:
            self.finish_intro()
            return
        self.fade = QGraphicsOpacityEffect(self.body)
        self.body.setGraphicsEffect(self.fade)
        self.set_progress(0.0)
        self.skip.show()
        self.skip.raise_()
        self.animation.start()

    def hideEvent(self, event):
        self.finish_intro()
        self.scan.stop()
        self.finish_scan()
        super().hideEvent(event)

    def resizeEvent(self, event):
        self.body.setGeometry(62, 224, max(240, self.width()-124), max(200, self.height()-258))
        self.skip.setGeometry(self.width()-104, 18, 64, 30)
        super().resizeEvent(event)

    @staticmethod
    def _diamond(painter, center, radius, fill, outline):
        x, y = center.x(), center.y()
        points = QPolygonF((QPointF(x, y-radius), QPointF(x+radius, y),
                            QPointF(x, y+radius), QPointF(x-radius, y)))
        painter.setBrush(fill)
        painter.setPen(QPen(outline, 1))
        painter.drawPolygon(points)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        reveal = max(0.0, min(1.0, (self.progress-0.16)/0.54))
        frame = QRectF(22, 18, self.width()-44, self.height()-36)
        p.setOpacity(reveal)
        p.setBrush(QColor(7, 14, 24, 255))
        p.setPen(QPen(QColor(87, 156, 173, 95), 1))
        p.drawRoundedRect(frame, 28, 28)
        if self.scan_progress >= 0:
            x = frame.left() + frame.width() * self.scan_progress
            p.setClipRect(frame)
            p.setOpacity(0.22)
            p.setPen(QPen(QColor("#8cecf4"), 2))
            p.drawLine(QPointF(x, frame.top()+18), QPointF(x, 208))
            p.setClipping(False)
            p.setOpacity(reveal)
        start, dock = QPointF(self.width()/2, self.height()/2-20), QPointF(self.width()/2, 132)
        center = QPointF(start.x()+(dock.x()-start.x())*reveal,
                         start.y()+(dock.y()-start.y())*reveal)
        scale = 1.0-0.35*reveal
        if self.sprite.isNull():
            p.setOpacity(1)
            p.setPen(QPen(QColor("#8cecf4"), 2))
            p.setBrush(QColor(20, 57, 71, 230))
            p.drawEllipse(QRectF(center.x()-34, center.y()-34, 68, 68))
        else:
            w, h = self.sprite.width()*scale, self.sprite.height()*scale
            p.setOpacity(1)
            p.drawPixmap(QRectF(center.x()-w/2, center.y()-h/2, w, h), self.sprite,
                         QRectF(self.sprite.rect()))
        if reveal < 0.12:
            return
        p.setOpacity(reveal)
        accent = QColor("#a5edf2") if getattr(self, 'is_speaking', False) else QColor("#49616d")
        p.setPen(QPen(accent, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(center.x()-74, 204, 148, 12))
        for i in range(4):
            p.setBrush(QColor("#a5edf2") if i == self.current_step else QColor("#304550"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(self.width()/2-24+i*16, self.height()-23), 2.5, 2.5)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 58:
            self.drag_offset = event.globalPosition().toPoint()-self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None:
            self.move(event.globalPosition().toPoint()-self.drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_offset = None
        super().mouseReleaseEvent(event)


class RegistrationDialog(HologramDialog):
    authenticated = Signal(object)

    def __init__(self, reduced_motion=False, speech_enabled=True, db_path=None):
        super().__init__(reduced_motion)
        self.db_path = db_path
        self.proof_nonce = ""
        self.setWindowTitle("LYA · Owner introduction")
        self.setStyleSheet("""
            QWidget { color:#eaf3f6; font:14px "Segoe UI"; background:transparent; }
            QScrollArea, QScrollArea > QWidget > QWidget { background:transparent; }
            QLabel#eyebrow { color:#79dbe6; font-size:11px; font-weight:600; }
            QLabel#heroTitle { color:#f4fbfc; font-size:30px; font-weight:600; }
            QLabel#subtle { color:#9db0b8; font-size:13px; }
            QLabel#status { color:#b8d0d6; font-size:12px; padding:9px 12px;
                background:#0e1c29; border:1px solid #263c49; border-radius:9px; }
            QFrame#card { background:#0d1b27; border:1px solid #263d49; border-radius:12px; }
            QLineEdit { min-height:44px; padding:0 14px; background:#0b1823;
                border:1px solid #345665; border-radius:10px; selection-background-color:#2b7f8b; }
            QLineEdit:hover { border-color:#4a7482; }
            QLineEdit:focus { border:1px solid #8cecf4; }
            QPushButton { min-height:38px; padding:0 15px; background:#142837;
                border:1px solid #355363; border-radius:9px; color:#eaf4f6; font-weight:600; }
            QPushButton:hover { background:#1a3445; border-color:#5d8998; }
            QPushButton:pressed { background:#10222f; }
            QPushButton:focus { border:1px solid #9ff4fa; }
            QPushButton:disabled { color:#607781; background:#101c25; border-color:#273843; }
            QPushButton#primary { background:#a5edf2; color:#071317; border-color:#c8fbff; }
            QPushButton#primary:hover { background:#c0f7fa; }
            QPushButton#primary:disabled { background:#172b35; color:#67818b; border-color:#304653; }
            QPushButton#quiet, QPushButton#skipIntro { background:transparent; color:#94abb4; border-color:#2a414d; }
            QCheckBox { spacing:12px; padding:4px 0; }
            QCheckBox::indicator { width:18px; height:18px; border:1px solid #527887;
                border-radius:5px; background:#0b1823; }
            QCheckBox::indicator:hover { border-color:#8cecf4; }
            QCheckBox::indicator:checked { background:#8cecf4; border-color:#bffaff; }
        """)
        layout = QVBoxLayout(self.form)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        self.steps = QLabel(self.form)
        self.steps.hide()  # Accessible state for tests; visual progress is four small dots.
        self.prompt = self.text(layout, "", role="heroTitle")
        self.prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption = self.text(layout, "", role="subtle")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pages = QStackedWidget()
        layout.addWidget(self.pages, 1)
        first = self.page()
        self.name = QLineEdit()
        self.name.setMaxLength(80)
        self.name.setPlaceholderText("Your name…")
        self.name.setAccessibleName("Preferred display name")
        self.name.returnPressed.connect(lambda: self.change_step(1))
        first.addWidget(self.name)
        first.addStretch()
        device = self.page()
        self.consent = QCheckBox("Allow Windows to verify me")
        device.addWidget(self.consent)
        self.verify = self.button("Verify with Windows", device, self.start_verification, primary=True)
        row = QHBoxLayout()
        self.check_device = self.button("Check device", row, self.check_availability, quiet=True)
        self.settings = self.button("PIN settings", row, self.open_settings, quiet=True)
        device.addLayout(row)
        device.addStretch()
        privacy = self.page()
        self.face = QCheckBox("Face greetings later")
        self.voice = QCheckBox("Recognize my voice later")
        privacy.addWidget(self.face)
        privacy.addWidget(self.voice)
        privacy.addStretch()
        review = self.page()
        self.summary = self.text(review, "", role="subtle")
        self.summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.profile_consent = QCheckBox("Create my encrypted admin profile on this Windows account")
        self.profile_consent.setAccessibleName("Confirm local admin profile creation")
        review.addWidget(self.profile_consent)
        review.addStretch()
        self.status = self.text(layout, "", role="subtle")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setAccessibleName("Setup status")
        audio_row = QHBoxLayout()
        self.mute = self.button("Voice on" if speech_enabled else "Voice off", audio_row, self.toggle_speech, quiet=True)
        self.mute.setCheckable(True)
        self.mute.setChecked(speech_enabled)
        self.replay = self.button("Replay", audio_row, self.narrate, quiet=True)
        layout.addLayout(audio_row)
        nav = QHBoxLayout()
        self.cancel = self.button("Close", nav, self.reject, quiet=True)
        nav.addStretch()
        self.back = self.button("Back", nav, lambda: self.change_step(-1), quiet=True)
        self.next = self.button("Continue", nav, lambda: self.change_step(1), primary=True)
        layout.addLayout(nav)
        from desktop.setup_speech import SetupSpeech
        self.speech = SetupSpeech(self)
        self.is_speaking = False
        self.speech.speaking.connect(self.speech_state)
        self.speech.unavailable.connect(lambda: self.status.setText("Voice unavailable. You can continue by typing."))
        self.narration_timer = QTimer(self)
        self.narration_timer.setSingleShot(True)
        self.narration_timer.timeout.connect(self.narrate)
        self.closing = False
        self.active, self.operation = False, "verify"
        self.verified_name, self.verified_until = "", 0.0
        self.process = QProcess(self)
        self.process.finished.connect(self.completed)
        self.process.errorOccurred.connect(self.failed)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.expired)
        self.proof_timeout = QTimer(self)
        self.proof_timeout.setSingleShot(True)
        self.proof_timeout.timeout.connect(self.update_step)
        self.name.textChanged.connect(self.name_changed)
        self.consent.toggled.connect(self.update_button)
        self.face.toggled.connect(self.update_summary)
        self.voice.toggled.connect(self.update_summary)
        self.profile_consent.toggled.connect(self.update_step)
        self.update_button()
        self.update_step()

    PROMPTS = (
        ("Hi. I'm LYA.", "What should I call you?"),
        ("Let's make this yours.", "Verify with Windows. Your PIN stays with Windows."),
        ("A familiar face. A familiar voice.", "Recognition is still being built. These are preferences only."),
        ("Ready when you are.", "Create a local admin profile. Face and voice can be added later."),
    )

    def speech_state(self, speaking):
        self.is_speaking = speaking
        self.update()

    def narrate(self):
        self.narration_timer.stop()
        if self.isVisible() and not self.closing and self.mute.isChecked() and not self.active:
            self.speech.say(" ".join(self.PROMPTS[self.pages.currentIndex()]))

    def toggle_speech(self):
        self.mute.setText("Voice on" if self.mute.isChecked() else "Voice off")
        if self.mute.isChecked():
            self.narrate()
        else:
            self.narration_timer.stop()
            self.speech.stop()

    def hideEvent(self, event):
        self.narration_timer.stop()
        self.speech.stop()
        super().hideEvent(event)

    def page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 5, 0)
        layout.setSpacing(15)
        self.pages.addWidget(widget)
        return layout

    def section(self, layout, title, subtitle):
        self.text(layout, title, heading=True)
        self.text(layout, subtitle, role="subtle")

    @staticmethod
    def card(layout):
        frame = QFrame()
        frame.setObjectName("card")
        inside = QVBoxLayout(frame)
        inside.setContentsMargins(18, 16, 18, 16)
        inside.setSpacing(12)
        layout.addWidget(frame)
        return frame, inside

    @staticmethod
    def text(layout, value, heading=False, role=""):
        label = QLabel(value)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        if heading:
            label.setStyleSheet("font-size:22px; font-weight:600; color:#f0fafb;")
        if role:
            label.setObjectName(role)
        layout.addWidget(label)
        return label

    @staticmethod
    def button(value, layout, callback, primary=False, quiet=False):
        button = QPushButton(value)
        button.setAutoDefault(False)
        button.setObjectName("primary" if primary else "quiet" if quiet else "")
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def name_changed(self):
        self.verified_name, self.verified_until = "", 0
        self.proof_timeout.stop()
        self.update_button()
        self.update_step()

    def update_summary(self):
        verified = self.verified_name == self.name.text().strip() and time.monotonic() < self.verified_until
        mark = lambda yes: "READY" if yes else "PENDING"
        self.summary.setText(
            f"{mark(bool(self.name.text().strip()))}   Name · {self.name.text().strip() or 'not chosen'}\n"
            f"{mark(verified)}   Windows checkpoint\n"
            f"{mark(False)}   Face · {'requested' if self.face.isChecked() else 'not selected'} · capture not connected\n"
            f"{mark(False)}   Voice · {'requested' if self.voice.isChecked() else 'not selected'} · capture not connected\n"
            "LOCKED   Owner profile: not created\n"
            "Recovery requires an independent encrypted backup; none is made here.")

    def update_step(self):
        index = self.pages.currentIndex()
        self.current_step = index
        self.steps.setText(f"OWNER INTRODUCTION   /   0{index+1} OF 04   /   {self.STAGES[index]}")
        self.back.setEnabled(index > 0 and not self.active)
        verified = (self.verified_name == self.name.text().strip()
                    and time.monotonic() < self.verified_until)
        self.next.setEnabled(not self.active and (index < 3 or
                             (verified and self.profile_consent.isChecked())))
        self.next.setText(("Continue", "Continue", "Continue", "Create admin")[index])
        self.prompt.setText(self.PROMPTS[index][0])
        self.caption.setText(self.PROMPTS[index][1])
        self.update_summary()
        self.update()

    def change_step(self, delta):
        if self.active:
            return
        if delta > 0 and self.pages.currentIndex() == 3:
            self.create_admin()
            return
        if delta > 0 and not self.name.text().strip():
            self.status.setText("Add a display name to continue.")
            self.name.setFocus()
            return
        self.pages.setCurrentIndex(max(0, min(3, self.pages.currentIndex()+delta)))
        self.body.verticalScrollBar().setValue(0)
        self.update_step()
        self.status.clear()
        self.speech.stop()
        if self.isVisible():
            self.narration_timer.start(250)

    def open_settings(self):
        QDesktopServices.openUrl(QUrl("ms-settings:signinoptions"))

    def update_button(self):
        idle = not self.active and self.process.state() == QProcess.ProcessState.NotRunning
        self.verify.setEnabled(idle and bool(self.name.text().strip()) and self.consent.isChecked())
        self.check_device.setEnabled(idle)
        self.settings.setEnabled(idle)

    def check_availability(self):
        self.start_process("check")

    def start_verification(self):
        if self.name.text().strip() and self.consent.isChecked():
            self.start_process("verify")

    def start_process(self, operation):
        if self.active or self.process.state() != QProcess.ProcessState.NotRunning:
            return
        if not HELPER.is_file():
            self.status.setText("Verification helper missing · Run security\\build-hello.cmd")
            return
        self.narration_timer.stop()
        self.speech.stop()
        self.start_scan()
        self.active, self.operation = True, operation
        self.verified_name, self.verified_until = "", 0
        self.proof_nonce = secrets.token_urlsafe(24) if operation == "verify" else ""
        self.name.setEnabled(False)
        self.consent.setEnabled(False)
        self.update_button()
        self.update_step()
        self.status.setText("Checking Windows · Sensors remain off…" if operation == "check" else
                            "Complete the secure Windows prompt · PIN stays with Windows…")
        self.timeout.start(15000 if operation == "check" else 100000)
        self.process.start(str(HELPER), ["check"] if operation == "check" else
                           ["verify", str(int(self.winId())), self.proof_nonce])

    def reset_controls(self):
        self.active = False
        self.timeout.stop()
        self.name.setEnabled(True)
        self.consent.setEnabled(True)
        self.update_button()
        self.update_step()

    def completed(self, code, exit_status):
        if not self.active:
            self.update_button()
            return
        result = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace").strip()
        nonce, self.proof_nonce = self.proof_nonce, ""
        self.reset_controls()
        success = code == 0 and exit_status == QProcess.ExitStatus.NormalExit
        if self.operation == "check" and success and result == "Available":
            self.status.setText("Windows verification available · Availability alone does not verify you")
        elif (self.operation == "verify" and success and nonce
              and result == "Verified:" + nonce):
            self.verified_name, self.verified_until = self.name.text().strip(), time.monotonic()+90
            self.proof_timeout.start(90000)
            try:
                from storage.store import get_primary_admin
                existing = get_primary_admin(self.db_path)
            except RuntimeError:
                self.verified_name, self.verified_until = "", 0
                self.status.setText("Multiple admin profiles need owner review. Sign-in and new registration are locked.")
                return
            except Exception:
                self.verified_name, self.verified_until = "", 0
                self.status.setText("The encrypted identity store is unavailable. No admin access was granted.")
                return
            if existing:
                if not existing["device_only"]:
                    self.verified_name, self.verified_until = "", 0
                    self.status.setText("This admin profile needs its original verification method. Windows-only sign-in was denied.")
                    return
                if existing["display_name"].casefold() != self.verified_name.casefold():
                    self.verified_name, self.verified_until = "", 0
                    self.status.setText("An admin already exists. Enter that profile's display name to sign in.")
                    return
                self._finish_authentication(existing["person_id"], existing["display_name"])
                return
            self.status.setText("Windows verified. Review the local profile before creating it.")
        else:
            self.status.setText(MESSAGES.get(result, "Windows verification unavailable. You remain a guest."))
        self.update_step()

    def _finish_authentication(self, person_id, name):
        from security.policy import Session
        session = Session(role="admin", person=name,
                          id="session_" + secrets.token_urlsafe(18),
                          person_id=person_id, verified_until=time.time()+300)
        self.authenticated.emit(session)
        self.accept()

    def create_admin(self):
        if (self.active or self.pages.currentIndex() != 3
                or not self.profile_consent.isChecked()
                or self.verified_name != self.name.text().strip()
                or time.monotonic() >= self.verified_until):
            self.status.setText("Verify with Windows again, then confirm local profile creation.")
            return
        try:
            from storage.store import register_device_admin
            person_id = register_device_admin(self.verified_name, self.db_path)
        except (OSError, ValueError, PermissionError) as exc:
            self.status.setText(str(exc))
            return
        except Exception:
            self.status.setText("Encrypted profile creation failed. No admin access was granted.")
            return
        self._finish_authentication(person_id, self.verified_name)

    def failed(self, _error):
        if self.active:
            detail = self.process.errorString().casefold()
            self.proof_nonce = ""
            self.reset_controls()
            self.status.setText(
                "Windows Application Control blocked LYA's verifier. Admin setup remains locked."
                if "policy" in detail or "blocked" in detail else
                "Windows verification could not run. You remain a guest.")

    def expired(self):
        self.proof_nonce = ""
        self.reset_controls()
        self.process.kill()
        self.status.setText(MESSAGES["TimedOut"])

    def showEvent(self, event):
        area = (QApplication.screenAt(self.pos()) or QApplication.primaryScreen()).availableGeometry()
        self.resize(min(700, area.width()-24), min(650, area.height()-24))
        self.move(area.center()-self.rect().center())
        self.closing = False
        super().showEvent(event)
        self.narration_timer.start(0 if self.reduced_motion else 1100)

    def done(self, result):
        self.closing = True
        self.narration_timer.stop()
        self.speech.stop()
        self.finish_intro()
        self.reset_controls()
        self.process.kill()
        self.name.clear()
        self.consent.setChecked(False)
        self.face.setChecked(False)
        self.voice.setChecked(False)
        self.profile_consent.setChecked(False)
        self.proof_timeout.stop()
        self.proof_nonce = ""
        self.verified_name, self.verified_until = "", 0
        self.pages.setCurrentIndex(0)
        self.update_step()
        self.status.clear()
        super().done(result)
