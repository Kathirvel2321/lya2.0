"""Tests for lya_agent. Only the safety-critical pieces are tested here:
pathguard escapes, gate deny-by-default, the kill switch, the max-steps cap,
and the Bash-denied hook. Glue code (imports, argparse) is NOT tested."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from lya_agent import pathguard  # noqa: E402
from lya_agent.config import ConfigError  # noqa: E402
from lya_agent.killswitch import KillSwitch  # noqa: E402
from lya_agent.tools import ToolContext, ToolError, wrap_result  # noqa: E402


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    return tmp_path / "root"


# ---- pathguard --------------------------------------------------------------

class TestPathguard:
    def test_simple_inside_ok(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        target = pathguard.check_subpath(root, "docs/note.txt")
        assert target == (root / "docs" / "note.txt").resolve()

    def test_traversal_denied(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        with pytest.raises(pathguard.PathOutsideAllowlist):
            pathguard.check_subpath(root, "..")
        with pytest.raises(pathguard.PathOutsideAllowlist):
            pathguard.check_subpath(root, "a/../../escape.txt")

    def test_absolute_subpath_denied(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        with pytest.raises(pathguard.PathOutsideAllowlist):
            pathguard.check_subpath(root, "C:/Windows/system32")
        with pytest.raises(pathguard.PathOutsideAllowlist):
            pathguard.check_subpath(root, str(tmp_path / "elsewhere"))

    def test_drive_switch_denied(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        with pytest.raises(pathguard.PathOutsideAllowlist):
            pathguard.check_subpath(root, "D:/somewhere/x.txt")

    def test_unc_denied(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        with pytest.raises(pathguard.PathOutsideAllowlist):
            pathguard.check_subpath(root, r"\\\\server\\share\\file.txt")

    def test_ads_denied(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        with pytest.raises(pathguard.PathOutsideAllowlist):
            pathguard.check_subpath(root, "file.txt:hidden_stream")

    def test_reserved_names_denied(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        for name in ("CON", "NUL.txt", "COM1", "LPT2.log"):
            with pytest.raises(pathguard.PathOutsideAllowlist):
                pathguard.check_subpath(root, name)

    def test_symlink_escape_denied(self, tmp_path):
        real_root = tmp_path / "real"
        real_root.mkdir()
        fake_root = tmp_path / "root"
        fake_root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        link = fake_root / "jump"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("symlink creation needs admin rights on this Windows")
        with pytest.raises(pathguard.PathOutsideAllowlist):
            pathguard.check_subpath(fake_root, "jump/secret.txt")

    def test_unc_root_denied(self):
        with pytest.raises(pathguard.PathOutsideAllowlist):
            pathguard.check_root(r"\\\\server\\share")


# ---- tools: read_text_file extension + size ---------------------------------

def _ctx(tmp_path: Path) -> ToolContext:
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    return ToolContext({"apps": {"notepad": "C:/Windows/System32/notepad.exe"},
                        "folders": {"docs": root}}, audit=None)


class TestTools:
    def test_read_bad_extension_denied(self, tmp_path):
        ctx = _ctx(tmp_path)
        (tmp_path / "root" / "evil.exe").write_bytes(b"MZ")
        with pytest.raises(ToolError):
            ctx.__class__  # noqa: B018 - keep linters quiet about the fixture
            from lya_agent.tools import read_text_file
            read_text_file(ctx, "docs", "evil.exe")

    def test_read_too_large_denied(self, tmp_path):
        from lya_agent.tools import read_text_file
        ctx = _ctx(tmp_path)
        big = tmp_path / "root" / "big.txt"
        big.write_text("x" * (200 * 1024 + 1), encoding="utf-8")
        with pytest.raises(ToolError):
            read_text_file(ctx, "docs", "big.txt")

    def test_binary_refused(self, tmp_path):
        from lya_agent.tools import read_text_file
        ctx = _ctx(tmp_path)
        (tmp_path / "root" / "weird.md").write_bytes(b"hello\x00world")
        with pytest.raises(ToolError):
            read_text_file(ctx, "docs", "weird.md")

    def test_wrap_truncates_and_marks_untrusted(self):
        wrapped = wrap_result("a" * 9000)
        assert wrapped.startswith("<untrusted_data>")
        assert wrapped.endswith("</untrusted_data>")
        assert len(wrapped) <= 4000 + 40


# ---- config -----------------------------------------------------------------

class TestConfig:
    def test_missing_file_raises(self, tmp_path, monkeypatch):
        from lya_agent import config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_candidate_paths",
                            lambda: [tmp_path / "nope.json"])
        with pytest.raises(ConfigError):
            cfg_mod.load_config()

    def test_alias_shape_enforced(self, tmp_path, monkeypatch):
        from lya_agent import config as cfg_mod
        bad = tmp_path / "lya_agent.local.json"
        bad.write_text(json.dumps({
            "apps": {"Bad Name!": "C:/Windows/System32/notepad.exe"},
            "folders": {"docs": "C:/Windows"}}), encoding="utf-8")
        monkeypatch.setattr(cfg_mod, "_candidate_paths", lambda: [bad])
        with pytest.raises(ConfigError):
            cfg_mod.load_config()

    def test_lya_repo_protected(self, tmp_path, monkeypatch):
        from lya_agent import config as cfg_mod
        cfg_file = tmp_path / "lya_agent.local.json"
        cfg_file.write_text(json.dumps({
            "apps": {"notepad": str(REPO / "runner")},
            "folders": {"docs": "C:/Windows"}}), encoding="utf-8")
        monkeypatch.setattr(cfg_mod, "_candidate_paths", lambda: [cfg_file])
        with pytest.raises(ConfigError):
            cfg_mod.load_config()


# ---- kill switch --------------------------------------------------------------

class TestKillSwitch:
    def test_flag_file_stops(self, tmp_path):
        ks = KillSwitch(tmp_path / "LYA_KILL")
        assert not ks.stopped()
        ks.flag_path.write_text("manual", encoding="utf-8")
        assert ks.stopped()
        assert "flag" in ks.reason()

    def test_hotkey_request_stop(self, tmp_path):
        ks = KillSwitch(tmp_path / "LYA_KILL")
        ks.request_stop("hotkey pressed")
        assert ks.stopped()
        assert ks.flag_path.exists()
        ks.clear()
        assert not ks.stopped()

    def test_max_steps_reported(self, tmp_path):
        """The brain loop honours max_steps: a run must report it, not hang."""
        from lya_agent.brain import ClaudeAgentBrain
        ks = KillSwitch(tmp_path / "LYA_KILL")

        class FakeClient:
            def __init__(self, options): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def query(self, task): pass
            def receive_response(self):
                # yields 50 messages; the loop must cut at max_steps=3
                for _ in range(50):
                    yield type("M", (), {"content": None})()

        import lya_agent.brain as brain_mod
        brain_mod._cli_authenticated = lambda: (True, "")
        brain = ClaudeAgentBrain(killswitch=ks, max_steps=3, timeout_sec=30)
        try:
            import claude_agent_sdk as sdk_mod
        except ModuleNotFoundError:
            pytest.skip("claude-agent-sdk is not installed yet")
        sdk_mod.ClaudeSDKClient = FakeClient
        sdk_mod.ClaudeAgentOptions = lambda **kw: kw
        result = brain.run("test")
        assert result["status"] == "max_steps"
        assert not result["ok"]


# ---- gate: deny-by-default hook proves Bash is refused -------------------------

class TestGateDenyByDefault:
    def test_bash_call_denied(self, tmp_path):
        """A Bash tool call MUST be denied by the PreToolUse hook."""
        import asyncio
        pytest.importorskip("claude_agent_sdk")
        from lya_agent.brain import ClaudeAgentBrain, OWN_MCP_PREFIX
        ks = KillSwitch(tmp_path / "LYA_KILL")
        brain = ClaudeAgentBrain(killswitch=ks, gate=None)
        hooks = brain._pretooluse_hook()
        hook_fn = hooks["PreToolUse"][0].hooks[0]

        bash_decision = asyncio.run(hook_fn(
            tool_name="Bash", tool_input={"command": "dir"}, context={}))
        spec = bash_decision["hookSpecificOutput"]
        assert spec["permissionDecision"] == "deny"

        mcp_decision = asyncio.run(hook_fn(
            tool_name=OWN_MCP_PREFIX + "open_app",
            tool_input={"name": "notepad"}, context={}))
        assert mcp_decision == {}          # allowed silently

    def test_gate_never_tier_blocks(self, tmp_path):
        """With a real gate wired, calls outside our namespace cannot pass."""
        from security.gate import Gate
        from lya_agent.brain import ClaudeAgentBrain
        ks = KillSwitch(tmp_path / "LYA_KILL")
        brain = ClaudeAgentBrain(killswitch=ks, gate=Gate())
        assert brain._gate_allows("Bash") is False
        assert brain._gate_allows("Write") is False


# ---- subprocess contract with jobs.py ------------------------------------------

class TestSubprocessContract:
    def test_help_exits_cleanly(self):
        """python -m lya_agent --help must work; proves the module wires up."""
        proc = subprocess.run(
            [sys.executable, "-m", "lya_agent", "--help"],
            cwd=str(REPO), capture_output=True, text=True, timeout=60,
            shell=False)
        assert proc.returncode == 0
        assert "--task" in proc.stdout

    def test_missing_task_fails(self):
        proc = subprocess.run(
            [sys.executable, "-m", "lya_agent"],
            cwd=str(REPO), capture_output=True, text=True, timeout=60,
            shell=False)
        assert proc.returncode != 0
