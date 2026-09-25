"""Disposable encrypted-note retrieval benchmark; no real LYA data is opened."""
from pathlib import Path
import statistics
import sys
import tempfile
import time

from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from security import vault
from storage import store
from brain import notes


def main():
    vault._F = Fernet(Fernet.generate_key())
    for count in (100, 1000, 2000):
        with tempfile.TemporaryDirectory(prefix="lya-bench-") as temporary:
            db_path = Path(temporary) / "fake.enc"
            person = store.create_person("Fake benchmark owner", "admin", db_path=db_path)
            with store.store_connection(db_path) as db:
                db.executemany("""INSERT INTO memories
                    (person_id,kind,key_enc,value_enc,source,importance,hits,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?)""", [
                    (person, "fact", vault.encrypt_text(f"fixture_{number:04d}"),
                     vault.encrypt_text("needle unique saved fact" if number == count - 1
                                        else f"haystack item {number:04d}"),
                     "test", 1.0, 0, "fixture", "fixture")
                    for number in range(count)
                ])
            times = []
            for _ in range(5):
                start = time.perf_counter()
                found = notes.retrieve(person, "needle", db_path=db_path, now=2_000_000_000.0)
                times.append((time.perf_counter() - start) * 1000)
                assert len(found) == 1 and found[0]["value"] == "needle unique saved fact"
            print(f"{count:4d} notes  median={statistics.median(times):6.2f} ms"
                  f"  max={max(times):6.2f} ms  encrypted_db={db_path.stat().st_size / 1024:.1f} KiB")


if __name__ == "__main__":
    main()
