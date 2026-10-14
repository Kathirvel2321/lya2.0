# Foundation-first acceptance restart — 2026-09-27

Current direction: the owner clarified that hands-free speech is the primary interface and typing is a public-place fallback. The first acceptance step is now [wake, listen and spoken reply](../2026-09-27-hands-free-voice/README.md). The typed baseline below remains supporting evidence, not the next owner task.

Owner requested one tested and confirmed step before advancing. Restart acceptance from the foundation, preserving existing implementation and data.

## Step 1: desktop lifecycle

Status: **isolated-tested; current visible desktop acceptance NOT RUN**. No source fix was indicated by these checks.

| Fresh check | Result |
| --- | --- |
| `.venv-ui/Scripts/python.exe -B test_foundations.py` | 14 passed |
| `python -B -m unittest desktop.check_ui.InterfaceChecks` | 16 passed |
| Five selected `desktop.check_experience.ExperienceChecks` tests | 5 passed |

Selected tests: `test_intro_dock_input_answer_and_chat`, `test_private_denial_and_cancelled_reply`, `test_typing_on_finished_compact_answer_starts_next_input`, `test_stop_during_pending_worker_hides_late_answer`, `test_quit_waits_for_recovery_cancellation_without_blocking`.

Each suite ran separately using `.venv-ui/Scripts/python.exe`. Qt used `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH=<project>/desktop;<project>`. Scripts were inspected first. No preview-writing entry point was run. These checks cover selected safety rules, temporary encrypted storage, base UI and compact desktop behavior; they do not execute the visible launcher/main startup. No real sensors, protected store contents, Windows proof, cloud call or enrollment were exercised.

## Owner test for this step

From the project folder in PowerShell:

```powershell
.\launch-lya.cmd --no-voice --skip-setup --reduced-motion
```

Existing flags disable microphone startup and bypass setup for this run without granting identity or changing saved settings. Speech output may still play. Default voice/setup startup remains a later test.

1. Wait for the intro; click the small circle. Input must open.
2. Type `voice off`, then `time`. A readable current time must appear.
3. Type `who am i`. It must report guest/unverified.
4. Type `show memories`. It must stay locked.
5. Type `stop`. The answer panel must close and stay closed.
6. Reopen the panel and type `time`. It must still respond.
7. Quit from the LYA tray menu and repeat the launch. Restart must work.

Report the first failed item and visible error, or confirm all seven passed. Check sleep/tray recovery within this same lifecycle step afterward. Owner confirmation is part of the owner's requested workflow. Do not advance while this gate remains open.

## Higher work with missing lower prerequisites

| Existing higher work | Missing prerequisite and reason |
| --- | --- |
| Voice, captions and activation screens | Current visible desktop acceptance; offscreen object tests and dated launches do not prove today's launcher |
| Provider routing and council | T02 independent live backup acceptance; recorded candidates missed latency/quality gates |
| Private memory, tasks and registration | T04 real identity/session/exact phone-approval journey; fake identities pass but live integration is unproven and recorded admin ambiguity remains unresolved |
| Voice-first interaction | Real wake -> command -> answer -> stop and listening acceptance; injected signals do not prove microphone recognition or naturalness |
| Recognition and device execution | Accepted authorization, required recognition components and bounded executor; presence detection is not identity |

The whole-project report overstates end-to-end completion. Its helper-only Windows diagnosis is also stale: `desktop/registration.py::windows_verify` and `desktop/activation.py` call `security/windows_consent.py` in-process. That path still needs live proof; an unsigned legacy helper alone cannot establish its failure. No protected records were inspected to recheck historical ambiguity.

After step 1 is owner-confirmed, resume the existing roadmap at T02, one acceptance gate at a time. Higher code can remain present without being declared accepted. Repair observed failures at their shared cause; do not rewrite working code speculatively.
