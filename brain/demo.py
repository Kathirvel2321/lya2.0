"""Synthetic workflow demonstration. Run in a separate process, never import in the UI."""
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    # An ephemeral test key is set BEFORE any database operation; no real key is read.
    from cryptography.fernet import Fernet
    from security import vault
    vault._F = Fernet(Fernet.generate_key())
    from storage import store
    from security.policy import Session
    from brain.workflow import Brain
    print("SYNTHETIC DEMO — fake identities, approval and model; real storage/workflow code.\n")
    with tempfile.TemporaryDirectory(prefix="lya-brain-demo-") as tmp:
        path = Path(tmp).resolve() / "demo.enc"
        pid = store.create_person("Demo owner", "admin", db_path=path)
        brain = Brain(Session("admin", "Demo owner", "demo", pid, time.time()+120),
                      approve=lambda *args: True, db_path=path,
                      client=lambda messages: "Demo recommendation: build one tested local workflow first. Verify missing evidence before expanding.")
        for command in ("remember short laptop = use limited local resources",
                        "remember permanent LYA = build a reliable personal assistant",
                        "link 2 depends_on 1", "recall laptop", "show graph",
                        "council: important plan for LYA on my laptop",
                        "correct laptop = prefer small bounded local workloads", "recall laptop"):
            answer = brain.respond(command)
            print("> " + command + "\n" + answer.text + "\n")
        brain.bind_session(Session(id="different-guest"))
        print("> guest asks show memories\n" + brain.respond("show memories").text)


if __name__ == "__main__":
    main()
