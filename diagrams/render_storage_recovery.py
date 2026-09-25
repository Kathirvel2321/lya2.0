"""Local companion overview; Mermaid source is checked separately."""
from pathlib import Path

# Reuse the existing companion renderer without running its older diagram jobs.
p = Path(__file__).with_name("render_brain_map.py")
exec(p.read_text(encoding="utf-8").split("body = text(60,65,")[0])
from PySide6.QtGui import QFontDatabase
QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")

body = text(60, 65, "LYA / PRIVATE MEMORY + RECOVERY", 18, "#81bac8")
body += text(60, 114, "Your memory. Explicit access. Recoverable notes.", 34, "#f3f8fa")
body += box(60, 160, 390, 170, "1  Owner authorization", [
    "Active verified session", "Exact approval; failure means stop",
    "Real enrollment remains deferred", "Desktop is still guest-locked"], "#e6b35a")
body += box(505, 160, 390, 170, "2  Relevant memory", [
    "Only this person's active notes", "Source, revision and expiry",
    "Small explicit relationship graph", "Encrypted SQLite on your laptop"])
body += box(950, 160, 390, 170, "3  Answer locally", [
    "Personal context uses local inference", "No cloud fallback if unavailable",
    "Recheck identity and note expiry", "Replies are not auto-saved facts"])
body += arrow(452, 245, 493, 245) + arrow(897, 245, 938, 245)
body += text(60, 382, "SAVE ONLY WHAT YOU CHOOSE", 19, "#81bac8")
body += box(60, 405, 1280, 105, "Choose a lifetime", [
    "Session RAM  |  7 days  |  90 days  |  Your deadline  |  Permanent until deleted"])
body += box(60, 570, 390, 165, "4  Select and encrypt", [
    "Explicit note IDs and approval", "Separate random recovery key",
    "No identities, biometrics or .env", "Returns encrypted archive bytes"])
body += box(505, 570, 390, 165, "5  Validate and restore", [
    "Reject wrong key / tampered data", "Empty verified owner profile only",
    "New local key; keep original expiry", "Interrupted writes preserve store"])
body += box(950, 570, 390, 165, "NEXT: owner recovery UI", [
    "Save archive; keep key separately", "Perform clean-device restore drill",
    "Then optional encrypted Drive sync", "No cloud sync has been enabled"], "#e6b35a")
body += arrow(452, 653, 493, 653)
body += text(60, 800, "OPTIONAL TOOLS STAY OUTSIDE PRIVATE MEMORY", 19, "#81bac8")
body += box(60, 825, 620, 110, "Obsidian: proposed selected Markdown export", [
    "Preview first; exported text needs its own protection."], "#e6b35a")
body += box(720, 825, 620, 110, "NotebookLM: optional public research only", [
    "No private store, key, face or voice uploads."], "#e6b35a")
body += text(60, 978, "CYAN: isolated code tests. AMBER: pending integration. No live owner or cloud recovery was tested.", 18)
body += text(60, 1010, "Companion overview | 2026-09-20 | Full limits and release gates: LYA_STORAGE_SECURITY_PLAN.md", 17, "#81bac8")
render("17-storage-recovery", body)
