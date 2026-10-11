"""Synthetic archive timings; excludes SSH, full LYA, ASR and inference."""
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from storage.public_archive import PublicArchive

with tempfile.TemporaryDirectory(prefix='lya-public-size-') as temporary:
    archive = PublicArchive(Path(temporary)/'archive.sqlite')
    started = time.perf_counter()
    for number in range(1000):
        item = dict(owner='synthetic-check', project='alpha' if number%2 else 'beta', id='doc-'+str(number),
                    revision=1,title='Synthetic document '+str(number),source='https://example.invalid/doc-'+str(number),
                    text='Synthetic asyncio guide marker'+str(number)+' '+('public fixture text '*40),
                    expires_at=None,sensitivity='public')
        archive.handle(dict(op='put',owner=item['owner'],project=item['project'],record=item,expected_revision=0,reviewed_public=True))
    ingestion_ms = (time.perf_counter()-started)*1000
    durations=[]
    for _ in range(7):
        started=time.perf_counter()
        hits=archive.handle(dict(op='search',owner='synthetic-check',project='alpha',query='marker999'))['records']
        durations.append((time.perf_counter()-started)*1000)
        assert [hit['id'] for hit in hits]==['doc-999']
    evidence=dict(documents=1000,read_samples=7,warm_keyword_median_ms=round(statistics.median(durations),3),
                  warm_keyword_max_ms=round(max(durations),3),ingest_total_ms=round(ingestion_ms,3),
                  database_kib=round(archive.path.stat().st_size/1024,1),
                  exclusions=['SSH/network','full application','semantic quality','owner data','sustained CPU/RAM'])
    (Path(__file__).parent/'resource-check.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))
