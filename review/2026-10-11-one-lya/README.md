# One LYA across laptop and phone - 2026-10-11

Owner correction: the full neural-schema design has not been implemented in the
laptop experience. Existing storage commands/components must not be described as
the completed design. Laptop and phone are interfaces to one logical LYA, with
the same authenticated person, memory contract, personality and retained knowledge.
Owner explicitly chose the laptop visual interface adapted to the phone screen.

Status: visual update implemented/deployed and checked over private HTTPS, without
service restart. Shared brain/memory design remains unfinished. Owner asked which
placement fits best; recommended NEW explicitly saved shared facts/preferences in
the separate encrypted Oracle store described below. This recommendation is not
owner approval to enable server-readable personal retention. Placement approval
remains pending. Full laptop/phone memory acceptance has not passed.

## Current source trace

| Area | Laptop | Phone | Remaining integration |
|---|---|---|---|
| Conversation | desktop/app.py BrainJob -> brain/workflow.py Brain.respond | cloud/mobile.py Connection.chat -> cloud/mobile_runtime.py infer | Two active dispatch/prompt paths; no shared conversation state |
| Memory | Explicit authorized save/recall/correct/forget, retention and project scopes in Brain.respond/brain.notes | Last two exchanges in session RAM only | Shared memory policy, identity mapping, transport and durable records |
| Owner tone | Verified-name placeholder substituted locally in native workflow | Generic system prompt; fresh proof does not enter prompt | One consistent style contract under authenticated identity |
| Authority | Native session, protected store and exact operation approvals | Separate HTTPS-RP paired passkey, public-chat scope, bounded fresh proof | Reviewed narrowly scoped shared-memory grants; same logical owner, device-specific sessions |
| Learning | Selected explicit notes/project foundations; generated skill activation remains blocked | No lasting facts or learned skills | Full selective learning/verification/retention experience is unfinished |

This is read-only source evidence, not live laptop memory acceptance. No real
profile/store was inspected and no real save/recall was attempted. The original
eight-layer neural-schema document is a proposal, extended by later decisions.
Do not claim either device has the completed design.

## Implemented visual scope

cloud/mobile.html now adapts the native dark glass result panel, typography/colors,
accent edge and circle with diamond/listening, crossing/thinking and wave/speaking
patterns. SVG/CSS only; states use the existing body data-state set by the
conversation script. Panel scrolls while the circle/status stay on screen.
Passkey, voice and authority are preserved. The phone is voice-first: after
authentication it starts listening automatically, submits after a bounded pause,
speaks the reply and resumes listening without a checkbox or Send/Stop/Talk
controls. Page hide/unload stops microphone tracks and closes audio contexts.
No assets, dependencies or new model introduced.

check_layout.py renders synthetic locked/listening/thinking/speaking states at
320/390/768 CSS pixels with a disposable headless Chrome profile, checks overflow,
state visibility and on-screen status, and saves phone-preview.png and
layout-validation.json. preview.html is synthetic, with production script removed.
Existing client harness uses fake DOM/media/network only. It checks the unchanged
conversation behavior; it does not establish actual iPhone visual acceptance.

Checks: existing check_client.js passed 18 simulated client scenarios. Final layout
run passed 12 rendered viewport/state scenarios, including long unbroken replies
and focus/scroll access to the open manual composer in speaking fixtures. An early
direct headless screenshot clipped because its outer window did not supply an exact
phone CSS viewport; the iframe fixture verified exact 320/390/768 widths and removed
that test limitation. The first local browser preview could not reach the sandbox
listener; local synthetic headless rendering succeeded outside the sandbox, with
disposable profiles removed. No actual user browser profile was used.

update_page.py applied only cloud/mobile.html after checking deployed/local script
and control IDs matched. A root-protected prior page permits rollback. page-update.json
records unchanged backend/inference hashes, unchanged service PID and auth-file inode,
nonce count and no-store/camera restrictions. live-network.json confirms private TLS,
exact served page/source match, security headers and unsigned session denial. No
runtime grant/default/expiry/voice/model/private-data migration or provider call.
Phone owner visual acceptance remains pending; refresh the existing page, no new
pairing required.

## Concrete shared-memory build boundary (proposed, not enabled)

Use one shared request/memory/style contract consumed by both device adapters.
Separate per-device sessions/cancellation remain necessary; never share one
mutable Brain instance between threads. A common code path alone is insufficient
unless both devices read/write the same authorized records and revisions.

1. Reuse owner-approved pairing to bind the laptop and HTTPS phone session to one
   opaque owner namespace. Existing credentials remain in place. Define narrow
   fresh, request-bound memory grants; a supplied name/role is never proof.
2. Shared selected memory includes explicit facts/preferences/decisions and verified
   lessons, with person/project/source/sensitivity/revision/retention. Preserve
   session/7-day/90-day/exact/permanent policies, correction, forgetting and
   unconfirmed candidates. No automatic raw transcript retention.
3. For laptop-off personal recall, a protected always-on memory home must be
   available to the phone. The proposed first scope is NEW explicitly saved
   facts/preferences in a separate encrypted Oracle store, with a protected
   server-side key. Oracle's operator/service can therefore decrypt those records.
   This is a trust choice, not client-only confidentiality. Existing laptop vault,
   private notes, photos, biometrics and credentials are not copied. No personal
   records enter ordinary public inference prompts; direct recall is deterministic.
4. Both adapters expose save/list/recall/correct/forget against those same revisions;
   preserve local-only records as explicitly unavailable when the laptop is off.
   Add bounded protected recovery and prove restore before valuable production use.
5. Reuse one owner style, with approved display-name/preference handling. Distinct
   hardware capabilities remain explicit: Windows actions need the laptop online.
   Measure pause/transcription/retrieval/inference/first-audio separately before
   changing accepted pause handling or Amy output.

The alternative retains client-only private keys on the laptop and leaves that
private recall unavailable while it is off, until a separately designed phone key
and recovery path exists. Do not solve this choice by silently repurposing the
public archive or copying the DPAPI key.

## End-to-end acceptance required for one LYA

- Save a harmless synthetic fact from laptop, restart, recall on phone; reverse the
  direction and confirm the same person/project record and revision.
- Correct on one device and verify the other immediately stops returning old values.
- Forget/expire/revoke on one device; neither device nor its cache can disclose it.
- Two people with identical labels remain isolated; unsigned/expired/replayed requests
  fail; request cancellation cannot publish a stale result or duplicate a write.
- Test server outage/conflicting revisions, duplicate retry and independent restore.
- Owner later checks the real harmless save/restart/recall/correct/forget journey,
  familiar tone and phone recall while laptop sleeps. Fake tests alone do not pass it.

Shared memory proposal is reviewable but not implemented/deployed. Owner placement
choice is needed before enabling new server-readable personal retention. No private
migration, new authentication grant, sensor capture or provider call in this work.
