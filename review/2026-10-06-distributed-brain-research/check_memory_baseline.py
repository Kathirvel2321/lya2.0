"""Synthetic quality fixture for existing notes, not a new memory engine.

All store calls use one disposable path and an ephemeral Fernet key. No owner
data, network/model requests or production writes. Misses are measurements;
failed boundary assertions are errors. Run with the existing .venv-asr Python.
"""
import json
from pathlib import Path
import sys
import tempfile
import time

from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from security import vault


def no_external_calls(event, args):
    if event.startswith("socket.") or event == "subprocess.Popen":
        raise RuntimeError("This fixture does not permit external calls")


def main():
    sys.addaudithook(no_external_calls)
    vault._F = Fernet(Fernet.generate_key())
    from storage import store
    from brain import notes

    now = 2_000_000_000.0
    corpus = {
        "daily_drink": "Black coffee without sugar.",
        "backend_framework": "FastAPI for the Atlas service.",
        "shipment_courier": "DHL handles this shipment.",
        "graphics_card": "NVIDIA GTX 1650.",
        "preferred_language": "English.",
        "release_date": "14 October 2026.",
    }
    cases = [
        ("exact", "daily_drink", "coffee"),
        ("exact", "backend_framework", "FastAPI"),
        ("exact", "shipment_courier", "DHL"),
        ("exact", "graphics_card", "GTX 1650"),
        ("exact", "preferred_language", "English"),
        ("exact", "release_date", "October"),
        ("paraphrase", "daily_drink", "Which beverage do I prefer?"),
        ("paraphrase", "backend_framework", "Which stack powers the web API?"),
        ("paraphrase", "shipment_courier", "Who is delivering my parcel?"),
        ("paraphrase", "graphics_card", "Which GPU is installed?"),
        ("paraphrase", "preferred_language", "Which language do I prefer?"),
        ("paraphrase", "release_date", "When does the release happen?"),
    ]
    with tempfile.TemporaryDirectory(prefix="lya-memory-quality-") as temporary:
        db_path = Path(temporary) / "synthetic.enc"
        owner = store.create_person("Synthetic owner", "admin", db_path=db_path)
        other = store.create_person("Synthetic other", "friend", db_path=db_path)
        for key, value in corpus.items():
            notes.save(owner, key, value, retention="permanent", db_path=db_path, now=now)
        notes.save(other, "other_canary", "crossownercanary", retention="permanent", db_path=db_path, now=now)
        notes.save(owner, "temporary", "expiredcanary", retention="until", until=now + 1, db_path=db_path, now=now)
        results = []
        for group, expected, query in cases:
            start = time.perf_counter()
            found = notes.retrieve(owner, query, db_path=db_path, now=now)
            keys = [item["key"] for item in found]
            results.append({"group": group, "query": query, "expected": expected,
                            "retrieved": keys, "hit": expected in keys,
                            "milliseconds": round((time.perf_counter() - start) * 1000, 3)})

        def find(query, at=now):
            return notes.retrieve(owner, query, db_path=db_path, now=at)

        assert find("crossownercanary") == [], "Cross-person storage result"
        assert find("expiredcanary", now + 2) == [], "Expired note returned"
        assert find("nonexistentuniqueidentifier") == [], "Unknown identifier returned"
        notes.save(owner, "daily_drink", "Green tea without sugar.", correct=True, db_path=db_path, now=now)
        assert find("coffee") == [], "Stale FTS entry after correction"
        assert find("Green tea")[0]["revision"] == 2, "Correction revision lost"
        assert "Green tea".encode() not in db_path.read_bytes(), "Plaintext body on disk"
        print(json.dumps({"scope": "12 hand-authored queries over six synthetic facts; existing notes retrieval only",
                          "runtime_integration_test": False, "boundary_assertions_passed": 6,
                          "groups": {group: {"hits": sum(r["hit"] for r in results if r["group"] == group),
                                               "queries": sum(r["group"] == group for r in results)}
                                     for group in ("exact", "paraphrase")},
                          "results": results}, indent=2))


if __name__ == "__main__":
    main()
