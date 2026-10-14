"""One-time, local source/document organization. Never imports project runtime."""
import hashlib
import json
from pathlib import Path
import posixpath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MANIFEST = HERE/'move-manifest.json'
KEPT_REVIEWS = {'2026-10-03-voice-conversation', '2026-10-05-conversation-design'}
ROOT_DOCS = {
    'BUILD_PROGRESS.md': 'archive/history/documentation/BUILD_PROGRESS.md',
    'LYA_ARCHITECTURE.md': 'docs/architecture/LYA_ARCHITECTURE.md',
    'LYA_BRAIN_WORKFLOW.md': 'docs/architecture/LYA_BRAIN_WORKFLOW.md',
    'LYA_ADVANCED_BRAIN_PLAN.md': 'docs/plans/LYA_ADVANCED_BRAIN_PLAN.md',
    'LYA_CAMERA_VOICE_DECISION.md': 'docs/plans/LYA_CAMERA_VOICE_DECISION.md',
    'LYA_IMPLEMENTATION_CHECKLIST.md': 'docs/plans/LYA_IMPLEMENTATION_CHECKLIST.md',
    'LYA_MODEL_STRATEGY.md': 'docs/plans/LYA_MODEL_STRATEGY.md',
    'LYA_STORAGE_SECURITY_PLAN.md': 'docs/plans/LYA_STORAGE_SECURITY_PLAN.md',
    'LYA_TASK_REASONING_LEVELS.md': 'docs/guides/LYA_TASK_REASONING_LEVELS.md',
    'LYA_TASK_ROADMAP.md': 'docs/plans/LYA_TASK_ROADMAP.md',
    'LYA_TEST_GUIDE.md': 'docs/guides/LYA_TEST_GUIDE.md',
}


def checked(name):
    path = ROOT/name
    assert path.resolve().is_relative_to(ROOT.resolve()) and not path.is_symlink(), name
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_files():
    result = subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True)
    return [n for n in result.stdout.decode().split('\0') if n and checked(n).is_file()]


def destination(name):
    if name in ROOT_DOCS:
        return ROOT_DOCS[name], 'documentation'
    if name == 'lya-project-brain.md':
        return 'archive/history/continuity/project-brain-through-2026-10-12.md', 'replaced-document'
    if name == 'README.md':
        return 'archive/history/documentation/README-before-organization.md', 'replaced-document'
    if name.startswith('noneeded/'):
        tail = name.removeprefix('noneeded/')
        if tail.startswith('unsafe-test-scripts/'):
            return 'archive/unsafe-tests/'+tail.removeprefix('unsafe-test-scripts/'), 'unsafe-tests'
        return 'archive/retired/'+tail, 'retired'
    if name.startswith('tools/voice-evaluation/'):
        return 'archive/experiments/voice-evaluation/'+name.removeprefix('tools/voice-evaluation/'), 'unused-evaluation'
    if name in ('store_key.py','review_checks.py','review/review_20260913.py'):
        return 'archive/retired/maintenance/'+Path(name).name, 'superseded-maintenance'
    if name == 'test_summary.txt':
        return 'archive/history/validation/'+name, 'historical-validation'
    if name.startswith('review/'):
        folder = name.split('/')[1]
        if folder not in KEPT_REVIEWS and (folder < '2026-10-10' or folder.startswith('local-model-')):
            return 'archive/history/reviews/'+name.removeprefix('review/'), 'historical-review'
    if name.startswith(tuple('desktop/qa/'+d+'/' for d in
            ('2026-09-15-orb','2026-09-16-compact','2026-09-17-bottom-center'))):
        return 'archive/history/desktop-qa/'+name.removeprefix('desktop/qa/'), 'historical-layout'
    return None


LINK = re.compile(r'(!?\[[^\]\n]*\]\()([^\)\n]+)(\))')


def local_target(source, target):
    target = target.strip().strip('<>')
    if not target or target.startswith(('#','/')) or re.match(r'^[a-zA-Z][\w+.-]*:',target):
        return None
    path = target.split('#',1)[0].split('?',1)[0]
    return posixpath.normpath(posixpath.join(posixpath.dirname(source),path))


def missing_links(source, text):
    return sorted({target for match in LINK.finditer(text)
        if (target := local_target(source,match[2])) and not (ROOT/target).exists()})


def rewrite_document(text, old, new, mapping):
    # Resolve links from their original document location, then relocate them.
    saved = []
    def link(match):
        target = local_target(old,match[2])
        if target is None:
            value = match[0]
        else:
            relocated = mapping.get(target,target)
            tail = match[2].strip().strip('<>')[len(match[2].strip().strip('<>').split('#',1)[0].split('?',1)[0]):]
            relative = posixpath.relpath(relocated,posixpath.dirname(new) or '.')+tail
            value = match[1]+('<'+relative+'>' if ' ' in relative else relative)+match[3]
        saved.append(value)
        return f'@@LOCAL_LINK_{len(saved)-1}@@'
    text = LINK.sub(link,text)
    # Inline code and prose use repository-relative paths, not document-relative links.
    replacements = dict(mapping)
    for before, after in list(mapping.items()):
        if before.startswith(('review/','noneeded/')) and '/' in before:
            replacements.setdefault(posixpath.dirname(before)+'/',posixpath.dirname(after)+'/')
    for before, after in sorted(replacements.items(),key=lambda item:-len(item[0])):
        text = re.sub(r'(?<![\w/\\.-])'+re.escape(before)+r'(?![\w.-])',lambda _:after,text)
    for index, value in enumerate(saved):
        text = text.replace(f'@@LOCAL_LINK_{index}@@',value)
    return text


def plan():
    assert not (ROOT/'archive').exists(), 'Archive already exists; inspect manifest instead of rerunning.'
    files = tracked_files()
    moves = []
    for name in files:
        if item := destination(name):
            target, category = item
            assert not checked(target).exists(), target
            moves.append(dict(source=name,destination=target,category=category,sha256=digest(checked(name))))
    moved = {item['source'] for item in moves}
    # These hashes cover retained tracked code/assets/config examples/launchers/tests,
    # including the already modified mobile client. No ignored credentials/data are read.
    retained = {name:digest(checked(name)) for name in files
        if name not in moved and Path(name).suffix not in ('.md','.mmd','.svg','.html')}
    retained['cloud/mobile.html'] = digest(ROOT/'cloud/mobile.html')
    baseline_links = {name:missing_links(name,checked(name).read_text(encoding='utf-8-sig'))
        for name in files if name.endswith('.md') and not name.startswith('noneeded/')}
    data = dict(date='2026-10-12',status='planned',moves=moves,retained_hashes=retained,
        baseline_missing_links=baseline_links,kept_reviews=sorted(KEPT_REVIEWS),rewritten_documents=[])
    MANIFEST.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(planned_files=len(moves),retained_hashed_files=len(retained),
        categories={category:sum(m['category']==category for m in moves) for category in sorted({m['category'] for m in moves})})))


def apply():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert data['status']=='planned'
    mapping = {item['source']:item['destination'] for item in data['moves'] if item['category']!='replaced-document'}
    for item in data['moves']:
        source, target = checked(item['source']), checked(item['destination'])
        assert source.is_file() and digest(source)==item['sha256'] and not target.exists(),item['source']
    # Validate every final absolute path before moving a single file.
    completed = []
    try:
        for item in data['moves']:
            source, target = checked(item['source']), checked(item['destination'])
            target.parent.mkdir(parents=True,exist_ok=True)
            source.rename(target)
            completed.append(item)
    except BaseException:
        for item in reversed(completed):
            source, target = checked(item['source']), checked(item['destination'])
            source.parent.mkdir(parents=True,exist_ok=True)
            target.rename(source)
        raise
    # Historical archive bytes stay untouched. Only maintained explanations get link updates.
    for old in data['baseline_missing_links']:
        new = mapping.get(old,old)
        if new.startswith('archive/') or not checked(new).is_file():
            continue
        path = checked(new)
        raw = path.read_bytes()
        text = raw.decode('utf-8-sig')
        updated = rewrite_document(text,old,new,mapping)
        if updated != text:
            path.write_bytes(updated.encode('utf-8'))
            data['rewritten_documents'].append(dict(path=new,sha256=digest(path),
                previous_missing_links=data['baseline_missing_links'][old]))
    # Remove only empty former directories; ignored/private/untracked contents stay put.
    parents = {checked(item['source']).parent for item in data['moves']}
    for path in sorted(parents,key=lambda p:len(p.parts),reverse=True):
        while path!=ROOT and path.exists() and not any(path.iterdir()):
            assert path.resolve().is_relative_to(ROOT.resolve())
            path.rmdir()
            path = path.parent
    data['status']='moved'
    MANIFEST.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(moved_files=len(completed),rewritten_documents=len(data['rewritten_documents']))))


if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ('--plan','--apply')
    (plan if sys.argv[1]=='--plan' else apply)()
