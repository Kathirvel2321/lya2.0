"""Manual routine draft review. No timers, model calls or execution controls."""
from PySide6.QtCore import QTime
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QTextBrowser, QTimeEdit, QVBoxLayout)

from cloud.routine_drafts import DraftStore, PROVIDERS, Settings, proposal
from cloud.tech_news import data_path


class RoutineDialog(QDialog):
    def __init__(self, *, store=None):
        super().__init__()
        self.store = store or DraftStore(data_path().with_name('routine-drafts.sqlite'))
        self.storage_error = False
        self.setWindowTitle('LYA · Routine drafts')
        self.resize(760, 760)
        layout = QVBoxLayout(self)
        label = QLabel('Plan a routine. Drafts are never enabled by this screen.')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.saved = QComboBox()
        self.saved.addItem('New draft', None)
        self.saved.activated.connect(self.load_selected)
        layout.addWidget(self.saved)
        form = QFormLayout()
        self.provider = QComboBox()
        for key, title in PROVIDERS.items(): self.provider.addItem(title, key)
        self.start = QTimeEdit(QTime(13, 0)); self.start.setDisplayFormat('HH:mm')
        self.notify = QTimeEdit(QTime(13, 5)); self.notify.setDisplayFormat('HH:mm')
        self.zone = QComboBox(); self.zone.addItems(['Asia/Kolkata', 'Etc/UTC'])
        self.placement = QComboBox()
        self.placement.addItem('Server — setup required', 'oracle')
        self.placement.addItem('This laptop — must be awake', 'desktop')
        self.window = QSpinBox(); self.window.setRange(1, 168); self.window.setValue(168)
        self.catchup = QSpinBox(); self.catchup.setRange(0, 120); self.catchup.setValue(30)
        self.retention = QSpinBox(); self.retention.setRange(1, 24); self.retention.setValue(24)
        self.filter = QComboBox()
        for title, key in [('Important or uncertain', 'important_or_uncertain'),
                           ('Important only', 'important_only'), ('Every report', 'always')]:
            self.filter.addItem(title, key)
        for title, widget in [('Task', self.provider), ('Daily collection', self.start),
                ('Daily notification', self.notify), ('Timezone', self.zone),
                ('Where', self.placement), ('Input window (hours)', self.window),
                ('Missed-run grace (minutes)', self.catchup), ('Report expiry (hours)', self.retention),
                ('Notify for', self.filter)]:
            form.addRow(title, widget)
        layout.addLayout(form)
        self.review = QTextBrowser()
        self.review.setOpenLinks(False); self.review.setOpenExternalLinks(False)
        layout.addWidget(self.review)
        self.status = QLabel(''); self.status.setWordWrap(True); layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.save_button = QPushButton('Save draft only'); self.save_button.clicked.connect(self.save)
        self.remove_button = QPushButton('Remove selected draft'); self.remove_button.clicked.connect(self.remove)
        close = QPushButton('Close'); close.clicked.connect(self.close)
        for button in (self.save_button, self.remove_button, close): buttons.addWidget(button)
        layout.addLayout(buttons)
        self.provider.currentIndexChanged.connect(self.task_changed)
        for widget in (self.placement, self.zone, self.filter):
            widget.currentIndexChanged.connect(self.refresh_review)
        for widget in (self.start, self.notify): widget.timeChanged.connect(self.refresh_review)
        for widget in (self.window, self.catchup, self.retention): widget.valueChanged.connect(self.refresh_review)
        self.reload_saved()
        self.refresh_review()

    def settings(self):
        return Settings(provider=self.provider.currentData(), start=self.start.time().toString('HH:mm'),
            notify=self.notify.time().toString('HH:mm'), zone=self.zone.currentText(),
            placement=self.placement.currentData(), lookback_hours=self.window.value(),
            catchup_minutes=self.catchup.value(), retention_hours=self.retention.value(),
            notification_filter=self.filter.currentData())

    def task_changed(self):
        private = self.provider.currentData() != 'official_news'
        self.start.setTime(QTime(18, 0) if private else QTime(13, 0))
        self.notify.setTime(QTime(19, 0) if private else QTime(13, 5))
        self.window.setValue(24 if private else 168)
        self.refresh_review()

    def refresh_review(self):
        try:
            self.review.setPlainText(proposal(self.settings())['text'])
            self.save_button.setEnabled(True)
            entry = self.saved.currentData()
            if self.storage_error:
                self.status.setText('Saved drafts could not be read. You can review these choices; nothing is enabled.')
            elif entry and entry[1] == self.settings():
                self.status.setText('Saved draft. It is NOT enabled or scheduled.')
            else:
                self.status.setText('Unsaved choices. Saving creates a draft, not a scheduled routine.')
        except Exception:
            self.review.setPlainText('These choices cannot be compiled. Check the timezone and bounded schedule.')
            self.status.setText('Draft could not be compiled. Nothing was enabled.')
            self.save_button.setEnabled(False)

    def reload_saved(self, select=None):
        self.storage_error = False
        self.saved.clear(); self.saved.addItem('New draft', None)
        try:
            for key, settings in self.store.list():
                title = f'{PROVIDERS[settings.provider]} · {settings.start}/{settings.notify} · {settings.zone} · {key[:8]}'
                self.saved.addItem(title, (key, settings))
                if key == select: self.saved.setCurrentIndex(self.saved.count() - 1)
            self.remove_button.setEnabled(self.saved.currentData() is not None)
        except Exception:
            self.saved.clear(); self.saved.addItem('New draft', None)
            self.storage_error = True
            self.remove_button.setEnabled(False)
            self.status.setText('Saved drafts could not be read. No account access or scheduling was attempted.')

    def load_selected(self):
        entry = self.saved.currentData()
        settings = entry[1] if entry else Settings()
        self.provider.setCurrentIndex(self.provider.findData(settings.provider))
        self.start.setTime(QTime.fromString(settings.start, 'HH:mm'))
        self.notify.setTime(QTime.fromString(settings.notify, 'HH:mm'))
        if self.zone.findText(settings.zone) < 0: self.zone.addItem(settings.zone)
        self.zone.setCurrentText(settings.zone)
        self.placement.setCurrentIndex(self.placement.findData(settings.placement))
        self.window.setValue(settings.lookback_hours); self.catchup.setValue(settings.catchup_minutes)
        self.retention.setValue(settings.retention_hours)
        self.filter.setCurrentIndex(self.filter.findData(settings.notification_filter))
        self.remove_button.setEnabled(entry is not None)
        self.refresh_review()

    def save(self):
        try:
            key = self.store.save(self.settings())
            self.reload_saved(select=key)
            self.status.setText('Draft saved but its list could not be reopened. Nothing is enabled.' if self.storage_error else
                'Draft saved. It is NOT enabled or scheduled. Missing connections are listed above.')
        except Exception:
            self.status.setText('Draft could not be saved; storage may be unavailable or full. Nothing was enabled.')

    def remove(self):
        entry = self.saved.currentData()
        if not entry: return
        try:
            self.store.delete(entry[0]); self.reload_saved()
            self.status.setText('Saved draft removed. No provider messages or scheduled jobs were changed.')
        except Exception:
            self.status.setText('Draft could not be removed. No provider messages or scheduled jobs were changed.')
