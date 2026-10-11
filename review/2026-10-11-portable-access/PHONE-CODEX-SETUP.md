# LYA development from a personal phone

Prepared 11 October 2026. This is the Codex Cloud route, separate from Oracle's
running LYA service. No Oracle resource or paid upgrade is needed for this setup;
Codex availability and usage depend on the owner's existing ChatGPT account.

## Current setup status

- Local repository identified: `Kathirvel2321/lya2.0`.
- Owner signed into ChatGPT and authorized GitHub. Actual setup UI confirms
  `Kathirvel2321` connected; only `Kathirvel2321/lya2.0` selected for this environment.
  The selector also lists another repository; connector-wide permission scope has
  not been independently verified as LYA-only.
- Cloud onboarding task created: `01a12bca-e801-7066-a8ac-a8e4a1e39044`, titled
  `Set up lya2.0`. Confirmed remote durable execution, not the personal Windows host.
  Only me access, zero network secrets and zero environment variables observed;
  Package managers network preset selected and visually confirmed saved.
  Setup agent received isolated-development boundaries. Setup report records Python
  3.12 with NumPy 2.5.4, 65 selected portable tests passing and 227 tracked Python
  files compiled at revision `e88f026950a6ed78b65cdc64b6d5a2ba768afcf9`.
  Suites: test_router, test_provider_setup, test_t02, test_answer_verification,
  test_research_adapter, test_approval, test_pointing. These are onboarding-agent
  results for the GitHub checkout, not checks of the newer local implementation.
  Windows win32crypt/DPAPI and winsound remain blockers without bypasses.
  Draft scripts saved and published after report/config review. Actual UI shows
  **Environment published**; evidence: `cloud-published.png` in this directory.
  Environment name: **lya2.0**. Setup task link:
  https://chatgpt.com/local/01a12bca-e801-7066-a8ac-a8e4a1e39044?hostId=local
  (This is the observed setup-chat URL; choose Cloud and the environment for new work.)
  Latest-source handoff and real phone/laptop-off acceptance remain pending.
- Latest source and tests include uncommitted/untracked work. GitHub checkout will
  not contain these changes until a reviewed development checkpoint is pushed.
- Do not bulk-upload the project folder. It contains ignored local configuration
  and keys. A private repository is not a credential store.
- No local secret transfer, production connection, Oracle resource, commit, push or
  production deployment performed. An OpenAI-hosted development environment was
  created/published using the connected account; existing account usage limits apply.

## One-time setup on personal desktop or web

1. Sign in to the personal ChatGPT account used on the phone.
2. Choose **Work in > Cloud > Select environment > Create environment**, or
   **Settings > Codex Cloud > Environments > Create environment**.
3. Connect GitHub if required. Review permissions and select only the LYA repository
   where the connector allows repository selection. Confirm repository visibility
   before uploading any new development work.
4. Start with **Only me** access, no secrets/environment credentials, no VPN or cloud
   identity, and network access limited to required package registries. Do not add
   Oracle SSH keys, provider keys, the native vault, backups or personal recordings.
5. Give the setup agent the prompt below. Review its report and actual compatible
   checks before publishing. Unavailable account features or usage must not trigger
   a purchase or upgrade automatically.
6. Save and select **Publish**. Wait for **Environment published**.

### Setup prompt

> Prepare this repository for isolated LYA development. Read AGENTS.md and
> lya-project-brain.md first. Preserve accepted Windows UI, voice, hearing, pause,
> models and startup. Use Python 3.11 or 3.12. Inspect dependencies and tests before
> running anything. Do not install the full Windows/audio/biometric requirements
> on Linux; install only dependencies required by the selected portable checks.
> Use fake providers, generated fake keys and temporary storage only. Do not run
> main.py, enroll anyone, access Oracle, call real providers or read a private vault.
> Do not bypass Windows DPAPI or silently substitute a fake crypto implementation
> in production code. Report Windows-only imports as blockers. First compile the
> selected source without importing it, then run only tests verified to be isolated
> and compatible. Report exactly what passed, what is missing from GitHub and what
> still requires Windows. No deployment, paid resources or automatic merge.

The existing memory/contract tests import native Windows fixtures indirectly.
Do not promise they run unchanged on Linux. A compilation pass is not a runtime
test or proof that LYA works in the cloud.

## Daily phone workflow

1. Open ChatGPT on the personal phone, using the same account/workspace.
2. Open **Codex**, select **Cloud**, then the published LYA environment. Mobile
   availability depends on rollout/workspace settings. If missing, check the web
   account's Cloud options; do not select the sleeping laptop as a substitute.
3. Reopen the same cloud task to continue its saved work. A new task starts its own
   workspace; this local desktop chat and uncommitted files do not transfer by magic.
4. Give one bounded task, for example:

> Read AGENTS.md and lya-project-brain.md. Tell me the latest implemented, tested
> and deferred status. Then fix [specific issue] without changing adjacent accepted
> features. Use fake data and isolated tests, show the diff and results, and update
> project continuity. Do not access production, deploy or merge.

5. Review the changed files and test results. Save important work to a development
   branch/PR after review. Cloud task state is not a permanent backup.
6. On the personal Windows laptop, fetch that branch and complete relevant native
   voice, UI and hardware checks before any release. Do not overwrite local edits.

## First phone acceptance check

After the environment has the reviewed latest source, ask for a read-only summary
of AGENTS.md and the latest project-brain entry. Verify it matches the expected
checkpoint. Turn off the personal laptop, then send a second read-only request in
the **same Cloud task**. Verify a response and inspect a small source diff before
using the workflow for valuable development. This real device check is pending.

Official instructions: [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)
and [Codex on mobile](https://learn.chatgpt.com/docs/mobile).
