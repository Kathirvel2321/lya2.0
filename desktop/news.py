"""Qt delivery for public news; separate worker, no voice or chat mutation."""
import os
import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal, Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton, QCheckBox, QSystemTrayIcon

from cloud.tech_news import NewsStore, NewsMonitor, data_path, render_brief, INTERVAL


def quiet(owner):
    """Main-thread UI state only. Never inspect sensors, windows of other apps or private data."""
    if owner.brain_busy or owner.brain.private_mode or getattr(owner, 'quitting', False):
        return False
    if getattr(owner, 'first_run_setup', False): return False
    if getattr(owner, 'listener_phase', 'off') in ('listening', 'hearing', 'transcribing', 'thinking', 'speaking'):
        return False
    speech = getattr(owner, 'speech', None)
    if speech is not None and speech.busy: return False
    for name in ('owner_dialog', 'activation_dialog', 'registration_dialog', 'recovery_dialog',
                 'visitor_review', 'passkey_approval', 'vision_dialog', 'greeting'):
        widget = getattr(owner, name, None)
        if widget is not None and widget.isVisible(): return False
    return True


class NewsDialog(QDialog):
    def __init__(self, controller):
        super().__init__()
        self.setWindowTitle('LYA · Technology updates')
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.resize(650, 570)
        layout = QVBoxLayout(self)
        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(False)
        self.body.setOpenLinks(False)
        layout.addWidget(self.body)
        self.enabled = QCheckBox('Check official sources hourly while LYA is running')
        self.enabled.toggled.connect(controller.set_enabled)
        layout.addWidget(self.enabled)
        buttons = QHBoxLayout()
        refresh = QPushButton('Check updates (hourly limit)')
        refresh.clicked.connect(lambda: controller.tick(requested=True))
        buttons.addWidget(refresh)
        close = QPushButton('Close'); close.clicked.connect(self.close)
        buttons.addWidget(close); layout.addLayout(buttons)

    def display(self, snapshot, disabled=False, error=''):
        self.enabled.blockSignals(True)
        self.enabled.setChecked(snapshot['enabled'] and not disabled)
        self.enabled.setEnabled(not disabled)
        self.enabled.blockSignals(False)
        text = render_brief(snapshot)
        if disabled: text += '\n\nBackground checks are disabled by LYA_TECH_NEWS_ENABLED=0.'
        if error: text += '\n\n' + error
        self.body.setPlainText(text)  # Remote titles never become HTML or executable links.


class NewsController(QObject):
    ready = Signal(int, object, str)

    def __init__(self, owner, *, store=None, monitor=None, clock=time.time,
                 monotonic=time.monotonic, can_present=None, tray_available=None, autostart=True):
        super().__init__(owner)
        self.owner, self.clock, self.monotonic = owner, clock, monotonic
        self.store = store or NewsStore(data_path())
        self.monitor = monitor or NewsMonitor(self.store)
        self.can_present = can_present or (lambda: quiet(owner))
        self.tray_available = tray_available or (lambda: owner.tray.isVisible() and QSystemTrayIcon.supportsMessages())
        self.disabled = os.environ.get('LYA_TECH_NEWS_ENABLED') == '0'
        self.snapshot = {'items': [], 'unread': 0, 'coverage': [], 'last_attempt': None,
                         'last_completed': None, 'enabled': not self.disabled}
        self.error = ''; self.dialog = None; self.worker = None
        self.cancelled = threading.Event()
        self.closed = self.sleeping = False
        self.generation = 0
        self.want_brief = True; self.auto_shown = False
        self.last_launch = None; self.last_balloon = None
        self.ready.connect(self.on_ready)
        self.timer = QTimer(self); self.timer.setInterval(60000)
        self.timer.timeout.connect(self.tick)
        if autostart:
            self.timer.start()
            QTimer.singleShot(12000, self.tick)
        owner.app.aboutToQuit.connect(self.shutdown)

    def tick(self, requested=False):
        if self.closed or self.sleeping: return
        allowed = self.can_present()
        if not allowed:
            self.interrupt(); return
        self.present()
        if self.disabled or not self.snapshot['enabled']: return
        if self.worker is not None and self.worker.is_alive(): return
        # UI opens/ticks never force a second network check inside the hour.
        if self.last_launch is not None and self.monotonic() - self.last_launch < INTERVAL: return
        self.last_launch = self.monotonic()
        self.cancelled = threading.Event()
        cancelled = self.cancelled
        generation = self.generation
        def run():
            error = ''
            try:
                self.monitor.check(cancelled)
                if cancelled.is_set(): return
                snapshot = self.store.snapshot(self.clock())
            except InterruptedError: return
            except Exception:
                # Public-source/storage failures never take down the accepted assistant.
                snapshot = None
                error = 'Technology updates could not be checked. Cached information may be incomplete.'
            if not cancelled.is_set():
                try: self.ready.emit(generation, snapshot, error)
                except RuntimeError: pass  # Qt can already have shut down; worker is a daemon.
        self.worker = threading.Thread(target=run, daemon=True, name='LYA-OfficialNews')
        self.worker.start()

    def on_ready(self, generation, snapshot, error):
        if generation != self.generation or self.closed or self.sleeping or self.cancelled.is_set(): return
        if snapshot is not None: self.snapshot = snapshot
        self.error = error
        if self.dialog is not None and self.dialog.isVisible():
            self.dialog.display(self.snapshot, self.disabled, self.error)
        self.present()

    def present(self):
        if self.closed or self.sleeping or not self.can_present(): return
        if self.disabled or not self.snapshot['enabled']: return
        if self.want_brief and not self.auto_shown and self.snapshot['unread']:
            self.show_brief(automatic=True)
            return
        candidates = [item for item in self.snapshot['items'] if item['unread'] and not item['notification_requested']]
        if not candidates or self.disabled or not self.snapshot['enabled'] or not self.tray_available(): return
        if self.last_balloon is not None and self.monotonic() - self.last_balloon < INTERVAL: return
        try:
            self.owner.tray.showMessage('LYA · New technology updates',
                f"{len(candidates)} recent announcement(s). {candidates[0]['title'][:150]}\n"
                "Open Technology updates in LYA's tray menu for dates, sources and limits.",
                QSystemTrayIcon.MessageIcon.Information, 10000)
            self.last_balloon = self.monotonic()
            self.store.mark([item['id'] for item in candidates], self.clock(), notified=True)
            for item in candidates: item['notification_requested'] = True
        except Exception:
            self.last_balloon = self.monotonic()
            self.error = 'A news notification could not be requested; the in-app catch-up remains available.'

    def show_brief(self, automatic=False):
        if self.closed: return
        if automatic and (self.auto_shown or not self.can_present()): return
        if not automatic:
            try: self.snapshot = self.store.snapshot(self.clock())
            except Exception: self.error = 'The public news cache could not be read.'
        if self.dialog is None: self.dialog = NewsDialog(self)
        self.dialog.display(self.snapshot, self.disabled, self.error)
        self.dialog.show()
        if not automatic:
            self.dialog.raise_(); self.dialog.activateWindow()
        self.auto_shown = True; self.want_brief = False
        ids = [item['id'] for item in self.snapshot['items'] if item['unread']]
        try:
            self.store.mark(ids, self.clock())
            for item in self.snapshot['items']: item['unread'] = False
            self.snapshot['unread'] = max(0, self.snapshot['unread'] - len(ids))
        except Exception:
            self.error = 'The catch-up could not be marked seen; it may appear again.'
        if not automatic: self.tick(requested=True)

    def opened(self):
        if self.closed: return
        self.sleeping = False
        self.want_brief = not self.auto_shown
        QTimer.singleShot(0, self.tick)

    def suspend(self):
        self.sleeping = True; self.generation += 1; self.cancelled.set()
        if self.dialog is not None: self.dialog.hide()

    def interrupt(self):
        """Called before a user command; public news must yield to that conversation."""
        self.generation += 1; self.cancelled.set()

    def set_enabled(self, enabled):
        if self.disabled: return
        self.generation += 1; self.cancelled.set()
        try:
            self.store.set_enabled(bool(enabled))
            self.snapshot['enabled'] = bool(enabled)
        except Exception:
            self.error = 'The background news preference could not be saved.'
        if enabled:
            self.last_launch = None
            QTimer.singleShot(0, self.tick)

    def shutdown(self):
        if self.closed: return
        self.closed = True; self.generation += 1; self.cancelled.set(); self.timer.stop()
        if self.dialog is not None: self.dialog.close()
