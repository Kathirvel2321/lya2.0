# Routine setup and review

The desktop tray menu **Routine drafts**, or the spoken/typed command **routine
drafts**, **show routine drafts**, **plan a routine** or **new routine**, opens the
manual setup window. These explicit commands use the existing desktop command
path; arbitrary conversational schedule requests are not parsed in this delivery.
The assistant's existing artwork, microphone, speech and normal answers remain
on their existing paths.

Choose a task, daily collection time, daily notification time, timezone, placement,
input window, missed-run grace, report expiry and notification filter. The review
updates immediately and lists what still needs connecting. Default templates are
13:00/13:05 for public news and 18:00/19:00 for private inbox proposals, in
Asia/Kolkata. These are editable proposals, not active schedules. Initial timezone
choices are Asia/Kolkata and Etc/UTC; the underlying compiler validates other IANA
zones and can reopen a saved supported-zone draft. It never assumes server time.

The notification time means the earliest request time, not guaranteed completion,
OS display or human receipt. An earlier clock time than collection means the next
day. A 18:00 input snapshot excludes messages arriving after 18:00, even if its
notification is due at 19:00. A second collection needs its own explicit policy.

**Save draft only** persists setup choices; reopening the window lists saved
drafts. Changing any choice changes the review fingerprint and requires a new
save. Identical saves reuse the existing draft. **Remove selected draft** removes
only that setup record. No provider messages, executable jobs or reports are
deleted. The store permits 32 drafts and a 128-page logical SQLite budget, then
fails visibly instead of silently discarding records. This is not an OS disk quota.

Draft metadata lives in `routine-drafts.sqlite` beside the existing public news
cache, using the existing LYA data-directory selection. It contains fixed task/
provider choices, timezone, schedule and bounded numeric/filter settings. The UI
has no message, credential, account-ID, importance-rule text or arbitrary command
field. Drafts are local metadata, not encrypted private reports or tamper-resistant
authorization. Unrelated schemas, symbolic links, unexpected fields, fingerprint
mismatches and invalid settings are rejected. Remove unused drafts manually; no
automatic expiry of these small setup records is added.

Public proposals compile to the existing structured `Job` contract, but retain
an unconnected owner and missing deployment/notification requirements. Private
server proposals retain `private_remote=false`; they deliberately fail executable
contract validation until real consent and a properly bound contract exist.
Requested account types identify setup needs, not supported or connected accounts.
Personal WhatsApp access is not inferred from a Business API. YouTube proposals
refer to comments, not a private follower-message inbox or verified follower status.

Outgoing messages remain draft only with a zero-send cap. This screen cannot add a
catalogue, approve recipients, grant private remote access, create owner proof,
enable a job, install a timer or connect a provider. The fingerprint identifies a
proposal; it is not an owner signature. Future activation must bind the actual
provider/account and every reviewed execution field to verified owner authority,
not reuse this draft as a grant. The existing hourly public news watcher is not
migrated or rescheduled. It yields automatic presentation while this review is
visible; the new dialog hides on sleep and closes on quit.

Next integration work remains real owner/delegation checks, one qualified public
server worker and notifier, then protected read-only private reporting with a
supported account. Importance rules, catalogue reply review and unknown-send
reconciliation follow before delegated sending. No live account or server is
accessed by draft setup. See the [master strategy](LYA_AUTOMATION_STRATEGY.md) and
[dated qualification](../../review/2026-10-22-routine-drafts/README.md).
