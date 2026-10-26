#!/usr/bin/env python3
"""Stage 0 correction recheck. Preserve initial outputs; test only reviewed checkers.

No producer modules are executed. Documented corpus tests/wrapper allocate and
clean their existing corpus/runtime scratch. All persistent outputs are reviewer-*.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'observer-study/runtime/stage0'
PACKAGE = ROOT / 'observer-study/corpus'
EXPECTED_MANIFEST = 'e390d5606f01a4f365ceb4d3c604877f7cc451339a5b555a581ddd9c5f9fde00'
EXPECTED_REVIEW_SOURCE = '083e98039e9f54abfd08929a7c0327ce922ef7d5f8d1368c1603217bffa663d2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen():
    assert sha(PACKAGE / 'manifest.json') == EXPECTED_MANIFEST
    manifest = json.loads((PACKAGE / 'manifest.json').read_bytes())
    assert sha(PACKAGE / 'allowlist.json') == manifest['allowlist_sha256']
    for name, expected in manifest['files'].items():
        assert sha(PACKAGE / name) == expected, name
    return {name: sha(PACKAGE / name)
            for name in ['manifest.json', 'allowlist.json', *manifest['files']]}


def main():
    assert not (RUNTIME / 'reviewer-done.json').exists(), 'current marker must be absent during recheck'
    assert sha(ROOT / 'observer-study/review/focused_checks.py') == EXPECTED_REVIEW_SOURCE
    initial_summary = json.loads((RUNTIME / 'reviewer-initial-summary.json').read_bytes())
    assert initial_summary['measured_results']['unexpected_acceptances'] == 8
    initial_rel = [initial_summary['report'], initial_summary['review_source'],
                   'observer-study/runtime/stage0/reviewer-initial-summary.json',
                   *initial_summary['output_files']]
    initial_hashes = {name: sha(ROOT / name) for name in initial_rel}
    initial_probes = json.loads((RUNTIME / 'reviewer-focused.json').read_bytes())
    assert initial_probes['unexpected_acceptances'] == 8
    original_frozen = frozen()
    # Include all non-scratch files at corpus root; wrapper must not mutate them.
    corpus_root_before = {p.name: sha(p) for p in PACKAGE.iterdir() if p.is_file()}
    curator_before = {name: sha(RUNTIME / name)
                      for name in ['curator-summary.json', 'curator-done.json']}
    commands = [
        ('offline', ['observer-study/corpus/corpus.py']),
        ('sources', ['observer-study/corpus/corpus.py', '--sources']),
        ('availability', ['observer-study/corpus/corpus.py', '--availability']),
        ('tests', ['observer-study/corpus/test_corpus.py']),
        ('focused', ['observer-study/review/focused_checks.py']),
        ('mirror', ['observer-study/corpus/check_review.py']),
        ('final', ['observer-study/corpus/corpus.py', '--sources', '--availability']),
    ]
    results = []
    for label, args in commands:
        argv = [sys.executable, '-B', *args]
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=120)
        suffix = 'txt' if label == 'tests' else 'json'
        output = RUNTIME / f'reviewer-recheck-{label}.{suffix}'
        output.write_bytes(proc.stdout + (proc.stderr if label == 'tests' else b''))
        if proc.stderr and label != 'tests':
            raise AssertionError(proc.stderr.decode())
        assert proc.returncode == 0, (label, proc.returncode)
        result = {'command': 'python3 -B ' + ' '.join(args), 'exit_code': proc.returncode,
                  'output': str(output.relative_to(ROOT))}
        if label == 'tests':
            assert b'Ran 39 tests' in proc.stderr and b'\nOK\n' in proc.stderr
            result['tests_passed'] = 39
        else:
            parsed = json.loads(proc.stdout)
            if label in {'focused', 'mirror'}:
                assert (parsed['reject_required_probes'], parsed['correct_rejections'],
                        parsed['unexpected_acceptances']) == (16, 16, 0)
                assert len(parsed['probes']) == 16
                assert all(p['observed'] == 'rejected' for p in parsed['probes'])
                # Ensure R1/R4 are rejected for the intended reason, not a blanket error.
                reasons = {p['probe']: p.get('detail') for p in parsed['probes']}
                assert reasons['unknown-source-kind-offline'] == 'invalid source kind'
                assert reasons['unknown-gap-schema'] == 'unsupported gap schema'
                assert reasons['negative-original-byte-count-with-sources'] == 'invalid original byte count'
                if label == 'focused':
                    assert parsed['independent_integrity']['curator_completion_hashes_verified'] == 3
                else:
                    assert parsed['review_source_sha256'] == EXPECTED_REVIEW_SOURCE
                    assert parsed['unchanged_review_bytes'] is True
                    assert parsed['focused_exit_code'] == 0
                    assert 'validation-only marker' in parsed['validation_scope']
                result['correct_rejections'] = 16
            else:
                assert parsed['status'] == 'valid'
        results.append(result)
    assert frozen() == original_frozen
    assert {p.name: sha(p) for p in PACKAGE.iterdir() if p.is_file()} == corpus_root_before
    assert {name: sha(ROOT / name) for name in initial_rel} == initial_hashes
    assert {name: sha(RUNTIME / name) for name in curator_before} == curator_before
    assert not (RUNTIME / 'reviewer-done.json').exists()
    # Temp directories created by this run should have been removed by their owners.
    assert not list((PACKAGE / 'runtime').glob('curator-review-*'))
    assert not list(RUNTIME.glob('reviewer-probe-*'))
    inventory = {'status': 'pass', 'commands': results, 'frozen_files_verified': len(original_frozen),
                 'frozen_hashes_before_after': original_frozen,
                 'preserved_initial_artifact_hashes': initial_hashes,
                 'corpus_root_hashes_before_after': corpus_root_before,
                 'curator_completion_artifacts_unchanged': curator_before,
                 'unchanged_review_source_sha256': EXPECTED_REVIEW_SOURCE,
                 'current_reviewer_marker_absent_during_recheck': True,
                 'temporary_probe_and_mirror_cleanup': True}
    print(json.dumps(inventory, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
