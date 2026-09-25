# LYA brain: what now works and how to use it

Implemented 2026-09-13. This document distinguishes tested code from real-device
readiness. The new native message panel now dispatches brain requests to one
background worker. The default session is a guest; changing orb colors never
changes the identity or permissions.

## Does LYA respond now?

Yes to implemented commands, including `brain status`, `brain help`, `who am i`
and `brain demo`. The memory/reasoning workflow is connected and tested using fake
identities, approvals and model responses. The complete real-person AI journey is
not ready: no real identity/phone adapter is bound to the new brain, and the local
model service was not reachable in this check. LYA reports these missing pieces
instead of pretending to recognize someone or inventing a model response.

Restart the native app using `launch-lya.ps1`, click the crystal and enter:

```text
brain demo
```

This runs a separate process with synthetic people, an ephemeral encryption key,
temporary storage, fake approval and a clearly labelled mock model. It exercises
real save, recall, graph, correction, council orchestration and guest-denial code.
It cannot unlock your real profile. Run it directly with:

```powershell
.\.venv-ui\Scripts\python.exe -B brain\demo.py
```

View the [workflow PNG](diagrams/11-brain-workflow.png) and
[schema PNG](diagrams/12-brain-schema.png). Detailed Mermaid sources are beside them;
the PNGs are locally rendered companion overviews, not screenshots of private data.

## What “thinking before answering” means here

1. **Identify the session.** Use a trusted person ID, active role and verification
   expiry. A typed name or an admin-colored crystal is not authentication.
2. **Check permission.** Preserve the existing owner/phone-approval policy for
   personal memory and council work. Approval is requested for the exact operation.
   Other roles remain restricted until their access rules are explicitly extended.
3. **Retrieve relevant context.** Search only this person's active notes and add
   nearby graph relationships. Exclude credential kinds, expired notes and inactive
   profiles. Missing identity never selects the first person in the database.
4. **Choose a reasoning path.** Bounded simple arithmetic runs through a local
   deterministic evaluator. Public research requires an injected source adapter and
   structured claims; ordinary questions use one configured model call. Explicit
   council requests use three perspectives and a synthesis.
5. **Verify the output boundary.** Research facts need known source IDs, and visible
   research text is rebuilt only from validated claims. Missing adapters, malformed
   claims and unknown citations fail closed. Discard cancelled answers,
   changed/expired identities, revoked profiles and expired retrieved notes.
6. **Answer transparently.** Return relevant saved-note IDs/revisions and distinguish
   user-provided context from sourced evidence. Model prompts request a direct answer
   and brief material uncertainty, not a dump of hidden reasoning.
7. **Save only on request.** An answer, speculation or council consensus does not
   become a saved fact automatically. An explicit save or correction is a separate
   authorized operation.

This is a control workflow around a model. It is not a biological brain simulation
and does not guarantee correct answers. Routine public research now uses You.com's
keyless search-only MCP profile, bounded to six HTTPS sources and eight seconds.
Tavily is consulted only when the request begins `critical research:` or `important
research:` and its existing key plus both safety flags are present. Search snippets
carry source URLs, but independent full-page claim validation and consequential
decisions still require source review. Agent Reach 1.5.0 is installed in its dedicated
user environment for multi-channel work. Its read-only diagnostic currently verifies
Jina webpage reading, RSS, V2EX and basic Bilibili search; GitHub and Exa still need
their separate `gh` and `mcporter` dependencies.

## Memory lifetimes, in plain language

| Layer | Purpose | Lifetime | Implementation |
|---|---|---|---|
| Working context | The question and selected evidence needed for this answer | One request | RAM; not written to the database |
| Session notes | “Keep this in mind while we work” | Current verified session; cleared at next check after 15 minutes idle, identity expiry/change, panel close/sleep, or process exit | Up to 20 explicit notes in RAM |
| Short-term | Recent useful details | 7 days by default | Encrypted note with expiry |
| Longer-term | Ongoing projects, preferences and approved lessons | 90 days by default | Encrypted note with expiry |
| Specific timeline | Information valid until a particular deadline | User-supplied timezone-aware timestamp | Encrypted note with expiry |
| Permanent | Information explicitly chosen for lasting retention | No automatic expiry | Encrypted note; still correctable and forgettable |

Seven and ninety days are understandable starting policies, not scientific laws
about human memory. Permanent does not mean impossible to delete. Older records
keep their previous non-expiring behavior during the additive schema migration.

Expiry excludes notes from reads immediately when the clock passes the deadline.
Physical cleanup occurs on subsequent authorized save/retrieval activity; an
offline application cannot run a cleanup timer. Old backup copies, if created in
the future, will need their own retention/deletion policy. Neither expiry nor
Python object deletion is a promise of forensic erasure.

Examples, once a trusted session and approval adapter are connected:

```text
remember session current task = prepare the LYA plan
remember short laptop = prefer small local workloads
remember long project = finish the native command workflow
remember until 2026-12-01T18:00:00+05:30 deadline = finish phase one
remember permanent preference = keep answers clear and concise
recall laptop
correct laptop = prefer bounded local workloads and optional remote compute
forget deadline
```

An existing label is not silently overwritten. `correct` changes its value,
increments its revision and preserves its expiry. Correcting/forgetting clears
temporary context. Automatic chat-transcript storage is intentionally absent;
explicit session notes provide temporary continuity in this milestone.

## A small knowledge graph

A graph is a set of things and their relationships. Here each saved note is a
node, so we reuse the memory table rather than introducing a graph server:

```text
LYA plan  --depends_on-->  laptop resources
test results  --supports-->  implementation decision
new evidence  --contradicts-->  earlier assumption
```

Use actual note IDs returned by save:

```text
link 2 depends_on 1
show graph
```

Both endpoints must be active notes belonging to the same person. Relationships
are declared by the user; they are not automatically proven. Retrieval uses a
bounded BM25 full-text search plus one-hop graph expansion. It does not yet understand
every paraphrase, resolve entities automatically or run an embedding model.

The schema extends `storage/store.py`: `people` owns `memories`; memory records
carry label/value, kind, source, revision, retention and expiry; `memory_links`
references note IDs. Foreign-key enforcement removes edges when a note is deleted.
Existing face, pending-review, vault and audit tables remain separate concerns.

SQLite is suited to local application storage and needs no separate database
server. This choice follows its [documented use cases](https://www.sqlite.org/whentouse.html).
The relationships use [SQLite foreign keys](https://www.sqlite.org/foreignkeys.html).

## Council and accuracy

Use `council: ...`, or phrases such as “important plan”, “serious plan”, “major
decision” and “second opinion”. This simple routing rule is inspectable; it will
not perfectly recognize every serious question.

The implemented council asks an evidence reviewer, a planner and a critic, then
requests one synthesis. It makes at most four sequential calls, avoiding three
heavy models running on the laptop simultaneously. These are three perspectives
through the configured client, not three independent humans or verified experts.
Partial failure is labelled; complete failure produces no invented verdict.

Agreement is not evidence. The model sees saved user statements as untrusted
context, receives no credential records and cannot execute tools or save its own
output. Proper external source retrieval and factual evaluation are still needed
before making claims about real-world accuracy.

## What learning means

The implemented learning loop is: do a task, discuss the outcome, explicitly save
an approved lesson, correct it when needed, and retrieve it during a relevant task.
This changes LYA's available context. It does not retrain model weights, install
new executable skills, or promote a frequently repeated claim into truth.

Neural-model training, automatic lesson extraction, semantic embeddings and
automatic fact verification are deferred. Add them only after measuring a concrete
failure that this smaller workflow cannot handle.

## Laptop, model and cloud choices

The current implementation reuses Python, encrypted SQLite and the existing native
Qt UI. New note saves are bounded to 2,000 notes per person, with 2,000 characters
per note. Model evidence is bounded to 6,000 characters. Large files stay outside
the conversational database. The existing whole-file encryption is appropriate
only for small stores; it reserializes the database and is not a large-scale search
engine. Hardware inventory through WMI was denied, so no RAM/GPU claim was made.

The private model adapter now calls the installed llama.cpp server only at
`127.0.0.1:8080`, with the stable `lya-local` alias and a 60-second request bound.
Use `private mode`, `public mode`, `privacy status`, or a one-message `private:` /
`secret:` prefix. Private inference fails closed and never falls through to Oracle
or another cloud route. Start the local server with `run-local-model.cmd`. The
installed Qwen3 4B Q4_K_M model is hash-verified and improves the frozen local
rubric to 5 pass, 1 partial and 2 fail. It is still provisional: coding and Tamil
failed, so T03 verification is required before trusting high-impact answers.
Cancellation hides late results immediately but cannot interrupt a request already
inside its timeout.

Free cloud storage is useful for later encrypted snapshots and selected mobile
files. It is not a reasoning server, RAM or GPU. Keep the live database local;
design versioned backup exports separately. The current Windows-bound key cannot
simply be copied to an iPhone for recovery. Portable recovery/pairing, provider
choice and backup retention need design and tests before enabling upload.
No sync, upload, real enrollment or phone pairing was performed. The cloud service
question remains open.

## Checks and remaining gates

Run the isolated acceptance pack:

```powershell
.\.venv-ui\Scripts\python.exe -B review\review_20260913.py --retrieval
```

Latest isolated run: **91 checks passed, one online speech test skipped**. Five
earlier defect probes no longer reproduced. This is not a claim that all project
features work.

Latest results and synthetic renderings are saved in `review/2026-09-13-retrieval/`;
the previous `review/2026-09-13-brain/` evidence is preserved. The harness
uses a disposable source copy, temporary runtime paths and fake credentials. Model
answers and speech are mocked; network and hardware input are blocked.

The pack covers storage, synthetic identity, context boundaries, voice routing,
native brain dispatch, demo execution, cancellation, lifetimes, graph scope,
correction, restart and migration. It is not a camera accuracy, microphone accuracy,
live LLM quality or phone integration test. Real identity/approval binding, a
reachable selected model, real-device acceptance, live research and cloud backup
remain explicit next gates.

Research and next gates: [advanced brain plan](LYA_ADVANCED_BRAIN_PLAN.md).
