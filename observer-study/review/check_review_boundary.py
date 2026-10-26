#!/usr/bin/env python3
"""Focused wrapper trust check using synthetic child outputs, never producer code.

This deliberately mocks only the subprocess response. It establishes whether the
wrapper itself validates result fields; it is not an attack on the reviewed child.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'observer-study/corpus'
RUNTIME = ROOT / 'observer-study/runtime/stage0'
sys.path.insert(0, str(PACKAGE))
spec = importlib.util.spec_from_file_location('reviewed_mirror_wrapper', PACKAGE / 'check_review.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def main():
    real_marker = (RUNTIME / 'curator-done.json').read_bytes()
    results = []
    for name, code, stdout in [
        ('zero-exit-without-rejection-fields', 0, '{}'),
        ('zero-exit-with-contradictory-rejection-fields', 0,
         '{"reject_required_probes":16,"correct_rejections":0,"unexpected_acceptances":16}'),
        ('nonzero-exit-propagates', 1, '{}'),
        ('malformed-child-json-rejected', 0, 'not JSON'),
    ]:
        fake = subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr='')
        output = io.StringIO()
        with patch.object(M.subprocess, 'run', return_value=fake), contextlib.redirect_stdout(output):
            try:
                returned = M.main()
            except ValueError as exc:
                results.append({'case': name, 'outcome': 'rejected', 'exception': type(exc).__name__})
            else:
                results.append({'case': name, 'wrapper_returncode': returned,
                                'result': json.loads(output.getvalue())})
    assert results[0]['wrapper_returncode'] == 0
    assert results[1]['wrapper_returncode'] == 0
    assert results[1]['result']['unexpected_acceptances'] == 16
    assert results[2]['wrapper_returncode'] == 1
    assert results[3]['outcome'] == 'rejected'
    assert (RUNTIME / 'curator-done.json').read_bytes() == real_marker
    assert not (RUNTIME / 'reviewer-done.json').exists()
    assert not list((PACKAGE / 'runtime').glob('curator-review-*'))
    print(json.dumps({'status': 'observations-confirmed', 'cases': results,
                     'real_curator_marker_unchanged': True, 'mirror_cleanup': True,
                     'meaning': 'Wrapper trusts child exit code; does not independently enforce rejection fields. Actual unchanged child passes separately.'}, indent=2))


if __name__ == '__main__':
    main()
