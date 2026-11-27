# LYA desktop credentials from Bitwarden

The standard Windows LYA launcher reads Groq, OpenAI and NVIDIA credentials from Bitwarden. The desktop can also save the NVIDIA credential after fresh phone approval.

## Owner setup

1. In a PowerShell window outside the coding agent, sign the Bitwarden CLI in once with `bw login`.
2. For manual setup, create a Bitwarden **Login** item for each provider you use. Put the API key in the item's **Password** field and use these exact item titles:

   | Provider | Item title |
   | --- | --- |
   | Groq | `LYA GROQ_API_KEY` |
   | OpenAI | `LYA OPENAI_API_KEY` |
   | NVIDIA speech | `LYA NVIDIA_API_KEY` |

3. Use each exact title once; duplicate matches are refused by the CLI.
4. Start LYA normally. If the CLI is signed in but locked, LYA asks for the Bitwarden master password in a hidden native dialog. The password is passed to the CLI through a temporary child-process environment variable, then discarded. LYA syncs the encrypted vault at startup and retrieves each requested password through `bw get password`.

The CLI must be on `PATH`. Check with `bw --version`. The CLI's login, unlock, sync, retrieval and save commands are described in the [official Bitwarden CLI guide](https://bitwarden.com/help/cli/).

## Save the NVIDIA key from the glass panel

1. Open LYA with the standard launcher and unlock Bitwarden for this session. Set up [iPhone notifications in LYA](LYA_PHONE_OWNER_GATE.md#turn-on-returning-owner-notifications) if they are not already connected. Use normal mode for the save so LYA can contact Bitwarden.
2. Say or type “Add NVIDIA key” or “I want to add a secret.” If LYA is in guest mode, approve owner sign-in first.
3. Enter the NVIDIA key in the masked field and select **Save**. Use the field for the value and chat for the command.
4. Review and approve the save on your iPhone. LYA creates the personal NVIDIA Login item or updates the password in the one existing item with that exact title. NVIDIA speech uses the saved value for later requests when NVIDIA speech is enabled.

The phone sees the action description. The typed value goes from the local form to Bitwarden through the CLI's standard input. LYA sends it to NVIDIA only when authenticating an NVIDIA request. If LYA cannot confirm a save, check the vault item before trying again.

## Scope and limits

- The default desktop chat path uses Groq and OpenAI; the hosted speech launcher uses NVIDIA. Bitwarden values take priority over process environment values. Existing environment and protected Groq-store fallbacks remain available.
- If Bitwarden is not signed in, locked with a failed password, or cannot sync, LYA continues without Bitwarden credentials. NVIDIA keeps its existing hidden session-key prompt; chat uses any existing environment/protected Groq value or its existing local fallback.
- Credentials are cached only in the running LYA process and forgotten when it exits. No credential or Bitwarden session is written to a project file. LYA does not send vault data to its model provider; provider keys are sent only to their respective API when that route is used.
- This first connection does not wire Supabase, phone tokens, TLS private keys, Telegram runner credentials, NTFY, or optional Gemini/Jina/You/Hugging Face integrations. Those belong to separate processes or are not part of the default desktop provider route.
- The project-root `.env` was not inspected or removed. The default NVIDIA launcher no longer reads it, but separate provider diagnostic tools still support it. Remove the file only after the owner has saved the needed replacements in Bitwarden and confirmed LYA can start from them.
- Bitwarden CLI and LYA still run as the same Windows user. This removes plaintext keys from the workspace, but it is not a hard boundary against arbitrary code running with that same user's permissions. Use a separate Windows account for stronger separation from a coding agent.

Development uses simulated Bitwarden CLI output and signed phone approval fixtures. Verify actual iPhone delivery and vault changes on the owner's device before migrating the existing file.
