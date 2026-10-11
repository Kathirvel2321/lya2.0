# Clarification: develop LYA from phone and work laptop

11 October 2026. The owner clarified that the goal is to **build LYA during free
time from the phone and work-managed laptop**, not merely access the running
assistant. This supersedes the prior assumption about the primary purpose of
second-laptop access. It does not approve production secret migration or deployment.

Recommended candidate: one isolated remote development workspace on the existing
Oracle host, with a browser editor/terminal such as open-source code-server. The
phone/personal laptop and an employer-permitted work browser access the same
development workspace; code, installed development tools and supported tests stay
on the server. GitHub remains version control, rather than a secret transport.
[code-server documentation](https://coder.com/docs/code-server) describes browser
editing and terminal access. iPhone keyboard/layout/session behavior must be tested;
documented iPad support is not proof of comfortable iPhone operation.

The development environment must be separated from live LYA: no production
provider keys, native vault, administrator SSH key, recovery key or deployment
authority in its editor account. Fake providers and test data cover development;
approved integration tests can use separately scoped test credentials if needed
later. A browser IDE grants terminal access, so protect it with authentication,
private HTTPS and narrow access. Never publish its terminal openly.
[code-server security guidance](https://coder.com/docs/code-server/guide) explains
why authentication/encryption are necessary. Same-host account separation reduces
exposure but does not isolate kernel compromise; enforce resource limits and
verify permissions before use. No new VM, paid resource or resize is authorized.

Workplace permission still applies. Managed-browser software can observe editor
content and capture a powerful development session even when passwords/provider
keys are not copied to the laptop. Use the personal phone when work access is not
permitted. Do not bypass workplace network controls or expose the private editor
publicly just to make the work browser connect.

What can be done remotely: edit code, inspect diffs, run compatible backend tests,
review changes and commit approved work. Current signed native fixture tests import
Windows-specific vault/storage code; they cannot be promised to run unchanged on
Oracle Linux. Portable test fixtures need qualification. Windows UI, wake/voice,
camera and real hardware acceptance still require the personal Windows laptop.
A browser editor alone does not provide an AI coding agent or connect this desktop
chat automatically to another device.

Immediate edit-only option: open the owner's repository in github.dev using a
supported phone browser. It can edit and commit code but has no terminal or compute
for running LYA/tests. See [GitHub's editor documentation](https://docs.github.com/en/codespaces/the-githubdev-web-based-editor).
Do not mistake this for a runnable development workspace; phone usability remains
device/browser-dependent.

Implementation order: inventory and safely checkpoint current local work to an
approved development branch (uncommitted local files are not automatically on
GitHub); qualify isolated Oracle development permissions/resources; protect a
browser IDE with private access; test the personal iPhone; port the needed fake
backend checks; then try the work browser only with employer permission. Keep
production release and Windows acceptance separate. Real provider APIs do not need
to be recreated for every editing device.

Status: researched proposal only. No branch/commit/push, installation, resource
change, credential transfer, remote workspace, AI agent or deployment performed.
