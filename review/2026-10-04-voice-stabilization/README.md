# Structured hearing and conversation stabilization — 2026-10-04

Owner now reports the current speaking voice is clean and the replies sound good.
Preserve that output. The remaining objective is accurate hearing followed by
natural conversation timing. Earlier complaints about output quality are dated
evidence; they do not override this current owner report.

## Order of work and acceptance

| Stage | Required evidence | Current status |
| --- | --- | --- |
| Incoming speech | Intended input is selected; ordinary soft speech is intelligible; background sound is assessed separately | Unresolved. Earlier owner playback report was clear, but that does not prove a hardware defect or eliminate recognition failure |
| Recognized words | Complete short and longer questions match what the owner actually said, including internal pauses; uncertain input is declined | Failed/pending on tested local candidates; no replacement promoted |
| Conversation turns | Continue through an internal pause; reply after the turn ends; spoken interruption stops output/pending work; follow-up remains usable | Existing isolated pause/cancellation checks pass; real owner interruption and timing remain unaccepted |
| Speaking output | Owner hears clean understandable replies | Owner reports satisfactory now; no voice replacement needed |

Complete each input stage before interpreting a later-stage failure or starting
another model/device experiment. Keep the same question/input conditions for a
comparison and change one variable at a time. No hardware purchase, provider
change, new model download or new recording was made in this clarification task.
The prior Groq privacy/free-account choice remains unanswered and is deferred;
it does not authorize any audio upload. No new live test is requested here.

Headphone speaker quality and microphone capture quality are different stages.
Poor microphone capture may contribute; it is not established by the current
evidence. Sound level alone cannot distinguish the owner from background people
or prove that words are understandable. No claim of pronunciation failure, target
speaker isolation, human-level turn understanding or guaranteed noisy-room
recognition is made.

## Concrete repair

The existing microphone self-test incorrectly said the microphone was “hearing
you” and ruled out a misselected input merely because sound crossed a loudness
gate. Background noise can pass that gate. Corrected `audio/voice.py` and
`desktop/app.py`: the result now says **Sound reaches the microphone** and clearly
separates incoming sound from voice clarity and recognized words. The existing
verdict identifier remains compatible. Updated the existing UI assertion and
recorded the owner's current priorities in `LYA_VISION.md`.

Existing baseline: 2.5-second quiet gap, 120-second bounded capture, incomplete
turn rejection, local speech activity and stop/cancellation paths. These settings
are implemented; they do not prove the owner turn ended, and they are not a
verified optimum. Natural pause tuning follows faithful recognition rather than
compensating for it with arbitrary timing changes.

Checks: `test_voice` **37 passed, one intentional online skip**; isolated desktop
checks **52 passed**, using temporary stores, fake secrets and disabled live I/O.
No microphone/speaker/network/private-store operation was performed by those
checks. Read input metadata only to inspect the selection path; private runtime
details are excluded from this artifact. Formatting check passed.

Correction to the preceding route-audit ledger: the attempt to close the
task-launched Windows Voice Access control was denied by Windows. The command
printed a success line despite that error; closure was not achieved. The process
was still observed during this clarification. Windows automation initialization
also failed earlier, so the owner must close that trial window. No permission,
privacy or security setting was changed to bypass this limitation.
