"""Direct, owner-selected providers for the Windows desktop."""
import json
import os
import threading
from urllib import error, request

from cloud.probe_models import NoRedirect
from security import provider_credentials


CHAT = {
    "GROQ_API_KEY": ("Groq", "https://api.groq.com/openai/v1", "LYA_GROQ_MODEL", "llama-3.3-70b-versatile"),
    "OPENAI_API_KEY": ("OpenAI", "https://api.openai.com/v1", "LYA_MODEL", "gpt-4o-mini"),
}
HEARING = "NVIDIA_API_KEY"
LABELS = {HEARING: "NVIDIA hearing", **{name: item[0] for name, item in CHAT.items()}}
CHAT_CHOICE = "PublicChatProvider"


def _model(name):
    _, _, setting, default = CHAT[name]
    return os.environ.get(setting, "").strip() or default


def _json(url, key, payload=None):
    headers = {"Authorization": "Bearer " + key, "User-Agent": "LYA/1.0"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    with opener.open(request.Request(url, data=data, headers=headers), timeout=10) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Provider response is too large.")
        return json.loads(raw)


def check_key(name, key, nvidia_model=None, cancelled=None):
    if name not in LABELS or not key or len(key) > 2048 or any(not 33 <= ord(c) <= 126 for c in key):
        raise ConnectionError("Enter a valid API key.")
    if name == HEARING:
        from audio import nvidia_asr
        from audio.voice import RecognitionUncertain

        model = nvidia_model or os.environ.get("LYA_NVIDIA_ASR", "parakeet")
        try:
            # The speech service should return successfully with no recognized words.
            nvidia_asr._recognize(bytes(32000), key, model, cancelled or threading.Event())
        except RecognitionUncertain:
            pass
        except Exception:
            raise ConnectionError("NVIDIA hearing could not verify the key. Check the key and try again.") from None
        return

    label, base, _, _ = CHAT[name]
    try:
        models = _json(base + "/models", key)["data"]
        found = any(item.get("id") == _model(name) for item in models)
    except error.HTTPError as exc:
        message = "rejected access with this key" if exc.code in (401, 403) else "could not verify the key"
        raise ConnectionError(f"{label} {message}. Check the key and try again.") from None
    except Exception:
        raise ConnectionError(f"{label} could not be reached or returned an unexpected response.") from None
    if not found:
        raise ConnectionError(f"{label} accepted the key but did not list the configured chat model.")


class PublicModel:
    def __init__(self, name):
        self.name = name
        self.description = CHAT[name][0] + " public chat"

    def invoke(self, messages, *, task="general", sensitivity="private"):
        from brain.workflow import ModelUnavailable

        if sensitivity != "public":
            raise ModelUnavailable("This connection is available only for public chat.")
        label, base, _, _ = CHAT[self.name]
        key = provider_credentials.read(self.name)
        if not key:
            raise ModelUnavailable(f"{label} has no saved key. Open Connections or choose the current default.")
        try:
            response = _json(base + "/chat/completions", key, {
                "model": _model(self.name),
                "messages": messages,
                "max_completion_tokens": 600,
            })
            answer = response["choices"][0]["message"]["content"].strip()
            if answer:
                return answer
        except error.HTTPError as exc:
            if exc.code in (401, 403):
                raise ModelUnavailable(f"{label} rejected the request. Check the key in Connections.") from None
        except Exception:
            pass
        raise ModelUnavailable(f"{label} could not answer. Check Connections or choose the current default.")
