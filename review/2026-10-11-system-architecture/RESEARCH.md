# Research evidence and architectural decisions

Reviewed 2026-10-11. Primary papers, maintainer documentation and source repositories
were used. This is a focused architecture review, not an exhaustive survey of all
AI products. Vendor benchmark claims are not independent LYA measurements, and
scores from different models, prompts or benchmark versions cannot rank systems
fairly. No user conversations or private records were submitted to a provider.

## What established teams built, and what LYA should adopt

| Work and primary source | Mechanism studied | LYA decision | Important boundary |
|---|---|---|---|
| [MemGPT / Letta memory blocks](https://www.letta.com/blog/memory-blocks/) | Bounded in-context identity/user blocks and external persistent memory | Separate a small approved persona from retrieved facts and temporary dialogue | Do not let a model rewrite authorization or promote invented personality history |
| [Letta Context Repositories, Feb 2026](https://www.letta.com/blog/context-repositories/) and [current direction](https://www.letta.com/blog/our-next-phase/) | Git-backed files, progressive loading, versioned context and background learning | Use versioned files for public project knowledge and reviewed skills | Git history is a poor default home for deletable private conversations; do not copy their unrestricted memory-editing policy |
| [Mem0 paper](https://arxiv.org/abs/2504.19413) | Extract, consolidate and retrieve selected conversational facts; optional graph variant | Evaluate extraction/deduplication as a proposal stage outside the ordinary reply path | Their paper reports latency/token savings under its setup; automatic extraction is not consent to durable storage |
| [Zep paper](https://arxiv.org/abs/2501.13956) and [Graphiti implementation](https://github.com/getzep/graphiti) | Time-aware entities/relationships, evidence lineage and hybrid retrieval | Record valid time separately from recorded time; preserve source links and resolve corrections | Graphiti needs a graph backend and model services. Start with relational edges; add a graph engine only if measured queries demand it |
| [Hindsight paper](https://arxiv.org/abs/2512.12818) and [current implementation](https://hindsight.vectorize.io/) | Retain/recall/reflect; distinguish facts, experiences, summaries and beliefs; multiple retrieval methods | Separate confirmed facts, evidence and derived proposals; compare exact, text, vector and relationship recall | Reflection is inference, not truth. A full hosted memory product is not automatically compatible with LYA's privacy policy |
| [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Curated context, just-in-time retrieval, compaction and structured notes | A context compiler with explicit token/evidence budgets and progressive disclosure | Summaries can lose details; preserve approved source evidence, not every raw conversation |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Distinct task checkpoints and cross-thread durable memory | Separate resumable task state from lasting user facts | Checkpoint storage must not silently become a permanent transcript archive; no framework replacement required |
| [LiveKit turn handling](https://docs.livekit.io/agents/logic/turns/) and [Pipecat pipelines](https://docs.pipecat.ai/pipecat/learn/pipeline) | Streaming speech stages, interruptions and coordinated pipeline state | Measure each voice stage; prototype cancellation and sentence audio streaming independently | Semantic endpointing, transport and continuous capture require real phone/language testing; accepted Amy and pause behavior remain until acceptance |
| [llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README-dev.md) and [vLLM prefix caching](https://docs.vllm.ai/en/latest/design/prefix_caching/) | Warm inference, request scheduling and prompt-prefix reuse | Reuse the existing local engine; consider scoped cache reuse only where the runtime supports it | GPU-oriented serving infrastructure has no demonstrated benefit on this CPU-only personal setup; a cache is not lasting factual memory |
| [LongMemEval](https://arxiv.org/abs/2410.10813) | Extraction, multi-session reasoning, time, updates and abstention | Include these question classes in the held-out LYA evaluation | Recall accuracy alone does not prove safe permissions or successful actions |
| [MemoryArena, 2026](https://arxiv.org/abs/2602.16313) | Interdependent tasks where earlier experience must improve later actions | Test whether an approved lesson improves the next task without extra errors | Strong static memory scores need not transfer to acting over multiple sessions |
| [MemX, 2026](https://arxiv.org/abs/2603.16171) | Local hybrid retrieval with rejection when no reliable match exists | Keep a simple indexed baseline and explicit no-answer behavior in every comparison | A small custom benchmark or a different machine's latency does not establish LYA performance |

**Conclusion from the evidence:** the useful combination is controlled writes,
temporal evidence, hybrid retrieval, bounded context, recoverable task execution
and evaluation. Installing all of these platforms together would duplicate
authority, increase latency and complicate deletion. We should adopt selected
mechanisms inside LYA and benchmark candidate components against the same tests.

## Database decision after observing this machine

The earlier small design recommended SQLCipher. The larger design requested now
includes shared concurrent sessions, temporal links, vector retrieval and durable
jobs. The current Oracle host reports four ARM logical CPUs and 23.4 GiB visible
RAM, which makes a separately bounded PostgreSQL service plausible.

**Recommended full-system target: PostgreSQL with pgvector, subject to an isolated
prototype and resource/cost/security gates.** This is a revised recommendation,
not a migration or installation. SQLCipher remains the comparison baseline and
the fallback design if the small-service constraints win. There must be only one
authoritative shared memory database in either design.

| Candidate | Strength | Tradeoff | Decision |
|---|---|---|---|
| [SQLCipher](https://www.zetetic.net/sqlcipher/design/) + SQLite FTS5 | Encrypted pages, low operational footprint, transactional records | One writer; vector extension/build compatibility requires qualification | Compare at 10k/100k records; viable compact alternative |
| [PostgreSQL](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) + [pgvector](https://github.com/pgvector/pgvector) | Relational constraints, concurrent transactions, scoped rows, keyword/vector search and job records together | Server administration, encryption at storage level, backup/WAL growth and memory tuning | Preferred full-system candidate on observed Oracle host |
| Dedicated graph engine | Specialized deep relationship traversal | Another service, index, backup and deletion path | Defer until relational edges fail the actual relationship benchmark |
| Dedicated vector database | Independent vector scaling | Another authoritative-looking copy; transactional consistency work | Defer until Postgres retrieval cannot meet measured targets |
| Managed memory service | Faster product integration in some settings | Subscription/provider trust, extraction defaults and migration coupling | Reference/evaluation only under the current zero-subscription requirement |
| Git / Markdown | Readable reviewed knowledge and skills | History preserves removed data; weak transactional identity/retention semantics | Use for safe project artifacts, not primary private memory |

PostgreSQL does not become encrypted-at-rest merely by enabling TLS or installing
pgvector. The target needs an encrypted data volume covering data/WAL/temp files,
restricted runtime keys and encrypted backups. A mounted volume remains readable
to its authorized host. Searchable personal data therefore requires server trust.
[PostgreSQL encryption options](https://www.postgresql.org/docs/current/encryption-options.html)

PostgreSQL row policies are defense in depth. The application role must neither
own tables nor have superuser/BYPASSRLS privileges; scoped transaction context must
not leak through a reused connection. SQL filters must precede returned candidates,
reranking, caching and model use. Approximate pgvector search can under-return
after filtering; evaluate partitioning/iterative scans or exact search per scope.
[Row policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html),
[pgvector filtering](https://github.com/pgvector/pgvector#filtering)

## Model candidates and selection rules

The existing project evidence records Groq GPT-OSS 120B as the qualified public
route and local Qwen3 4B Q4_K_M as a provisional private route, with known quality
limits. This research did not call either provider or establish current account
availability. Catalog presence is not a latency or reliability test.
[Groq model documentation](https://console.groq.com/docs/model/openai/gpt-oss-120b),
[official Qwen quantized model](https://huggingface.co/Qwen/Qwen3-4B-GGUF)

For semantic recall, compare keyword-only retrieval against
[multilingual E5-small](https://huggingface.co/intfloat/multilingual-e5-small)
(384-dimensional output; bounded 512-token input) and, if its larger runtime fits,
[Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
(configurable dimensions up to 1024). Model-card multilingual coverage is not proof
of Tamil, transliterated Tamil or mixed English/Tamil accuracy. Pin the model and
tokenizer revision, normalization, dimension and quantization together. Do not
mix incompatible embeddings in one index. Sensitive embeddings stay inside the
approved private processing boundary; embeddings are not anonymized records.

Candidate promotion requires a held-out comparison under the same reader model,
record corpus, hardware, prompt budget and scoring method. Measure retrieval
recall, unsupported answers, update correctness, no-answer calibration, latency,
peak RAM and resource cost. Choose a Pareto improvement, not a leaderboard name.

## Additional operational sources

| Topic | Primary documentation | How it affects the design |
|---|---|---|
| Private remote access | [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve), [WebAuthn](https://www.w3.org/TR/webauthn-3/) | Private transport plus independently verified application identity; network membership alone is insufficient |
| iPhone actions | [Apple App Intents](https://developer.apple.com/documentation/AppIntents/AppIntent) | Future native actions use supported app capabilities; a web client cannot promise arbitrary iOS control |
| Speech transport | [NVIDIA Riva ASR](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/asr/asr-overview.html) | Streaming is a service capability to verify on the exact authorized endpoint, not a property inferred from a different model |
| Database recovery | [Postgres PITR](https://www.postgresql.org/docs/current/continuous-archiving.html), [SQLite backup](https://www.sqlite.org/backup.html) | Consistent backups; distinguish logical snapshots from continuous recovery |
| Independent copies | [restic checks](https://restic.readthedocs.io/en/stable/045_working_with_repos.html), [retention/pruning](https://restic.readthedocs.io/en/stable/060_forget.html) | Encrypt, check, restore and rotate copies; deleting a snapshot reference is not always immediate data removal |
| Memory poisoning | [OWASP prompt-injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) | Retrieved content and generated lessons are data, never authority to change tools, prompts or permissions |
| Diagnostics | [OpenTelemetry sensitive-data handling](https://opentelemetry.io/docs/security/handling-sensitive-data/) | Record timings, sizes and safe error codes; omit raw prompts, notes, audio and credentials |
| Engine limits | [SQLite limits](https://www.sqlite.org/limits.html), [PostgreSQL limits](https://www.postgresql.org/docs/current/limits.html) | Separate format limits from qualified operating capacity |
| Hosting limits | [Oracle Always Free policy](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) | Account entitlement, storage allocation and reclamation must be checked separately from OS resource counters |

Research access: Agent Reach's Exa CLI and updater are not installed; its Jina
reader failed DNS. Official-source web browsing supplied the fallback. No login,
cookie extraction, tool installation, social posting or external architecture
upload was performed. The source list intentionally favors papers and maintainer
documentation over social popularity. A newer publication is evidence to examine,
not a reason to replace a working feature.
