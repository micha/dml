#!/usr/bin/env python3
"""Run the unchanged independent checker before real completion publication.

It requires marker hashes as inputs. An isolated corpus-owned mirror supplies a
validation-only marker, never a current completion marker in the real repository.
Copies only explicit corpus/source paths, executes no producer code, and cleans
its mirror. The normal live focused_checks.py command can run after publication.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import corpus as C


def main():
    recipe = C.load(C.HERE, 'allowlist.json')
    manifest = C.load(C.HERE, 'manifest.json')
    # Validate paths, sizes, hashes and projections before copying any originals.
    C.check(sources=True)
    review_rel = 'observer-study/review/focused_checks.py'
    review_bytes = C.read_bytes(C.ROOT, review_rel)
    runtime = C.HERE / 'runtime'
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='curator-review-', dir=runtime) as tmp:
        root = Path(tmp)
        def put(rel, data):
            C.parts(rel)
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as out:
                out.write(data)
        for rel in ['allowlist.json','manifest.json','corpus.py','REPORT.md',*manifest['files']]:
            put('observer-study/corpus/' + rel, C.read_bytes(C.HERE, rel))
        for entry in recipe['sources']:
            put(entry['path'], C.read_bytes(C.ROOT, entry['path']))
        put(review_rel, review_bytes)
        summary_rel = 'observer-study/runtime/stage0/validation-input-summary.json'
        summary = C.canonical({'stage':0,'status':'validation-input-only-not-completion',
                               'purpose':'isolated marker dependency fixture; not historical evidence'})
        put(summary_rel, summary)
        report_rel = 'observer-study/corpus/REPORT.md'
        marker = {'status':'validation-input-only-not-completion', 'stage':0,
                  'report':report_rel, 'report_sha256':C.digest(C.read_bytes(C.HERE,'REPORT.md')),
                  'summary':summary_rel, 'summary_sha256':C.digest(summary),
                  'manifest_sha256':C.digest(C.read_bytes(C.HERE,'manifest.json'))}
        put('observer-study/runtime/stage0/curator-done.json', C.canonical(marker))
        assert C.read_bytes(root, review_rel) == review_bytes
        process = subprocess.run([sys.executable,'-B',str(root/review_rel)],
                                 cwd=root, capture_output=True, text=True, timeout=60)
        if process.stderr:
            print(process.stderr, file=sys.stderr, end='')
        result = C.decode_json(process.stdout)
        result['validation_scope'] = 'isolated corpus-owned mirror, validation-only marker; real completion marker not created'
        result['review_source_sha256'] = C.digest(review_bytes)
        result['unchanged_review_bytes'] = C.read_bytes(root, review_rel) == review_bytes
        result['focused_exit_code'] = process.returncode
        print(C.canonical(result).decode(), end='')
        return process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
