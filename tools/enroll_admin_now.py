"""One-time admin enrollment - run this ONCE, ever.

    python tools/enroll_admin_now.py

Opens the webcam, captures 5 frames of your face, computes ArcFace
embeddings in memory, and stores ONLY the encrypted embeddings. The photos
are never saved anywhere. After this, "LYA, it's me" works forever.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from vision import identity  # noqa: E402
from brain import admin_recognizer  # noqa: E402


def main():
    print("[LYA-ENROLL] Looking at your webcam now - sit centered, good light.")
    print("[LYA-ENROLL] Capturing 5 frames ...")
    frames = admin_recognizer.capture_frames(count=5, camera_index=0)
    if len(frames) < 3:
        print(f"[LYA-ENROLL] Only got {len(frames)} usable frames - "
              "check nothing else is using the camera, then re-run.")
        sys.exit(1)

    ok = identity.enroll_admin(frames, name="admin")
    if ok:
        print("[LYA-ENROLL] DONE. Your face is enrolled (encrypted embeddings only;")
        print("             no photos were saved). From now on just say: \"LYA, it's me\"")
    else:
        print("[LYA-ENROLL] Enrollment failed - no usable face found. Try again in")
        print("             better lighting; move closer to the camera.")
        sys.exit(1)


if __name__ == "__main__":
    main()
