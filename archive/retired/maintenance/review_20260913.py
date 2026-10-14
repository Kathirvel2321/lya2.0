"""Review existing suites in a disposable source copy, never the real data stores.
Run with .venv-ui/Scripts/python.exe -B review/review_20260913.py.
Network and hardware input are blocked; TTS is replaced by a fake engine.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / ("2026-09-13-retrieval" if "--retrieval" in sys.argv else "2026-09-13-brain" if "--brain" in sys.argv else "2026-09-13")
SUITES = ["test_storage.py", "test_identity.py", "test_mind.py", "test_voice.py", "desktop/check_ui.py"]
if "--brain" in sys.argv or "--retrieval" in sys.argv:
    SUITES.extend(["test_brain_workflow.py", "test_foundations.py", "test_regressions_r01_r05.py"])
BOOT = r'''
import os, sys, runpy, types
from pathlib import Path
root = Path.cwd()
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'desktop'))
def audit(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo'):
        raise RuntimeError('Review blocks network access')
sys.addaudithook(audit)
def denied(*args, **kwargs):
    raise RuntimeError('Review blocks sensor input')
import sounddevice
sounddevice.rec = denied
sounddevice.RawInputStream = denied
import cv2
cv2.VideoCapture = denied
engine = types.SimpleNamespace(setProperty=lambda *a: None, say=lambda *a: None,
                               runAndWait=lambda: None, stop=lambda: None)
sys.modules['pyttsx3'] = types.SimpleNamespace(init=lambda: engine)
target = sys.argv[1]
sys.argv = [target]
runpy.run_path(target, run_name='__main__')
'''
PROBES = r'''
import json
from pathlib import Path
from storage import store
from brain import mind
from vision import identity
from unittest.mock import patch
db = Path('runtime/probes.enc')
alice = store.create_person('Synthetic Alice', 'admin', db_path=db)
store.remember(alice, 'test_fact', 'SYNTHETIC_ALICE_ONLY', db_path=db)
store.remember(alice, 'secondary_password', 'SYNTHETIC_HASH_MATERIAL', kind='credential', db_path=db)
missing_person = mind._memory_block(db_path=db)
with patch.object(store, 'recall', side_effect=RuntimeError('test store failure')):
    with patch.object(mind.memory, 'recall', return_value=[('legacy', 'SYNTHETIC_LEGACY', 'private', 0)]):
        fallback = mind._memory_block(person_id=alice, db_path=db)
expired = store.record_pending_face(embedding=[1.0, 0.0], expires_days=-1, db_path=db)
try:
    store.promote_pending_face(expired, 'Expired fixture', 'friend', db_path=db)
    expired_promoted = True
except KeyError:
    expired_promoted = False
import main
assistant = main.Assistant.__new__(main.Assistant)
assistant.build = False
from security.policy import Session
assistant.session = Session(id='fixture')
with patch.object(identity, 'STORE', str(Path('runtime/missing-legacy-file'))):
    with patch.object(identity, 'has_enrolled_admin', return_value=True):
        with patch.object(identity, 'snapshot_jpg', return_value=b'fake'):
            with patch.object(identity, 'identify', return_value={'role':'admin', 'who':'fixture', 'person_id':'fixture'}) as recognize:
                assistant.identify()
                legacy_file_blocks_recognition = not recognize.called
results = {'missing_person_selects_first_profile': 'SYNTHETIC_ALICE_ONLY' in missing_person,
           'credential_kind_included_in_model_context': 'SYNTHETIC_HASH_MATERIAL' in missing_person,
           'scoped_store_failure_falls_back_to_legacy_memory': 'SYNTHETIC_LEGACY' in fallback,
           'expired_pending_face_can_be_promoted': expired_promoted,
           'legacy_file_gate_prevents_new_registry_lookup': legacy_file_blocks_recognition}
print(json.dumps(results, indent=2))
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix="lya-review-") as tmp:
        copy = Path(tmp).resolve()
        # Only code, public project docs and the owner's UI artwork; no runtime data.
        paths = list(ROOT.glob("*.py")) + list(ROOT.glob("*.md"))
        for directory in ("audio", "brain", "security", "storage", "vision", "skills", "ui", "desktop"):
            paths += list((ROOT / directory).glob("*.py"))
        paths.append(ROOT / "desktop/assets/crystal-original.png")
        for path in paths:
            dest = copy / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
        (copy / "bootstrap.py").write_text(BOOT, encoding="utf-8")
        (copy / "review_probes.py").write_text(PROBES, encoding="utf-8")
        env = os.environ.copy()
        for name in tuple(env):
            if any(s in name.upper() for s in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "OMNIROUTE", "LYA_", "PYTHONPATH")):
                env.pop(name, None)
        env.update(LYA_DATA_DIR=str(copy / "runtime"), LOCALAPPDATA=str(copy / "local"),
                   APPDATA=str(copy / "roaming"), USERPROFILE=str(copy / "home"),
                   PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        (copy / "runtime").mkdir()
        for suite in SUITES + ["review_probes.py"]:
            p = subprocess.run([sys.executable, "-B", "bootstrap.py", suite], cwd=copy,
                               env=env, capture_output=True, text=True, encoding="utf-8", timeout=90)
            log = suite.replace("/", "-") + ".txt"
            (OUT / log).write_text(p.stdout + p.stderr, encoding="utf-8")
            results.append({"suite": suite, "exit_code": p.returncode, "log": log})
            print(suite, p.returncode, flush=True)
        for path in (copy / "desktop/qa").glob("*"):
            shutil.copyfile(path, OUT / path.name)
    (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    if any(result["exit_code"] for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
