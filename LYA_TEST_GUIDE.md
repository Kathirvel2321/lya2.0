# How to test LYA now

## Window controls update (2026-09-17)

Restart `launch-lya.cmd`. The circle expands into a centered crystal, rotates
once, greets, and returns. Try `stay as a crystal` and `become a circle`.
Ordinary replies contain answer text only; click the circle to type again.
Use `open chat box`, `make it full screen`, `restore chat`, and `close chat`.
Try `show three files`: each approved document gets an independent movable
window. Move the orb and verify those windows stay put. Drag chat by its top edge.
Full behavior and limitations: `desktop/qa/2026-09-17-window-controls/README.md`.
The older instructions below record previous milestones.

## Updated compact experience (2026-09-17)

`launch-lya.cmd` shows a bottom-center guest greeting and crystal for 2.2 seconds,
then gently transforms it into a circle over 1.1 seconds.
Click the circle for the single-line input; type `time` for a typewriter response card
or `open chat` for the expanded workspace. `stop`/Escape closes it. The baked model
artwork is now selected by default per the owner's revised request; use
`--original-art --reduced-motion` for the conservative alternative.
Check that cards stay above the circle, text appears gradually, and ordinary
answers have no extra heading. A question still uses the configured brain;
these UI checks alone do not verify live provider availability or battery life.

`check-t01.cmd` now runs the five compact-experience checks too: 62 checks in total.
Its final message is `PASS: LYA offline baseline and compact interface checks completed.`
The original T01 instructions and 57-check evidence below are historical.

Updated: 2026-09-16. This guide tests the completed T01 baseline. It does not
prove that voice, face recognition, private memory, backup providers or mobile
access are ready.

## 1. Run the safe automatic check

Close any LYA window you are currently using, open PowerShell in the project
folder, then run:

```powershell
.\check-t01.cmd
```

Expected final line:

```text
PASS: T01 offline baseline completed - 57 checks passed.
```

These checks use fake providers, temporary encrypted storage and an offscreen Qt
interface. They do not call a live AI provider, camera or microphone. If a test
fails, copy from the first `FAIL`/`ERROR` line through the bottom of the output;
do not hide the failure by rerunning only the passing suites.

## 2. Start the visible interface

Use the conservative visual mode for this test:

```powershell
.\launch-lya.cmd --original-art --reduced-motion
```

Pass if the native crystal and compact message panel appear without a browser.
If nothing appears, run this diagnostic command and keep its error text:

```powershell
.\.venv-ui\Scripts\python.exe -B .\desktop\app.py --show-panel --original-art --reduced-motion
```

## 3. Test the working commands

Enter each command separately and compare the result:

| Command | Pass condition |
| --- | --- |
| `help` | A list of available LYA commands appears. |
| `status` | A System Readiness card appears. It must not claim pending features work. |
| `time` | The current local time appears. |
| `show files` | Four approved project-document rows appear. |
| `brain help` | Brain and memory command syntax appears. |
| `who am i` | It says `Guest / unverified`; color selection must not change this. |
| `brain status` | It describes the connected workflow and missing real integrations. |
| `brain demo` | It clearly says the workflow is synthetic. It must not unlock real data. |
| `show memories` | It is blocked because real identity and phone approval are not connected. |
| `stop` | The panel closes and a late result does not reopen it. |
| `sleep` | Temporary context is cleared; the orb hides when tray support is available. |
| `quit` or Ctrl+Q | LYA exits. |

`show memories` being blocked is a **pass** today. Allowing it for the guest would
be a serious failure.

## 4. What currently works

- Native orb and glass panel startup.
- Local help, readiness, time and allowlisted project-document display.
- Guest identity reporting and denial of private memory.
- Brain help/status and the labelled synthetic brain demonstration.
- Background work, panel cancellation and stale-result suppression.
- Stop, sleep and Quit paths.
- Public-text Groq through Oracle passed an earlier live check on 2026-09-14,
  but T01 did not make another live request and model accuracy remains unresolved.

## 5. What is not ready yet

- A dependable independent AI provider backup (T02, next).
- Verified research sources and answer-quality gates (T03).
- Real trusted identity/phone approval and private-memory journey (T04-T05).
- Actual offline microphone wake acceptance, consented face enrollment, recovery,
  iPhone access, bounded action execution and reusable generated skills.

Do not test pending features using real faces, private notes or credentials. Their
fixture/device procedures are defined in `LYA_IMPLEMENTATION_CHECKLIST.md`.

## Visual workflow

Mermaid source: [`diagrams/14-t01-working-and-test.mmd`](diagrams/14-t01-working-and-test.mmd).
Directly viewable companions: `diagrams/14-t01-working-and-test.svg` and `.png`.

Legend: green = verified in T01, amber = passed earlier but not rechecked in T01,
blue = next task, gray dashed = planned/pending, purple = your test steps, red = failure.

## Report a failure

Include:

1. The command you entered.
2. What you expected from the table.
3. What actually appeared.
4. The first failing automatic-test line and the final summary.
5. Whether the problem happened before or after the orb appeared.

Never paste API keys, `.env` contents, SSH private keys, faces or private notes.
