"""Render local SVG/PNG companion overviews for the validated detailed Mermaid maps.
No browser, network, user-desktop capture or image-generation service.
"""
from pathlib import Path
from html import escape
import sys
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

HERE = Path(__file__).resolve().parent
app = QApplication.instance() or QApplication(sys.argv[:1])


def text(x, y, words, size=20, color='#cee3e9'):
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="Segoe UI, sans-serif" font-size="{size}">{escape(words)}</text>'


def box(x, y, w, h, heading, lines, accent='#70d4dd'):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="#142933" stroke="{accent}" stroke-opacity=".65"/>'
    s += text(x+22,y+36,heading,23,accent)
    for i, line in enumerate(lines):
        s += text(x+22,y+70+i*27,line,18)
    return s


def arrow(x1,y1,x2,y2):
    return f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#638f9b" stroke-width="2" marker-end="url(#arrow)"/>'


def render(name, body):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1040" viewBox="0 0 1400 1040">'
           '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="#638f9b"/></marker></defs>'
           '<rect width="1400" height="1040" fill="#0b1821"/>' + body + '</svg>')
    (HERE / (name+'.svg')).write_text(svg, encoding='utf-8')
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    if not renderer.isValid():
        raise ValueError('Invalid SVG')
    canvas = QImage(1400,1040,QImage.Format.Format_ARGB32)
    canvas.fill(0)
    painter = QPainter(canvas)
    renderer.render(painter)
    painter.end()
    if not canvas.save(str(HERE/(name+'.png'))):
        raise RuntimeError('PNG save failed')


body = text(60,65,'LYA / A BRAIN WITH BOUNDARIES',17,'#81bac8')
body += text(60,114,'How LYA prepares an answer',38,'#f3f8fa')
body += box(60,160,390,150,'1  Your request',['Typed text or a forwarded utterance','Classify the requested operation','Color never establishes identity'])
body += box(505,160,390,150,'2  Identity + permission',['Active person ID and expiry','Exact-request approval for private work','Unknown person stays a guest'])
body += box(950,160,390,150,'3  Relevant context',['Only that person’s active notes','Sources, revisions and linked notes','Credentials excluded'])
body += arrow(452,235,493,235)+arrow(897,235,938,235)+arrow(1145,312,1145,365)
body += box(950,380,390,160,'4  Reason / council',['Ordinary: one model request','Important: reviewer, planner, critic','Then a synthesis; at most four calls'])
body += box(505,380,390,160,'5  Check before showing',['Identity still valid? Context expired?','Was the operation cancelled?','Agreement is not verification'])
body += box(60,380,390,160,'6  Answer clearly',['Recommendation and concise reasons','Saved-context references and uncertainty','Generated claims are not auto-saved'])
body += arrow(948,458,907,458)+arrow(503,458,462,458)
body += text(60,597,'Explicit saves take a separate path into memory',25,'#f3f8fa')
cards = [('Temporary',['Request context / RAM','Session notes: 15 min idle','Clear on session change']),
         ('Short-term',['7 days by default','Useful recent information','Excluded after expiry']),
         ('Longer-term',['90 days by default','Ongoing projects / lessons','Explicit saved notes']),
         ('Timed',['Your exact deadline','Timezone required','Expired notes excluded']),
         ('Permanent',['Explicit save only','No automatic expiry','Still correctable / deletable'])]
for i,(label,lines) in enumerate(cards):
    body += box(60+i*260,625,240,145,label,lines,'#e3bd79')
body += box(60,805,1280,125,'Small knowledge graph · encrypted SQLite',[
    'LYA plan  — depends_on →  laptop resources       |       Both notes belong to the same person.',
    'Each note: owner · label · value · source · revision · retention · expiry. Forgetting also removes its links.'])
body += text(60,970,'TESTED: storage, boundaries, expiry, UI dispatch and council orchestration with synthetic fixtures.',17)
body += text(60,1002,'PENDING: real identity/phone binding, a reachable model, live evidence research and cloud backup.',17,'#e3bd79')
render('11-brain-workflow',body)

body = text(60,65,'LYA / STORAGE SCHEMA',17,'#81bac8')
body += text(60,114,'Ownership first. Relationships second.',37,'#f3f8fa')
body += box(60,175,390,275,'PEOPLE',['person_id  ·  primary key','display_name','role','active','Owns every personal record'])
body += box(505,175,390,370,'MEMORIES',['id  ·  primary key','person_id  ·  owner','kind','key_enc / value_enc','source / revision','retention / expires_at','created_at / updated_at','Nodes of the knowledge graph'])
body += box(950,175,390,275,'MEMORY_LINKS',['src  →  memory ID','dst  →  memory ID','relation','Same owner, active notes only','Delete note → remove edges'])
body += arrow(452,280,493,280)+arrow(897,280,938,280)
body += box(60,585,390,230,'FACE_TEMPLATES',['person_id  ·  owner','embedding_enc','model_version / quality','Runtime enrollment is deferred'],'#e3bd79')
body += arrow(255,452,255,573)
body += box(505,585,835,230,'Outside persistent conversational memory',[
    'Working context: one request, then discarded.',
    'Session notes: bounded RAM only; never written to SQLite.',
    'Existing pending_faces, vault_items and audit_events remain.',
    'Credentials are not eligible for model context.'],'#e3bd79')
body += text(60,882,'One local encrypted database; no separate graph server or vector model is required.',23)
body += text(60,930,'Additive migration keeps existing note data and its previous non-expiring behavior.',20)
body += text(60,979,'Companion overview · detailed validated schema: 12-brain-schema.mmd',17,'#81bac8')
render('12-brain-schema',body)
print('Rendered workflow and schema SVG/PNG companions.')
