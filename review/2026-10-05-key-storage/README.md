# Owner change rule and NVIDIA key location - 2026-10-05

The owner requests a single key-storage location and an explicit rule against
changing working features without an instruction. The owner also reports that
recent changes made previously good behavior appear broken; the exact affected
components have not been identified. No rollback or repair of those components
is authorized or attempted in this task.

Added the preserve-working-features rule to `AGENTS.md`: explicit feature-specific
owner permission before changes; explanations/status questions do not authorize
behavior changes; no opportunistic redesign/refactoring/default/model/startup
changes to adjacent working features. Necessary validation/continuity work stays
within the requested scope.

Save the NVIDIA key yourself in **Windows Credential Manager > Windows
Credentials > Add a generic credential**:

| Field | Value |
| --- | --- |
| Internet or network address | `LYA/NVIDIA_API_KEY` |
| User name | `LYA` |
| Password | Your NVIDIA API key |

New `security/api_credentials.py` reads only this named generic credential,
supports Windows password/ASCII encoding and optional terminal NUL, validates
the resulting key and suppresses private error payloads. Windows manages the
stored credential under the current account; this does not isolate it from other
software running as that same user.

`tools/start_nvidia_lya.py` uses the existing session environment key first, then
this credential, then the existing input prompt. Missing/unreadable credentials
retain that prompt. No save/export routine, plaintext key file, model change,
voice/interface/wake change or startup migration was added. The loaded process
environment is cleared on desktop exit/failure as before. Delete or edit the
entry through Credential Manager to change the saved key.

13 isolated credential/launcher checks passed using fake payloads, mocked Windows
credential reads and temporary bridge paths. Covered accepted encodings, missing
entry, denied access, malformed key, saved key bypassing the prompt, argument/file
exclusion, process cleanup and retained input behavior. Compilation and affected
tracked whitespace checks passed. No real credential store, owner key, microphone,
camera, model request or running desktop was accessed. Live owner-managed saved
key use remains pending. Previous design/voice acceptance is not inferred from
these checks. Enrollment/weather remain deferred.
