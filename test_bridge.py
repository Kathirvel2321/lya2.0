"""Tests for the LYA <-> iPhone bridge.

Fake secrets, fake frames, no network. Every test runs in-process.
"""
import base64
import os
import sys
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge import actions as A
from bridge import gate as G
from bridge import server as S


def fake_face_ok(frame):
    return True, "ok"


def fake_face_bad(frame):
    return False, "no face"


class GateTests(unittest.TestCase):
    def setUp(self):
        G.reset_gate()

    def test_both_pass(self):
        ok, detail = G.verify_gate(b"frame", "open sesame",
                                   verify_face=fake_face_ok,
                                   check_word=lambda t: "ok" if t == "open sesame" else False)
        self.assertTrue(ok)
        self.assertEqual(detail, "ok")

    def test_face_failure_counts(self):
        for _ in range(G.MAX_FAILURES):
            ok, _ = G.verify_gate(b"x", "open sesame", verify_face=fake_face_bad,
                                  check_word=lambda t: "ok")
        ok, reason = G.gate_status()
        self.assertFalse(ok)
        self.assertEqual(reason, "locked")

    def test_lockout_blocks_even_correct_face(self):
        for _ in range(G.MAX_FAILURES):
            G.verify_gate(b"x", "nope", verify_face=fake_face_bad,
                          check_word=lambda t: False)
        ok, _ = G.verify_gate(b"x", "open sesame", verify_face=fake_face_ok,
                              check_word=lambda t: "ok")
        self.assertFalse(ok)   # locked out - a good face after lockout is refused

    def test_duress_reported_like_wrong_word(self):
        ok, detail = G.verify_gate(b"x", "help me", verify_face=fake_face_ok,
                                   check_word=lambda t: "duress")
        self.assertFalse(ok)
        self.assertEqual(detail, "duress")
        G.reset_gate()

    def test_success_resets_counter(self):
        ok1, _ = G.verify_gate(b"x", "no", verify_face=fake_face_bad, check_word=lambda t: False)
        self.assertFalse(ok1)
        ok2, _ = G.verify_gate(b"x", "open sesame", verify_face=fake_face_ok,
                               check_word=lambda t: "ok")
        self.assertTrue(ok2)
        # First failure AFTER the reset is refused as a normal failure, not a
        # lockout: only one strike is on the counter now.
        ok3, reason3 = G.verify_gate(b"x", "no", verify_face=fake_face_bad,
                                     check_word=lambda t: False)
        self.assertFalse(ok3)
        self.assertEqual(reason3, "face:no face")   # 'locked' would mean the reset failed
        ok4, _ = G.gate_status()
        self.assertTrue(ok4)


class ActionTests(unittest.TestCase):
    def setUp(self):
        self.actions = {}
        A.register("ping", "laptop", lambda p: {"ok": True, "echo": p},
                   actions=self.actions)

    def test_register_and_execute(self):
        r = A.execute("ping", {"x": 1}, self.actions)
        self.assertTrue(r["ok"])
        self.assertEqual(r["echo"], {"x": 1})

    def test_unknown_action(self):
        r = A.execute("missing", {}, self.actions)
        self.assertFalse(r["ok"])

    def test_duplicate_registration_refused(self):
        with self.assertRaises(ValueError):
            A.register("ping", "laptop", lambda p: {}, actions=self.actions)

    def test_queue_and_drain(self):
        ok, _ = A.queue_phone_action("open_app", {"app": "whatsapp"})
        self.assertTrue(ok)
        items = A.drain_phone_actions()
        self.assertEqual(len(items), 1)
        self.assertEqual(A.drain_phone_actions(), [])   # consumed once

    def test_shell_allowlist_strict(self):
        self.assertFalse(A.run_shell_action("rm_rf_slash")["ok"])
        self.assertFalse(A.run_shell_action("lock_screen", "x" * 500)["ok"])

    def test_query_bounds_length(self):
        # Empty input is refused before any model/network import. The real
        # mind.reply is never called in tests - that import chain pulls audio
        # and storage and is far too heavy for a unit test.
        r = A.run_query("")
        self.assertFalse(r["ok"])


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.token = "unit-test-token"
        self.actions = {}
        A.register("ping", "laptop", lambda p: {"ok": True, "echo": p},
                   actions=self.actions)
        self.gate_calls = []

        def fake_gate(frame, phrase):
            self.gate_calls.append((frame, phrase))
            return True, "ok"

        self.Handler = S.make_handler(self.token, self.actions,
                                      verify_gate=fake_gate,
                                      check_nonce=lambda n, now: True)

    def test_handler_rejects_wrong_token(self):
        import io

        body = b'{"token":"wrong","nonce":"' + b"x" * 20 + b'","action":"ping","frame":"","phrase":""}'
        h = self.Handler.__new__(self.Handler)
        h.rfile = io.BytesIO(body)
        h.wfile = io.BytesIO()
        h.headers = {"Content-Length": str(len(body))}
        h.responses = []
        h.send_response = lambda c, *a, **k: h.responses.append(("resp", c))
        h.send_header = lambda *a, **k: None
        h.end_headers = lambda *a, **k: None
        h.do_POST()
        self.assertIn(403, [c for _, c in h.responses])

    def test_nonce_replay_rejected(self):
        S.RECENT_NONCES.clear()
        self.assertTrue(S.check_nonce("n" * 20, time.time()))
        self.assertFalse(S.check_nonce("n" * 20, time.time()))

    def test_execute_via_registry(self):
        r = A.execute("ping", {"hi": 1}, self.actions)
        self.assertEqual(r["echo"], {"hi": 1})


class ReplayTests(unittest.TestCase):
    def test_window_expiry(self):
        S.RECENT_NONCES.clear()
        S.RECENT_NONCES["old"] = time.time() - S.REPLAY_WINDOW - 10
        self.assertTrue(S.check_nonce("old", time.time()))


if __name__ == "__main__":
    unittest.main()
