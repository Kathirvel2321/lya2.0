# Manual verification and safe access from another laptop

11 October 2026. The owner asked for manual checks and portable LYA access without
creating new provider accounts or copying laptop-bound secrets. The second laptop
is **work-managed**, so it is a different trust boundary from the personal laptop.
This guide adds a fake-data walkthrough and an access proposal. It does not upload
secrets, migrate private records, enroll real devices or change running behavior.

## Manually verify the new memory pieces

On the **personal laptop**, open PowerShell in the LYA project folder and run:

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-11-portable-access/manual_demo.py
```

Press Enter at each step and read the printed outcome:

| Step | Expected visible result |
|---|---|
| Laptop adapter saves a fake preference; phone adapter reads it | `SYNTHETIC_BLUE`, revision 1 |
| Phone adapter corrects it; database reopens; laptop adapter reads | `SYNTHETIC_GREEN`, revision 2 |
| Phone adapter forgets it; laptop adapter reads/searches | `None` and empty search |
| Fake clock advances; old encrypted backup restores with latest trusted checkpoint | One deleted and one expired record suppressed; zero active bindings and resumed jobs |

These are generated signed fake passkey fixtures and simulated adapters on one
computer, **not two physical devices**. No real owner verification, provider,
microphone/camera, private store or Oracle connection occurs. The encryption key,
backup and databases are temporary and removed on exit/Ctrl+C; do not enter any
personal information. Fixture `approved=True` is a test boundary, not real consent.
Backup files are encrypted; the disposable database remains plaintext.

For detailed pass/fail names, run:

```powershell
.\.venv-ui\Scripts\python.exe -m unittest test_conversation_contract test_memory_prototype test_memory_recovery -v
```

The previous [combined checkpoint](../2026-10-11-implementation-checkpoint/README.md)
also provides the broader 82-test/client/layout/network runner. Its results do not
mean the isolated memory code is available in the live LYA interface.

## Manually check the existing live app

Use the already paired personal phone and existing private LYA address. Sign in
with its existing passkey; do not create another owner or rerun pairing. Ask a
harmless question, check the reply/voice, then use the visible Stop button during
a longer answer. Lock the page and confirm another question requires sign-in.
Check Talk/Start conversation only when you choose to grant microphone consent.
These manual interactions use the existing provider quota; the agent did not run
them or record your voice. Do not test with a password or private fact.

The laptop-sleep check is optional and remains owner-deferred until chosen: with
Oracle and the phone's private network connected, sleep the personal laptop and
ask another harmless phone question. Record the result, including any failure.
This tests the existing public server route, not shared private memory. Device
actions on a sleeping laptop remain unavailable. New selective-memory UI testing
comes after its adapters are connected; asking the live app to remember something
today will not exercise the new isolated prototype.

## Why a GitHub clone is insufficient today

Source inspection finds:

- [brain/oracle.py](../../brain/oracle.py) uses ignored local host configuration,
  a private SSH key and pinned known-hosts data. They are deliberately outside Git.
- [security/vault.py](../../security/vault.py) wraps its encryption key with Windows
  DPAPI. Normally that protection is bound to the Windows user/computer; copying
  the wrapped file is not a portable decryption or account-recovery workflow.
  Microsoft's [DPAPI documentation](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)
  describes the binding and roaming-profile exception.
- [cloud/mobile_runtime.py](../../cloud/mobile_runtime.py) already calls existing
  server inference and speech workers; the deployed public phone route does not
  need the laptop's private vault or a provider key on the phone.
- [cloud/mobile.py](../../cloud/mobile.py) currently supports one paired service
  credential and separate short-lived sessions, not a per-device enrollment and
  revocation registry. Its owner verification still grants only public-chat scope.
- [.gitignore](../../.gitignore) excludes runtime secrets/private stores/models.
  A targeted current Git-index filename check found none of the named secret-file
  patterns tracked; this is not a repository-history or full secret-content audit.

The solution is to separate a server's application credentials from each client's
authentication. One set of provider accounts can serve authorized devices within
its quotas/terms; a new laptop does not inherently require a new provider account.
Each client still needs a revocable application session. Moving credentials does
not move Windows-only tools, local model assets or private authorization to Linux.

## Recommended placement

| Item | Recommended home | Work laptop |
|---|---|---|
| Source code and safe setup templates | GitHub | Code only if workplace policy permits development there |
| Provider API keys | Existing protected Oracle worker/service account; scoped permissions and rotation | Never deliver them to the browser/client |
| Oracle SSH/operator key | Personal administration device; separate from app login | No copy, download or server-shell access |
| Passkey private material | Personal phone/authenticator | Prefer cross-device sign-in without saving/syncing it onto the managed device |
| Short-lived LYA session | Each authorized client separately | Public-chat-only, clear/revoke on exit; no owner/private tool grant |
| New selected shared records | Planned separate encrypted Oracle store after scope/recovery gates | No personal confidential-memory access by default |
| Existing local vault, biometrics, photos and DPAPI key | Preserve current personal-laptop protection | No migration or copied identity database |
| Recovery key and independent encrypted backup | Separate protected recovery arrangements outside the sole Oracle host/account | No recovery material |

The server must decrypt any records it processes in plaintext: encryption at rest
does not hide them from a compromised server/admin with the decryption key. This
is why the shared-record scope must be selected and why secrets must stay out of
ordinary model prompts. A lost sole Oracle account must not also lose every backup
and recovery key. No paid service or new Oracle resource is proposed for immediate
provisioning; actual free-tier entitlement remains unverified.

See [the editable boundary diagram](access-boundaries.mmd). Solid nodes represent
existing components; amber/dashed nodes are proposed. Work access is not tested.

## Work-managed laptop: limited browser access

Treat a managed endpoint as unsuitable for personal secrets: organization-managed
security software/browser policies may audit or restrict activity. Microsoft's
[Endpoint DLP documentation](https://learn.microsoft.com/en-us/purview/endpoint-dlp-learn-about)
is one example; it does not prove which controls your employer uses. A phone
approval or private/incognito window cannot guarantee confidentiality once text
is typed or displayed on that endpoint.

If workplace policy permits access, use the existing public-chat browser interface
with no saved personal credentials or private-memory/admin access. FIDO supports
[cross-device passkey authentication](https://fidoalliance.org/passkeys-2/): a phone
can authenticate a browser using a QR/proximity flow where the browser, phone and
policies support it. Use the already paired HTTPS credential, not the native
localhost credential. This is a candidate manual compatibility check, not an
integration we have verified on the work laptop. Do not re-pair/reset the phone.

The current URL is private to Tailscale. An ordinary work browser cannot reach it
just because it has the URL or a passkey. It needs an IT-permitted network path.
Do not install a VPN, add the laptop to the personal tailnet or expose LYA publicly
without permission. If later allowed, restrict access to the LYA HTTPS service,
not the home laptop, SSH, admin interfaces or entire tailnet. Tailscale provides
[device approval](https://tailscale.com/docs/features/access-control/device-management/device-approval)
and [access control](https://tailscale.com/docs/concepts/device-visibility);
approval alone is not a least-privilege policy. Their actual configuration was not
inspected/changed here. If workplace policy does not permit a path, use the
personal phone for LYA instead.

## Implementation order for portability

1. Keep the accepted personal laptop and phone working. Complete manual checks
   above; record which are live-device tests and which are simulations.
2. Confirm approved shared-record scope, independent free recovery/key custody
   and actual Oracle free eligibility; qualify encrypted live storage.
3. Build a narrow authenticated HTTPS client/backend path for personal desktops,
   reusing existing server providers. Separate app sessions from operator SSH;
   qualify identity mapping, revocation and Stop before switching an accepted path.
4. Add exact owner-approved device/session grants and a revocation registry before
   giving multiple devices different private capabilities. Keep public work-browser
   sessions separate and limited; no client-supplied trust flag grants authority.
5. Connect only the selected shared memory and test save/correct/forget across real
   permitted devices, including outages, restart and laptop-off behavior.
6. If the employer permits the necessary network/browser access, test the existing
   public interface on the work laptop with the personal phone's passkey. It can be
   explored earlier as public-chat-only; it does not depend on moving all secrets.

Manual-demo assertions pass in `--auto` mode. The boundary diagram passes structural
Mermaid validation with no warnings; full graphical rendering was not qualified.
Agent Reach CLI/mcporter were unavailable, so official-source web fallback supplied
the current security/platform references. No secret contents were read or copied,
no real device enrolled and no provider, runtime or server migration performed.
