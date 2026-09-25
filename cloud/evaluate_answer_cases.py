"""Run the frozen synthetic T03 cases through Brain and save raw review evidence."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from brain.oracle import OracleModel
from brain.workflow import Brain

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'cloud' / 'answer-verification-cases.json'


def evaluate(client, cases, *, clock=time.monotonic, progress=None):
    rows = []
    for case in cases:
        sources = case.get('sources', [])
        researcher = lambda query, **limits: sources
        brain = Brain(client=client, researcher=researcher)
        started = clock()
        answer = brain.respond(case['prompt'])
        row = {
            'id': case['id'], 'category': case['category'],
            'elapsed_ms': round((clock() - started) * 1000),
            'route': answer.route, 'answer': answer.text,
            'expected': case['expected'], 'forbidden': case['forbidden'],
            'score': None, 'review_notes': '',
        }
        rows.append(row)
        if progress:
            progress(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--ids', help='Comma-separated frozen case IDs to resume')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.relative_to(ROOT / 'review')
    if output.exists():
        parser.error('Output exists; preserve it and choose a new path')
    cases = json.loads(CASES.read_text(encoding='utf-8'))['cases']
    if args.ids:
        selected = {value.strip() for value in args.ids.split(',') if value.strip()}
        known = {case['id'] for case in cases}
        if not selected or not selected <= known:
            parser.error('Every requested ID must exist in the frozen case pack')
        cases = [case for case in cases if case['id'] in selected]
    report = {
        'evaluated_at': datetime.now(timezone.utc).isoformat(),
        'data_class': 'synthetic_public',
        'review_status': 'human_review_required',
        'cases': evaluate(OracleModel(), cases,
                          progress=lambda row: print(json.dumps({
                              'id': row['id'], 'route': row['route'],
                              'elapsed_ms': row['elapsed_ms']
                          }), flush=True)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                      encoding='utf-8')
    print(json.dumps({'report': str(output), 'cases': len(report['cases'])}))


if __name__ == '__main__':
    main()
