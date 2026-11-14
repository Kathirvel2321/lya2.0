"""LYA <-> iPhone bridge - the outbound client.

Two directions, one module:

  laptop -> phone   queue_phone_action() then the phone polls /drain through
                    the same bridge server (works because the iPhone is also
                    on the tailnet and can reach the laptop's bridge).

  phone -> laptop   phone posts to /command (the server handles it). This
                    module additionally offers post_to_lya() for callers that
                    want to reach the EXISTING phone chat gateway instead.

Everything is a small stdlib-only HTTP call - no new dependencies, matching
the rest of the project's transport style.
"""
import json
import os
import secrets
import urllib.request

from bridge.server import check_nonce


def post_to_bridge(host, port, token, action, packet, frame_b64, phrase, timeout=15):
    """Send one authenticated action to the laptop bridge server."""
    url = f"https://{host}:{port}/command"
    body = json.dumps({
        "token": token,
        "nonce": secrets.token_urlsafe(16),
        "action": action,
        "packet": packet,
        "frame": frame_b64,
        "phrase": phrase,
    }).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def drain_from_bridge(host, port, timeout=10):
    """The iPhone calls this to fetch queued actions. The bridge server
    exposes /drain WITHOUT the two-factor gate (it is read-only and returns
    only queued, already-approved actions)."""
    url = f"https://{host}:{port}/drain"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())
