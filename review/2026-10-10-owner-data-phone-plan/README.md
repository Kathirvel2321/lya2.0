# LYA owner data and secure phone review

2026-10-10. The local summary/name changes below are implemented; the phone system below is a researched implementation plan, not a deployed service. No photos were collected and no phone or network configuration was changed in this task.

## Available local changes

After loading the updated desktop, say **show my saved data** and approve that exact request with the existing phone flow. LYA reports the encrypted database location, current face/voice sample counts, profile consent and saved-note count. It does not export biometric vectors or passkey credentials. **Show memories** remains the existing separately protected note-review command.

The normal protected location is `%LOCALAPPDATA%\LYA\lya.db.enc`. Registration stores mathematical face/voice features, not a photo album or audio recordings. The protected encryption key is also required for recovery; copying the database alone is not a verified portable backup. Do not move, delete or upload either file to inspect it.

Owner conversation now asks the model for a familiar, capable tone and substitutes the registered name locally. The name and person ID are not inserted into the cloud prompt by this feature. This does not remove private-action approval. Approximate face familiarity receives familiar tone without owner authority; an unknown person receives ordinary public conversation. Existing selected hearing/voice/models and working interface are preserved. A prompt guides style; live answer quality still needs owner acceptance.

## Recommended phone arrangement

Use **Tailscale Serve + a small LYA phone review page + a separate review passkey**. Serve exposes a local service to the private tailnet and supports access rules and HTTPS. Explicitly disable public Funnel access and verify its state; serve only the review application, never a directory or database. [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve)

The current Personal plan offers free non-commercial use. Verify the actual account qualifies before setup; stop if it requires payment. No paid fallback. [Tailscale pricing](https://tailscale.com/pricing)

The phone page is a secondary visitor-review interface; the native LYA desktop stays the main assistant. It cannot execute arbitrary laptop commands, retrieve confidential memories, change the owner, or bypass existing desktop phone approval.

## Pair once, then review

1. Connect the laptop and owner's iPhone to the private tailnet; restrict access to the review service. Check the phone's supported iOS version, private HTTPS access and certificate. Use a neutral device hostname because certificate names are public metadata.
2. On the laptop, the current owner approves the exact **pair visitor-review phone** operation through the existing owner passkey. Only then create a one-use, short-lived QR pairing challenge, kept in RAM and consumed atomically.
3. Open that private HTTPS page on the phone. Create a **new review-only passkey** and complete a fresh assertion before committing pairing. Bind it to the current unique owner's public-credential fingerprint and a narrow visitor-review permission. A scanned QR alone does not authorize pairing.
4. Reuse the installed FIDO2 verifier: validate RP ID, exact expected origin, challenge, user presence and user verification on the server. The existing desktop credential belongs to `localhost`; do not accept it as though it belonged to the new HTTPS hostname. [Server-side passkey verification](https://developers.google.com/identity/passkeys/developer-guides/server-registration)
5. Add the review page to the iPhone Home Screen. Offer an explicit notification permission action. Each later review starts with passkey verification; each mutation approves the exact visitor, decision, name and limited role, with a one-use challenge. A short review session reduces repeated login prompts but does not approve later mutations.

Passkeys may sync through the owner's provider. This is owner-account proof, not a claim of hardware-exclusive binding to one physical iPhone. Tailnet device restrictions add another boundary; neither network membership nor a proxy identity header replaces passkey proof.

## Photo and reply behavior

Before enabling retention, show a new setup consent explaining the changed policy: one brief visible camera check at LYA startup; one usable unknown face may be retained encrypted until the owner decides. Existing consent promised no saved photos and cannot silently enable this change. No hidden or periodic camera, room surveillance, voice recording or scan on ordinary questions.

After capture, close the camera immediately. Keep a compressed face crop and its necessary matching features in the existing protected local store, bound to the owner credential. Avoid retaining the whole room. Start with a bounded queue of at most 32 pending items and a strict per-image byte limit; these are design limits, not measured capacities. When full, stop retaining new photos and inform the owner; never silently delete retained items to make room. Disabling capture stops new retention; existing items remain until an explicit deletion choice.

The paired phone displays a pending photo only after authentication. The owner can:

| Choice | Exact effect |
|---|---|
| Register person | Confirm a name and fixed family/friend capability tier; create only limited recognition permission. Never admin access. |
| Keep for later | Leave the encrypted pending item until a later decision. |
| Delete | Remove the pending photo/features from the active store. Explain any retained encrypted backup copies separately; do not promise physical erasure from SSDs. |
| Block | Deny LYA's limited tools to a future approximate match; retain only the necessary encrypted blocking features and delete the pending photo after explicit review. |

Registration does not implicitly keep a photo permanently. Show the exact retention effect on the decision screen. Owner passkey proof must remain available if a face is falsely blocked. Blocking cannot prevent Windows from launching LYA, identify everyone reliably, or defeat photos/injected camera feeds. Faces are not secrets or secure authenticators; confidential access keeps phone proof. [NIST biometric limitations](https://pages.nist.gov/800-63-4/sp800-63b.html)

No automatic identification of who has replaced a person after the camera closes. A return review requires the owner to signal it or open the phone page. A missed startup face gives no private permission.

## Mobile alerts

Prefer standards-based **Web Push** from the small Home Screen review app, avoiding another chat bot or public notification topic. iOS 16.4+ supports this after Home Screen installation and permission from a user gesture, without Apple Developer Program membership. Validate it on the actual iPhone before enabling capture. [WebKit iPhone Web Push](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)

Send only a generic notice: **LYA has a person for you to review.** No photo, name, biometric, secret link or approval token in the push payload. Tapping opens the private review page; phone authentication happens there. Apple push infrastructure receives delivery metadata and an encrypted generic payload; this is not an entirely offline system. Notifications are advisory and may be delayed or disabled. They never authorize an action. The review inbox must work even if push fails.

Implement notifications with a maintained Web Push library selected at that stage, not hand-written encryption. Protect its signing key and subscription in the existing protected store. Validate subscription endpoints against the supported push provider; reject arbitrary URLs, redirects, private addresses and oversized requests to prevent a notification setting from becoming server-side request forgery. The old ntfy reminder helper is not an authenticated review channel and will remain disconnected.

The laptop must be awake, running LYA and reachable for new photos and phone review. With the private tunnel disconnected, the phone may receive an alert but cannot fetch a photo until reconnected. No always-on Oracle relay is needed for this first version; laptop-off review would be a separate encrypted-relay project.

## Minimum server protections

- Bind the application to loopback; proxy only through private Serve. No router port forwarding, public listener, directory listing or unrestricted CORS.
- Allow only fixed HTTPS Host/Origin/RP values. Expire/reject replayed or wrong-owner challenges, revoked pairing and owner-credential rotation. Apply bounded request size, rate and concurrency limits.
- Use short-lived Secure, HttpOnly, SameSite=Strict cookies, CSRF checks, parameterized queries and escaped display names. Bind every mutation challenge to item ID, immutable content digest and canonical decision fields. Changing fields requires a new approval; replay and conflicting decisions fail atomically.
- Return `Cache-Control: no-store` for private responses. Never put photos in URLs, logs, browser storage, push or service-worker caches. The service worker handles push only and never caches authenticated review responses. Revoke sessions and clear the visible image on lock/logout; screenshots on an authorized phone cannot be prevented reliably.
- Reuse current encrypted storage, file protections and unique-owner checks. Never send visitor material to the public archive, LLM, ordinary cloud ASR or external image analysis.
- Permit pairing revocation locally with fresh owner proof and remove the phone's review authority immediately. Preserve the existing desktop owner credential and its recovery limitations. Disable the route when owner binding is unavailable or changed.

## Build and acceptance order

1. Implement the narrow pairing/verifier/storage lifecycle with fake credentials and temporary encrypted stores. Test wrong origin/RP/owner, missing user verification, expiry, replay, concurrent consumption, revocation and attempted role elevation.
2. Implement synthetic-photo review and atomic decisions. Verify no private responses without proof, no cache/log/export leaks, failed writes preserve pending records, queue limits, and backup/deletion semantics.
3. Configure private access with the owner; test actual iPhone pairing, permission, reconnect and generic push. Verify outside-tailnet access fails and public Funnel remains off. No real visitor photo required for these checks.
4. Present the explicit retention consent and enable one startup capture only after the phone workflow passes. Test camera closure/cancel/failure, known/unknown uncertainty, exact limited registration and false-block recovery.
5. Measure idle/active CPU, RAM and time to notification/review on the actual laptop. No continuous detector or additional local model is proposed; photo processing reuses the existing one-shot worker. Do not claim lightweight performance from architecture alone.

## Validation and limits

`check_local.py` checks the local name/summary changes and existing visitor, owner-profile, passkey, approval, native lifecycle, legacy-retirement and brain regressions using fake keys and temporary stores. See `validation.json` for actual results. It does not validate a phone service, real iPhone, live camera, provider reply style or resource performance.

Result: **171 checks passed**, zero failures/errors/skips. Six source files pass syntax/whitespace checks, and the usual launcher's desktop import succeeds without starting the app. Scoped tracked-file `git diff --check` passes; the workspace also contains earlier work and untracked files, so its overall diff is not this task's change set.

Phone pairing, retained-photo queue, mobile decisions, blocking and push are **planned only**. Tailscale account/device setup is unverified; its CLI was not found on the current PATH. Agent Reach's documented web reader failed DNS in the restricted shell, so official primary sources were checked with the web tool. Its update command was unavailable on PATH; nothing was installed or updated.

Encryption and passkeys cannot protect an already compromised unlocked laptop or phone from every attack. Do not describe this design as unhackable or a certified biometric security system.
