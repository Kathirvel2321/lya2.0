# Set up LYA Connections on Windows

1. Open `launch-lya.cmd`. If LYA opens normally, right-click its Windows tray icon and select **Connections…**.
2. Choose **NVIDIA hearing**, paste the current NVIDIA API key, and click **Check and save key**. The check sends one second of generated silence to the selected NVIDIA hearing model. It does not use the microphone.
3. When LYA says the provider accepted the key and it was saved in Windows, click **Done**. Future launches on this Windows account can reuse the saved key without asking for your Bitwarden master password.

For Groq or OpenAI, select the provider and use **Check and save key**. The check asks the provider for its available models and confirms that the configured model is listed. It does not run a chat request. To switch public desktop chat, choose that provider under **Public chat after restart**, save and confirm the choice, then restart LYA. Cloud API charges may apply. **Current default (Oracle or local)** restores the preceding route. Private requests still use LYA's local model.

To rotate a key, paste the replacement in the same dialog. A failed check leaves the old saved key in place. Use **Remove saved key** to remove the local copy. This does not revoke a key with the provider. If the removed key was selected for public chat, choose the current default or save a replacement.

Windows Credential Manager stores the enrolled keys outside the project for this Windows account. Keep a backup in Bitwarden. The protection boundary against a coding agent is a separate Windows account and a trusted LYA installation the agent cannot edit. The same Windows account can read its own saved entries.

The desktop setup covers NVIDIA hearing, Groq, and OpenAI. Another supported feature can use its existing provider adapter and credential lookup. A new provider needs its own adapter and an explicit setup action. Separate phone, cloud server, and Telegram processes keep their existing credential setup. Check which settings those processes still need before retiring the old `.env`.

The [legacy Bitwarden session launcher](LYA_BITWARDEN_SECRETS.md) is still available.
