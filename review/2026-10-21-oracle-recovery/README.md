# Full-authority fake recovery — reconciled 22 October 2026

The 22 October continuation found this existing implementation and its evidence beyond the last project-brain entry. It requalified the current local source and restored the missing documentation. No runtime module, prior test, default, enrollment or account was changed. The Oracle run below is preserved evidence from the earlier work, not a remote run performed during this continuation.

## What is implemented

[memory_authority_transfer.py](../../brain/memory_authority_transfer.py) captures an explicitly approved, single-lineage `SyntheticPublicationAuthority` into a bounded authenticated encrypted envelope. Unlike the earlier record-only pack, it includes the authority catalogue and pre-existing fake-owner mapping, encrypted live database, backup/checkpoint, key capsule and trust record. Capture holds the source/latest locks and refuses unresolved publication or owner recovery. Its envelope uses the existing fake unlock and encryption primitives; no real key or new dependency is introduced.

Restore requires a separately trusted exact envelope fingerprint, fake unlock and existing current latest-state store. It rejects an old checkpoint or writer epoch before creating the new destination. It never bootstraps latest state from the envelope. A successful restore republishes writer revocation before returning recovery metadata, leaves memory quarantined with zero bindings/jobs and requires fresh pre-existing fake-owner verification for subsequent activation. It never returns the exported old writer token.

An incomplete destination keeps `RECOVERY-INCOMPLETE`. Explicit `resume_authority()` reconciles the journal before distinguishing committed recovery from rollback. A committed quarantine is checked against its acknowledged digest and is not replayed. If rollback left an unacknowledged quarantine file, the operator must select the fixed `retry-quarantine.sqlite` name; the first file is preserved. Partial extraction is not promised to be repairable: missing or divergent catalogue/input files refuse, and a new attempt must use a new destination and independently current trust. Directory presence and an exception are not success or rollback evidence.

## Qualification and provenance

The reviewed [runner](check.py) selects exactly eight transfer cases, excluding inherited cases. [Tests](../../test_memory_authority_transfer.py) use generated keys, fake identities and temporary stores. They cover source/catalogue loss in a fresh child, usable owner continuity after fresh verification, correction/forget/expiry, stale record/epoch refusal, literal approvals, ciphertext/authentication, pending capture refusal, byte budgets, no overwrite, missing latest without recreation, committed failure reconciliation and rollback retry.

| Evidence | Result and limit |
| --- | --- |
| [Fresh Windows run, 22 October](windows-20261022-permitted.json), [log](windows-20261022-permitted.txt) | Eight pass, zero failures/errors/skips; all 48 runner-pinned source hashes match before/after. |
| [Fresh Ubuntu run, 22 October](ubuntu-20261022.json), [log](ubuntu-20261022.txt) | Eight pass, zero failures/errors/skips; same sources/tests through the existing WSL lab runtime. This still shares the Windows laptop. |
| [Recorded Oracle ARM64 run](oracle-validation.json), [test log](oracle-tests.txt) | Eight pass plus one Windows-origin fake-envelope recovery, owner reactivation and old-envelope replay refusal. Temporary stage removed and existing service/source preservation reported. Not rerun on 22 October. |
| [Earlier Windows run](windows-validation.json), [focused correction](windows-recheck.json); [earlier Ubuntu run](ubuntu-validation.json), [focused correction](ubuntu-recheck.json) | Initial runs each had seven passes and one test-sequence error; corrected-case rechecks passed. Preserved as dated evidence. The fresh full runs above replace the need to combine those counts. |
| [Restricted Windows attempt, 22 October](windows-20261022.json), [log](windows-20261022.txt) | Eight setup errors at atomic hard-link creation, before transfer behavior. The permitted run used identical sources; no filesystem setting or publication safety check was changed. |
| [Current source manifest](oracle-source-manifest-3.json), [22 October validation](continuation-20261022.json) | Current normalized hashes match all 53 reviewed source entries; all 20 recorded Oracle payload members match, including its two generated empty package markers. Forty-five preceding evidence artifacts remain byte-identical. |

These are the same eight test cases across platforms, not 24 distinct cases. No new runtime behavior is claimed from this documentation/qualification task. The system `python` initially lacked `cryptography`; the Windows run used the existing `.venv-ui` and qualified driver. WSL required its existing permitted execution path. No package was installed. Tests are process/transaction failure exercises, not power-loss durability qualification.

## What the Oracle result does not establish

The recorded staging code explicitly creates a fresh latest-state store on Oracle and seeds it using the same incoming drill packet that carries the fake envelope fingerprint and unlock. That is controlled fixture bootstrap. It tests recovery on a physically separate runtime but **does not demonstrate independently surviving current latest-state or key custody**. Its `separate_surviving_latest` field describes the staged folder/process arrangement and must not be read as independent provisioning or rollback-resistant survival. The temporary store is removed at the end.

The envelope is an explicit point-in-time capture, not part of every memory acknowledgement. A later source or writer update can make it stale; rejection then preserves safety but does not provide recovery availability. Full-catalogue publication/retention must be coordinated with the eventual live acknowledgement boundary before private use.

All tests assume trustworthy current latest state. Joint rollback of that store and all copies remains undetectable. Unpacked catalogue metadata is plaintext in the fake recovery directory; `mode=0o700` is not Windows ACL qualification. Existing fake-only guards remain mandatory. Real owner proof, vault/offline retrieval, protected persistent hosting, network/TLS witness composition, quotas/durability and production device acceptance remain pending.

## Next concrete milestone

Use the [bounded independent-custody placement plan](placement-plan.md). Prove latest-state survival and protected key retrieval from separately established custody before deleting a generated source, then reject stale/missing/pending trust on recovery. This requires the placement and acknowledgement protocol work described there; repeating the existing Oracle staging script would not prove it. Real enrollment, real private data and face anti-spoofing remain deferred.
