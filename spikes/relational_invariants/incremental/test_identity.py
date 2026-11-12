import copy
from pathlib import Path

import pytest

from incremental.driver import Controller, envelope
from incremental.identity import FORMAT, REQUIRED, canonical, digest, file_manifest, key, manifest_digest, parse


def fixture_envelope(stage='E'):
    return {'format': FORMAT, 'namespace': digest(b'CONTROL'), 'stage': stage,
            'dependencies': {name: digest(name.encode()) for name in REQUIRED[stage]},
            'context': {'scenario': 'CONTROL'}, 'limits': {'objects': 10000}}


@pytest.mark.parametrize(('stage', 'field'), [(stage, name) for stage in REQUIRED for name in sorted(REQUIRED[stage])])
def test_every_dependency_partitions_key(stage, field):
    original = fixture_envelope(stage)
    changed = copy.deepcopy(original)
    changed['dependencies'][field] = digest(b'actual changed dependency')
    assert key(original) != key(changed)


@pytest.mark.parametrize('field', ['namespace', 'context', 'limits'])
def test_applicable_context_namespace_and_limits_partition(field):
    original = fixture_envelope()
    changed = copy.deepcopy(original)
    changed[field] = digest(b'other') if field == 'namespace' else {'changed': True}
    assert key(original) != key(changed)


@pytest.mark.parametrize('value', [1.25, 2**63, -(2**63)-1, ('tuple',), {1: 'key'}, b'implicit bytes'])
def test_ambiguous_values_rejected(value):
    with pytest.raises(ValueError):
        canonical(value)


def test_duplicates_nonfinite_and_unknown_fields_fail_closed():
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1.5}'):
        with pytest.raises(ValueError):
            parse(raw)
    unknown = fixture_envelope()
    unknown['unclaimed'] = True
    with pytest.raises(ValueError):
        key(unknown)
    unknown = fixture_envelope()
    unknown['dependencies'].pop('candidate')
    with pytest.raises(ValueError):
        key(unknown)


def test_path_neutral_code_manifests_conflicts_and_symlinks(tmp_path):
    left, right = tmp_path / 'left', tmp_path / 'right'
    for directory in (left, right):
        directory.mkdir()
        (directory / 'same.py').write_bytes(b'code bytes')
    rows = file_manifest(left)
    assert manifest_digest(rows) == manifest_digest(file_manifest(right))
    with pytest.raises(ValueError):
        manifest_digest(rows + rows)
    (right / 'link.py').symlink_to(left / 'same.py')
    with pytest.raises(ValueError):
        file_manifest(right)


def test_directory_prefixes_use_relative_string_order_not_path_component_order(tmp_path):
    for name in ('spec/a.py', 'spec-next/a.py'):
        target = tmp_path / name
        target.parent.mkdir()
        target.write_bytes(b'owned fixture bytes')
    rows = file_manifest(tmp_path)
    assert [row['path'] for row in rows] == ['spec-next/a.py', 'spec/a.py']
    assert manifest_digest(rows) == digest(canonical(rows))


def test_real_snapshot_candidate_and_stage_changes_partition_only_own_stages(pins):
    a, b = envelope(pins, 'E'), envelope(pins, 'E', candidate='B')
    assert key(a) != key(b)
    upstream = {'key': key(a), 'digest': digest(b'E evidence'), 'roots': ['a' * 32]}
    p1 = envelope(pins, 'P', variant='P1', upstream=upstream)
    p2 = envelope(pins, 'P', variant='P2', upstream=upstream)
    assert key(p1) != key(p2)
    projected = {'key': key(p1), 'digest': digest(b'P artifact'), 'roots': upstream['roots']}
    c1 = envelope(pins, 'C', variant='C1', upstream=projected)
    c2 = envelope(pins, 'C', variant='C2', upstream=projected)
    assert key(c1) != key(c2)
    relocated = {**pins, 'root': '/different/operational/prefix'}
    assert envelope(relocated, 'E') == a
    # Checker payloads are deliberately NOT a dependency of E or P.
    changed_checker = copy.deepcopy(pins)
    changed_checker['fingerprints']['C1'] = digest(b'new checker')
    assert envelope(changed_checker, 'E') == a
    assert envelope(changed_checker, 'P', variant='P1', upstream=upstream) == p1
    chained = {**upstream, 'key': key(b)}
    assert key(envelope(pins, 'P', variant='P1', upstream=chained)) != key(p1)
    with pytest.raises(ValueError):
        envelope(pins, 'E', scenario='random ambient context')
    with pytest.raises(ValueError):
        envelope(pins, 'C', variant='C-disabled', upstream=projected)


def test_exercise_cannot_smuggle_an_actual_variant_under_another_key(pins):
    controller = Controller.__new__(Controller)
    controller.pins = pins
    controller.pins_path = Path(pins['root']) / 'pins.json'
    # No store/actor exists: the variant guard must reject before touching either.
    with pytest.raises(ValueError, match='variant differs'):
        controller.stage(envelope(pins, 'E'), variant='wrong')
