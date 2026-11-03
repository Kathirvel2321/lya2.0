# LYA recovery storage recommendation — 2026-10-17

Status: researched proposal, no account selected or connected. The owner confirms having Google Drive and OneDrive and asks whether a more advanced cloud would suit LYA. Account quotas, subscription status and recovery access have not been inspected. Password-manager setup remains pending.

## Recommendation

Evaluate **Backblaze B2 Cloud Storage** first for automated encrypted recovery artifacts. Its object retention and narrowly restricted application keys suit backup protection. Keep one existing Drive service as an optional second encrypted copy. Until a new service is chosen and qualified, existing Google Drive plus OneDrive are a reasonable proposed starting point for copied artifacts; neither is currently connected. This recommendation concerns recovery storage, not moving LYA's models, live database or runtime.

| Candidate | Official allowance/features reviewed | Fit for LYA |
| --- | --- | --- |
| Google Drive | Personal storage is advertised as up to 15 GB, shared with Gmail/Photos. Ordinary uploaded-file versions may disappear after 30 days or 100 newer versions unless pinned. [Quota](https://support.google.com/mail/answer/6374270?hl=en), [versions](https://support.google.com/drive/answer/2409045?hl=en). | Existing account; convenient additional encrypted copy. Actual free space is unknown. Sync/version history alone is insufficient recovery protection. |
| OneDrive | Free accounts have 5 GB shared Microsoft cloud storage. Restoring the entire OneDrive over the preceding 30 days requires Microsoft 365. [Quota](https://support.microsoft.com/en-au/onedrive/microsoft-storage-faqs), [restore](https://support.microsoft.com/en-us/onedrive/restore-your-onedrive). | Existing second provider. Do not assume the owner has paid restore features or spare quota. |
| Backblaze B2 | Official transaction documentation lists the first 10 GB free, and signup requires no credit card. Object Lock provides governance/compliance retention; application keys can be limited by bucket, prefix and capabilities. [Allowance](https://www.backblaze.com/cloud-storage/transaction-pricing), [signup](https://www.backblaze.com/sign-up/cloud-storage), [retention](https://www.backblaze.com/docs/cloud-storage-object-lock), [keys](https://www.backblaze.com/docs/cloud-storage-application-keys). | Preferred dedicated backup candidate: programmable copies and deletion protection independent of the existing Oracle account. New account and live qualification are still required. |
| Cloudflare R2 Standard | Monthly free allowance: 10 GB-month, one million Class A and ten million Class B operations; no egress charge. Signup requires an R2 subscription checkout. Bucket retention rules exist but administrators can remove them. [Pricing](https://developers.cloudflare.com/r2/pricing/), [setup](https://developers.cloudflare.com/r2/get-started/), [locks](https://developers.cloudflare.com/r2/buckets/bucket-locks/). | Strong alternative, especially for frequent downloads. Metered storage/operations and removable retention rules must be understood. Not preferred over B2 for this backup-focused first evaluation. |
| Oracle Object Storage | Official Always Free documentation advertises 20 GB combined object-storage tiers. [Allowance](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm). | Potential extra copy, subject to actual tenancy quota. A bucket in the same Oracle account would retain account-wide failure risk; do not make it the only recovery destination for an Oracle-hosted authority. |

These are public advertised allowances, not measured owner entitlements or a promise of permanent zero cost. B2's pricing page currently lists $6.95/TB/month while its transaction page retains an older $0.005/GB/month note. Recheck actual account pricing before any paid use; no paid use is proposed. [Current pricing](https://www.backblaze.com/cloud-storage/pricing). B2 caps are separate from alerts; Class D event notifications cannot be capped. Free allowance and alerts do not establish a tested zero-spend guarantee. [Caps](https://www.backblaze.com/docs/cloud-storage-data-caps-and-alerts). R2 is also metered above its allowances.

## What this does and does not place

The existing [synthetic recovery pack](../../docs/guides/LYA_MEMORY_RECOVERY_PACK.md) contains three encrypted artifacts, bounded to eight MiB total. One hundred maximum-sized packs total 800 MiB before any additional provider versions, failed uploads or other account data. Retention must count all of those; a per-pack bound is not an account quota.

Keep the unlock key separately from cloud artifacts and service credentials. Bitwarden Free is a candidate for protected secure notes and encrypted exports, not an installed or selected manager. [Official plan](https://bitwarden.com/help/password-manager-plans/). Its account recovery and an independent offline recovery method need a separate setup decision. Do not put unlock keys in chat, source, the ledger, a pack folder or an uploader's configuration.

The live encrypted authority, protected catalogue/owner mappings and fresh latest-state witness have separate placement requirements. A copied cloud folder is not an implementation of LYA's generation reservations, compare-and-swap and writer fencing. Current witness code is synthetic and loopback-only. No candidate above has been qualified as a witness. The pack still restores records into quarantine; it cannot recreate trusted authority metadata or resume devices/jobs.

Provider retention preserves old bytes; it does not prove which backup is latest. Recovery must obtain fresh independent pins. An old backup plus old pins can still be rolled back together. A daily extra copy also cannot establish remote survival of every acknowledged write: publication order, independent acknowledgement and failure reconciliation must be qualified before claiming that guarantee.

## Concrete next evaluation

After the owner chooses a provider, verify its actual free allowance and recovery access, then use a private fake-data destination. For B2, propose a bucket/prefix-limited uploader without delete, key-management or governance-bypass permissions; retain administration separately. Validate exact permissions through actual refused operations. Read uploaded bytes back, match independent digests and perform the existing quarantined restore on an independent host. Exercise partial uploads, stale/corrupt copies, quota refusal, unavailable trust and revoked credentials before private use.

Do not enable indefinite retention or compliance locks as a default. B2 Object Lock enablement cannot be disabled for the bucket; compliance retention cannot be shortened by users. A finite retention proposal needs owner review and fake-data validation first. Retained historical encrypted snapshots may still contain subsequently forgotten information; tested restore suppression is not physical erasure or destruction of old keys.

## Evidence and limits

Reviewed public primary documentation and current pack/witness source. Agent Reach's search executables were absent; its Jina reader route failed DNS resolution in the shell, so official pages were read with the available web tool. No installation or backend update was performed. No signed-in account, billing dashboard, latency, region availability, upload, download, retention operation or independent recovery was tested. Documentation-only task: no runtime tests rerun and no integration or zero-cost guarantee claimed.

Decision remains proposed. Next: owner provider choice, then account allowance/custody setup and an explicitly scoped fake-data remote qualification. No real key, account, cloud object, subscription, service, deployment or accepted assistant feature changed.

## B2 account readiness — follow-up on 2026-10-17

The owner requested the next step after the recommendation. Prepared B2 account-readiness instructions; no account creation, binding or remote test has occurred. Plugin discovery for Backblaze B2 returned unrelated business-sales tools, with no relevant connection among the results; that search is not an exhaustive directory inventory. No plugin was suggested or installed.

Owner steps:

1. Open the official [B2 signup page](https://www.backblaze.com/sign-up/cloud-storage). If you already have a Backblaze account, use its sign-in link instead.
2. Follow the account flow and verify your email. The documented flow includes region selection and acceptance of provider terms; those are owner account choices. Use your own browser for passwords and verification codes. [Official account instructions](https://www.backblaze.com/docs/cloud-storage-enable-backblaze-b2).
3. Keep this evaluation within the free account offer; signup advertises no credit card required. Do not add a payment method or select a paid upgrade for this work. If the flow requires payment, leave it pending and report that requirement rather than accepting it.
4. Review your account security settings and retain recovery access separately from this laptop. Backblaze documents email MFA and authenticator-based options. [Account security](https://www.backblaze.com/computer-backup/docs/account-security). Password-manager selection/setup remains pending; no real LYA unlock key should be generated yet.
5. Report only that the account is ready, the displayed free storage allowance and whether a payment method is required. Do not send passwords, login codes, recovery codes or API keys. Leave buckets, application keys, retention locks and uploads for the scoped fake-data qualification.

The next technical acceptance target is a private destination with restricted uploader permissions, actual uploaded-byte readback and quarantined restore using fake artifacts. Its allowance and permissions must be verified first. No existing synthetic API is approved for real memory merely because the account is ready. See the separate witness/catalogue and retention limitations above.

This follow-up checked public signup, account/security and cap documentation, plus plugin discovery. Local documentation checks are recorded in [follow-up static validation](b2-setup-static-validation.json). No account, billing entitlement, region performance, cloud upload/download, denial behavior or independent restore was tested; runtime tests were not rerun for these instructions.
