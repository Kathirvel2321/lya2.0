# LYA iPhone bridge — setup guide

Two-directional secure control between LYA (laptop) and your iPhone, over the
Tailscale tailnet you already run. Works **anywhere** — home Wi-Fi or 4G in
another city — because the tunnel is Tailscale's, not your router's.

## What exists in the repo now

| File                            | Role                                                              |
| ------------------------------- | ----------------------------------------------------------------- |
| `bridge/gate.py`                | Two-factor gate: face + secret word, with 5-strike lockout        |
| `bridge/actions.py`             | Action registry + whitelisted shell commands + phone action queue |
| `bridge/server.py`              | HTTPS server bound to the tailnet IP only                         |
| `bridge/client.py`              | Outbound calls for the phone and desktop sides                    |
| `test_bridge.py`                | 15 tests, all passing                                             |
| `tools/setup_iphone_bridge.ps1` | One-time token generation (DPAPI-encrypted)                       |

## Security model (what makes this "most secured")

1. **Two factors, both required.** A camera frame matching the enrolled owner
   (`vision.identity.verify_owner` — the same pipeline as escalation) **and**
   the spoken secret word (`security.escalation.check_security_word` — salted
   PBKDF2). Either one failing = no action.
2. **Lockout.** 5 consecutive failures lock the bridge for 15 minutes.
   Retries during lockout are refused WITHOUT running biometrics, so an
   attacker learns nothing by hammering.
3. **Duress phrase is indistinguishable.** Saying the duress word returns the
   same "verification failed" as a wrong word — the coercer cannot tell, but
   LYA can act on it.
4. **Tailnet-only binding.** The server binds the Tailscale IP, never
   `0.0.0.0`. Nobody off your tailnet can even connect.
5. **Allowlisted shell commands.** The phone may run `lock_screen`, `speak`,
   `notify` — fixed argv, no command strings accepted from the packet.
6. **Replay protection.** Every request carries a one-time nonce; reuse is
   rejected for 5 minutes.
7. **Constant-time token compare.** The pairing token is compared with
   `hmac.compare_digest`, never `==`.
8. **Token at rest is DPAPI-encrypted** (`security/bridge_token.lya`) via the
   existing vault.

## Laptop setup (once)

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup_iphone_bridge.ps1
python bridge\server.py
```

The setup script generates the pairing token, encrypts it, and prints the
tailnet address. The server needs Tailscale running.

## iPhone setup (once, ~5 minutes)

In the **Shortcuts** app, create a shortcut named **"LYA Command"**:

1. **Get device frame** — no. Instead add: **Take Photo** (camera, auto-capture).
2. **Base64 Encode** (action: "Base64 Encode", encode the photo).
3. **Text** action containing:
   ```
   {"token":"YOUR_TOKEN","nonce":"CURRENT-DATE-TIME","action":"laptop_shell","packet":{"arg":"[SPOKEN WORD]"},"frame":"[BASE64 PHOTO]","phrase":"[SPOKEN WORD]"}
   ```
4. **Get Contents of URL** — POST to `http://<TAILNET-IP>:8770/command`,
   body type JSON.
5. **Show Result.**

For the "phrase" and body text, use **Dictate Text** first: the shortcut
starts with Dictate Text → that becomes the `phrase` field. So one tap:
_dictate "open sesame" → camera snaps → POST → LYA executes._

### Queued phone actions (LYA → phone)

A second shortcut **"LYA Drain"**:

1. **Get Contents of URL** — GET `http://<TAILNET-IP>:8770/drain`
2. **Repeat Each** item → run a **If/Menu** per action name (open_app, send_message…)
3. Assign this shortcut to a **Back Tap** or an automation.

## Voice flow with LYA

Say: _"LYA, bridge command lock screen"_ — the workflow router sends
`bridge` + the secret word you just spoke → LYA runs the gate → executes.
The phone side uses the identical gate in reverse for laptop commands.

## Testing

```powershell
python run_bridge_tests.py
```

15/15 passing. No network, no camera, no real secrets — fakes only.

## What this deliberately does NOT do

- No full iPhone screen mirroring — Apple does not expose that API to Windows.
- No storage of face images, transcripts or packets — everything is
  in-memory, request-scoped.
- No enrollment change: the bridge uses the owner already enrolled.
- No server exposed to the public internet: tailnet only.
