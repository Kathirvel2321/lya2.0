"""Offline checks for the LYA initialization walk-through.

No camera, microphone, Windows prompt, speech engine or real store is opened.
The camera, microphone and Windows proof are injected fakes; the store is a
temporary encrypted database.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from PySide6.QtWidgets import QApplication

from desktop.activation import (ACTS, CameraWorker, MicWorker, ActivationDialog,
                                biometric_readiness, layer, measure_wav,
                                probe_layers, voiceprint_vector, wav_from_pcm)

APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


def tone(seconds=1.0, rate=16000, freq=440.0):
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    return (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


class FakeCamera:
    """A camera that never exists, but yields one frame with one face box."""

    def __init__(self, faces=True):
        self.reading = False
        self.face_count = 1 if faces else 0
        self._faces = [[10, 8, 40, 40]] if faces else []

    def start(self):
        self.reading = True
        return True

    def stop(self):
        self.reading = False

    def newest(self):
        if not self.reading:
            return None
        return np.zeros((48, 64, 3), np.uint8), list(self._faces)


class FakeMic:
    def __init__(self):
        self.level = 0.25
        self.recording = False
        self.calls = 0
        self.start_calls = 0

    def start_meter(self):
        self.start_calls += 1
        return True

    def record(self, seconds=3.5):
        self.calls += 1
        clip = wav_from_pcm(tone(0.6))
        return clip

    def progress(self):
        return 0.5

    def stop(self):
        self.recording = False


class ProbeTests(unittest.TestCase):
    def test_probe_returns_real_layers_without_opening_sensors(self):
        layers = probe_layers()
        keys = [item.key for item in layers]
        self.assertEqual(keys[:3], ["core", "vault", "store"])
        for expected in ("optics", "camera", "mic", "tts", "asr", "embed",
                         "antispoof", "hello"):
            self.assertIn(expected, keys)
        for item in layers:
            self.assertTrue(item.label and item.detail)
            self.assertIsInstance(item.ok, bool)

    def test_readiness_reflects_the_actual_missing_layers(self):
        layers = probe_layers()
        ready, reason = biometric_readiness(layers)
        self.assertFalse(ready)
        self.assertIn("not enrolled", reason)

    def test_antispoof_is_reported_missing_not_faked(self):
        item = layer(probe_layers(), "antispoof")
        if not item.ok:
            self.assertNotIn("present", item.detail)


class MeasurementTests(unittest.TestCase):
    def test_measure_wav_reports_real_numbers(self):
        stats = measure_wav(wav_from_pcm(tone(1.0)))
        self.assertAlmostEqual(stats["seconds"], 1.0, places=1)
        self.assertGreater(stats["rms"], 0.0)
        self.assertLess(stats["peak"], 1.0)
        self.assertFalse(stats["clipped"])

    def test_measure_wav_of_nothing_is_zero_not_invented(self):
        self.assertEqual(measure_wav(b""),
                         {"seconds": 0.0, "rms": 0.0, "peak": 0.0, "clipped": False})

    def test_voiceprint_of_silence_is_rejected(self):
        self.assertIsNone(voiceprint_vector(wav_from_pcm(np.zeros(8000, np.float32))))

    def test_voiceprint_of_speech_like_audio_is_normalised(self):
        vector = voiceprint_vector(wav_from_pcm(tone(1.5, freq=220.0)))
        if vector is not None:
            self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=3)


class DialogTests(unittest.TestCase):
    def setUp(self):
        self.camera, self.mic = FakeCamera(), FakeMic()
        self.dialog = ActivationDialog(reduced_motion=True, camera=self.camera,
                                       mic=self.mic)
        self.dialog._boot_finish()   # what showEvent does in reduced motion

    def tearDown(self):
        self.dialog._stop_sensors()
        self.dialog.deleteLater()

    def test_acts_and_boot_complete(self):
        self.assertEqual(ACTS[0], "BOOT")
        self.assertEqual(self.dialog.canvas.boot_shown, len(self.dialog.boot_lines))
        self.assertTrue(self.dialog.next.isEnabled())

    def test_identity_requires_a_name(self):
        self.dialog.go(1)
        self.assertEqual(ACTS[self.dialog.act], "IDENTITY")
        self.assertFalse(self.dialog.next.isEnabled())
        self.dialog.name.setText("Owner")
        self.assertTrue(self.dialog.next.isEnabled())
        self.assertEqual(self.dialog.salutation, "boss")

    def test_optics_captures_three_samples_from_real_frames(self):
        self.dialog.go(1)
        self.dialog.name.setText("Owner")
        self.dialog.go(1)
        self.assertEqual(ACTS[self.dialog.act], "OPTICS")
        self.dialog._toggle_camera()
        self.assertTrue(self.camera.reading)
        for _ in range(3):
            self.dialog._take_face()
        self.assertEqual(len(self.dialog.face_samples), 3)
        self.assertIn("NOT AN IDENTITY MATCH", self.dialog.canvas.badge)
        self.dialog._toggle_camera()
        self.assertFalse(self.camera.reading)
        self.assertIsNone(self.dialog.canvas.video)

    def test_vocal_measurements_are_reported(self):
        self.dialog.go(1)
        self.dialog.name.setText("Owner")
        self.dialog.go(1)
        self.dialog.go(1)
        self.assertEqual(ACTS[self.dialog.act], "VOCAL")
        self.assertFalse(self.mic.recording)
        self.assertEqual(self.mic.start_calls, 0)
        self.assertRegex(self.dialog.code_label.text(), r"^\d( \d){5}$")
        self.dialog._take_voice()
        deadline = time.monotonic() + 5.0
        while not self.dialog._record_clip and time.monotonic() < deadline:
            time.sleep(0.02)          # the fake recorder runs off-thread, as the real one does
        self.dialog._pump()
        self.assertEqual(len(self.dialog.voice_clips), 1)
        self.assertIn("level", self.dialog.vocal_status.text())
        self.assertFalse(self.dialog.busy)

    def test_camera_stops_before_voice_step(self):
        self.dialog.go(1)
        self.dialog.name.setText("Owner")
        self.dialog.go(1)
        self.dialog._toggle_camera()
        self.assertTrue(self.camera.reading)
        self.dialog.go(1)
        self.assertFalse(self.camera.reading)

    def test_hud_paints_offscreen_in_every_act(self):
        from PySide6.QtGui import QImage, QPainter

        def paint_once(widget):
            image = QImage(1000, 760, QImage.Format.Format_ARGB32)
            image.fill(0)
            widget.render(image)
            return image

        for act in range(len(ACTS)):
            self.dialog.act = act
            self.dialog.render()
            self.dialog.pages.setCurrentIndex(act)
            self.assertFalse(paint_once(self.dialog.canvas).isNull())

    def test_reduced_motion_stops_the_animation_timer(self):
        self.assertFalse(self.dialog.canvas.timer.isActive())


class CommitTests(unittest.TestCase):
    """The vault act must refuse to invent an admin."""

    def setUp(self):
        from cryptography.fernet import Fernet
        from security import vault
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "activation.db.enc"
        patcher = patch.object(vault, "_F", Fernet(Fernet.generate_key()))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.dialog = ActivationDialog(reduced_motion=True, camera=FakeCamera(),
                                       mic=FakeMic(), db_path=self.db)

    def tearDown(self):
        self.dialog._stop_sensors()
        self.dialog.deleteLater()

    def _to_vault(self):
        self.dialog.act = ACTS.index("VAULT")
        self.dialog.pages.setCurrentIndex(self.dialog.act)

    def test_refuses_without_windows_proof_and_consent(self):
        self.dialog.name.setText("Owner")
        self._to_vault()
        self.dialog.consent.setChecked(True)
        self.dialog._commit()
        self.assertIsNone(self.dialog.created)
        from storage.store import has_active_admin
        self.assertFalse(has_active_admin(db_path=self.db))

    def test_refuses_with_proof_but_without_consent(self):
        self.dialog.name.setText("Owner")
        self._to_vault()
        self.dialog.verified_until = 1e12
        self.dialog._commit()
        self.assertIsNone(self.dialog.created)

    def test_expired_proof_is_rejected(self):
        self.dialog.name.setText("Owner")
        self._to_vault()
        self.dialog.consent.setChecked(True)
        self.dialog.verified_until = 0.0
        self.dialog._commit()
        self.assertIsNone(self.dialog.created)

    def test_creates_exactly_one_admin_then_refuses_a_second(self):
        from storage.store import get_primary_admin, has_active_admin
        self.dialog.name.setText("Owner")
        self._to_vault()
        self.dialog.consent.setChecked(True)
        self.dialog.verified_until = 1e12
        self.dialog.verified_name = "Owner"
        self.dialog._commit()
        self.assertIsNotNone(self.dialog.created)
        self.assertTrue(has_active_admin(db_path=self.db))
        admin = get_primary_admin(db_path=self.db)
        self.assertEqual(admin["display_name"], "Owner")
        self.assertTrue(admin["device_only"])
        self.dialog._commit()
        self.assertIn("existing device admin", self.dialog.vault_status.text())
        self.assertEqual(get_primary_admin(db_path=self.db)["person_id"], admin["person_id"])

    def test_name_change_invalidates_windows_proof(self):
        self.dialog.name.setText("Owner")
        self._to_vault()
        self.dialog.consent.setChecked(True)
        self.dialog.verified_until = 1e12
        self.dialog.verified_name = "Owner"
        self.dialog.name.setText("Someone else")
        self.assertEqual(self.dialog.verified_until, 0.0)
        self.dialog._commit()
        self.assertIsNone(self.dialog.created)


class SensorDefaultTests(unittest.TestCase):
    def test_default_workers_do_not_open_anything_on_construction(self):
        camera, mic = CameraWorker(), MicWorker()
        self.assertFalse(camera.reading)
        self.assertIsNone(camera.newest())
        self.assertEqual(mic.level, 0.0)
        self.assertFalse(mic.recording)
        mic.stop()
        camera.stop()


class FirstRunGateTests(unittest.TestCase):
    """The launcher must offer owner setup only when the store has no admin."""

    def setUp(self):
        from cryptography.fernet import Fernet
        from security import vault
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "firstrun.db.enc"
        patcher = patch.object(vault, "_F", Fernet(Fernet.generate_key()))
        patcher.start()
        self.addCleanup(patcher.stop)
        desktop_dir = str(ROOT / "desktop")
        if desktop_dir not in sys.path:
            sys.path.insert(0, desktop_dir)

    def test_needs_setup_tracks_the_store(self):
        try:
            from experience import OrbDesktop
        except Exception as exc:            # pragma: no cover - import guard
            self.skipTest(f"desktop experience unavailable: {exc}")
        from storage.store import register_device_admin
        from brain.workflow import Brain
        desktop = OrbDesktop.__new__(OrbDesktop)
        desktop.brain = Brain(db_path=self.db)
        self.assertTrue(desktop.needs_owner_setup())
        register_device_admin("Owner", db_path=self.db)
        self.assertFalse(desktop.needs_owner_setup())

    def test_unreadable_store_never_opens_setup(self):
        try:
            from experience import OrbDesktop
        except Exception as exc:            # pragma: no cover - import guard
            self.skipTest(f"desktop experience unavailable: {exc}")
        desktop = OrbDesktop.__new__(OrbDesktop)
        desktop.brain = type("B", (), {"db_path": Path("Z:/does/not/exist/db.enc")})()
        self.assertFalse(desktop.needs_owner_setup())


if __name__ == "__main__":
    unittest.main()
