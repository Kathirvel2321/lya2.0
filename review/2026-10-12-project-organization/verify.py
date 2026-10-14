"""Dated organization verification: static reads, fake config, no app launch."""
import ast
import configparser
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from organize import ROOT, HERE, MANIFEST, missing_links


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


data = json.loads(MANIFEST.read_text(encoding='utf-8'))
assert data['status'] in ('moved','verified')
mapping = {m['source']:m['destination'] for m in data['moves'] if m['category']!='replaced-document'}
for item in data['moves']:
    path = ROOT/item['destination']
    assert path.is_file(), item['destination']
    if item['destination'].startswith('archive/'):
        assert sha(path)==item['sha256'],item['destination']
    if item['category']!='replaced-document':
        assert not (ROOT/item['source']).is_file(),item['source']
for name, expected in data['retained_hashes'].items():
    assert sha(ROOT/name)==expected,name

active = set(data['retained_hashes']) | {item['path'] for item in data['rewritten_documents']}
active |= {mapping.get(name,name) for name in data['baseline_missing_links'] if not mapping.get(name,name).startswith('archive/')}
active |= {'README.md','AGENTS.md','lya-project-brain.md','docs/README.md','archive/README.md','archive/AGENTS.md'}
active |= {p.relative_to(ROOT).as_posix() for p in HERE.glob('*.py')}
active |= {p.relative_to(ROOT).as_posix() for p in HERE.glob('*.md')}
parsed = 0
local_links = 0
new_missing = {}
original_names = {target:source for source,target in mapping.items()}
for name in sorted(active):
    path = ROOT/name
    if not path.is_file():
        continue
    if path.suffix=='.py' and not name.startswith('archive/'):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'),filename=name)
        parsed += 1
        for node in ast.walk(tree):
            modules = [alias.name for alias in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
            assert not any(module=='archive' or module.startswith('archive.') for module in modules),name
    if path.suffix=='.md':
        missing = set(missing_links(name,path.read_text(encoding='utf-8-sig')))
        old = original_names.get(name,name)
        previous = {mapping.get(target,target) for target in data['baseline_missing_links'].get(old,[])}
        if missing-previous:
            new_missing[name] = sorted(missing-previous)
        local_links += 1
assert not new_missing,json.dumps(new_missing,indent=2)

# Exercise the actual reader without importing Qt, sensors, auth or providers.
tree = ast.parse((ROOT/'desktop/app.py').read_text(encoding='utf-8-sig'))
documents = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id=='DOCUMENTS' for t in n.targets))
reader = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='read_project_document')
namespace = {'ROOT':ROOT,'DOCUMENTS':documents}
exec(compile(ast.Module(body=[reader],type_ignores=[]),'desktop-document-reader','exec'),namespace)
for name in documents:
    assert namespace['read_project_document'](name).strip(),name
try:
    namespace['read_project_document']('archive/retired/maintenance/store_key.py')
except PermissionError:
    pass
else:
    raise AssertionError('Desktop document allowlist widened')
assert not (ROOT/'archive/__init__.py').exists()
assert not (ROOT/'noneeded').exists()
pytest = configparser.ConfigParser()
pytest.read(ROOT/'pytest.ini')
assert '--ignore=archive' in pytest['pytest']['addopts'].split()
launcher = (HERE/'launcher-validation.txt').read_text(encoding='utf-8')
assert launcher.rstrip().endswith('OK')
launcher_tests = int(re.search(r'Ran (\d+) tests',launcher)[1])
mobile = json.loads((HERE/'mobile-client-validation.json').read_text(encoding='utf-8'))
assert mobile['success'] and not mobile['provider_call']

result = dict(success=True,date='2026-10-12',moved_files=len(data['moves']),
    archived_original_hashes=sum(m['destination'].startswith('archive/') for m in data['moves']),
    retained_file_hashes=len(data['retained_hashes']),active_python_files_parsed=parsed,
    maintained_markdown_files_checked=local_links,new_broken_markdown_links=0,
    desktop_documents_read=len(documents),desktop_allowlist_preserved=True,
    archive_is_not_a_test_discovery_package=True,pytest_archive_excluded=True,
    isolated_launcher_tests=launcher_tests,synthetic_mobile_client_checks=mobile['synthetic_client_checks'],
    real_sensors=False,provider_call=False,deployed=False)
(HERE/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
