# Desktop technology watcher and opening catch-up — 2026-10-16

The owner explicitly requested implementing proactive AI/technology updates after
reviewing the design. Source baseline is GitHub main
`d9bcc0f596f25293e6ae160554402cbb0f5025ab`. Direct main publication remains authorized;
this is not a laptop/Oracle deployment or change to another chat's interface work.

## Implemented

- `cloud/news_sources.py`: fixed official OpenAI RSS, Gemini release-note and Anthropic
  listing adapters. Bounded UTF-8/XML/HTML parsing; DTD/entity/depth/element guards,
  official-host URL checks, explicit dates and date-only precision. Preview text is
  plain untrusted publisher data. Undated/changed-format data produces coverage gaps.
- `cloud/tech_news.py`: public SQLite catalogue, hourly atomic reservation, seven-day
  catch-up, bounded retention, seen/notification-request distinction and persistent
  pause. Source rounds use no LLM, search allowance, keys or paid service. The catalogue
  is separate from private memory; relevance is a conservative topic hint, not a
  semantic quality/capability/entitlement assessment.
- `desktop/news.py`: one independent daemon worker, queued generation-checked Qt
  delivery, a non-modal plain-text brief and pause/check controls. Startup/opening
  catches up on unseen items; later discoveries can request one tray message per
  hour. Unsupported tray delivery leaves the item unread for the in-app brief.
  No automatic voice, browser opening or chat-history mutation.
- `desktop/app.py`: minimal menu, command, opening, sleep and quit hooks.
  `desktop/experience.py`: one wake hook because that subclass overrides base wake.
  Accepted voice/hearing, artwork, chat, startup registration and permissions remain.
- `cloud/web_reader.py`: an optional MIME list for the internal bounded GET method;
  news admits XML explicitly, while existing public page-reader defaults are retained.

[Maintained guide](../../docs/guides/LYA_TECHNOLOGY_UPDATES.md) records exact behavior,
source limitations, budgets, controls and target-host acceptance. The monitor is
installed as source by this commit and becomes active when that desktop source is
actually run; no runtime setting, installed service or real data store was modified.

## Checks and evidence

[Final result](validation-published.json), [complete log](validation-published.txt),
[reproducible runner](run_checks.py): **187 passed, zero failures/errors/skips**.
The selection contains 42 new cases plus the prior 145 selected regressions.
Counts overlap prior runs and are not added together. The new cases include source
formats, qualifiers/date precision, official URLs, missing dates, hostile XML,
partial/offline coverage, four-day catch-up, atomic concurrent reservation, rollback,
restart deduplication, pause/cancel, retention, read-versus-notification state,
quiet delivery, actual offscreen Qt widgets, worker limits and stale queued results.

The first `validation` run had one **test fixture** error: a loop deleted its fake
owner's required `brain_busy` attribute. The fixture now restores that boolean;
no production delivery rule/assertion was weakened. `validation-fixed` passed all
187. Final evidence additionally includes missing-link rejection, bounded title
handling and generation invalidation when quiet-state suppression is observed.
The final publication run also executes the actual desktop command method against
a fake owner to verify news questions with speech-style question/exclamation punctuation.

Synthetic Qt inspection rendered a real offscreen brief with a fictional launch;
plain-text formatting, visible source/date/limitations and controls were inspected.
Qt's offscreen plugin reports unsupported raising/size-hint operations; this does
not qualify native Windows placement or notifications. Test-only PySide6 Essentials
6.8.3 and shiboken6 6.8.3 were installed in an isolated scratch dependency directory.
The project's runtime dependency/configuration was not changed. The Linux import-only
DPAPI shim refuses operations; disposable Fernet/passkey fixtures qualify no real
Windows identity or private store.

[Public access probe](public-access-probe.json) records three failed direct stdlib
URL probes from this environment (no model call, account or credentials). The web
lookup renderer rejected RSS/XML MIME types; Google/Anthropic HTML documentation was
read only through that lookup. No successful live LYA source round is claimed.
Source-hash/compile inspection accompanies the final evidence. No archive discovery,
full repository tests, actual owner enrollment or production store was run.

## Limits and next acceptance

The watcher verifies publisher listings/feeds and dates, not each linked article,
current pricing/access, benchmark rank, independent capability or overall market
coverage. Publisher previews are explicitly marked potentially shortened; topic
relevance is labelled possible. It does not use the owner's Gemini Pro account,
upgrade LYA's model, auto-install a new tool or claim everyone is adopting it.

Endpoint access, current raw HTML contracts, OS toast visibility/focus policy,
Windows/whole-assistant integration, startup/setup behavior on a real device and
network/CPU/battery costs require target-host checks. Hourly source attempts are
not instant push; a paused, private, sleeping or closed app can discover later.
Date-only entries are never translated into an exact release time. Source changes,
robots failures, unsupported redirects/compression and a missed seven-day window
can all reduce coverage. Notifications are requested, not acknowledged by the OS.
There is no mobile/offline-process notification service. Physical disk/journal use
and DNS-operation duration are not hard OS resource ceilings.

Next qualify source access and native desktop behavior on the target laptop, using
public fixtures first, then review actual current announcements and measure resource
impact. A runtime deployment and its rollback remain separate from this main commit.
