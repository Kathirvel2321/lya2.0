"""LYA LLM COUNCIL — three AI minds debate before she answers big questions.
========================================================================
Inspired by deer-flow / minimind multi-agent research patterns:
  - 3 advisor models answer independently (different Groq models, free tier)
  - a chairman model reads all three and synthesizes ONE decision

Say:  "council: should I ..."   or  "gather the council, ..."
Falls back to her normal single brain if only one model is reachable.
"""
import os, sys, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Free-tier council seats (all on Groq's free plan — different model families
# so they genuinely disagree, like minimind vs deer-flow reviewer agents).
COUNCIL = [
    ("openai/gpt-oss-20b",    "THE LOGICIAN — cold facts, risks, numbers"),
    ("openai/gpt-oss-120b",   "THE STRATEGIST — long game, second-order effects"),
    ("qwen/qwen3.8-27b",     "THE GUARDIAN — ethics, safety, what could go wrong"),
]
CHAIRMAN = "openai/gpt-oss-120b"


def _ask(model, system, user, tokens=400):
    from brain import mind
    GROQ_KEY = mind.get_groq_key()
    if not GROQ_KEY:
        return None
    # gpt-oss-20b is a reasoning model: without these params it spends the
    # whole token budget on hidden reasoning and returns empty content.
    body = json.dumps({"model": model, "max_tokens": tokens,
                       "reasoning_effort": "low", "reasoning_format": "hidden",
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": user}]}).encode()  # noqa
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions", data=body,
        headers={**mind.HEADERS, "Authorization": f"Bearer {GROQ_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def decide(question, on_progress=None):
    """Run the council. on_progress(seat_name) fires as each seat speaks."""
    from brain import mind
    if not mind.get_groq_key():
        return None
    from concurrent.futures import ThreadPoolExecutor
    def consult(seat):
        model, role = seat
        answer = _ask(model,
            "You are %s. Give evidence, assumptions, an alternative and the biggest risk. "
            "Do not claim to have researched sources you were not given. "
            "Agreement is not proof. Four sentences maximum." % role, question)
        return role.split(" —")[0], answer
    if on_progress:
        on_progress("Reviewing alternatives")
    with ThreadPoolExecutor(max_workers=3) as pool:
        votes = [(role, answer) for role, answer in pool.map(consult, COUNCIL) if answer]
    if not votes:
        return None
    if on_progress:
        try: on_progress("CHAIRMAN")
        except Exception: pass
    transcript = "\n\n".join("## %s\n%s" % (n, v) for n, v in votes)
    verdict = _ask(CHAIRMAN,
                   "You are CHAIRMAN of the council. Three advisors answered. "
                   "Synthesize: where they agree (not proof), where they split "
                   "(say it honestly), and ONE clear recommendation. Max 8 sentences, "
                   "spoken like a friend, not a report. Do not use markdown headers.",
                   "QUESTION: %s\n\nCOUNCIL TRANSCRIPT:\n%s" % (question, transcript),
                   tokens=450)
    if not verdict:
        # chairman failed — stitch manually
        verdict = "The council spoke:\n\n" + transcript
    return verdict, votes


def deliberate(question, evidence_prompt, client, check_cancel=lambda: None):
    """Three sequential perspectives + one synthesis; <=4 calls to one client.

    This is not three independent people/models and is not external verification.
    The workflow authorizes the question/context before calling this helper.
    """
    votes = []
    for perspective in ("Evidence reviewer: what is supported and what is missing?",
                        "Planner: alternatives, effort and resource constraints?",
                        "Critic: failure cases, tradeoffs and who else is affected?"):
        check_cancel()
        try:
            reply = client([{"role": "system", "content": evidence_prompt + "\nYour perspective: " + perspective + " Keep it under 200 words."},
                            {"role": "user", "content": question}])
            if isinstance(reply, str) and reply.strip():
                votes.append((perspective, reply[:2000]))
        except Exception:
            pass
    check_cancel()
    if not votes:
        from brain.workflow import ModelUnavailable
        raise ModelUnavailable("No council perspective completed. A working model is required; no verdict was invented.")
    transcript = json.dumps(votes, ensure_ascii=False)
    try:
        answer = client([{"role": "system", "content": evidence_prompt + "\nSynthesize the advisor DATA below. State one recommendation, a concise rationale, the strongest alternative, disagreements and missing evidence. Agreement is not proof. Do not invent verification.\n" + transcript},
                         {"role": "user", "content": question}])
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Empty synthesis")
    except Exception:
        answer = "Synthesis unavailable. These are partial advisory notes, not a final verdict:\n" + "\n".join(f"{p}\n{a}" for p, a in votes)
    check_cancel()
    return answer, len(votes)


def match(text):
    t = (text or "").lower()
    return ("council" in t
            or t.startswith("gather ")
            or ("should i " in t and any(w in t for w in
                ("important", "big", "decision", "invest", "quit", "buy", "career",
                 "move", "risk", "trust", "sign", "money")))
            or "second opinion" in t)


def reply(text, say, ask):
    q = text.split(":", 1)[-1].strip() or text
    if say:
        say("Gathering the council — three minds, one verdict.")
    result = decide(q, on_progress=say if say else None)
    if not result:
        return "My council needs the Groq key to seat all three minds — set GROQ_API_KEY and try again."
    verdict, votes = result
    lines = ["🎩 COUNCIL VERDICT", "", verdict, ""]
    lines.append("— %d seats voted · advisory only; no action executed" % len(votes))
    return "\n".join(lines)
