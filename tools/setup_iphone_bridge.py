"""One-time iPhone bridge token setup. Run from the project root:

    python tools/setup_iphone_bridge.py

Generates the bridge pairing token, encrypts it with the existing DPAPI
vault, and prints the tailnet address the iPhone Shortcuts will call.
The token is printed ONCE at creation; after that it lives only encrypted.
"""
import os
import secrets
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from security import vault  # noqa: E402


def main():
    token_file = os.path.join(ROOT, "security", "bridge_token.lya")
    if os.path.exists(token_file):
        try:
            vault.decrypt_file(token_file)
            print("[LYA-BRIDGE] Bridge token already exists (encrypted, not printed).")
            print("[LYA-BRIDGE] If you lost the old token, delete")
            print(f"            {token_file}")
            print("            and run this again to mint a new one.")
        except Exception as e:
            print(f"[LYA-BRIDGE] Existing token is unreadable ({e}).")
            print("[LYA-BRIDGE] Delete the file above and re-run to mint a new one.")
            sys.exit(1)
    else:
        token = secrets.token_urlsafe(32)
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "wb") as f:
            f.write(vault.encrypt(token.encode()))
        print("[LYA-BRIDGE] New bridge token generated and DPAPI-encrypted.")
        print("[LYA-BRIDGE] TOKEN (shown once - paste it into your iPhone Shortcut):")
        print()
        print(f"  {token}")
        print()

    try:
        ip = subprocess.run(["tailscale", "ip", "-4"], capture_output=True,
                            text=True, timeout=10)
        addr = ip.stdout.strip().splitlines()[0] if ip.stdout.strip() else ""
    except Exception:
        addr = ""
    if not addr:
        print("[LYA-BRIDGE] Tailscale not reachable - start Tailscale and re-run.")
        sys.exit(1)
    print(f"[LYA-BRIDGE] Tailnet address: {addr}")
    print(f"[LYA-BRIDGE] iPhone Shortcut POST URL: http://{addr}:8770/command")
    print()
    print("Next: start the server with   python bridge/server.py")


if __name__ == "__main__":
    main()
