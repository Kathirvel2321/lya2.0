# LYA desktop credentials from Bitwarden

The normal Windows desktop launcher can now read only three provider passwords from the Bitwarden CLI: Groq, OpenAI and NVIDIA. It does not read every vault item or write anything to Bitwarden.

## Owner setup

1. In a PowerShell window outside the coding agent, sign the Bitwarden CLI in once with `bw login`.
2. Create a Bitwarden **Login** item for each provider you use. Put the API key in the item's **Password** field and use these exact item titles:

   | Provider | Item title |
   | --- | --- |
   | Groq | `LYA GROQ_API_KEY` |
   | OpenAI | `LYA OPENAI_API_KEY` |
   | NVIDIA speech | `LYA NVIDIA_API_KEY` |

3. Use each exact title once; duplicate matches are refused by the CLI.
4. Start LYA normally. If the CLI is signed in but locked, LYA asks for the Bitwarden master password in a hidden native dialog. The password is passed to the CLI through a temporary child-process environment variable, then discarded. LYA syncs the encrypted vault at startup and retrieves each requested password through `bw get password`.

The CLI must be on `PATH`. The current development machine has it available. The CLI's documented login, unlock, sync and password retrieval commands are described in the [official Bitwarden CLI guide](https://bitwarden.com/help/cli/).

## Scope and limits

- The default desktop chat path uses Groq and OpenAI; the hosted speech launcher uses NVIDIA. Bitwarden values take priority over process environment values. Existing environment and protected Groq-store fallbacks remain available.
- If Bitwarden is not signed in, locked with a failed password, or cannot sync, LYA continues without Bitwarden credentials. NVIDIA keeps its existing hidden session-key prompt; chat uses any existing environment/protected Groq value or its existing local fallback.
- Credentials are cached only in the running LYA process and forgotten when it exits. No credential or Bitwarden session is written to a project file. LYA does not send vault data to its model provider; provider keys are sent only to their respective API when that route is used.
- This first connection does not wire Supabase, phone tokens, TLS private keys, Telegram runner credentials, NTFY, or optional Gemini/Jina/You/Hugging Face integrations. Those belong to separate processes or are not part of the default desktop provider route.
- The project-root `.env` was not inspected or removed. The default NVIDIA launcher no longer reads it, but separate provider diagnostic tools still support it. Remove the file only after the owner has saved the needed replacements in Bitwarden and confirmed LYA can start from them.
- Bitwarden CLI and LYA still run as the same Windows user. This removes plaintext keys from the workspace, but it is not a hard boundary against arbitrary code running with that same user's permissions. Use a separate Windows account for stronger separation from a coding agent.

No Bitwarden vault, account state, credential value or live provider connection was accessed during implementation. Owner setup and a real launch remain pending.
