# Historical archive

Moved locally on 2026-10-12 at the owner's request. These files are retained for reference and recovery; they are outside the working implementation. No files were deleted and no runtime data, credentials, model weights or virtual environments were moved.

| Folder | Contents |
| --- | --- |
| `retired/` | Previously quarantined legacy skills, audio/UI code, dead tools and stray artifacts; also superseded root maintenance/review scripts. The earlier classification is preserved in [retired/MANIFEST.md](retired/MANIFEST.md). |
| `unsafe-tests/` | Old scripts documented to modify real stores. **Do not run them.** |
| `experiments/voice-evaluation/` | Unused upstream voice-evaluation source/configuration, separate from the voice implementation that the desktop currently uses. |
| `history/reviews/` | 75 historical review/evaluation folders. These include successful milestones as well as failures; archival does not mean the implemented feature was removed. |
| `history/desktop-qa/` | Three superseded layout evidence folders. Current screenshot generators/output locations remain in `desktop/qa/`. |
| `history/documentation/` | The old build-progress report and pre-organization root README. |
| `history/validation/` | Old root test-summary output. |
| `history/continuity/` | The complete previous project brain, preserved byte for byte. Read the [current brain](../lya-project-brain.md) first. |

The [move manifest](../review/2026-10-12-project-organization/move-manifest.json) maps every old path to its new location and records original SHA-256 values. Archived documents and scripts retain their original bytes: paths, instructions and status claims inside them may be obsolete. Consult the manifest for an old path rather than executing an archived script to reproduce its dated claim.

Normal application launch, deployment, imports and test discovery must not use this folder. Keep it off `sys.path`; do not add `__init__.py` here. Default unittest discovery does not recurse into this non-package folder, and root `pytest.ini` explicitly ignores it. To recover an item, look up its original path in the manifest, check current dependencies, restore only the selected file to an active location and requalify it with fake data before use. Never restore an unsafe script into a routine test suite.

Active source stays in `desktop/`, `brain/`, `audio/`, `cloud/`, `security/`, `storage/`, `skills/`, `vision/` and the supporting directories identified by [the project guide](../README.md). Maintained explanations are indexed in [docs](../docs/README.md). Newer prototypes and current validation/release helpers stay outside this archive.
