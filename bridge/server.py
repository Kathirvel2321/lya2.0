"""LYA <-> iPhone bridge - the HTTPS server.

Runs on the laptop, reachable ONLY over the Tailscale tailnet (binds the
Tailscale interface, never 0.0.0.0). Every POST must carry:

    token    - the bridge pairing token (constant-time compared)
    frame    - base64 JPEG from the phone camera (the FACE factor)
    phrase   - the spoken security word (the WORD factor)
    action   - one registered action name
    packet   - JSON action payload

A successful call returns the action result. A failed call returns 403 with
a bare reason and NOTHING else - no biometric detail leaks. The HTTP
server is single-purpose and deliberately does not reuse web_server.py: the
bridge needs bind-to-tailnet isolation and a different token, not the phone
chat page's HTML.
"""
import base64
import binascii
import hmac
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge import actions as bridge_actions
from bridge import gate

MAX_BODY = 1_500_000          # ~1 MB frame + packet headroom
RECENT_NONCES = {}            # nonce -> ts, replays rejected
REPLAY_WINDOW = 300
NONCE_LOCK = threading.Lock()


def tailscale_ip():
    """The laptop's tailnet address, or None when Tailscale is not running."""
    try:
        import subprocess
        out = subprocess.run(["tailscale", "ip", "-4"], capture_output=True,
                             text=True, timeout=10)
        ip = out.stdout.strip().splitlines()[0] if out.stdout.strip() else ""
        return ip or None
    except Exception:
        return None


def check_nonce(nonce, now):
    """A nonce may be used exactly once within the replay window."""
    with NONCE_LOCK:
        for k in [k for k, t in RECENT_NONCES.items() if now - t > REPLAY_WINDOW]:
            RECENT_NONCES.pop(k)
        if nonce in RECENT_NONCES:
            return False
        RECENT_NONCES[nonce] = now
        return True


def make_handler(token, actions=None, *, verify_gate=None, check_nonce=None):
    """Build a Handler class bound to one token. verify_gate is injectable for
    tests; production uses bridge.gate.verify_gate."""
    if verify_gate is None:
        verify_gate = gate.verify_gate
    if check_nonce is None:
        check_nonce = check_nonce

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, payload):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):   # quiet
            pass

        def do_GET(self):
            # A plain GET tells a human the bridge is alive; no data, no auth.
            self._send(200, {"bridge": "lya", "ok": True})

        def do_POST(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY:
                    return self._send(413, {"error": "bad size"})
                data = json.loads(self.rfile.read(size).decode())
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError,
                    binascii.Error):
                return self._send(400, {"error": "bad body"})

            if not isinstance(data, dict):
                return self._send(400, {"error": "bad body"})
            supplied = data.get("token", "")
            if not isinstance(supplied, str) or not hmac.compare_digest(supplied, token):
                return self._send(403, {"error": "wrong token"})
            nonce = data.get("nonce", "")
            if not isinstance(nonce, str) or len(nonce) < 16 or \
                    not check_nonce(nonce, time.time()):
                return self._send(403, {"error": "nonce rejected"})

            frame = data.get("frame", "")
            phrase = data.get("phrase", "")
            action = data.get("action", "")
            packet = data.get("packet") if isinstance(data.get("packet"), dict) else {}
            if not isinstance(frame, str) or not isinstance(phrase, str) \
                    or not isinstance(action, str):
                return self._send(400, {"error": "bad fields"})

            try:
                frame_bytes = base64.b64decode(frame, validate=False)
            except binascii.Error:
                frame_bytes = b""

            allowed, detail = verify_gate(frame_bytes, phrase)
            if not allowed:
                return self._send(403, {"error": "verification failed", "detail": detail})

            result = bridge_actions.execute(action, packet, actions)
            code = 200 if result.get("ok") else 400
            self._send(code, result)

    return Handler


def _load_token():
    """Read the encrypted bridge token; the server refuses to start without it.
    The token never appears in a log or exception message."""
    token_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "security", "bridge_token.lya")
    if os.path.exists(token_file):
        try:
            from security import vault
            token = vault.decrypt_file(token_file).decode()
            if token:
                return token
        except Exception as e:
            raise SystemExit(f"Bridge token file exists but is unreadable ({e}); "
                             "re-run tools/setup_iphone_bridge.ps1 to regenerate.")
    return os.environ.get("LYA_BRIDGE_TOKEN", "")


def serve(port=8770, token=None):
    """Blocking serve. Binds the tailnet IP only; refuses to start on 0.0.0.0
    or without a token, so a misconfiguration is loud, not silent."""
    token = token or _load_token()
    if not token:
        raise SystemExit("No bridge token: run tools/setup_iphone_bridge.ps1 first.")
    ip = tailscale_ip()
    if not ip:
        raise SystemExit("Tailscale is not running; the bridge binds the tailnet only.")
    server = ThreadingHTTPServer((ip, port), make_handler(token))
    print(f"[LYA-BRIDGE] listening on https://{ip}:{port} (tailnet only)")
    server.serve_forever()


if __name__ == "__main__":
    serve()
