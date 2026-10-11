# Notion, Obsidian and low-local-storage placement

Clarification, 2026-10-11. The owner asked whether external platforms should help
because laptop capacity and Oracle free resources are finite. This is a placement
explanation, not authorization to connect accounts, export private content or
replace the proposed primary memory store.

| Platform | Useful role in LYA | What it does not solve |
|---|---|---|
| Oracle memory service | Small indexed authoritative selected facts, revisions, source references and authorized recall | Unlimited storage, guaranteed free hosting or independent disaster recovery |
| Notion | Optional cloud project notebook: approved research, decisions, tasks and links, published asynchronously | A low-latency transactional private brain; attachments and API use have limits |
| Obsidian | Optional small Markdown working notebook for approved material | Free remote disk capacity: vaults and their metadata are local |
| Google Drive or another approved file service | Candidate encrypted file/archive/recovery destination; core records keep opaque references | A database service, an unlimited free plan or automatic private-data authorization |
| External drive | Independent offline recovery copy with protected keys | Always-on phone access |

Recommended division: Oracle holds the compact live memory and indexes; selected
project material may be exported to Notion; large approved files and encrypted
backups go to an independently chosen file destination; Obsidian stays optional
and selective if local disk footprint is a concern. The live answer path does not
wait for Notion exports. Imports/edits from external notes are reviewed data, not
instructions that can change LYA authority. Correction/forgetting must propagate
to any exported copies; platform trash/history may delay physical removal.

Notion currently lists unlimited pages/blocks for an individual Free workspace,
5 MB per uploaded file and seven-day page history. Multi-member Free workspaces
have different block restrictions, including REST API enforcement. Their free
connection budget is 180 requests/minute, with additional workspace/endpoint
limits. Actual workspace membership and remaining capacity were not inspected.
[Pricing](https://www.notion.com/pricing),
[workspace limits](https://developers.notion.com/reference/workspace-block-limits),
[API limits](https://developers.notion.com/reference/request-limits).

Obsidian stores Markdown vault files on the local filesystem. The core app is free;
official Sync is a paid add-on. Syncing a vault does not make it remote-only, so
duplicating the whole corpus there conflicts with minimizing laptop/phone content.
[Storage behavior](https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data),
[pricing](https://obsidian.md/pricing).

Google advertises up to 15 GB per personal account shared across Drive, Gmail and
Photos. Available capacity depends on current use. Any sensitive backup would
be encrypted before upload, with recovery keys protected separately; no upload or
account inspection occurred here.
[Google storage](https://support.google.com/mail/answer/9312312?hl=en).

Read-only C-drive counter on this turn reports 269,190,983,680 free bytes, about
250.7 GiB. The earlier 1.16 GiB free reading was RAM, not disk. A different partition
or intended budget may still be constrained; do not assume all free disk should
be consumed by LYA. No folders were scanned or cleaned. Provider-free capacity
is finite even when a notebook plan calls individual text blocks unlimited.

Nothing was installed, connected or moved. External-platform export scope,
available account quotas, recovery destination and Oracle billing eligibility
remain unresolved. The existing full architecture is a proposal, and these
platforms are optional adapters rather than competing memory authorities.
