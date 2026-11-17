"""Linux/Nix portability controls; no acceptance stages or historical evidence replay."""
import copy
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from incremental import driver, runtime
from incremental.identity import canonical, digest, parse
from per_exercise import pins as per_pins


@pytest.fixture(scope='module')
def reviewed():
    return runtime.read_review(os.environ['PORTABLE_REVIEW'])


def test_reviewed_runtime_matches_actual_executables(reviewed):
    runtime.verify_runtime(reviewed['runtime'])
    assert Path(sys.executable).resolve() == Path(reviewed['runtime']['python'])
    assert reviewed['runtime']['machine'] == runtime.platform.machine()


@pytest.mark.parametrize('field', ['python_sha256', 'duckdb_sha256', 'machine', 'closure', 'library_path'])
def test_runtime_identity_tamper_rejected(reviewed, field):
    changed = copy.deepcopy(reviewed['runtime'])
    changed[field] = [] if field == 'closure' else 'not-the-reviewed-value'
    with pytest.raises(ValueError):
        runtime.verify_runtime(changed)


@pytest.mark.parametrize('path', ['/usr/bin/python3', '/tmp/tool', '/nix/store-other/tool'])
def test_non_nix_runtime_rejected(path):
    with pytest.raises(ValueError, match='Nix store'):
        runtime.store_root(path)


def test_source_inventory_tracks_bytes_and_rejects_symlinks(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    module = tmp_path / 'spikes/relational_invariants/incremental/runtime.py'
    module.parent.mkdir(parents=True)
    module.write_bytes(b'original')
    source = tmp_path / 'source.py'
    source.write_bytes(b'first')
    subprocess.run(['git', '-C', str(tmp_path), 'add', 'source.py'], check=True)
    first = runtime.source_manifest(tmp_path)
    source.write_bytes(b'second')
    second = runtime.source_manifest(tmp_path)
    assert first != second
    assert next(row for row in second if row['path'] == 'source.py')['sha256'] == digest(b'second')
    source.unlink()
    source.symlink_to(module)
    with pytest.raises(ValueError, match='regular file'):
        runtime.source_manifest(tmp_path)


def test_prepare_requires_explicit_review_without_creating_destination(tmp_path):
    for prepare in (driver.prepare, per_pins.prepare):
        with pytest.raises(ValueError, match='review_path'):
            prepare(Path.cwd(), tmp_path / 'never')
        assert not (tmp_path / 'never').exists()


@pytest.mark.parametrize('damage', ['source', 'native', 'python', 'duckdb', 'format'])
def test_preparation_rejects_changed_review_before_copy(reviewed, tmp_path, damage):
    changed = copy.deepcopy(reviewed)
    if damage == 'source':
        changed['sources'][0]['sha256'] = digest(b'wrong')
    elif damage == 'native':
        changed['core_sha256'] = digest(b'wrong')
    elif damage == 'format':
        changed['format'] = 'unknown'
    else:
        changed['runtime'][damage + '_sha256'] = digest(b'wrong')
    path = tmp_path / 'review.json'
    path.write_bytes(canonical(changed))
    destination = tmp_path / 'never'
    with pytest.raises(ValueError):
        driver.prepare(Path.cwd(), destination, review_path=path)
    assert not destination.exists()


def test_runtime_changes_partition_namespace_and_stage_key():
    from per_exercise.profiles import envelope, specs
    from incremental.identity import key
    pins = per_pins.verify(Path(os.environ['PER_EXERCISE_PINS']))
    changed = copy.deepcopy(pins)
    changed['runtime_digest'] = digest(b'another reviewed runtime')
    assert key(envelope(pins, 'E', specs()[0])) != key(envelope(changed, 'E', specs()[0]))
    base = driver.verify_pins(Path(pins['root']) / 'base/pins.json')
    alternate = copy.deepcopy(base)
    alternate['runtime']['machine'] = 'another-platform'
    assert per_pins.claims(Path(pins['root']), base)['namespace'] != per_pins.claims(Path(pins['root']), alternate)['namespace']


def test_pin_verification_rejects_relocated_receipt(tmp_path):
    original = Path(os.environ['PER_EXERCISE_PINS'])
    pins = parse(original.read_bytes())
    # Location is checked before any filesystem walking, so copied receipts cannot relocate.
    moved = tmp_path / 'pins.json'
    moved.write_bytes(canonical(pins))
    with pytest.raises(ValueError, match='location'):
        per_pins.verify(moved)


@pytest.mark.parametrize('damage', ['native', 'source', 'runtime-claim', 'bytecode'])
def test_frozen_snapshot_tamper_rejected(tmp_path, damage):
    pins = per_pins.verify(Path(os.environ['PER_EXERCISE_PINS']))
    base = Path(pins['root']) / 'base'
    copied = tmp_path / 'base'
    shutil.copytree(base, copied)
    receipt = parse((copied / 'pins.json').read_bytes())
    receipt['root'] = str(copied)
    if damage == 'runtime-claim':
        receipt['runtime']['python_sha256'] = digest(b'forged interpreter')
    elif damage == 'bytecode':
        cache = copied / 'controller/daggerml/__pycache__'
        cache.mkdir()
        (cache / 'unexpected.pyc').write_bytes(b'not an admitted asset')
    else:
        relative = ('controller/daggerml/_core.abi3.so' if damage == 'native' else
                    'candidate-A/python/daggerml/daggerml/builtin.py')
        target = copied / relative
        target.chmod(0o644)
        target.write_bytes(target.read_bytes() + b'tamper')
    path = copied / 'pins.json'
    path.chmod(0o644)
    path.write_bytes(canonical(receipt))
    with pytest.raises(ValueError):
        driver.verify_pins(path)
