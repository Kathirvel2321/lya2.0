# Publication-confirmed fake-owner recovery — 2026-10-21

Owner requested continuation of the memory/recovery foundation. This extends only the optional generated-data publication authority. No real enrollment, startup integration, cloud access or deployment is included.

## Change and recovery behavior

[SyntheticPublicationAuthority](../../brain/memory_publication_authority.py) now delegates `activate_restored()` to the existing authority's pre-existing-owner recovery implementation. Its existing overridden transaction reserves recovery, commits source plus publication journal, verifies the encrypted publication, confirms latest and completes the journal before returning. The small override rechecks the authenticated turn and cancellation after publication, then adds `publication_confirmed: true`. The accepted base authority and its validation are unchanged.

Activation requires literal approval, a fresh verified synthetic owner already mapped to this lineage, the exact acknowledged quarantine, and current recovery anchor/epoch. It activates one existing binding, resumes zero jobs and advances the writer epoch. The old writer remains fenced; the quarantine input remains unchanged. There is no new identity registration, default change, dependency or new token storage.

An exception can follow a committed activation. Reconcile publication explicitly before further operations; reconciliation returns metadata, never a writer token. If the source transaction rolled back, pending recovery remains and fresh activation may be retried. If activation committed, repeating activation refuses because recovery is already consumed. An explicitly approved writer takeover can issue a later generation after reconciliation; it cannot recover or redisclose the lost token. Even a refused operation that entered a publication transaction can leave a reservation that needs reconciliation. Never interpret an exception as proof of rollback.

## Qualification

[Reviewed runner](check.py) selects seven new reactivation cases and the ten preceding publication cases, without counting inherited cases twice. Generated keys, pre-existing fake identities and isolated temporary stores only. Windows uses the existing qualified SQLCipher driver; Ubuntu uses the existing lab Python/runtime against the reviewed source, without installation or service changes. Both environments are on the same physical laptop.

The seven new cases exercise:

1. Published one-owner activation, revoked old writer, usable fresh writer, preserved correction/deletion/expiry, unchanged quarantine and cold archive recovery back into zero-binding quarantine.
2. Literal approval, verified/fresh/cancelled turns, unknown identity, stale anchor/epoch and changed quarantine refusal, with recovery preserved.
3. Source publication rollback, blocking reservation, reconciliation and a safe fresh retry.
4. Committed activation with publication failure, blocked latest, metadata-only reconciliation, refusal to mint a duplicate activation grant and explicit later writer takeover.
5. Expiry, identity change and cancellation during publication, preventing success/token disclosure even when activation committed.
6. Missing latest store refusal without recreation or source modification.
7. Five actual child-process exits after reservation, before/after source commit, after latest confirmation and after journal commit; reconciliation distinguishes rolled-back versus consumed recovery.

Seventeen distinct cases are qualified per platform across the initial runs and focused rechecks, comprising seven new cases and ten regressions. Each initial unrestricted run completed sixteen passing cases and one test-sequence error: [Windows](windows-validation-2.json), [Ubuntu](ubuntu-validation.json). The happy-path test checked old-writer rejection but omitted the required reconciliation before continuing. Added that reconciliation to the test, with no runtime change, then reran the affected case successfully on [Windows](windows-recheck.json) and [Ubuntu](ubuntu-recheck.json), zero failures/errors/skips. The full seventeen were not rerun after the test-only correction; counts do not add repeated or cross-platform cases together.

The [initial manifest](source-manifest.json) and [current manifest](source-manifest-2.json) pin forty-five normalized source hashes. Only the test and runner changed between these qualification revisions; the runner gained exact reviewed-case selection to avoid repeating passing cases. All runtime sources stayed identical. The current manifest also verifies forty-five preserved artifacts, including the initial reports. An earlier sandbox run failed Windows hard-link creation before exercising the feature; its [report](windows-validation.json) and log are preserved. There was no automatic approval rejection or OS setting change.

[Preservation checks](preservation-validation.json) verify eighteen accepted HEAD sources unchanged, thirty-seven preceding evidence artifacts unchanged, the original three-file fake transfer pack unchanged and valid Python syntax. [Final static validation](static-validation.json) records the combined case evidence, current hashes, affected document links, whitespace and fixture cleanup. The original code ZIP remains byte-identical and is exercised by the successful cold recovery case. Earlier evidence remains dated evidence for its earlier source revisions.

## Limits and next step

The protected source catalogue, owner mapping, keys and latest state must already survive. Cold record recovery does not recreate authority or prove a real owner. Source/latest metadata remain trusted plaintext in this local simulation. Joint rollback, independent custody/hosting, network/TLS witness composition, resource/remote durability qualification and production cutover remain pending. The next infrastructure step is to qualify the intended independent catalogue/latest/key recovery placement before valuable private use. Face anti-spoofing remains deferred.
