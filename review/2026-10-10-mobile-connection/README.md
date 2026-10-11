# LYA private laptop / iPhone connection — 2026-10-10

## Current stage

Implemented and activated on the existing Oracle VM. Tailscale is installed on
the laptop and server; the owner signed in and enabled private Serve HTTPS.
The laptop and server were verified on the same private network and an iOS peer
was online. A valid-certificate HTTPS request from the laptop loaded the page;
an unsigned chat request was rejected. Public Funnel is disabled.

The owner's subsequent laptop screenshot shows the authenticated web state
(`Connected. I'm here` and the question composer), providing UI evidence that
the laptop web authentication step completed. The separate native voice panel
in that screenshot is not a phone-service conversation. The owner subsequently
confirmed that Safari sign-in on the iPhone succeeded and LYA correctly answered
the ordinary arithmetic text check. This is owner-reported end-to-end acceptance
of the iPhone public-text route, beyond the earlier online-peer/network checks.
The owner chose to test laptop sleep later; live Stop and sleep/off operation
remain unverified. This stage is **public text conversation**, served by Oracle
without routing through the laptop. It does not yet provide phone
voice, shared confidential memory, visitor photos, notifications or device tools.
The existing laptop hearing, voice, models, appearance and private vault remain
unchanged.

## Owner walkthrough

1. Leave Tailscale connected on the laptop and iPhone using the same account.
   On iPhone, allow the app's VPN configuration. No exit node is required.
2. Fully Quit LYA from its tray menu and reopen the usual launcher once to load
   this new command. Say **connect my phone** (or **pair my phone**).
3. Complete LYA's existing owner verification / exact-request phone approval.
   If it says the session is locked, say **sign in**, approve the existing
   passkey, then repeat **connect my phone** and approve its separate request.
   The trusted pairing page opens in the laptop's default browser. A face
   greeting alone does not authorize pairing.
4. Select **Pair with phone passkey**. In the browser's passkey chooser, select
   the iPhone / another device and scan its QR code. Keep phone and laptop near
   each other with Bluetooth enabled. Save the new passkey on the iPhone.
5. Select **Verify the new passkey**, then approve using that same iPhone
   passkey. Registration is not committed until this signed confirmation.
   The pairing invitation lasts three minutes; if it expires, repeat the laptop
   command. Do not send or publish the invitation link.
6. Open the same private LYA base address in iPhone Safari (use the address in
   the laptop page or the ignored `desktop/mobile.local.json`; omit any `#...`
   invitation). Select **Sign in with passkey**. Use the passkey just created,
   not the earlier localhost passkey used for native laptop approvals.
7. Ask a harmless text question, then a follow-up. Try **Stop** during a reply.
   After that works, put the laptop to sleep and ask another question on the
   phone. The Oracle VM and iPhone Tailscale must remain connected.
8. Optionally use Safari **Share → Add to Home Screen**. **Lock** removes the
   current server session and clears the visible text when the network permits.

To revoke phone access, use the laptop LYA command **disconnect my phone** and
approve the exact request. Revocation invalidates existing sessions and the
paired service credential; it does not remove the native owner registration.
A new pairing requires another explicitly approved laptop invitation.

No API key or password is needed on the iPhone or in chat. Provider credentials
remain with the existing Oracle inference account. Pairing never copies the
laptop's encrypted store, owner profiles or private keys.

## Boundaries and storage

- HTTPS is reachable only through the owner's private Tailscale network, with
  exact-origin WebAuthn and user verification in addition to network access.
- Native localhost passkeys and the new HTTPS service use different RP IDs.
- Restricted `lya-connect` Linux account; loopback HTTP only, bounded requests,
  at most two inference jobs, 256 MiB service memory limit and fixed sudo command
  to the existing public inference entry point. No arbitrary shell/tool API.
- `/var/lib/lya-connect/auth.sqlite`: restricted permissions; only public
  credential metadata, owner binding hash, one-use invitation hash and counter.
  No biometric templates, photos, recordings or persisted conversations.
- The last two conversation turns are retained only in server RAM for the
  session. Sessions expire after 15 minutes and after at most 50 requests.
  Expired RAM entries are pruned on subsequent use/auth activity or restart.
- iPhone: small browser/app/passkey/session state and the current displayed text;
  no deliberate model/database/chat archive download, service worker,
  localStorage or IndexedDB. No guarantee against OS/browser memory or snapshots.
- Public questions are sent to the existing cloud model providers. **Do not put
  confidential information in this first phone route.** Laptop private memory
  and exact private approvals are not delegated by this phone login.
- Oracle free-tier availability, provider quotas and connectivity can interrupt
  service. This is not an uptime or latency guarantee.

## Implementation and checks

Sources: `cloud/mobile.py`, `cloud/mobile_runtime.py`, `cloud/mobile_client.py`,
`cloud/mobile.html`; narrow command/approval/browser-open integration in
`brain/capabilities.py`, `brain/workflow.py`, `security/policy.py`,
`desktop/experience.py`; isolated checks in `test_mobile.py` and
`desktop/check_experience.py`. Ignored configuration: `desktop/mobile.local.json`.

- `validation.json`: final 188 isolated fake-key / temporary-store regressions pass,
  including existing owner, visitor, passkey, workflow and desktop checks.
- `linux-validation.json`: 11 synthetic mobile checks pass as the actual staged
  Linux service account, without model inference or real enrollment.
- Installer resume/conflict checks: two tests included in that final suite pass.
  Matching partial activation can resume; another Serve target or public
  Funnel is rejected before service mutation.
- Owner's first live spoken command was accurately transcribed as
  `Connect my phone.` but fell into ordinary conversation because this new
  exact matcher rejected terminal punctuation. Fixed punctuation only for the
  new mobile commands; added a synthetic regression covering spoken pairing,
  revocation and quoted/negated phrases. Native app restart is needed to load it.
  The next live command reached the protected route and correctly blocked an
  unsigned owner session. Normal **Sign in** is not the first-time pairing page:
  its first button must say **Pair with phone passkey**, from the approved
  laptop command. An earlier unpaired browser preview was closed to avoid
  confusing that sign-in page with an authorized invitation.
- The unauthenticated live HTTPS screen was also opened and visually inspected
  in the browser; this does not verify iPhone passkeys or the signed chat UI.
- `live-network.json`: private TLS certificate/page/no-store and unsigned chat
  rejection pass from the laptop. No live model call or signed phone proof.
- `service-check.json`: active service idle memory 16.59 MiB, one task, 256 MiB
  limit and Funnel disabled. This is one idle sample, not a load benchmark.
- `host-stage.json`, `host-network.json`, `host-activate.json`: dated staged,
  installed and activated evidence. Earlier stage reports are not current state.
- `validation-host-abort.json` and `validation-fixture-path.json` preserve failed
  earlier runs; the synthetic path fixture was fixed, and the unchanged prior
  Windows loopback passkey test passed in the final full run.

Deployment helper: `tools/setup_mobile_connection.py stage|network|activate`.
Stage is deliberately one-time and refuses existing installations; do not rerun
it. Activation checks the private DNS origin and refuses conflicting Serve or
Funnel configuration. Its initial HTTPS attempt needed owner Serve approval;
the same configuration then resumed successfully. No public firewall port,
Funnel, Tailscale SSH, exit node or advertised route was enabled.

If maintenance is needed, stop only `lya-connect.service` and its exact Serve
mapping after inspecting current configuration. Preserve its auth database unless
the owner requests reset. Do not reset all Tailscale settings or touch the
existing archive/inference services. Rollback is not performed by this document.

Next: when the owner is ready, verify live Stop and a phone reply with the
laptop asleep. Plan mobile voice and explicitly permitted
shared memory/photo workflows only after this connection gate passes.
