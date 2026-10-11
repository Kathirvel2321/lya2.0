# LYA - full architecture research and prototype atlas

2026-10-11. Requested scope: research established work deeply, then explain the
complete brain/storage/platform design, formats, capacities, speed and recovery
before implementation. This pack supersedes the earlier small diagram as the
detailed target design; earlier artifacts remain as historical evidence.

**Start with [the visual architecture explorer](index.html).** It contains eight
rendered, zoomable diagrams and an interactive storage/backup calculator. The
explorer is a standalone local design artifact; it does not connect to LYA, a
provider or any private memory. The accompanying SVGs can be zoomed independently.

Recommended target: one shared Python orchestration/memory contract; existing
native Windows and thin iPhone interfaces; a separately bounded PostgreSQL/pgvector
candidate on the existing Oracle host; exact/keyword/semantic/temporal retrieval;
confirmed writes with provenance and revisions; private-local separation;
independent encrypted recovery; measured model/voice pipelines. This recommendation
is conditional on the isolated prototype and owner-approved personal-data placement.

The earlier SQLCipher recommendation is retained as the compact comparison
baseline. The expanded requirements and observed Oracle headroom support evaluating
PostgreSQL as the full target. This changes the proposed new shared store, not the
working laptop vault. No database installation or migration has occurred.

## Read in this order

Latest recommendation: [Final platform, transport and implementation roadmap](FINAL-ROADMAP.md).
Its numbered sequence supersedes the earlier implementation order: measure early,
qualify recovery before valuable records, then improve speed and add optional apps.

Storage-platform clarification: [Notion, Obsidian and low-local-storage placement](PLATFORM-STORAGE.md)
explains their optional roles, current free limits and why Obsidian is local storage.

1. [Research and decisions](RESEARCH.md): what Letta/MemGPT, Mem0, Graphiti/Zep,
   Hindsight, Anthropic, LangGraph, LiveKit/Pipecat and memory benchmarks contribute;
   what we adopt and why we do not install every framework.
2. [Complete architecture contract](ARCHITECTURE.md): platforms, identity, every
   memory type, data formats/schema, read/write paths, model routing, learning,
   privacy, failure behavior and future upgrades.
3. [Capacity and performance](CAPACITY.md): actual machine readings, current app
   caps, theoretical engine limits, transparent storage arithmetic, backups and
   unpassed latency targets.
4. [Implementation gates](IMPLEMENTATION.md): isolated prototype -> shared records
   -> recovery -> quality/personality -> measured speed -> reviewed learning.

## Diagram map

| Diagram | Question answered |
|---|---|
| [Whole system](01-whole-system.svg) / [editable source](01-whole-system.mmd) | What connects to what across the entire assistant? |
| [Answer sequence](02-answer-sequence.svg) / [source](02-answer-sequence.mmd) | How does a turn become a supported answer and stop safely? |
| [Memory lifecycle](03-memory-lifecycle.svg) / [source](03-memory-lifecycle.mmd) | How does a fact become durable, corrected, forgotten and restored? |
| [Data schema](04-data-model.svg) / [source](04-data-model.mmd) | What records and relationships exist, and in which form? |
| [Platforms and trust](05-platform-trust.svg) / [source](05-platform-trust.mmd) | Which machine can see/process which information? |
| [Recovery](06-recovery.svg) / [source](06-recovery.mmd) | How do years of knowledge survive host loss without reviving deletions? |
| [Model routing](07-model-routing.svg) / [source](07-model-routing.mmd) | When is no model needed, and which model is eligible? |
| [Fast workflow](08-fast-workflow.svg) / [source](08-fast-workflow.mmd) | How are replies separated from background exports and recovery? |

Colors: green = existing component retained, blue = proposed shared behavior,
amber = proposed component with explicit qualification/trust/recovery gates.
An edge in a target diagram is a proposed integration, not proof that it is wired.
Existing components are not a claim that the complete experience passed acceptance.

## Key findings

- Oracle reports four ARM logical CPUs, 23.41 GiB RAM and 189.21 GiB free disk.
  Laptop reports an i3-1215U and 7.70 GiB RAM, with 1.16 GiB free at the reading.
  These counters support a prototype, not an uptime, speed or billing claim.
- The current Oracle public free-tier document lists a smaller A1 allowance than
  the resources visible on this host. Actual account eligibility/cost is unresolved.
- At an illustrative 19 KiB per selected record including index allowance, 100k
  records use about 1.81 GiB; one million use about 18.12 GiB before attachments,
  WAL, models and backups. This is arithmetic, not a load test.
- Server-readable personal placement remains a pending decision. Existing private
  laptop data stays local; public-provider context excludes personal records.
- Long-lived memory quality requires evidence, time, correction, abstention and
  deletion-aware recovery. A vector database alone does not provide these.

Evidence/checks: `capacity-observed.json`, `laptop-capacity-observed.json`,
`mermaid-validation.json`, `validation.json`, `atlas-preview.png`.
`build_atlas.cjs` renders locally using a pinned Mermaid bundle in temporary
storage and the existing bundled Playwright/Chrome. The exported explorer embeds
SVGs and has no external scripts, fonts, analytics or network dependencies.

Not implemented by this pack: shared runtime memory, new model defaults, embeddings,
database migration, deployment, automatic collection or backup scheduling. Next is
review of this concrete design and trust/cost gates, followed by the isolated
prototype described in IMPLEMENTATION.md.
