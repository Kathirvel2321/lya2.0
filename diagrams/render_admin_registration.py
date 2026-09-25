from pathlib import Path

p = Path(__file__).with_name("render_brain_map.py")
exec(p.read_text(encoding="utf-8").split("body = text(60,65,")[0])

body = text(60, 65, "LYA / PRIMARY ADMIN REGISTRATION", 18, "#81bac8")
body += text(60, 114, "Local identity with a trusted authority", 36, "#f3f8fa")
body += box(60, 160, 390, 170, "1  Consent + bootstrap", [
    "Owner opens setup intentionally", "Local-template consent is mandatory",
    "Existing admin blocks first-run setup", "Windows Hello adapter is pending"], "#e6b35a")
body += box(505, 160, 390, 170, "2  Live face", [
    "Center + blink", "Turn left, then turn right", "Three templates must agree",
    "Failure leaves no partial profile"])
body += box(950, 160, 390, 170, "3  Live voice", [
    "Six random digits each round", "Three fresh spoken challenges",
    "Voice templates must agree", "Real replay resistance is untested"])
body += arrow(452, 245, 493, 245) + arrow(897, 245, 938, 245)
body += box(740, 410, 600, 190, "4  Atomic local save", [
    "One active primary administrator", "Encrypted face + voice templates",
    "Recovery hash; redemption is pending", "No raw photo or recording accepted by storage"])
body += box(60, 410, 600, 190, "5  Session + greeting", [
    "Five-minute verified local session", "Welcome, owner name",
    "Face or voice recognition personalizes", "Protected work still needs fresh approval"])
body += arrow(1145, 332, 1145, 398) + arrow(738, 505, 672, 505)
body += box(60, 680, 600, 170, "TESTED NOW", [
    "Consent and adapter contract checks", "Fake liveness failures rejected",
    "Encrypted save and one-admin rule", "12 isolated registration tests pass"], "#70d4dd")
body += box(740, 680, 600, 170, "PENDING ON THIS LAPTOP", [
    "Windows Hello desktop adapter", "Real camera and microphone adapters",
    "Lighting, noise and false-match calibration", "Visible deletion and recovery journey"], "#e6b35a")
body += text(60, 930, "Legacy Supabase raw-media enrollment is disabled.", 22, "#f3f8fa")
body += text(60, 976, "Synthetic orchestration only; no live enrollment UI or biometric security validation.", 18, "#e6b35a")
render("16-admin-registration", body)
