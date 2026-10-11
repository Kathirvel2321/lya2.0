# Mobile voice, repeated sign-in and Face ID feasibility — 2026-10-10

The owner reports that the iPhone client cannot speak and repeatedly asks for
passkeys, and asks whether a spoken secret word could request a face scan and
identify the admin. This is an investigation/recommendation, not authorization
to replace the accepted authentication policy or silently extend its duration.

## Current implementation findings

- `cloud/mobile.html` has text submission only, no microphone capture or speech
  playback. `cloud/mobile.py` explicitly disables microphone/camera permissions.
  Mobile voice was deferred in the first connection stage, not implemented.
- Server sessions and the cookie expire after 900 seconds. A session permits at
  most 50 chat request IDs; logout, revocation, server restart and session eviction
  can also require a new sign-in. Expiry is enforced server-side.
- The page unconditionally calls `locked()` on load and has no server session
  restore endpoint. Reopening/reloading therefore presents sign-in even if its
  existing cookie could still identify a valid session. This is a source-proven
  contributor; the exact timing/cause of each reported prompt is unverified.
- Laptop owner sign-in, exact laptop connection approval, and the new HTTPS-RP
  service passkey are separate ceremonies. First-time service pairing also
  requires a signed confirmation. The current phone session grants public chat,
  not confidential laptop authority.

## Recommended sequence

1. Restore only an already valid, unrevoked server session when the page reopens;
   keep its existing expiry and server authorization checks. Do not store a
   bearer token in localStorage or make the client decide that it is an owner.
   Change session duration only following an explicit owner policy choice.
2. Add bounded, explicitly activated foreground phone voice input/output with
   Stop and visible states. Reuse the accepted hosted recognition approach where
   the server credential/quota path is actually available and verified. Provider
   keys stay on the server. Explain ordinary audio cloud processing before
   capture; public voice must never become a confidential capture route by
   recognizing a phrase. Browser voice support and round-trip quality require
   real iPhone tests, not feature detection alone.
3. Offer a normal phrase such as `LYA, owner mode` as a request to start owner
   verification while the interface is open and explicitly listening. The phrase
   is not a password or identity proof. A supported tap fallback invokes the
   standard passkey UI; Apple may use Face ID, Touch ID or device passcode.
4. Verify the fresh exact-origin challenge and registered owner credential on the
   server, then grant only a defined, expiring scope. Confidential actions still
   need fresh exact-request proof through a separately implemented authority
   path. Phone chat login must not silently become full Windows/vault authority.

The existing passkey is already compatible with Face ID on supported iPhones;
there is no need to collect a second camera face profile for this purpose. Apple
does not expose Face ID templates to LYA. Standard website passkey verification
cannot promise that Face ID specifically was used rather than an allowed device
verification method. A copied webcam image or spoken word must not unlock admin.

Safari may require a user gesture for a passkey prompt. Fully automatic spoken
invocation, background/locked-screen listening and scanning are not promised.
Native iOS biometric-only policy is a different integration and is not selected
or built here. No enrollment, secret phrase, biometric recording, authentication
timeout, deployed service or permission was changed in this investigation.

## Primary sources

- [Apple: use passkeys on iPhone](https://support.apple.com/guide/iphone/iphf538ea8d0/ios)
  — Face ID/Touch ID sign-in and device passcode option; passkeys stored by the
  device/password manager rather than a website-held password.
- [Apple: passkey security](https://support.apple.com/en-ie/102195)
  — signed challenge and public/private key separation.
- [Apple: Face ID privacy](https://support.apple.com/en-ca/102381)
  — face data stays protected on the device; apps receive authentication outcome.
- [WebKit: Face ID and Touch ID for the web](https://webkit.org/blog/11312/meet-face-id-and-touch-id-for-the-web/)
  and [user activation](https://webkit.org/blog/13862/the-user-activation-api/)
  — system authentication and gesture restrictions; actual iPhone behavior must
  be verified before promising a voice-only flow.
- [WebKit: Safari speech support](https://webkit.org/blog/11648/new-webkit-features-in-safari-14-1/)
  — platform speech APIs exist, but this does not establish current LYA voice
  integration, reliability or privacy suitability.

Agent Reach web-reader instructions were applied; its Jina request failed DNS.
Official web search/open fallback supplied the primary sources above. No broad
multi-platform research or dependency installation was necessary. Checks were
read-only source tracing and research; no new runtime tests or live sensor/model
calls were needed for this recommendation-only task.
