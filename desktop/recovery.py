"""Native recovery UI. Authority comes from a trusted session/gate, never widgets."""
from pathlib import Path
import math
import threading
import time

from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QLineEdit, QCheckBox, QListWidget, QListWidgetItem,
                               QTabWidget, QWidget, QFileDialog, QMessageBox)
from security.policy import Session
from storage import recovery, store


class _Signals(QObject):
    done = Signal(object, str)


class _Job(QRunnable):
    def __init__(self, action, signals):
        super().__init__()
        self.action, self.signals = action, signals

    def run(self):
        try:
            result, error = self.action(), ""
        except PermissionError:
            result, error = None, "Permission denied or operation cancelled. Verify your owner session and try again."
        except ValueError:
            result, error = None, "Check the recovery key, archive and destination. Existing files and notes cannot be overwritten."
        except OSError:
            result, error = None, "File operation failed. Check free space, file access and choose a new destination."
        except Exception:
            result, error = None, "Recovery could not complete. No success is claimed; retry after checking your setup."
        self.signals.done.emit(result, error)
        self.action = None  # Release key-bearing closure; not guaranteed RAM wiping.


class RecoveryDialog(QDialog):
    def __init__(self, *, get_session=lambda: Session(), approve=None, db_path=None, clock=time.time):
        super().__init__()
        self.get_session, self.approve, self.clock = get_session, approve, clock
        self.db_path = Path(db_path) if db_path is not None else store.get_data_dir() / "lya.db.enc"
        self.pool = QThreadPool.globalInstance()
        self.signals = _Signals(self)
        self.signals.done.connect(self.completed)
        self.busy = False
        self.cancelled = threading.Event()
        self.operation = ""
        self.operation_session = None
        self.visible_session = None
        self.preview = None
        self.close_pending = False
        self.setWindowTitle("LYA · Memory recovery")
        self.resize(640, 660)
        self.setStyleSheet('QDialog {background:#12202d;} QWidget {background:#12202d; color:#edf4fa; font:14px "Segoe UI";} '
                           'QLineEdit, QListWidget, QPushButton {background:#24394a; padding:8px; border:1px solid #6d95a3; border-radius:6px;} '
                           'QWidget:disabled {color:#93a5b2;} QTabWidget::pane {border:1px solid #44606f;} '
                           'QTabBar::tab {padding:10px 18px; background:#203748; color:#b9cdd8;} '
                           'QTabBar::tab:selected {background:#315168; color:#ffffff;} '
                           'QCheckBox::indicator, QListWidget::indicator {width:14px; height:14px; border:1px solid #89adba; background:#162934;} '
                           'QCheckBox::indicator:checked, QListWidget::indicator:checked {background:#88d3df;} '
                           'QPushButton:focus, QLineEdit:focus {border:1px solid #a5edf2;}')
        layout = QVBoxLayout(self)
        title = QLabel("A safe way back to your notes")
        title.setStyleSheet("font-size:24px; font-weight:600;")
        layout.addWidget(title)
        self.lock = self.label("", layout)
        self.label("Back up selected notes only. Files, API keys, faces and voice templates are excluded.", layout)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        backup = QWidget()
        bl = QVBoxLayout(backup)
        self.load = self.button("Load my available notes", bl, self.load_notes)
        self.notes = QListWidget()
        self.notes.setMinimumHeight(125)
        bl.addWidget(self.notes)
        self.notes.itemChanged.connect(self.update_controls)
        self.generate = self.button("Create a separate recovery key", bl, self.generate_key)
        self.key = self.field("Recovery key — keep in a separate password manager or offline", bl, readonly=True)
        self.reveal = QCheckBox("Show key so I can store it separately")
        bl.addWidget(self.reveal)
        self.reveal.toggled.connect(lambda show: self.key.setEchoMode(QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password))
        self.confirm_key = self.field("Re-enter the saved key to confirm", bl)
        self.custody = QCheckBox("I stored this key separately from the backup and can retrieve it.")
        bl.addWidget(self.custody)
        self.save = self.button("Save encrypted backup…", bl, self.save_backup)
        self.tabs.addTab(backup, "Create backup")
        restore = QWidget()
        rl = QVBoxLayout(restore)
        self.label("Restore adds notes to an empty verified owner profile. It never creates an admin or replaces existing notes.", rl)
        self.archive = QLineEdit()
        self.archive.setReadOnly(True)
        self.archive.setPlaceholderText("Choose a .lya-notes archive")
        rl.addWidget(self.archive)
        self.choose = self.button("Choose encrypted archive…", rl, self.choose_archive)
        self.restore_key = self.field("Enter the separate recovery key", rl)
        self.inspect = self.button("Check archive", rl, self.inspect_archive)
        self.preview_text = self.label("No archive has been checked.", rl)
        self.restore_consent = QCheckBox("Restore the checked archive into my empty owner profile.")
        rl.addWidget(self.restore_consent)
        self.restore = self.button("Restore notes", rl, self.restore_backup)
        rl.addStretch()
        self.tabs.addTab(restore, "Restore")
        self.status = self.label("Nothing has been read or saved.", layout)
        row = QHBoxLayout()
        self.cancel = self.button("Cancel operation", row, self.cancel_operation)
        self.close_button = self.button("Close", row, self.reject)
        layout.addLayout(row)
        for widget in (self.key, self.confirm_key):
            widget.textChanged.connect(self.update_controls)
        self.custody.toggled.connect(self.update_controls)
        self.restore_consent.toggled.connect(self.update_controls)
        self.restore_key.textChanged.connect(self.invalidate_preview)
        self.archive.textChanged.connect(self.invalidate_preview)
        self.guard = QTimer(self)
        self.guard.setInterval(1000)
        self.guard.timeout.connect(self.update_controls)
        self.update_controls()

    @staticmethod
    def label(text, layout):
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        layout.addWidget(label)
        return label

    @staticmethod
    def button(text, layout, callback):
        button = QPushButton(text)
        button.setAutoDefault(False)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    @staticmethod
    def field(placeholder, layout, readonly=False):
        field = QLineEdit()
        field.setEchoMode(QLineEdit.EchoMode.Password)
        field.setMaxLength(256)
        field.setPlaceholderText(placeholder)
        field.setReadOnly(readonly)
        layout.addWidget(field)
        return field

    def owner_session(self):
        try:
            s = self.get_session()
            if (type(s) is Session and s.role == "admin" and s.person_id and s.id
                    and math.isfinite(s.verified_until) and s.verified_until > self.clock()):
                return s
        except Exception:
            pass
        return None

    def scrub(self):
        self.notes.clear()
        self.key.clear()
        self.confirm_key.clear()
        self.restore_key.clear()
        self.custody.setChecked(False)
        self.reveal.setChecked(False)
        self.archive.clear()
        self.invalidate_preview()

    def invalidate_preview(self):
        self.preview = None
        self.restore_consent.setChecked(False)
        self.preview_text.setText("No archive has been checked.")
        self.update_controls()

    def update_controls(self):
        s = self.owner_session()
        if s != self.visible_session:
            self.visible_session = s  # Set before clearing fields emits nested signals.
            self.cancelled.set()
            self.scrub()
            self.status.setText("Session changed. Private recovery details cleared." if s else
                                "Recovery is locked. No private notes are displayed.")
        ready = s is not None and not self.busy
        self.lock.setText("Verified session present. Each private operation still needs trusted approval." if s else
                          "Locked · Set up and verify the owner first. Enrollment is deferred; this screen does not grant access.")
        self.tabs.setEnabled(ready)
        selected = any(self.notes.item(i).checkState() == Qt.CheckState.Checked for i in range(self.notes.count()))
        self.save.setEnabled(ready and selected and bool(self.key.text())
                             and self.key.text() == self.confirm_key.text() and self.custody.isChecked())
        self.inspect.setEnabled(ready and bool(self.archive.text()) and len(self.restore_key.text()) == 44)
        self.restore.setEnabled(ready and bool(self.preview) and self.preview["empty"]
                                and self.preview["available"] > 0 and self.restore_consent.isChecked())
        self.cancel.setEnabled(self.busy)

    def options(self):
        return dict(get_session=self.get_session, approve=self.approve, db_path=self.db_path,
                    clock=self.clock, cancelled=self.cancelled.is_set)

    def begin(self, operation, action):
        if self.busy or self.owner_session() is None:
            return
        self.cancelled = threading.Event()
        self.operation_session = self.owner_session()
        self.operation = operation
        self.busy = True
        self.status.setText("Working locally… You can cancel while the operation is in progress.")
        self.update_controls()
        # Build kwargs after begin creates this job's cancellation token.
        options = self.options()
        self.pool.start(_Job(lambda: action(options), self.signals))

    def load_notes(self):
        self.begin("list", lambda options: recovery.list_notes(**options))

    def generate_key(self):
        if self.busy or self.owner_session() is None:
            return
        self.confirm_key.clear()
        self.custody.setChecked(False)
        self.key.setText(recovery.new_recovery_key().decode("ascii"))
        self.status.setText("Store this key separately, then re-enter it. LYA will not save it beside your backup.")

    def save_backup(self):
        if not self.save.isEnabled():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save encrypted notes", "", "LYA notes (*.lya-notes)",
                                             options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return
        if not Path(path).suffix:
            path += ".lya-notes"
        ids = [self.notes.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.notes.count())
               if self.notes.item(i).checkState() == Qt.CheckState.Checked]
        if QMessageBox.question(self, "Confirm encrypted backup",
                                f"Save {len(ids)} selected notes to:\n{path}\n\nThe recovery key will not be included.") != QMessageBox.StandardButton.Yes:
            return
        key = self.key.text().encode("ascii")
        self.begin("export", lambda options: recovery.export_file(ids, key, path, **options))

    def choose_archive(self):
        if self.busy or self.owner_session() is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open encrypted notes", "", "LYA notes (*.lya-notes)")
        if path:
            self.archive.setText(path)

    def inspect_archive(self):
        if not self.inspect.isEnabled():
            return
        path, key = self.archive.text(), self.restore_key.text().encode("utf-8")
        self.begin("preview", lambda options: recovery.preview_file(path, key, **options))

    def restore_backup(self):
        if not self.restore.isEnabled():
            return
        path, key, digest = self.archive.text(), self.restore_key.text().encode("utf-8"), self.preview["digest"]
        if QMessageBox.question(self, "Confirm restore", "Restore the checked notes into your empty owner profile?\nExisting notes will never be replaced.") != QMessageBox.StandardButton.Yes:
            return
        self.begin("restore", lambda options: recovery.restore_file(path, key, digest, **options))

    def cancel_operation(self):
        self.cancelled.set()
        self.status.setText("Cancellation requested. A save already committed cannot be undone by cancellation.")

    def completed(self, result, error):
        self.busy = False
        if self.owner_session() != self.operation_session or self.close_pending:
            self.scrub()
            self.status.setText("Session ended or window closed. Any already completed save remains on disk.")
        elif error:
            self.status.setText(error)
            if self.operation == "preview":
                self.invalidate_preview()
        elif self.cancelled.is_set() and self.operation in ("list", "preview"):
            self.scrub()
            self.status.setText("Cancelled. No private preview is displayed.")
        elif self.operation == "list":
            self.notes.clear()
            for row in result:
                if row["expires_at"] is not None and row["expires_at"] <= self.clock():
                    continue
                item = QListWidgetItem(f"{row['label'][:160]}  ·  {row['retention']}")
                item.setData(Qt.ItemDataRole.UserRole, row["id"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.notes.addItem(item)
            self.status.setText(f"{self.notes.count()} available notes. Select only the notes you want to back up.")
        elif self.operation == "preview":
            self.preview = result
            self.preview_text.setText(f"Authenticated archive: {result['available']} unexpired notes; {result['expired']} expired notes will be skipped.\n" +
                                      ("Destination profile is empty." if result["empty"] else "Restore blocked: this owner profile already has notes."))
            self.status.setText("Archive checked. Review the summary before restoring.")
        else:
            self.scrub()
            self.status.setText(f"Encrypted backup saved: {result['saved']} notes. Keep the separate recovery key safe." if self.operation == "export" else
                                f"Restored {result['restored']} notes; skipped {result['expired_skipped']} expired notes.")
        self.update_controls()
        if self.close_pending:
            super().done(QDialog.DialogCode.Rejected)

    def showEvent(self, event):
        self.close_pending = False
        self.guard.start()
        self.update_controls()
        super().showEvent(event)

    def done(self, result):
        self.guard.stop()
        self.scrub()
        if self.busy:
            self.close_pending = True
            self.cancel_operation()
            return
        super().done(result)
