# Direct Ubuntu lab testing — 15 October 2026

The owner asked how to avoid manually copying test commands/results between this chat and Ubuntu. Verified direct access to the existing Ubuntu-24.04 WSL distribution and `~/lya-lab` virtual environment through `wsl.exe`. No installation, WSL/Codex configuration, account, shell profile, production source or service change was needed.

The restricted sandbox returned `Wsl/E_ACCESSDENIED` for the initial read-only distribution listing. The permitted execution path succeeded. This is a host access boundary, not a broken Ubuntu installation; retain normal execution approval checks rather than changing permissions globally.

## Verified result

Measured 13 selected Linux source/test SHA-256 values and compared them with the reviewed workspace copies before execution. All matched, including the process/TLS tests, their protocol/coordinator helpers, eight portable memory modules and the portable qualification fixture. No real store, configuration, key or private capture was inspected or copied.

The assistant then directly ran **all 15 process/TLS checks in Ubuntu**, with zero failures/errors/skips and final `OK`. [Validation and both source-hash maps](validation.json), [test log](tests.txt) and [documentation/source preservation](static-validation.json) retain the evidence without terminal prompts, host identifiers or credentials. This independently executed result supplements the earlier owner-reported pass; counts overlap and are not added.

## Workflow for future authorized development

Use the existing distro and lab Python directly, without interactive virtual-environment activation. An equivalent PowerShell invocation is:

```powershell
wsl.exe --distribution Ubuntu-24.04 --exec bash -lc 'cd ~/lya-lab && exec .venv/bin/python -m unittest -v test_memory_witness_process test_memory_witness_tls'
```

Before executing changed tests, read the relevant current source/tests and compare selected lab hashes. Refresh only reviewed source/test files needed by the authorized task, preserve numbered backups, then recheck hashes. Keep credentials, real stores, runtime configuration and `archive/` out of the lab selection. Use isolated fake keys and temporary stores, explicit module names and captured results. Never discover/run archived tests or synchronize the whole project as a shortcut.

If WSL access is sandbox-blocked, use the permitted scoped execution path with the specific test/source scope. A denial is not a reason to change Windows/WSL settings, install SSH or broaden permissions. Report any unresolved approval block. This task creates no background scheduler, automation, permanent permission grant or automatic source-sync helper; future commands remain subject to the session's actual tool availability and access review.

## Limits and next step

Direct testing is verified for this existing local WSL lab and reviewed fake-data suite. It does not establish Oracle/independent-host behavior, OS service supervision, power-loss durability, production resource/admission limits, real custody or private-device acceptance. Existing WSL can reach Windows mounts, so the lab is not a hard security sandbox.

The owner need not repeat these commands or paste their output for this completed verification. Future authorized Ubuntu checks can be run directly by the agent. Continue the memory roadmap at concrete resource/request-admission qualification and independent free placement; real-key setup, enrollment, private transfer and deployment remain separate scopes.
