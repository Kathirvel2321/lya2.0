"""Owner-operated setup for desktop provider credentials."""
import threading

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton)

from cloud.desktop_connections import CHAT, CHAT_CHOICE, HEARING, LABELS, check_key
from security import provider_credentials


class KeyCheck(QThread):
    def __init__(self, name, key, nvidia_model, parent):
        super().__init__(parent)
        self.name, self.key, self.nvidia_model = name, key, nvidia_model
        self.error = ""
        self.cancelled = threading.Event()

    def run(self):
        try:
            check_key(self.name, self.key, self.nvidia_model, self.cancelled)
        except ConnectionError as error:
            self.error = str(error)
        except Exception:
            self.error = "The provider check could not finish."
        else:
            if not self.cancelled.is_set():
                try:
                    provider_credentials.write(self.name, self.key)
                except Exception:
                    self.error = "Windows Credential Manager could not save this key."
        finally:
            self.key = ""


class ConnectionsDialog(QDialog):
    def __init__(self, *, nvidia_model=None):
        super().__init__()
        self.worker = None
        self.closing = False
        self.nvidia_model = nvidia_model
        self.setWindowTitle("LYA Connections")
        self.setMinimumWidth(460)
        form = QFormLayout(self)
        self.provider = QComboBox()
        for name, label in LABELS.items():
            self.provider.addItem(label, name)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setMaxLength(2048)
        self.saved = QLabel()
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.check = QPushButton("Check and save key")
        self.forget = QPushButton("Remove saved key")
        self.route = QComboBox()
        self.route.addItem("Current default (Oracle or local)", "")
        for name, config in CHAT.items():
            self.route.addItem(config[0], name)
        selection = self.route.findData(provider_credentials.read(CHAT_CHOICE))
        self.route.setCurrentIndex(max(0, selection))
        self.apply_route = QPushButton("Save public chat choice")
        self.done_button = QPushButton("Done")
        for label, widget in (("Provider", self.provider), ("Saved key", self.saved),
                              ("API key", self.key)):
            form.addRow(label, widget)
        form.addRow(self.check, self.forget)
        form.addRow(self.message)
        form.addRow("Public chat after restart", self.route)
        form.addRow(self.apply_route)
        form.addRow(self.done_button)
        self.provider.currentIndexChanged.connect(self._show_provider)
        self.check.clicked.connect(self._check_key)
        self.forget.clicked.connect(self._forget_key)
        self.apply_route.clicked.connect(self._save_route)
        self.done_button.clicked.connect(self.reject)
        self._show_provider()

    def _show_provider(self):
        self.key.clear()
        name = self.provider.currentData()
        saved = bool(provider_credentials.read(name))
        self.saved.setText("Saved in Windows" if saved else "Setup required")
        self.forget.setEnabled(saved)
        if name == HEARING:
            self.message.setText("The check sends one second of generated silence to NVIDIA.")
        else:
            self.message.setText("The check asks the provider which models this key can access.")

    def _check_key(self):
        key = self.key.text().strip()
        self.key.clear()
        if not key:
            self.message.setText("Paste the provider API key first.")
            return
        self.worker = KeyCheck(self.provider.currentData(), key, self.nvidia_model, self)
        self.worker.finished.connect(self._check_finished)
        for widget in (self.provider, self.key, self.check, self.forget, self.apply_route):
            widget.setEnabled(False)
        self.message.setText("Checking the key…")
        self.worker.start()

    def _check_finished(self):
        worker, self.worker = self.worker, None
        if self.closing:
            worker.deleteLater()
            super().reject()
            return
        outcome = worker.error or "The provider accepted the key. Saved in Windows."
        worker.deleteLater()
        for widget in (self.provider, self.key, self.check, self.apply_route, self.done_button):
            widget.setEnabled(True)
        self._show_provider()
        self.message.setText(outcome)

    def _forget_key(self):
        name = self.provider.currentData()
        if QMessageBox.question(self, "Remove saved key", f"Remove the saved key for {LABELS[name]}?") != QMessageBox.StandardButton.Yes:
            return
        try:
            provider_credentials.remove(name)
        except Exception:
            self.message.setText("Windows Credential Manager could not remove the key.")
            return
        self._show_provider()
        self.message.setText("Saved key removed.")

    def _save_route(self):
        name = self.route.currentData()
        if name:
            if not provider_credentials.read(name):
                self.message.setText(f"Check and save a key for {LABELS[name]} first.")
                return
            if QMessageBox.question(self, "Use this provider for public chat",
                                    f"Send future public requests to {LABELS[name]}? Your API account may be charged."
                                    ) != QMessageBox.StandardButton.Yes:
                return
        try:
            if name:
                provider_credentials.write(CHAT_CHOICE, name)
            else:
                provider_credentials.remove(CHAT_CHOICE)
        except Exception:
            self.message.setText("Windows Credential Manager could not save your choice.")
            return
        self.message.setText("Public chat choice saved. Restart LYA to use it.")

    def reject(self):
        if self.worker is not None:
            self.closing = True
            self.worker.cancelled.set()
            self.done_button.setEnabled(False)
            self.message.setText("Closing after the current check stops…")
            return
        super().reject()
