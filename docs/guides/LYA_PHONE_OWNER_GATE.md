# Register the first LYA owner from iPhone

The Windows app starts the invitation. Safari on the iPhone opens the private registration page and uses the phone’s passkey prompt. The direct phone gate is opt-in and uses an HTTPS hostname on the laptop. Keep the same hostname for later sign-in.

## Set up the private connection

1. On the laptop and iPhone, connect to your private Tailscale network. Restrict access to the laptop’s HTTPS service to your trusted devices. Enable HTTPS for Tailscale Serve.
2. On the laptop, make sure the HTTPS root is available for this gate. From PowerShell, run `tailscale serve --bg --https=443 http://127.0.0.1:8767`. Use the exact HTTPS URL shown for **this laptop**. LYA checks the mapping and refuses to show a QR if it is public through Funnel.
3. Install the desktop requirements in the environment that runs LYA. Phone recognition uses the existing isolated `.venv-owner` worker environment, verified YuNet and SFace model files, and pinned Resemblyzer weights. Without those assets the phone offers an explicit passkey-and-passphrase enrollment without recognition.
4. In the PowerShell session used to start LYA, set `$env:LYA_OWNER_PHONE_ORIGIN = 'https://laptop.your-tailnet.ts.net'` using the laptop’s actual URL without a trailing slash. Open LYA from that same session.

An existing LYA owner keeps their enrolled passkey path. Switching an existing owner would require a separately authorized migration. This setup does not reset the owner store. [Tailscale Serve documentation](https://tailscale.com/docs/reference/tailscale-cli/serve).

## Walk through registration

1. On the laptop, open owner access and select **Show registration QR**. The invitation expires in five minutes.
2. Scan the QR with the iPhone camera and open the page. Select **Create passkey**, then follow the phone’s verification prompt. The authenticator can use Face ID or another supported local verification method. [WebAuthn user verification](https://www.w3.org/TR/webauthn-3/).
3. Enter the eight-digit code displayed on the laptop, the name LYA should use, and a unique owner passphrase of at least 16 characters. Keep the passphrase in your password manager. Enter it silently on the phone. Submit the details, then confirm the new passkey.
4. Review the recognition explanation. To enroll it, explicitly grant camera access and take three guided face views. Then grant microphone access and record three short phrases. LYA pauses desktop hearing during setup and processes the samples with the laptop’s local models. Review the result and choose **Save profiles and finish**, or explicitly finish without profiles.
5. Return to the laptop. The first owner record is written only after signed confirmation and your decision about the profiles. Later sign-in uses the same private phone page, passphrase, and passkey. Protected laptop operations still ask for a fresh passkey signature for the exact action.

## What the gate stores

The laptop store holds the display name, public passkey, a salted scrypt verifier for the passphrase, and the derived face and voice recognition vectors if you save them. The store is encrypted and its key is protected by Windows DPAPI. Camera frames and recordings travel to the laptop over the private HTTPS connection for in-memory processing. The phone passkey’s private key and the phone’s own biometric verification data stay with the authenticator. Recognition is for personalization.

The QR token is carried in the URL fragment, expires, and is replaced after successful pairing. The phone page uses no third-party service to generate codes or process samples. Cancelling before final confirmation leaves the owner vault empty on a fresh installation. During a retry, the iPhone may still list a passkey created by the cancelled attempt.

Keep access to the phone’s passkey manager and your stored passphrase. The current gate has no passphrase reset flow.

## Turn on returning-owner notifications

1. On the laptop that owns the registration, install the updated desktop requirements in the Python environment that starts LYA. Keep its registered private Tailscale HTTPS address and Serve mapping available.
2. Say or type **Enable phone approvals** and choose the primary control in the setup window. For first use, scan the setup QR to open Safari. Use **Add to Home Screen** and open **LYA Owner** from the iPhone Home Screen.
3. Enter the eight-digit code shown on the laptop. Enter your existing LYA owner passphrase and verify with your iPhone passkey. Tap **Allow approval notifications**.
4. In a later LYA session, ask for a saved personal fact or an owner-only task. LYA sends a generic notification to the paired phone. Tap it, review the request, and verify on iPhone. Your phone chooses its verification method, so it can offer a device passcode when Face ID is unavailable.

After notification sign-in, LYA resumes the waiting request and keeps the owner session in memory until you close the LYA panel, enter guest mode, put LYA to sleep, or exit. Routine local note reads, new saves, and task-list commands use that session. Sensitive requests including deletion and supported data export ask for a fresh phone approval and the owner passphrase. The passphrase is entered on the phone.

Both devices need access to the laptop’s private Tailscale address during approval. The laptop must be awake and running LYA. This route uses the laptop’s existing private HTTPS endpoint with encrypted Apple Web Push for delivery. It works independently of the Oracle conversation service. Notification receipt and Face ID behavior need a live iPhone test. If a request expires or push delivery fails, retry from the laptop.
