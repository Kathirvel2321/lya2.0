# Provider key location - updated 2026-10-06

LYA reads its NVIDIA API key from the same project-root `.env` file used by the
other provider configuration. Add or update `NVIDIA_API_KEY=...` there. The
NVIDIA launcher first honors the process environment (for explicit launches),
then reads `NVIDIA_API_KEY` or the existing `NVAPI_KEY` alias from `.env`. A
masked prompt appears only when neither is configured. `.env` is ignored by Git.
No key value was inspected or copied during this change.

The repeated prompt occurred because the NVIDIA launcher did not load `.env`;
it only checked its process environment and the formerly documented separate
Windows Credential Manager entry. The other provider setup reads `.env`, so an
NVIDIA key placed there was invisible to that launcher. The Credential Manager
reader has now been removed; one saved location is the project `.env` file.

The earlier instruction to save under `LYA/NVIDIA_API_KEY` in Windows Credential
Manager is superseded. Any value already saved there is no longer used. Add the
key to project-root `.env` yourself and remove the old entry if you want one
stored location. Keep keys out of source code and `lya-project-brain.md`.

The existing launcher has a masked session prompt as fallback; it never writes
submitted input to disk. This change affects only provider-key lookup, not which
model is selected, cloud consent, voice, camera, startup or authorization.
