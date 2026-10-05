# Native session-key launch - 2026-10-05

The terminal appeared because the online launcher used console Python and
`getpass` for the session-only NVIDIA key. It stayed attached to the desktop.

Changed `tools/start_nvidia_lya.py` to support `--gui`: a masked native Qt key
dialog, Start LYA/Cancel, and fixed safe error messages. Cancel exits before
desktop launch. The key remains in the process environment only, never a file
or command argument, and is removed when the desktop exits/fails. Desktop main
reuses the existing Qt application instead of constructing another one.
Console input remains available for manual diagnostics without `--gui`.

`launch-lya.cmd`, `launch-lya.ps1`, and `tools/set-startup.ps1` now select
`.venv-asr/Scripts/pythonw.exe` with `--gui`. Migrated the existing owned startup
shortcut with `-OnlyIfExisting`; disabled or unrelated shortcuts are not enabled
or overwritten by that mode. Verified its target and arguments. Added and
verified project `LYA.lnk` for direct native launch. Opening `.cmd` may briefly
flash its shell, so use the shortcut to avoid that too.

Validation: seven new isolated launcher checks passed with fake keys, temporary
paths and mocked desktop/client; 60 existing isolated offscreen desktop checks
passed with fake secrets and live I/O disabled. Checks cover masked/cleared input,
Cancel, no console-input fallback in GUI mode, session environment and argument
handling, cleanup/safe errors, console diagnostics and Qt application reuse.
Python compilation, PowerShell syntax, shortcut target/argument verification and
affected tracked whitespace checks passed.

[Synthetic native key-dialog preview](key-dialog.png) was rendered and visually
inspected using example input only. No owner key, microphone, model request,
private store or running desktop session was accessed. Actual owner launch through
the new shortcut remains to be confirmed. Existing hearing/output/privacy and
authorization policies are unchanged. Enrollment/weather remain deferred.
