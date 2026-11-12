from pathlib import Path

import pytest

from incremental.artifacts import admit, describe, finalize, validate
from incremental.identity import canonical, digest


def artifact(root, name, producer='CONTROL/fixture', dependencies=None, stage='E', key=None, status='success'):
    partial = root / (name + '.partial')
    partial.mkdir()
    (partial / 'data.json').write_bytes(canonical({'fixture': 'CONTROL, not stage execution'}))
    document = describe(partial, stage=stage, key=key or digest(b'key'), producer=producer,
                        dependencies=dependencies or {}, status=status, exit_code=0 if status == 'success' else 1)
    fingerprint = finalize(partial, root / name, document)
    return fingerprint, document


@pytest.mark.parametrize('fault', ['missing', 'tamper', 'unlisted', 'symlink', 'manifest', 'partial'])
def test_incomplete_tampered_and_unsafe_artifacts_never_become_success(tmp_path, fault):
    fingerprint, document = artifact(tmp_path, 'case')
    assert admit(tmp_path, 'case', expected_digest=fingerprint) == document
    directory = tmp_path / 'case'
    if fault == 'missing':
        (directory / 'data.json').unlink()
    elif fault == 'tamper':
        (directory / 'data.json').write_bytes(b'different')
    elif fault == 'unlisted':
        (directory / 'additional.py').write_bytes(b'undeclared')
    elif fault == 'symlink':
        (directory / 'data.json').unlink()
        (directory / 'data.json').symlink_to(directory / 'manifest.json')
    elif fault == 'manifest':
        (directory / 'manifest.json').write_bytes(canonical({**document, 'producer': 'wrong'}))
    else:
        directory.rename(tmp_path / 'case.partial')
    with pytest.raises((ValueError, FileNotFoundError)):
        admit(tmp_path, 'case', expected_digest=fingerprint)


def test_finalize_is_not_dml_publication_and_orphan_is_unselected(tmp_path):
    partial = tmp_path / 'orphan.partial'
    partial.mkdir()
    (partial / 'data.json').write_bytes(b'{}')
    document = describe(partial, stage='P', key=digest(b'p'), producer='CONTROL/orphan', dependencies={},
                        status='success', exit_code=0)
    with pytest.raises(ValueError):
        admit(tmp_path, 'orphan.partial')
    (partial / 'data.json').write_bytes(b'changed before finalization')
    with pytest.raises(ValueError):
        finalize(partial, tmp_path / 'orphan', document)
    assert not (tmp_path / 'orphan').exists()


def test_outcome_digest_fields_and_profile_fail_closed(tmp_path):
    _, document = artifact(tmp_path, 'case')
    for changes in ({'status': 'success', 'exit': 1}, {'stage': 'future'}, {'surprise': True}):
        with pytest.raises(ValueError):
            validate({**document, **changes})
    with pytest.raises(ValueError):
        admit(tmp_path, '../case')
