"""Entry point: python -m lya_agent --task "..."

Contract with runner/jobs.py: the task text arrives as exactly one argv
element after --task; the process exits 0 on success, non-zero on any
failure; stdout is the human-readable summary.

Limits: --max-steps (default 15) caps agent turns; --timeout-sec (default
120) is a hard wall-clock cap enforced here even if the SDK hangs.
"""
from __future__ import annotations

import argparse
import logging
import sys
import threading
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("lya_agent")

REPO_ROOT = Path(__file__).resolve().parents[1]
KILL_FLAG = REPO_ROOT / "data" / "LYA_KILL"
AUDIT_PATH = REPO_ROOT / "data" / "lya_agent_audit.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lya_agent",
                                     description="LYA desktop task agent")
    parser.add_argument("--task", required=True,
                        help="task text (one argv element, from the runner)")
    parser.add_argument("--max-steps", type=int, default=15,
                        help="maximum agent steps (default 15)")
    parser.add_argument("--timeout-sec", type=int, default=120,
                        help="hard wall-clock timeout in seconds (default 120)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_steps < 1 or args.max_steps > 100:
        print("ERROR: --max-steps must be between 1 and 100", file=sys.stderr)
        return 2
    if args.timeout_sec < 10 or args.timeout_sec > 3600:
        print("ERROR: --timeout-sec must be between 10 and 3600", file=sys.stderr)
        return 2

    from lya_agent.brain import ClaudeAgentBrain
    from lya_agent.killswitch import KillSwitch
    from lya_agent.tools import build_mcp_server

    try:
        from security.chained_audit import ChainedAudit
        audit = ChainedAudit(AUDIT_PATH)
    except Exception as exc:
        log.error("audit log unavailable: %s", exc)
        print("ERROR: the audit log could not be opened; refusing to run.",
              file=sys.stderr)
        return 2

    killswitch = KillSwitch(KILL_FLAG)
    killswitch.clear()          # stale flag from a previous run is cleared at
    # startup ONLY by the runner relaunching the process; a manual flag left
    # behind still stops THIS run because stopped() re-reads the file... but
    # here we must honour a pre-existing flag: do NOT clear silently.
    if KILL_FLAG.exists():
        log.warning("kill flag %s already exists; run aborted", KILL_FLAG)
        print("ERROR: kill flag exists (data/LYA_KILL); delete it to run.",
              file=sys.stderr)
        return 3

    try:
        server, ctx_holder_unused = build_mcp_server(audit=audit)
    except Exception as exc:
        log.exception("tool registration failed")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    killswitch.start_hotkey()
    brain = ClaudeAgentBrain(killswitch=killswitch, audit=audit,
                             max_steps=args.max_steps,
                             timeout_sec=args.timeout_sec, cwd=None)

    # Hard wall-clock cap in a daemon thread: the SDK receive loop can hang
    # on a broken pipe; this guarantee the process always exits.
    result: dict = {}
    timed_out = threading.Event()

    def _watchdog():
        if not timed_out.wait(timeout=args.timeout_sec):
            return
        if "result" not in result:
            result["result"] = {"ok": False, "status": "timeout",
                                "summary": f"hard timeout after "
                                           f"{args.timeout_sec}s"}
        import os
        os._exit(4)             # last-resort: guarantee no hang

    watchdog = threading.Thread(target=_watchdog, daemon=True)
    watchdog.start()
    try:
        outcome = brain.run(args.task)
        result["result"] = outcome
    except Exception as exc:                       # noqa: BLE001
        log.exception("brain.run crashed")
        outcome = {"ok": False, "status": "error",
                   "summary": f"{type(exc).__name__}: {exc}"}
        result["result"] = outcome
    timed_out.set()                                 # stop the watchdog timer

    status = outcome.get("status", "error")
    summary = outcome.get("summary", "")
    print(f"[lya_agent] status={status}")
    if summary:
        print(summary[:4000])
    audit.log("agent-run", status, "ok" if outcome.get("ok") else "failed",
              approver="owner")
    return 0 if outcome.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
