# One LYA, laptop and iPhone

Research and proposal, 2026-10-10. Owner explicitly requires the iPhone to keep answering when the laptop is asleep/off, with no LYA bulk storage on the iPhone. No implementation, deployment, account configuration or data migration is authorized by this feasibility discussion.

## Recommendation

Build a small LYA Home Screen web app on the iPhone, connected to an always-on shared LYA service on the existing Oracle VM through private HTTPS. Keep the native laptop interface and approved Windows execution on the laptop. Both devices use one logical assistant, owner identity, selected conversation and approved shared memory. Devices are clients and tool endpoints; neither has to mirror the other's full storage.

This extends the earlier laptop-hosted visitor-review plan: a laptop-only server cannot meet the new laptop-off requirement. The earlier narrow review credential must not silently gain general assistant, memory or device-control permissions. General mobile access needs a separate explicit capability grant and reviewed pairing flow.

See [architecture.mmd](architecture.mmd). Amber nodes are planned. Blue nodes already exist; connections to the shared service are planned. No claim of a deployed shared brain or measured performance.

## What lives where

| Location | Proposed responsibility | Storage boundary |
|---|---|---|
| iPhone | Microphone when requested, lightweight interface, streamed replies, approved photo review and supported Shortcuts | No model weights, LYA memory database, retained chats, visitor photos or recordings. Small browser/app resources, passkey, network-app data and short session state remain. |
| Oracle shared service | Paired-device identity, bounded model routing, conversation IDs, explicitly retained shared knowledge, action status and notifications | Only deliberately approved data classes; encrypted persistent state, quotas, separate restricted account, protected keys and tested backup/recovery. Existing public archive remains public-only. |
| Laptop | Existing LYA voice/UI, approved Windows actions, local sensors and existing protected private vault | Existing private data/biometrics/keys stay in place. Small bounded working cache; no unrequested replacement of accepted behavior. |

Literal zero phone storage is not feasible. A passkey, installed private-network client and Home Screen app use space, and browsers manage their own resources. The achievable requirement is **no deliberate persistent LYA content or model storage on iPhone**, with private content only transiently displayed/played. Do not claim guaranteed zero disk traces, screenshot prevention or secure RAM erasure. WebKit documents local storage, caches and cookies as separate mechanisms. [WebKit storage policy](https://webkit.org/blog/14403/updates-to-storage-policy/)

## Mobile experience and iOS limits

Use Safari's Add to Home Screen for a focused LYA interface matching the accepted visual design. Start with tap-to-talk and visible listening/thinking/speaking states, plus Stop. A selected server-side speech path receives audio transiently; provider keys never go to browser JavaScript. Ordinary cloud transcription remains external processing and cannot be relabeled private merely because no recording is retained. Preserve the laptop's accepted hearing/voice; mobile audio needs its own adapter and live acceptance.

Apple supports Home Screen web apps and Web Push on supported iPhones, including user-requested notification permission without Apple Developer Program enrollment. Push delivery is advisory, not a guarantee or an authorization method. [Apple Home Screen apps](https://support.apple.com/en-lamr/guide/iphone/iphea86e5236/ios), [WebKit Web Push](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)

Conversation, research, drafting, approved shared-memory retrieval and visitor decisions are feasible targets. They are not already working mobile features. For phone actions, use explicitly supported Shortcuts/Siri workflows; App Intents is the later native integration route if justified. The web app cannot automatically create arbitrary system integrations or control every installed app. Apple sandboxes apps and restricts background execution. Do not promise an always-listening custom wake word while locked, universal phone control or full Windows capability parity. [Apple sandboxing](https://support.apple.com/en-euro/guide/security/sec15bfe098e/web), [Siri Shortcuts](https://support.apple.com/en-am/guide/shortcuts/apd07c25bb38/ios), [App Intents](https://developer.apple.com/documentation/AppIntents)

A native Swift app is not the first choice under the current Windows/zero-subscription constraints. Apple's free Personal Team provisioning expires after seven days and requires rebuilding/reinstalling; ordinary development uses Xcode on Mac. The Home Screen approach avoids starting with that distribution burden. [Apple developer account limitations](https://developer.apple.com/help/account/basics/about-your-developer-account)

## Connection and owner protection

Use Tailscale on the iPhone, laptop and Oracle host, with Serve on the Oracle host exposing only the new loopback LYA endpoint over private HTTPS. Disable public Funnel, directory serving, broad ACL access and unnecessary network features. Tailscale Personal currently offers free noncommercial use; verify the actual account before setup. [Private Serve](https://tailscale.com/docs/features/tailscale-serve), [Tailscale plan](https://tailscale.com/pricing)

Reuse standard WebAuthn/FIDO2 verification with a new credential for the exact shared HTTPS RP/origin. Bind the new service/device grant to current owner proof through explicit one-use pairing. Do not copy the laptop's SSH private key, DPAPI key or full database to the phone; do not treat a QR, VPN membership, face match or identity header as admin proof. Private actions still require fresh request-bound owner approval. The existing localhost credential stays unchanged. Narrow visitor review and general conversation permissions stay distinct.

Use short Secure/HttpOnly sessions, Origin/Host/CSRF validation, no-store private responses, bounded uploads, rate limits, revocation and audit metadata without conversation/photo contents. No private content in notifications, URLs, analytics, IndexedDB or service-worker caches. Tailscale protects transport; it does not replace application authorization or make a compromised cloud host harmless.

## A genuinely shared brain

Use server-assigned conversation IDs, owner-scoped retrieval, revisions and idempotent operation IDs. The phone can resume a deliberately selected shared conversation on the laptop without downloading all history. Temporary turns expire; permanent memory requires the existing deliberate retention strategy. Do not infer permission to save every utterance or upload old history. Different people remain isolated.

Keep per-device sessions and independent worker state; the existing Brain explicitly must not be shared across threads. One logical LYA means shared controlled state, not one mutable Brain object reused by two callers. Cancel/Stop is scoped to the request/device; stale replies cannot overwrite a newer turn. Clearly identify the device targeted by an action.

The laptop agent initiates an authenticated outbound connection to fetch only allowlisted, approved actions. No generic remote shell and no arbitrary model-generated execution. If the laptop is off, the phone can still chat through the server, but laptop files, camera and Windows actions are unavailable. A queued sensitive action must expire and require fresh approval on reconnect; never silently execute it hours later.

## Confidential memory and photos

Current protected memory, face/voice templates and visitor material are local; the Oracle archive is intentionally public-only. Existing inference is not a shared private vault. Do not move any of these materials as part of connectivity setup.

For full private-memory access while the laptop is off, add a separately reviewed encrypted cloud vault, explicit data-class migration, key/recovery policy and restore test. Encryption at rest does not hide plaintext from a server that decrypts it to reason; that is a separate trust decision. Until that work passes, keep local confidential queries locked/unavailable when the laptop is offline rather than using public inference as fallback. Shared public/nonconfidential knowledge can be the first cloud memory class.

Likewise, laptop-off visitor photo review requires an explicitly approved encrypted remote-photo relay; private laptop-to-phone viewing alone cannot provide it. The earlier promise that photos remain local still applies. Do not silently upload photos to achieve always-on availability. No continuous camera or additional photo collection is proposed here.

## Smoothness and free-service limits

Keep the private HTTPS connection reusable, stream model text and bounded speech playback when the selected provider path supports it, and return actual listening/transcribing/error states promptly. No large framework, local mobile model or polling loop is necessary. Reuse existing working provider choices through a constrained server adapter, with hard quotas and no paid fallback; do not promise unlimited free speech/model usage.

Measure speech end to transcript, first answer/audio, interruption delay, reconnect behavior and idle resource use separately on Wi-Fi and cellular. Shared hosting removes laptop dependence but does not guarantee faster speech recognition; provider queueing, network quality and voice playback remain latency sources.

The existing Oracle VM is a candidate, not a newly verified deployment. Check current resource headroom, free allowances and isolation without changing existing inference/archive services. Oracle may reclaim idle Always Free compute, so free hosting cannot support a professional uptime guarantee; add bounded health/recovery procedures, real backup/restore and honest outage behavior, not artificial CPU load. [Oracle Always Free reclamation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)

## Order to build

1. Verify capacity and free eligibility; implement isolated owner-approved shared-service pairing and capability grants with synthetic identities. Preserve the current desktop proof and working routes.
2. Build the small phone interface and shared public conversation path; test text first, then microphone/transcription, reply playback, Stop and reconnect on the actual iPhone.
3. Connect the existing native laptop through a narrow adapter. Test selected conversation handoff, user separation, conflicting memory revisions and duplicate-action prevention.
4. Add explicitly retained shared nonconfidential memory and notifications. Prove phone conversation works with laptop off, and laptop actions report unavailable safely.
5. Separately design/approve private vault migration and encrypted photo relay if laptop-off access to those materials is required. Then test exact decisions, revocation, restore and deletion behavior before activation.

No runtime code, working feature, enrollment, private record, device setting or server was changed during this research. Sources were read through the official web tool after Agent Reach's documented Jina reader failed DNS. Agent Reach executable/update check was unavailable in the preceding same-session research; no installation/update attempted. No live latency, iPhone version, Oracle capacity, billing or phone deployment qualification is claimed.
