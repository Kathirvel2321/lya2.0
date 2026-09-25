"""Offline tests for secure first-admin registration. No sensors or real data."""

from pathlib import Path
from dataclasses import replace
import tempfile
import unittest

from security.registration import AdminRegistrar, RegistrationConsent, RegistrationDenied
from security import vault
from storage import list_face_templates, list_people, list_voice_templates
from storage.store import create_person, get_primary_admin


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "registration.db.enc"
        self.original_key_path = vault.KEY_PATH
        vault.KEY_PATH = str(Path(self.temp.name) / "test-dpapi.key")
        vault._F = None
        self.face_calls = []
        self.voice_calls = []

    def tearDown(self):
        vault._F = None
        vault.KEY_PATH = self.original_key_path
        self.temp.cleanup()

    def consent(self):
        return RegistrationConsent("Kathir", True, True, True)

    def registrar(self, proof=lambda challenge: challenge, live=True):
        faces = [[1.0, 0.01, 0.0], [1.0, 0.02, 0.0], [1.0, 0.03, 0.0]]
        voices = [[0.0, 1.0, 0.01], [0.0, 1.0, 0.02], [0.0, 1.0, 0.03]]

        def capture_face(prompt):
            self.face_calls.append(prompt)
            return f"face-{len(self.face_calls)}".encode()

        def capture_voice(prompt):
            self.voice_calls.append(prompt)
            return f"voice-{len(self.voice_calls)}".encode()

        return AdminRegistrar(
            trusted_device_verifier=proof,
            capture_face=capture_face,
            capture_voice=capture_voice,
            verify_face_liveness=lambda sample, prompt: live,
            verify_voice_challenge=lambda sample, prompt: live,
            encode_face=lambda sample: faces[int(sample[-1:]) - 1],
            encode_voice=lambda sample: voices[int(sample[-1:]) - 1],
            db_path=self.db_path,
            clock=lambda: 100.0,
        )

    def test_registers_first_admin_and_returns_greeting(self):
        result = self.registrar().register(self.consent())
        self.assertEqual(result.session.role, "admin")
        self.assertEqual(result.session.person_id, result.person_id)
        self.assertIn("Welcome, Kathir", result.greeting)
        self.assertGreaterEqual(len(result.recovery_code), 32)
        self.assertEqual(len(list_people(db_path=self.db_path)), 1)
        self.assertEqual(len(list_face_templates(result.person_id, self.db_path)), 3)
        self.assertEqual(len(list_voice_templates(result.person_id, self.db_path)), 3)
        disk = self.db_path.read_bytes()
        self.assertNotIn(b"Kathir", disk)
        self.assertNotIn(result.recovery_code.encode(), disk)

    def test_denies_without_explicit_consent_before_capture(self):
        consent = RegistrationConsent("Kathir", True, True, False)
        with self.assertRaises(RegistrationDenied):
            self.registrar().register(consent)
        self.assertEqual(self.face_calls, [])
        self.assertEqual(self.voice_calls, [])

    def test_boolean_is_not_trusted_device_proof(self):
        with self.assertRaises(RegistrationDenied):
            self.registrar(proof=lambda challenge: True).register(self.consent())
        self.assertEqual(self.face_calls, [])

    def test_denies_spoof_and_leaves_no_partial_admin(self):
        with self.assertRaises(RegistrationDenied):
            self.registrar(live=False).register(self.consent())
        self.assertEqual(list_people(db_path=self.db_path), [])

    def test_denies_inconsistent_samples_atomically(self):
        registrar = self.registrar()
        registrar.encode_face = lambda sample: (
            [1.0, 0.0, 0.0] if sample != b"face-3" else [0.0, 1.0, 0.0]
        )
        with self.assertRaises(RegistrationDenied):
            registrar.register(self.consent())
        self.assertEqual(list_people(db_path=self.db_path), [])

    def test_refuses_second_primary_admin(self):
        self.registrar().register(self.consent())
        with self.assertRaises(PermissionError):
            self.registrar().register(RegistrationConsent("Other", True, True, True))
        self.assertEqual(len(list_people(db_path=self.db_path)), 1)

    def test_ambiguous_active_admin_fails_closed(self):
        create_person("Fake first", "admin", db_path=self.db_path)
        create_person("Fake second", "admin", db_path=self.db_path)
        with self.assertRaisesRegex(RuntimeError, "Multiple active admin"):
            get_primary_admin(db_path=self.db_path)

    def test_legacy_cloud_enrollment_is_disabled(self):
        from security.enroll import enroll
        with self.assertRaises(PermissionError):
            enroll("face.jpg", "voice.wav", "phrase")

    def test_tuple_failure_cannot_pass_liveness(self):
        registrar = self.registrar()
        registrar.verify_face_liveness = lambda *_: (False, "replay")
        with self.assertRaises(RegistrationDenied):
            registrar.register(self.consent())
        self.assertEqual(self.voice_calls, [])
        self.assertEqual(list_people(db_path=self.db_path), [])

    def test_truthy_consent_cannot_enable_capture(self):
        with self.assertRaises(RegistrationDenied):
            self.registrar().register(replace(self.consent(), explicitly_confirmed="false"))
        self.assertEqual(self.face_calls, [])

    def test_expiry_during_capture_prevents_save(self):
        registrar = self.registrar()
        now = [100.0]
        registrar.clock = lambda: now[0]
        def capture(_):
            now[0] = 190.0
            return b"face-1"
        registrar.capture_face = capture
        with self.assertRaises(RegistrationDenied):
            registrar.register(self.consent())
        self.assertEqual(self.voice_calls, [])
        self.assertEqual(list_people(db_path=self.db_path), [])

    def test_cancel_during_capture_prevents_save(self):
        registrar = self.registrar()
        stopped = [False]
        registrar.cancelled = lambda: stopped[0]
        def capture(_):
            stopped[0] = True
            return b"face-1"
        registrar.capture_face = capture
        with self.assertRaises(RegistrationDenied):
            registrar.register(self.consent())
        self.assertEqual(self.voice_calls, [])
        self.assertEqual(list_people(db_path=self.db_path), [])

    def test_invalid_config_is_rejected(self):
        from security.registration import RegistrationConfig
        for change in ({"sample_count": 0}, {"face_consistency": float("nan")},
                       {"voice_consistency": -1}, {"session_seconds": float("inf")}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                RegistrationConfig(**change)


if __name__ == "__main__":
    unittest.main()
