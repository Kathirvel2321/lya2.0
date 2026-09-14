"""Step 7: Phone Approval Escalation Gateway Test Suite
=====================================================
Tests:
  1. Challenge & nonce lifecycle, TTL expiration, and cleanup
  2. Single-use grant consumption (no replay, burn-on-read)
  3. Nonce mismatch and invalid challenge rejection
  4. Spoken security word & sliding window token matching
  5. Duress phrase detection and silent alarm trigger
  6. Rate limiting, brute-force lockout, and fail-closed on tamper
  7. request_phone cancellation event and non-blocking mutex lock
  8. Web gateway token authentication (constant-time compare)
  9. Web gateway plain HTTP rejection (TLS enforcement)
 10. Web gateway deferred enrollment enforcement (403)
 11. Web gateway private memory access gating
 12. End-to-end HTTPS escalation approval flow with TLS socket
"""
import base64
import datetime
import io
import ipaddress
import json
import os
import ssl
import sys
import tempfile
import threading
import time
import unittest
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from security import escalation, vault
import web_server as ws


def generate_self_signed_cert(cert_path: Path, key_path: Path):
    """Generate temporary self-signed certificate for local HTTPS testing."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


class EscalationTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

        # Rebind escalation files to isolated temporary directory
        self.orig_word_file = escalation.WORD_FILE
        self.orig_grant_file = escalation.GRANT_FILE
        self.orig_challenge_file = escalation.CHALLENGE_FILE
        self.orig_attempt_file = escalation.ATTEMPT_FILE

        escalation.WORD_FILE = str(self.tmp_path / "security_word.lya")
        escalation.GRANT_FILE = str(self.tmp_path / "escalation_grant.lya")
        escalation.CHALLENGE_FILE = str(self.tmp_path / "escalation_challenge.lya")
        escalation.ATTEMPT_FILE = str(self.tmp_path / "escalation_attempts.lya")

        escalation._NONCE = None
        escalation._clear_challenge()
        escalation._reset_attempts()

    def tearDown(self):
        escalation._NONCE = None
        escalation._clear_challenge()
        escalation.WORD_FILE = self.orig_word_file
        escalation.GRANT_FILE = self.orig_grant_file
        escalation.CHALLENGE_FILE = self.orig_challenge_file
        escalation.ATTEMPT_FILE = self.orig_attempt_file
        self.tmp_dir.cleanup()

    def test_nonce_and_challenge_lifecycle(self):
        """Test nonce writing, reading across processes, expiration TTL, and cleanup."""
        self.assertIsNone(escalation.current_challenge())
        self.assertIsNone(escalation.current_nonce())

        nonce = "test-challenge-nonce-1"
        task_desc = "Export private cryptographic keys"
        escalation._write_challenge(nonce, task_desc)

        ch = escalation.current_challenge()
        self.assertIsNotNone(ch)
        self.assertEqual(ch["nonce"], nonce)
        self.assertEqual(ch["task"], task_desc)
        self.assertAlmostEqual(ch["t"], time.time(), delta=5.0)
        self.assertEqual(escalation.current_nonce(), nonce)

        # Expiration TTL check: challenges older than POLL_SECONDS + GRANT_TTL are invalid
        with open(escalation.CHALLENGE_FILE, "wb") as f:
            stale_payload = {"nonce": nonce, "t": time.time() - 300, "task": task_desc}
            f.write(vault.encrypt(json.dumps(stale_payload).encode()))

        self.assertIsNone(escalation.current_challenge())
        self.assertIsNone(escalation.current_nonce())

        # Cleanup deletes file
        escalation._write_challenge(nonce, task_desc)
        self.assertTrue(os.path.exists(escalation.CHALLENGE_FILE))
        escalation._clear_challenge()
        self.assertFalse(os.path.exists(escalation.CHALLENGE_FILE))

    def test_grant_single_use_and_replay_prevention(self):
        """Test that a phone grant is single-use and burns immediately upon consumption."""
        nonce = "active-nonce-42"
        escalation._NONCE = nonce
        escalation._write_challenge(nonce, "Unlock secure vault")

        # Phone approves matching challenge
        escalation.phone_approve(nonce=nonce)
        self.assertTrue(os.path.exists(escalation.GRANT_FILE))

        # First consumption must succeed
        self.assertTrue(escalation._consume_phone_grant())

        # Replay attempt must fail immediately
        self.assertFalse(escalation._consume_phone_grant())
        self.assertFalse(escalation._consume_phone_grant())

    def test_challenge_nonce_mismatch_and_missing_challenge(self):
        """Test that grants for mismatched nonces or issued without active challenge fail closed."""
        active_nonce = "legit-nonce-100"
        escalation._NONCE = active_nonce
        escalation._write_challenge(active_nonce, "Sensitive task")

        # Grant with different nonce
        escalation.phone_approve(nonce="attacker-spoofed-nonce")
        self.assertFalse(escalation._consume_phone_grant())

        # Grant with None nonce
        escalation.phone_approve(nonce=None)
        self.assertFalse(escalation._consume_phone_grant())

        # Grant issued when no challenge is active on laptop
        escalation._NONCE = None
        escalation.phone_approve(nonce=active_nonce)
        self.assertFalse(escalation._consume_phone_grant())

    def test_spoken_security_word_and_sliding_window(self):
        """Test salted PBKDF2 hashing, normalization, and sliding window phrase detection."""
        self.assertFalse(escalation.has_security_word())
        escalation.set_security_word("blue falcon")
        self.assertTrue(escalation.has_security_word())

        # Exact match
        self.assertEqual(escalation.check_security_word("blue falcon"), "ok")

        # Case, whitespace, and punctuation normalization
        self.assertEqual(escalation.check_security_word("  Blue,   Falcon! "), "ok")

        # Embedded in spoken natural utterance
        self.assertEqual(escalation.check_security_word("um my secret word is blue falcon i believe"), "ok")

        # Incomplete / prefix must fail
        self.assertFalse(escalation.check_security_word("blue"))
        self.assertFalse(escalation.check_security_word("falcon"))

        # Inverted word order must fail
        self.assertFalse(escalation.check_security_word("falcon blue"))

        # Empty / whitespace-only must fail
        self.assertFalse(escalation.check_security_word(""))
        self.assertFalse(escalation.check_security_word("   "))

        # Salt is unique per setting (prevents rainbow tables)
        data1 = escalation._word_data()
        escalation.set_security_word("blue falcon")
        data2 = escalation._word_data()
        self.assertNotEqual(data1["salt"], data2["salt"])
        self.assertNotEqual(data1["sha256"], data2["sha256"])

    def test_duress_phrase_detection(self):
        """Test duress phrase detection and silent alarm handling."""
        escalation.set_security_word("safe harbor", duress="red alert nine")

        # Normal word produces "ok"
        self.assertEqual(escalation.check_security_word("safe harbor"), "ok")

        # Duress phrase produces "duress"
        self.assertEqual(escalation.check_security_word("red alert nine"), "duress")
        self.assertEqual(escalation.check_security_word("under coercion red alert nine now"), "duress")

        # Duress phrase cannot be identical to normal phrase
        with self.assertRaises(ValueError):
            escalation.set_security_word("same phrase", duress="same phrase")

        # Empty phrase raises ValueError
        with self.assertRaises(ValueError):
            escalation.set_security_word("!!!")

    def test_brute_force_lockout_and_fail_closed(self):
        """Test 5-attempt rate-limiting lockout and fail-closed behavior on corrupted counters."""
        self.assertFalse(escalation._locked_out())

        for _ in range(escalation.MAX_ATTEMPTS - 1):
            escalation._record_failure()
            self.assertFalse(escalation._locked_out())

        # 5th failure triggers lockout
        escalation._record_failure()
        self.assertTrue(escalation._locked_out())

        # Reset clears lockout
        escalation._reset_attempts()
        self.assertFalse(escalation._locked_out())

        # Corrupted attempt file must fail CLOSED (treated as locked out)
        with open(escalation.ATTEMPT_FILE, "wb") as f:
            f.write(b"corrupted_tampered_bytes")
        self.assertTrue(escalation._locked_out())

        # Deleting the file returns to clean initial state (not locked)
        os.remove(escalation.ATTEMPT_FILE)
        self.assertFalse(escalation._locked_out())

    def test_request_phone_cancellation_and_concurrency(self):
        """Test request_phone responds to cancellation and enforces mutex locking."""
        cancelled = threading.Event()
        cancelled.set()

        # Immediate cancellation
        start = time.monotonic()
        approved = escalation.request_phone("Test task", cancelled=cancelled, seconds=5)
        duration = time.monotonic() - start
        self.assertFalse(approved)
        self.assertLess(duration, 1.0)
        self.assertIsNone(escalation._NONCE)

        # Mutex concurrency test: secondary request while primary is holding lock
        ready = threading.Event()
        stop = threading.Event()
        results = []

        def hold_lock():
            ready.set()
            results.append(escalation.request_phone("Task 1", cancelled=stop, seconds=5))

        t = threading.Thread(target=hold_lock, daemon=True)
        t.start()
        ready.wait(timeout=2.0)
        time.sleep(0.05)

        # Second request while first is running must fail immediately (cannot acquire lock)
        overlapping = escalation.request_phone("Task 2", seconds=5)
        self.assertFalse(overlapping)

        stop.set()
        t.join(timeout=2.0)
        self.assertFalse(results[0])


class WebGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

        self.orig_word_file = escalation.WORD_FILE
        self.orig_grant_file = escalation.GRANT_FILE
        self.orig_challenge_file = escalation.CHALLENGE_FILE
        self.orig_attempt_file = escalation.ATTEMPT_FILE

        escalation.WORD_FILE = str(self.tmp_path / "security_word.lya")
        escalation.GRANT_FILE = str(self.tmp_path / "escalation_grant.lya")
        escalation.CHALLENGE_FILE = str(self.tmp_path / "escalation_challenge.lya")
        escalation.ATTEMPT_FILE = str(self.tmp_path / "escalation_attempts.lya")

        escalation._NONCE = None
        escalation._clear_challenge()
        escalation._reset_attempts()

        self.orig_token = ws.TOKEN
        self.test_token = "secret-test-token-777"
        ws.TOKEN = self.test_token

    def tearDown(self):
        escalation._NONCE = None
        escalation._clear_challenge()
        escalation.WORD_FILE = self.orig_word_file
        escalation.GRANT_FILE = self.orig_grant_file
        escalation.CHALLENGE_FILE = self.orig_challenge_file
        escalation.ATTEMPT_FILE = self.orig_attempt_file
        ws.TOKEN = self.orig_token
        self.tmp_dir.cleanup()

    def test_web_gateway_token_authentication(self):
        """Test token validation rejects unauthorized requests with 403."""
        sent = []
        handler = ws.Handler.__new__(ws.Handler)
        handler._send = lambda code, body, ctype="text/html; charset=utf-8": sent.append((code, body))

        # Wrong token
        data = {"token": ["wrong-token"]}
        self.assertFalse(handler._check_token(data))
        self.assertEqual(sent[0][0], 403)
        self.assertIn("wrong token", sent[0][1])

        # Correct token
        sent.clear()
        data = {"token": [self.test_token]}
        self.assertTrue(handler._check_token(data))
        self.assertEqual(len(sent), 0)

    def test_web_gateway_plain_http_rejection(self):
        """Test that plain HTTP connections cannot approve escalations."""
        sent = []
        handler = ws.Handler.__new__(ws.Handler)
        handler.path = "/escalate"
        payload = f"token={self.test_token}&nonce=test-nonce".encode()
        handler.headers = {"Content-Length": str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        handler.connection = object()  # Not an SSLSocket
        handler._send = lambda code, body, ctype="text/html; charset=utf-8": sent.append((code, body))

        handler.do_POST()
        self.assertEqual(sent[0][0], 403)
        self.assertIn("HTTPS", sent[0][1])

    def test_web_gateway_enrollment_deferred(self):
        """Test that enrollment endpoints on phone gateway return 403."""
        for path in ("/enroll_face", "/enroll_voice"):
            sent = []
            handler = ws.Handler.__new__(ws.Handler)
            handler.path = path
            payload = f"token={self.test_token}&data=dummy".encode()
            handler.headers = {"Content-Length": str(len(payload))}
            handler.rfile = io.BytesIO(payload)
            handler._send = lambda code, body, ctype="text/html; charset=utf-8": sent.append((code, body))

            handler.do_POST()
            self.assertEqual(sent[0][0], 403)
            self.assertIn("Enrollment is deferred", sent[0][1])

        # GET /enroll
        sent = []
        handler = ws.Handler.__new__(ws.Handler)
        handler.path = "/enroll"
        handler._send = lambda code, body, ctype="text/html; charset=utf-8": sent.append((code, body))
        handler.do_GET()
        self.assertEqual(sent[0][0], 403)
        self.assertIn("Enrollment is deferred", sent[0][1])

    def test_web_gateway_private_memory_gating(self):
        """Test that phone chat refuses private memory operations when unverified."""
        for query in ("remember my password is secret", "what do you remember about me"):
            reply = ws.lyas_answer(query, verified=False)
            self.assertEqual(reply, ws._NEEDS_FACE)

    def test_web_gateway_tls_escalate_and_approval_flow(self):
        """End-to-end integration: run local HTTPS server, approve escalation via TLS, consume grant."""
        cert_path = self.tmp_path / "cert.pem"
        key_path = self.tmp_path / "key.pem"
        generate_self_signed_cert(cert_path, key_path)

        # Set up active escalation challenge on laptop
        nonce = "tls-test-nonce-888"
        escalation._NONCE = nonce
        escalation._write_challenge(nonce, "Transfer administrative authority")
        escalation.set_security_word("golden eagle")

        # Spin up local HTTPS server
        server = HTTPServer(("127.0.0.1", 0), ws.Handler)
        port = server.server_port

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(cert_path, key_path)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        # Client SSLContext that trusts our self-signed cert
        client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client_ctx.load_verify_locations(cert_path)

        import urllib.request

        try:
            # 1. Fetch challenge via POST /challenge
            req_data = f"token={self.test_token}".encode("utf-8")
            req = urllib.request.Request(
                f"https://127.0.0.1:{port}/challenge",
                data=req_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, context=client_ctx) as resp:
                ch_resp = json.loads(resp.read().decode())
                self.assertEqual(ch_resp["nonce"], nonce)
                self.assertEqual(ch_resp["task"], "Transfer administrative authority")

            # 2. Mock identity owner verification for this test
            with patch("vision.identity.verify_owner", return_value=(True, "Owner matched.")):
                escalate_data = (
                    f"token={self.test_token}&nonce={nonce}&phrase=golden+eagle&frame=AAAA"
                ).encode("utf-8")
                req = urllib.request.Request(
                    f"https://127.0.0.1:{port}/escalate",
                    data=escalate_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                with urllib.request.urlopen(req, context=client_ctx) as resp:
                    result = json.loads(resp.read().decode())
                    self.assertTrue(result.get("ok"))
                    self.assertIn("Approved", result.get("msg", ""))

            # 3. Verify laptop consumes the grant
            self.assertTrue(escalation._consume_phone_grant())
            # Replay fails
            self.assertFalse(escalation._consume_phone_grant())

        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
