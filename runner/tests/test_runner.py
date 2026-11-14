"""Tests for the LYA Remote Runner. Telegram and the agent are mocked.
No network, no real token, no writes outside tmp dirs.
"""
import os
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from runner import config as cfg            # noqa: E402
from runner.audit import Auditor            # noqa: E402
from runner import commands as C            # noqa: E402
from runner import jobs as J                # noqa: E402
from runner import security as S            # noqa: E402


# ---- fixtures -------------------------------------------------------------
class FakeUser:
    def __init__(self, uid): self.id = uid


class FakeChat:
    def __init__(self, cid): self.id = cid


class FakeMsg:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kw):
        self.replies.append(text)
        return self


class FakeUpdate:
    def __init__(self, uid, cid):
        self.effective_user = FakeUser(uid)
        self.effective_chat = FakeChat(cid)
        self.effective_message = FakeMsg()


class FakeCtx:
    def __init__(self, args):
        self.args = args


@pytest.fixture
def owner_env(tmp_path):
    local = {"projects": {"alpha": str(tmp_path / "alpha")},
             "agent_command": ["echo-agent"],
             "task_timeout_seconds": 60,
             "rate_limit_per_minute": 60}
    project = tmp_path / "alpha"
    project.mkdir(exist_ok=True)
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.name", "t"],
                   check=True)
    (project / "f.txt").write_text("hello\n")
    subprocess.run(["git", "-C", str(project), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(project), "commit", "-qm", "init"], check=True)
    return local, project


def make_handlers(owner_env, monkeypatch):
    local, project = owner_env
    auditor = Auditor(HERE.parent / "logs")     # logs land in runner/logs (gitignored)
    manager = J.JobManager(["fake-agent"], 60, auditor=auditor)
    h = C.Handlers(local, manager, auditor)
    h.bind_owner(999)
    return h, manager, project


# ---- ownership -------------------------------------------------------------
@pytest.mark.asyncio
async def test_unknown_sender_ignored(owner_env):
    h, _, _ = make_handlers(owner_env, None)
    upd = FakeUpdate(111, 999)                 # right chat, wrong user
    await h.cmd_status(upd, FakeCtx([]))
    upd2 = FakeUpdate(999, 111)                # right user, wrong chat
    await h.cmd_status(upd2, FakeCtx([]))
    assert upd.effective_message.replies == []
    assert upd2.effective_message.replies == []


@pytest.mark.asyncio
async def test_owner_gets_status(owner_env):
    h, _, _ = make_handlers(owner_env, None)
    upd = FakeUpdate(999, 999)
    await h.cmd_status(upd, FakeCtx([]))
    assert "Uptime" in upd.effective_message.replies[0]


# ---- path containment ------------------------------------------------------
def test_dotdot_escape_rejected(owner_env):
    _, project = owner_env
    with pytest.raises(S.PathOutsideAllowlist):
        S.resolve_inside(project, "../outside.txt")


def test_absolute_rejected(owner_env):
    _, project = owner_env
    with pytest.raises(S.PathOutsideAllowlist):
        S.resolve_inside(project, "C:/Windows")


def test_symlink_escape_rejected(owner_env, tmp_path):
    _, project = owner_env
    outside = tmp_path / "outside"
    outside.mkdir()
    link = project / "link"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except OSError:
        pytest.skip("symlink privileges unavailable")
    with pytest.raises(S.PathOutsideAllowlist):
        S.resolve_inside(project, "link")


def test_unc_root_refused(tmp_path):
    with pytest.raises(ValueError):
        S.normalize_project_root(Path("//server/share"))


# ---- shell safety ----------------------------------------------------------
@pytest.mark.skipif(os.name != "nt", reason="windows-specific")
def test_user_text_never_reaches_shell(owner_env, monkeypatch):
    _, project = owner_env
    manager = J.JobManager(["fake-agent"], 60)
    captured = {}

    def fake_popen(argv, **kw):
        captured["argv"] = argv
        captured["shell"] = kw.get("shell")
        class P:
            pid = 0
            def poll(self): return 0
            def communicate(self, timeout=None): return (b"", b"")
            def wait(self, timeout=None): return 0
            def kill(self): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return P()

    monkeypatch.setattr(J.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(J, "git_run", lambda root, *a, **kw: mock.Mock(
        returncode=0, stdout="true"))
    manager._checkpoint = lambda root, job: setattr(job, "checkpoint", "HEAD")
    manager.start("alpha", project, "evil && format C:")
    for _ in range(50):
        if manager.status_line() is None:
            break
        time.sleep(0.02)
    assert captured.get("shell", False) is False
    # the task travels as ONE argv element after --task
    assert captured["argv"][-2] == "--task"
    assert captured["argv"][-1] == "evil && format C:"


# ---- timeout kills tree ----------------------------------------------------
@pytest.mark.skipif(os.name != "nt", reason="windows-specific")
def test_timeout_kills_tree(owner_env, monkeypatch):
    _, project = owner_env
    manager = J.JobManager(["fake-agent"], 1)
    manager._checkpoint = lambda root, job: setattr(job, "checkpoint", "HEAD")
    killed = []

    class FakeProc:
        pid = 4242
        def poll(self): return None
        def communicate(self, timeout=None):
            if timeout is not None:
                raise J.subprocess.TimeoutExpired("cmd", timeout)
            return (b"", b"")
        def wait(self, timeout=None): return 0
        def kill(self): pass

    monkeypatch.setattr(J.subprocess, "Popen", lambda *a, **k: FakeProc())
    monkeypatch.setattr(J, "git_run", lambda root, *a, **kw: mock.Mock(
        returncode=0, stdout="true" if "is-inside" in a[0] else ""))
    monkeypatch.setattr(J.subprocess, "run",
                        lambda cmd, **kw: killed.append(cmd) or mock.Mock(returncode=0))
    manager.start("alpha", project, "long task")
    for _ in range(200):
        if manager.status_line() is None:
            break
        time.sleep(0.05)
    assert any("taskkill" in str(cmd) and "/T" in str(cmd) for cmd in killed), \
        "tree kill (taskkill /T) must be invoked on timeout"


# ---- redaction / truncation -------------------------------------------------
def test_ansi_stripped():
    assert S.redact("\x1b[31mhello\x1b[0m") == "hello"


def test_secret_like_redacted():
    out = S.redact("key is sk-abcdef1234567890abcdef done")
    assert "sk-abcdef" not in out and "[REDACTED]" in out


def test_truncate_caps_length():
    words = "lorem ipsum dolor sit amet " * 140    # long, benign words
    out = S.truncate(words)
    assert len(out) <= 4000
    assert "truncated" in out.lower()


# ---- confirmations -----------------------------------------------------------
@pytest.mark.asyncio
async def test_destructive_requires_confirmation(owner_env):
    h, manager, project = make_handlers(owner_env, None)
    upd = FakeUpdate(999, 999)
    await h.cmd_run(upd, FakeCtx(["alpha", "delete", "the", "build", "folder"]))
    text = upd.effective_message.replies[-1]
    assert "Confirm" in text or "destructive" in text.lower()
    assert manager.status_line() is None          # nothing started


@pytest.mark.asyncio
async def test_confirmation_expiry(owner_env):
    h, _, _ = make_handlers(owner_env, None)
    h._pending["req1"] = ("alpha", time.time() - 120)   # 2 minutes old
    assert h._pending_pop("req1") is None


@pytest.mark.asyncio
async def test_confirmation_within_window(owner_env):
    h, _, _ = make_handlers(owner_env, None)
    h._pending["req2"] = ("alpha", time.time())
    assert h._pending_pop("req2") == "alpha"


# ---- single-job rule -------------------------------------------------------
@pytest.mark.asyncio
async def test_second_run_refused(owner_env, monkeypatch):
    h, manager, project = make_handlers(owner_env, None)

    class Busy:
        def status_line(self): return {"project": "alpha", "elapsed": 1, "task_len": 3}

    manager.status_line = Busy().status_line
    manager.start = lambda *a, **k: (_ for _ in ()).throw(J.JobError("A job is already running."))
    upd = FakeUpdate(999, 999)
    await h.cmd_run(upd, FakeCtx(["alpha", "safe", "task"]))
    assert any("already running" in r or "Started" in r
               for r in upd.effective_message.replies)


# ---- env errors ---------------------------------------------------------------
def test_missing_env_names_variable_only(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("OWNER_CHAT_ID", raising=False)
    monkeypatch.setattr(cfg, "HERE", Path("."))
    from dotenv import load_dotenv
    with pytest.raises(cfg.ConfigError) as info:
        cfg.owner_ids()
    message = str(info.value)
    assert "TELEGRAM_BOT_TOKEN" in message
    assert "OWNER_CHAT_ID" in message
    # never leaks a token-shaped value
    assert not S.SECRET_RE.search(message.replace("TELEGRAM_BOT_TOKEN", ""))


def test_malformed_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "no-colon-here")
    monkeypatch.setenv("OWNER_CHAT_ID", "999")
    monkeypatch.setattr(cfg, "HERE", Path("."))
    with pytest.raises(cfg.ConfigError) as info:
        cfg.owner_ids()
    assert "malformed" in str(info.value)
