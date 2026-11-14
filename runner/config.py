"""Configuration loading for the LYA Remote Runner.

config.local.json (gitignored) holds real values:
  {
    "projects": {"name": "C:/abs/path"},
    "agent_command": ["python", "-m", "my_agent"],   # placeholder until owner answers
    "task_timeout_seconds": 1200
  }

config.example.json ships with fake values. Nothing here prints secrets;
the .env values are read only inside config.owner_ids().
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL = HERE / "config.local.json"
EXAMPLE = HERE / "config.example.json"

DEFAULT_TIMEOUT = 1200          # 20 minutes
DEFAULT_RATE_LIMIT = 10         # commands per minute


class ConfigError(RuntimeError):
    pass


def load_local():
    """Config dict, or raise ConfigError with a variable-name-only message."""
    if not LOCAL.is_file():
        raise ConfigError(
            "config.local.json is missing. Copy config.example.json to "
            "config.local.json and fill in your real values.")
    try:
        data = json.loads(LOCAL.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ConfigError("config.local.json is malformed JSON.") from exc
    if not isinstance(data, dict):
        raise ConfigError("config.local.json must contain a JSON object.")
    return data


def owner_ids():
    """(bot_token, owner_chat_id) from .env. Values are never logged."""
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat = (os.environ.get("OWNER_CHAT_ID") or "").strip()
    problems = []
    if not token:
        problems.append("TELEGRAM_BOT_TOKEN is missing in runner/.env")
    elif ":" not in token:
        problems.append("TELEGRAM_BOT_TOKEN is malformed (expected '<id>:<hash>')")
    if not chat:
        problems.append("OWNER_CHAT_ID is missing in runner/.env")
    elif not chat.isdigit():
        problems.append("OWNER_CHAT_ID is malformed (expected a numeric chat id)")
    if problems:
        raise ConfigError("; ".join(problems))
    return token, int(chat)


def timeout_seconds(local):
    value = local.get("task_timeout_seconds", DEFAULT_TIMEOUT)
    if not isinstance(value, int) or not (30 <= value <= 4 * 3600):
        raise ConfigError("task_timeout_seconds must be an integer between 30 and 14400.")
    return value


def rate_limit(local):
    value = local.get("rate_limit_per_minute", DEFAULT_RATE_LIMIT)
    if not isinstance(value, int) or not (1 <= value <= 60):
        raise ConfigError("rate_limit_per_minute must be an integer between 1 and 60.")
    return value


def agent_command(local):
    value = local.get("agent_command")
    if not isinstance(value, list) or not value or \
            not all(isinstance(part, str) and part for part in value):
        raise ConfigError("agent_command must be a non-empty list of strings "
                          "(placeholder is fine until the owner picks the tool).")
    return value


def projects(local):
    raw = local.get("projects")
    if not isinstance(raw, dict) or not raw:
        raise ConfigError("projects must map at least one project name to an absolute path.")
    from runner.security import normalize_project_root
    out = {}
    for name, path in raw.items():
        if not isinstance(name, str) or not re_fullmatch_name(name):
            raise ConfigError(f"Project name {name!r} must be 1-40 chars of a-z0-9_- .")
        try:
            root = normalize_project_root(Path(path))
        except ValueError as exc:
            raise ConfigError(f"Project {name!r}: {exc}") from None
        out[name] = root
    return out


def re_fullmatch_name(name):
    import re
    return re.fullmatch(r"[a-z0-9_-]{1,40}", name) is not None
