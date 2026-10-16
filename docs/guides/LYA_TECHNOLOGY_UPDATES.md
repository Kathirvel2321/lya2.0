# Proactive technology updates

Implemented source: 2026-10-16. This adds desktop catch-up and periodic official-source
checks. Publishing this source is separate from installing it on the owner's laptop.

## Using it

When the updated desktop runs, it starts checking after the initial startup period
and when quiet enough. The first recent, unseen results can open a separate,
non-modal Technology updates window without changing chat or speaking over the user.
Later discoveries request a desktop tray notification. Open **Technology updates**
from LYA's tray menu, or say/type **technology updates**, **AI news**, or
**any news about technology updates**. The same command path accepts voice text;
no voice provider, hearing behavior or speech configuration was changed.

The window shows the publisher's title, announcement date, bounded preview where
available, possible relevance and official link. The links are plain selectable
text; copy them to review in a browser. It does not automatically open a browser,
click a signup, install software, replace LYA's model or connect the Gemini account.
The separate utility window uses native Qt controls; the existing crystal/chat
artwork and layout are preserved.

Use its checkbox to pause or resume background checking. The preference persists.
`LYA_TECH_NEWS_ENABLED=0` disables automatic checking and delivery; the manually
opened cached brief remains available. The Check updates button respects the same
hourly limit; repeated clicks and app restarts do not bypass it. This feature runs
only while the desktop process runs. It adds no startup registration, OS scheduled
task, Oracle service, mobile push or ChatGPT automation. When LYA next opens, its
seven-day source window can catch releases from days earlier. Older history is not
an exhaustive archive.

## Sources and meaning of verification

The initial fixed watchlist contains:

| Publisher | Watched source | Format |
| --- | --- | --- |
| OpenAI | `https://openai.com/news/rss.xml` | RSS / Atom parser |
| Google Gemini | `https://gemini.google/release-notes/` | Dated H2 sections and H3 update titles |
| Anthropic | `https://www.anthropic.com/news` | Dated article links in the news listing |

These are selected official channels, not the whole technology market. The monitor
checks the publisher feed/listing, not every linked article or pricing page.
External hosts and undated/malformed entries are rejected. It distinguishes exact
publisher timestamps from date-only entries; the latter never become a claim that
something launched an hour ago. An updated timestamp alone is not a launch date.

Publisher previews can be shortened. Capability claims in them remain publisher
claims. Access, pricing, account entitlement and performance are explicitly marked
as not independently checked. Possible relevance is a keyword-based hint for coding,
creative/voice tools or AI models, not a quality score. The monitor does not assert
industry ranking, mass adoption, superiority or fit from a marketing claim. Use the
existing [research route](LYA_WEB_RESEARCH.md) for a specific launch's current terms
and evidence before recommending a change. That follow-up is not automatic here.

A source that fails, changes format or exceeds a limit is shown as unavailable.
An empty cache says it has no matching items; it never proves no new model exists.
Duplicates use publisher/article URL identity; Gemini's shared release-notes URL
also uses date and title to separate updates. Gemini heading edits can therefore
produce a new identity. Cross-publisher reposts are not universally deduplicated.

## Resource and interruption boundaries

- A main-thread timer checks scheduling once per minute. Persisted reservations
  admit at most one source round per hour, including failed or cancelled rounds.
  Wall-clock rollback delays a round rather than causing repeated traffic.
- One separate daemon worker runs at a time, outside the chat worker. Each round
  attempts at most three sources and six HTTP requests (robots plus source). Each
  source body has a 1 MiB cap and robots text a 32 KiB cap. No AI model, search API,
  provider key, paid fallback, camera or microphone is invoked by this monitor.
- Retrieval has a twenty-second cooperative budget and the existing bounded socket
  calls. OS DNS resolution/blocking stages cannot be interrupted precisely at that
  deadline. Already-started I/O may finish after cancellation; later stages/results
  check cancellation. Shutdown does not wait for the daemon.
- Public HTTPS uses the existing global-address validation, pinned destination and
  TLS hostname checks. Robots policy is checked before each source. Redirects,
  compression, authenticated pages and JavaScript are unsupported; they become
  coverage gaps. The reader's new MIME argument admits XML only when this caller
  requests it; ordinary page research retains its prior default MIME policy.
- Delivery/check initiation yields to busy chat, active speech/listening, private
  mode, sleep, visible setup/review/camera windows and quitting. A generation drops
  queued results after a user-command interruption, pause, sleep or shutdown. Sleep
  resumes on explicit desktop opening/wake. No foreground-app inspection is used.
- The cached public catalogue is `technology-news.sqlite` in the existing LYA data
  directory, separate from private memory. It stores public excerpts, dates, coverage,
  seen/notification-request state, the pause preference and polling reservation.
  There are no conversation contents, queries, credentials, sensors or Gemini
  subscription details. Logical SQLite pages are capped at 256, item rows at 256,
  display at twelve; old items expire and the brief window is seven days. This is
  not a filesystem-wide quota, secure erase or private-memory store.

A requested tray notification is not proof Windows displayed it. The OS can suppress
it through settings or focus modes; unsupported tray messages leave the item for the
in-app catch-up. Items are marked seen when included in an opened brief. Notification
request state and seen state are distinct and survive restarts. There is no guaranteed
instant alert, global news coverage or measured battery-life claim.

## Qualification and release

[187 selected checks](../../review/2026-10-16-tech-news/validation-published.json) pass:
42 new parsing/cache/monitor/Qt cases plus 145 previous selected regressions.
Tests use actual PySide6 6.8.3 offscreen widgets, injected public feeds/transports,
fake credentials and temporary stores. They do not launch the full assistant,
open sensors, use real keys or qualify Windows notifications. The synthetic brief
was rendered and visually inspected. The [report](../../review/2026-10-16-tech-news/README.md)
records the initial fixture error and its corrected rerun.

Direct public-source probes from this workspace failed; feed/XML content was also
not supported by the web lookup renderer. Current endpoint access/parser contracts
are therefore not live-qualified by these tests. On the target laptop, qualify the
three sources and partial-failure behavior, opening catch-up, private/sleep cancellation,
real OS notification suppression, network/CPU/battery usage and rollback. No host
installation, configuration change or deployment was performed by this task.

Primary implementation references checked 2026-10-16:

- [Gemini release-note structure and publisher dates](https://gemini.google/release-notes/)
- [Anthropic news listing](https://www.anthropic.com/news)
- [Qt tray-message delivery limitations](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html)
- [Python XML security](https://docs.python.org/3.12/library/xml.html)
