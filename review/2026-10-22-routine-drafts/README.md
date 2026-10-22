# Desktop routine draft review — 2026-10-22

Baseline: GitHub main `0e527a9f537046f0dc99f8f9508666150094d775`.
Owner authorized continuation and direct main publication. This step connects a
manual review interface to structured automation proposals; it does not activate
the automation engine or deploy to the owner's laptop/server.

Delivered `cloud/routine_drafts.py`, `desktop/routines.py`, small tray/command and
sleep/quit hooks in `desktop/app.py`, and one extra quiet-window check in
`desktop/news.py`. [Setup guide](../../docs/guides/LYA_ROUTINE_SETUP.md) describes
all fields and boundaries. Existing news schedules, voice, hearing, artwork,
private stores, owner enrollment and provider choices remain on existing paths.

The compiler binds every editable choice into a deterministic review fingerprint,
shows next-day notification/input cutoff/missed-run/DST behavior and missing
capabilities, and emits a structured proposal. Private server consent remains
unresolved, rather than being silently granted to satisfy contract validation.
Draft storage holds only fixed setup metadata, has row/logical-page limits and
detects incompatible or modified saved content. No arbitrary prompt, message,
account ID, credential, executable command or provider receipt is accepted.

The UI can review/save/reopen/remove drafts. It has no enable/send/approval control.
Recognized explicit desktop commands open the form; general natural-language
schedule extraction is pending. Saving never calls JobStore.enable, Runner,
provider APIs, a scheduler, a notifier, a model or an enrollment service. Public
news and private inbox choices remain proposals with explicit unmet requirements.

## Checks

[Runner](run_checks.py), [evidence](validation.json), [full log](validation.txt):
**243 isolated checks pass, zero failures/errors/skips**, consisting of 15 new
draft/compiler/store/actual-Qt cases and 228 previous selected regressions.
Source hashes and case IDs are recorded. This is a focused selection, not the
entire repository suite. It uses synthetic data, temporary storage, fake secrets,
offscreen PySide6, and the previously reviewed deny-all Linux DPAPI shim.

New cases cover schedule/scope fingerprint changes, rejected ambiguous/unbounded
settings, unresolved private cloud consent, provider requests without access
claims, next-day notification, duplicate saves, restart/reopen, capacity failures,
unrelated databases, tampering, symbolic links, deletion boundaries, error messages,
editing saved drafts, quiet presentation and dialog launcher reuse.

Rendered the actual Qt window at 760 × 760 using a disposable WhatsApp-unspecified
18:00/19:00 draft and inspected labels, scrolling, visible draft-only state and
save/remove/close controls. This is a synthetic offscreen utility window, not
Windows interaction, microphone-command acceptance or whole-assistant qualification.
No real message reads/sends, account connections, provider calls, real owner proof,
notification deliveries, OS timers, deployment or paid resource changes occurred.

## Remaining work

Supported account type/channel is unresolved; the owner has not yet answered the
personal-versus-Business question. Do not assume personal WhatsApp API support.
Real owner delegation, private storage/custody, semantic importance rules, server
worker isolation, cloud scheduling, phone delivery, catalogue review and uncertain
action reconciliation remain separate integration work. A draft fingerprint is
not authorization. Start production qualification with one public read-only job;
private collection and sending remain unavailable until their actual dependencies
are implemented and qualified.
