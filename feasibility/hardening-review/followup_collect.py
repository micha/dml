#!/usr/bin/env python3
"""Condensed evidence with detached source/marker provenance, no raw state bodies."""
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import sys

HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__=='__main__':
    base=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(json.loads((HERE/'runtime/followup/latest.json').read_text())['base'])
    assert base.is_relative_to(HERE/'runtime/followup')
    manifest=json.loads((base/'source-manifest.json').read_text())
    for item in manifest['sources']:
        assert sha(Path(item['copy']))==item['sha256'], 'snapshot changed'
        assert sha(Path(item['source']))==item['sha256'], 'worker source changed since snapshot; reassessment needed'
    regression=json.loads((base/'gate/test-results.json').read_text())
    review=json.loads((base/'followup-review-results.json').read_text())
    assert regression['passed'] and review['passed']
    regression_logs=list((base/'gate/runtime').rglob('cli.log'))
    evidence={'status':'completed','report':str(HERE/'followup-report.md'),'source_manifest':manifest,
              'versions':{'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'opentofu':regression['tool']['terraform_version'],
                          'journal':'journal-v2','provider':'immutable 0.1.0'},
              'regression':{'result_groups':len(regression['cases']),'passed':regression['passed'],
                            'cli_invocations':sum(len(p.read_text().splitlines()) for p in regression_logs),
                            'results':str(base/'gate/test-results.json')},
              'independent':review,
              'review_code_checksums':{p.name:sha(p) for p in HERE.glob('followup_*.py')},
              'historical_boundary':'Initial report.md, evidence.json, checks.py and done.json remain unchanged. Original coordinator launcher exited with shell parse status 2 after delivery; not a zero wrapper exit.',
              'documentation':{'context7':'Monthly quota exceeded',
                               'files':'https://opentofu.org/docs/language/files/',
                               'memfd':'https://man7.org/linux/man-pages/man2/memfd_create.2.html'},
              'limitations':['No universal HCL parser, immutable execution directory, provider Delete authority, authoritative fake-journal membership/ownership, versioned exact manager receipts or state erasure.']}
    (HERE/'followup-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'evidence':str(HERE/'followup-evidence.json'),'regression':evidence['regression'],
                      'independent_groups':len(review['cases']),'independent_cli':review['cli_invocations'],
                      'bridge_cli':review['bridge_cli_invocations']}))
