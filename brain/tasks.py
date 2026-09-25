"""Explicit, person-scoped tasks in LYA's encrypted local database."""
import time

from security import vault
from storage import store


def _create_table(db):
    db.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id TEXT NOT NULL REFERENCES people(person_id),
        text_enc TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0 CHECK(done IN (0, 1)),
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS tasks_owner_state ON tasks(person_id, done, id)")


def add(person_id: str, text: str, *, db_path=None, now=None) -> int:
    title = " ".join(text.split())
    if not title or len(title) > 300:
        raise ValueError("Use task add followed by 1 to 300 characters.")
    if not person_id:
        raise PermissionError("A verified person is required.")
    stamp = time.time() if now is None else now
    with store.store_connection(db_path) as db:
        if not db.execute("SELECT 1 FROM people WHERE person_id=? AND active=1", (person_id,)).fetchone():
            raise PermissionError("The person is inactive or missing.")
        _create_table(db)
        count = db.execute("SELECT count(*) FROM tasks WHERE person_id=? AND done=0", (person_id,)).fetchone()[0]
        if count >= 100:
            raise ValueError("The task list is full (100 open tasks). Complete some first.")
        cur = db.execute("INSERT INTO tasks(person_id,text_enc,created_at,updated_at) VALUES(?,?,?,?)",
                         (person_id, vault.encrypt_text(title), stamp, stamp))
        return cur.lastrowid


def list_tasks(person_id: str, *, include_done=False, db_path=None) -> list[dict]:
    if not person_id:
        raise PermissionError("A verified person is required.")
    with store.store_connection(db_path, read_only=True) as db:
        if not db.execute("SELECT 1 FROM people WHERE person_id=? AND active=1", (person_id,)).fetchone():
            raise PermissionError("The person is inactive or missing.")
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone():
            return []
        query = "SELECT id,text_enc,done FROM tasks WHERE person_id=?"
        if not include_done:
            query += " AND done=0"
        query += " ORDER BY done ASC,id ASC LIMIT 200"
        return [{"id": task_id, "text": vault.decrypt_text(token), "done": bool(done)}
                for task_id, token, done in db.execute(query, (person_id,))]


def complete(person_id: str, task_id: int, *, db_path=None, now=None) -> bool:
    if task_id < 1 or not person_id:
        raise ValueError("Use task done followed by a task number.")
    stamp = time.time() if now is None else now
    with store.store_connection(db_path) as db:
        if not db.execute("SELECT 1 FROM people WHERE person_id=? AND active=1", (person_id,)).fetchone():
            raise PermissionError("The person is inactive or missing.")
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone():
            return False
        cur = db.execute("UPDATE tasks SET done=1,updated_at=? WHERE id=? AND person_id=? AND done=0",
                         (stamp, task_id, person_id))
        return cur.rowcount == 1
