"""Pure guards plus ONE shared CONTROL fixture, never an acceptance stage warm-up."""
from pathlib import Path
import copy
import os
import sys

import pytest

from incremental.identity import canonical, digest, key, parse
from incremental.driver import DUCKDB
from incremental.stages import load_dml
from per_exercise.profiles import envelope, specs, material_key, validate_spec
from per_exercise.pins import verify
from per_exercise.predicate import assert_agreement
from per_exercise import capsules


@pytest.fixture(scope='module')
def pins():
    return verify(Path(os.environ['PER_EXERCISE_PINS']))


def upstream(stage='E'):
    return {'stage': stage, 'key': digest((stage + 'key').encode()), 'digest': digest((stage + 'data').encode()),
            'roots': ['a' * 32], 'spec': specs()[0]}


DEPENDENCIES = [(stage, field) for stage, fields in {
    'E': ['candidate', 'exercise', 'wrapper', 'runtime'],
    'P': ['upstream_key', 'upstream_artifact', 'normalizer', 'decoder', 'wrapper', 'runtime'],
    'C': ['upstream_key', 'upstream_artifact', 'checker', 'wrapper', 'runtime']}.items() for field in fields]


@pytest.mark.parametrize('stage,field', DEPENDENCIES)
def test_every_declared_dependency_partitions_key(pins, stage, field):
    original = envelope(pins, stage, specs()[0], variant=stage + '1', upstream=upstream('E' if stage == 'P' else 'P'))
    changed = copy.deepcopy(original)
    changed['dependencies'][field] = digest(b'changed')
    assert key(original) != key(changed)


def test_only_changed_case_input_changes_its_E_key(pins):
    first = [key(envelope(pins, 'E', case)) for case in specs()]
    next_ = [key(envelope(pins, 'E', case)) for case in specs(True)]
    assert [a == b for a, b in zip(first, next_)] == [True, False, True]
    assert all(key(envelope(pins, 'E', case, candidate='B')) != original for case, original in zip(specs(), first))


@pytest.mark.parametrize('stage', ['P', 'C'])
def test_variant_payload_changes_no_upstream_key(pins, stage):
    up = upstream('E' if stage == 'P' else 'P')
    assert key(envelope(pins, stage, specs()[0], variant=stage + '1', upstream=up)) != key(envelope(pins, stage, specs()[0], variant=stage + '2', upstream=up))
    altered = copy.deepcopy(pins)
    altered['payloads'][stage + '1'] = digest(b'changed payload')
    assert key(envelope(altered, 'E', specs()[0])) == key(envelope(pins, 'E', specs()[0]))
    if stage == 'C':
        assert key(envelope(altered, 'P', specs()[0], variant='P1', upstream=upstream())) == key(envelope(pins, 'P', specs()[0], variant='P1', upstream=upstream()))


@pytest.mark.parametrize('change', [{'value': True}, {'value': 2**63}, {'fault': 1},
                                  {'label': 'latest'}, {'unknown': 0}, {'value': 2**63-1, 'fault': True}])
def test_unsupported_exact_spec_rejected(change):
    with pytest.raises(ValueError):
        validate_spec({**specs()[0], **change})


@pytest.mark.parametrize('roots', [[], ['a'*32, 'b'*32]])
def test_only_one_producer_publication(pins, roots):
    with pytest.raises(ValueError):
        envelope(pins, 'P', specs()[0], variant='P1', upstream={**upstream(), 'roots': roots})


def test_unrelated_projection_changes_pool_not_own_C_key(pins):
    selected = [{**upstream('P'), 'spec': case} for case in specs()]
    changed = copy.deepcopy(selected)
    changed[1]['digest'] = digest(b'different other case')
    assert material_key(pins, selected) != material_key(pins, changed)
    assert envelope(pins, 'C', specs()[0], variant='C1', upstream=selected[0]) == envelope(pins, 'C', specs()[0], variant='C1', upstream=changed[0])
    with pytest.raises(ValueError):
        material_key(pins, selected[::-1])


@pytest.mark.parametrize('positive,accepted,violations,ok', [
    (True, True, [], True), (True, False, [], False),
    (False, False, [{'invariant':'map_get_value','subject':'own','detail':'x'}], True),
    (False, True, [], False),
    (False, False, [{'invariant':'map_get_value','subject':'other','detail':'x'}], False),
    (False, False, [{'invariant':'map_get_value','subject':'own','detail':'x'},
                    {'invariant':'unexpected','subject':'own','detail':'x'}], False)])
def test_negative_requires_only_exact_owning_counterexample(positive, accepted, violations, ok):
    case = {'expectations': {'outcome': 'accept' if positive else 'reject'}, 'bad_operation': 'own'}
    verdict = {'accepted': accepted, 'violations': violations}
    if ok:
        assert assert_agreement(case, verdict)
    else:
        with pytest.raises(AssertionError):
            assert_agreement(case, verdict)


def test_extractor_defaultdict_boundary_keeps_strict_capsule_validation():
    from collections import defaultdict
    from schema import SCHEMA
    from per_exercise.project import canonical_rows
    raw = defaultdict(list, {name: [] for name in SCHEMA})
    converted = canonical_rows(raw)
    assert type(converted) is dict and converted == dict(raw)
    with pytest.raises(ValueError):
        capsules.ordered(raw)
    raw['unexpected-table'] = []
    with pytest.raises(ValueError):
        canonical_rows(raw)


@pytest.mark.parametrize('forged', [False, True])
def test_reported_selected_outcome_guard(forged):
    from per_exercise.batch import check_result
    attempt = {'outcome': 'CONTROL-real-outcome'}
    result = {'name': 'CONTROL-artifact', 'digest': digest(b'CONTROLdata'), 'key': digest(b'CONTROLkey'),
              'stage': 'E', 'outcome': 'CONTROL-forged-outcome' if forged else attempt['outcome']}
    reference = {'name': result['name'], 'sha256': result['digest']}
    if forged:
        with pytest.raises(ValueError, match='outcome'):
            check_result(attempt, {'key': result['key']}, reference, {'stage': 'E'}, result)
    else:
        check_result(attempt, {'key': result['key']}, reference, {'stage': 'E'}, result)


def fixture_dml(pins):
    """Tests may share originals' canonical module ONLY after exact package/core byte checks."""
    package = Path(pins['root']) / 'base/controller/daggerml'
    if 'daggerml' not in sys.modules:
        return load_dml(package)
    module = sys.modules['daggerml']
    actual = Path(module.__file__).resolve().parent
    names = sorted(path.name for path in package.glob('*.py'))
    if (sorted(path.name for path in actual.glob('*.py')) != names
            or any((actual / name).read_bytes() != (package / name).read_bytes() for name in names)
            or digest(Path(module._core.__file__).read_bytes()) != pins['core_sha256']):
        raise ValueError('test canonical module package/core bytes differ from pinned recorder')
    return module


@pytest.mark.parametrize('damage', ['python', 'core'])
def test_fixture_module_bridge_rejects_different_bytes(pins, tmp_path, monkeypatch, damage):
    from types import SimpleNamespace
    package = Path(pins['root']) / 'base/controller/daggerml'
    local = tmp_path / 'CONTROL-package'
    local.mkdir()
    for path in package.glob('*.py'):
        (local / path.name).write_bytes(path.read_bytes())
    core = package / '_core.abi3.so'
    if damage == 'python':
        path = local / '__init__.py'
        path.write_bytes(path.read_bytes() + b'\n# Deliberate CONTROL mismatch\n')
    else:
        core = local / 'CONTROLbadcore'
        core.write_bytes(b'deliberate control, never loaded')
    module = SimpleNamespace(__file__=str(local / '__init__.py'), _core=SimpleNamespace(__file__=str(core)))
    monkeypatch.setitem(sys.modules, 'daggerml', module)
    with pytest.raises(ValueError, match='bytes differ'):
        fixture_dml(pins)


@pytest.fixture(scope='module')
def metadata(pins, tmp_path_factory):
    dml = fixture_dml(pins)
    path = tmp_path_factory.mktemp('CONTROL-metadata') / 'repository'
    with dml.Repository(path, create=True):
        pass
    return dml, path


@pytest.mark.parametrize('mutation', ['valid', 'I64-for-BOOL', 'STRING-for-BYTES', 'literal-for-SubDAG'])
def test_native_batch_field_kind_guard(metadata, mutation):
    from per_exercise.batch import read_fields
    dml, path = metadata
    with dml.Repository(path) as repo, repo.write() as tx:
        literal = lambda value: tx.put_literal(tx.put_datum(value))
        child = tx.put_dag(root=literal('CONTROL-child'), bindings={})
        nodes = {'role': literal('CONTROL-native-kinds'), 'fresh': literal(1 if mutation == 'I64-for-BOOL' else True),
                 'foreign': literal('wrong' if mutation == 'STRING-for-BYTES' else bytes(16)),
                 'producer': literal(bytes(16)) if mutation == 'literal-for-SubDAG' else tx.put_subdag(child)}
        dag = tx.put_dag(root=nodes['role'], bindings=nodes)
        kinds = {'fresh': 'bool', 'foreign': 'bytes', 'producer': 'subdag'}
        if mutation == 'valid':
            fields = read_fields(tx, dml, dag, 'CONTROL-native-kinds', kinds)
            assert fields == {'fresh': True, 'foreign': bytes(16), 'producer': child}
            assert type(fields['fresh']) is bool
        else:
            with pytest.raises(ValueError, match='kind differs'):
                read_fields(tx, dml, dag, 'CONTROL-native-kinds', kinds)


@pytest.fixture(scope='module')
def control(pins, tmp_path_factory):
    root = tmp_path_factory.mktemp('CONTROL-per-exercise')
    sys.path.insert(0, str(Path(pins['root']) / 'common'))
    dml = fixture_dml(pins)
    from per_exercise.evidence import produce
    from per_exercise.project import project
    evidence, decoder = root / 'evidence', root / 'decoder'
    for path in (evidence, decoder):
        with dml.Repository(path, create=True):
            pass
    cases = []
    for number, spec in enumerate(specs(), 1):
        source, projected = root / f'E-{number}', root / f'P-{number}'
        source.mkdir(); projected.mkdir()
        e = produce(dml, evidence, spec, f'CONTROL/focus/case-{number}', source)
        c = project(dml, source, decoder, projected, spec)
        cases.append(c)
        assert e['calls'] == 6
    rows = capsules.merge(cases)
    identity, inputs = digest(b'CONTROLpool'), {'profile': 'CONTROL'}
    pool = root / 'pool'
    fingerprint = capsules.materialize(cases, pool, identity, inputs, DUCKDB)
    return {'root': root, 'dml': dml, 'cases': cases, 'rows': rows, 'pool': pool,
            'identity': identity, 'inputs': inputs, 'digest': fingerprint}


def test_case_fixtures_not_contaminated_by_other_values(control):
    cases = control['cases']
    assert cases[0]['case']['roots'][0] == cases[1]['case']['roots'][0]
    assert cases[0]['case']['roots'][0] != cases[2]['case']['roots'][0]
    for case in cases:
        assert capsules.validate(case) is case
        assert len(case['case']['membership']) <= 10000
    assert control['rows']['roots'] == []
    assert len(control['rows']['objects']) < sum(len(c['rows']['objects']) for c in cases)


@pytest.mark.parametrize('damage', ['membership', 'roots', 'run', 'parameters', 'drop-object', 'order'])
def test_capsule_forgery_rejected(control, damage):
    cap = copy.deepcopy(control['cases'][0])
    if damage == 'membership':
        cap['case']['membership'] = []
    elif damage == 'roots':
        cap['rows']['roots'][0]['commit_id'] = 'f'*32
    elif damage == 'run':
        cap['producer_run'] = 'f'*32
    elif damage == 'parameters':
        cap['case']['parameters']['value'] = 44
    elif damage == 'drop-object':
        cap['rows']['objects'] = []
    else:
        cap['rows']['objects'].reverse()
    with pytest.raises((ValueError, KeyError)):
        capsules.validate(cap)


@pytest.mark.parametrize('table', ['nodes', 'datums', 'fields'])
def test_merge_conflicting_shared_rows_fails_pure_owner(control, monkeypatch, table):
    # Pure union guard only; bypassed admission explicitly NOT independent native validation.
    caps = [copy.deepcopy(control['cases'][0]) for _ in range(3)]
    monkeypatch.setattr(capsules, 'validate', lambda value: value)
    row = caps[1]['rows'][table][0]
    column = 'kind' if table in ('nodes', 'datums') else 'node'
    row[column] = 'conflicting'
    with pytest.raises(ValueError, match='conflicting shared'):
        capsules.merge(caps)


def test_generated_all_base_views_and_semantics_are_confined(control):
    from shared_index.check import case_sql, check_case
    from schema import SCHEMA
    case = control['cases'][0]['case']
    sql = case_sql(case)
    for table in SCHEMA:
        assert ('CREATE TEMP TABLE roots' if table == 'roots' else f'CREATE TEMP VIEW {table} AS') in sql
    for name in ('field_data', 'profiles', 'argument_rows', 'expected_argument_rows', 'operations', 'trace_positions', 'violations'):
        assert f'CREATE OR REPLACE TEMP VIEW {name}' in sql
    result = check_case(control['pool'] / 'pool.duckdb', control['cases'][0]['rows'], case,
                        output_directory=control['root'] / 'positive-query')
    assert assert_agreement(case, result)


def test_negative_exact_semantic_violation_in_shared_pool(control):
    from shared_index.check import check_case
    case = control['cases'][1]['case']
    result = check_case(control['pool'] / 'pool.duckdb', control['cases'][1]['rows'], case,
                        output_directory=control['root'] / 'negative-query')
    assert assert_agreement(case, result)
    assert not result['accepted']


def test_owning_rule_disabled_is_not_cached_success(control, monkeypatch):
    import shared_index.check as checker
    original = checker.CHECKS.read_text()
    start = "UNION ALL\nSELECT 'map_get_value', o.dag"
    end = "UNION ALL\nSELECT 'empty_dataset', 'dataset'"
    before, following = original.split(start, 1)
    _, after = following.split(end, 1)
    weak = control['root'] / 'CONTROL-disabled.sql'
    weak.write_text(before + end + after)
    monkeypatch.setattr(checker, 'CHECKS', weak)
    cap = control['cases'][1]
    result = checker.check_case(control['pool'] / 'pool.duckdb', cap['rows'], cap['case'],
                               output_directory=control['root'] / 'disabled-query')
    assert result['accepted']
    with pytest.raises(AssertionError):
        assert_agreement(cap['case'], result)


def test_unrelated_pool_rows_cannot_supply_missing_case_object(control):
    cap = copy.deepcopy(control['cases'][0])
    cap['rows']['objects'] = []
    from shared_index.check import check_case
    with pytest.raises(ValueError):
        check_case(control['pool'] / 'pool.duckdb', cap['rows'], cap['case'],
                   output_directory=control['root'] / 'SHOULD-NOT-EXIST')
    assert not (control['root'] / 'SHOULD-NOT-EXIST').exists()


def test_pool_manifest_and_data_tamper_fail_without_rebuild(control):
    capsules.admit(control['pool'], control['identity'], control['inputs'], control['digest'])
    path = control['pool'] / 'objects.jsonl'
    before = path.read_bytes()
    try:
        path.write_bytes(before + b'\n')
        with pytest.raises(ValueError):
            capsules.admit(control['pool'], control['identity'], control['inputs'], control['digest'])
    finally:
        path.write_bytes(before)
    capsules.admit(control['pool'], control['identity'], control['inputs'], control['digest'])
