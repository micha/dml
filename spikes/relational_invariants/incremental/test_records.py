import pytest

from incremental.identity import canonical, digest, key
from incremental.records import read_record, write_record
from incremental.test_artifacts import artifact
from incremental.test_identity import fixture_envelope


def terminal_fixture(store, *, branch='main', status='success', env=None):
    env = fixture_envelope() if env is None else env
    request, _ = store.request(env, 'fresh', branch=branch)
    initial, occurrence, _ = store.begin(request, branch=branch)
    name = 'control-' + occurrence.rsplit('-', 1)[-1]
    fingerprint, _ = artifact(store.artifact_root, name, producer=occurrence,
                              dependencies=env['dependencies'], stage=env['stage'], key=key(env), status=status)
    terminal, commit = store.finish(initial, name, fingerprint, branch=branch)
    return request, initial, terminal, commit, env


def test_real_storage_explicit_reuse_fresh_no_adoption_and_two_branches(control):
    request1, initial1, terminal1, _, env = terminal_fixture(control)
    assert control.selected(env) is None
    _, selected_basis = control.adopt(terminal1)
    assert control.selected(env) == terminal1
    request2, _ = control.request(env, 'reuse')
    reused, satisfaction, _ = control.reuse(request2)
    assert reused == terminal1 and request2 != request1
    with control.dml.Repository(control.path) as repo, repo.read() as tx:
        w = read_record(tx, control.dml, satisfaction, 'satisfaction')
        assert w['request'] == request2 and w['attempt'] == terminal1
        old = read_record(tx, control.dml, terminal1, 'attempt')
        assert old['request'] == request1
        assert read_record(tx, control.dml, initial1, 'attempt')['outcome'] is None
    request3, _, terminal3, _, _ = terminal_fixture(control)
    assert control.selected(env) == terminal1  # Finishing fresh didn't adopt.
    fresh_request, _ = control.request(env, 'fresh')
    with pytest.raises(ValueError, match='fresh request cannot reuse'):
        control.reuse(fresh_request)
    basis = control.head()
    control.fork('sibling-new-choice', basis)
    control.adopt(terminal3, branch='sibling-new-choice', expected=basis)
    assert control.selected(env, branch='sibling-new-choice') == terminal3
    assert control.selected(env) == terminal1
    assert request3 != request1
    old_occurrence = control.terminal(terminal1)[0]['occurrence']
    new_occurrence = control.terminal(terminal3)[0]['occurrence']
    assert old_occurrence != new_occurrence and '/run-' in new_occurrence
    control.fork('old-snapshot', selected_basis)
    assert control.selected(env, branch='old-snapshot') == terminal1


@pytest.mark.parametrize('status', ['error', 'rejected'])
def test_failed_rejected_and_unknown_never_adopt(control, status):
    branch = 'non-success-' + status
    control.fork(branch, control.head())
    _, initial, terminal, _, env = terminal_fixture(control, branch=branch, status=status)
    with pytest.raises(ValueError):
        control.adopt(initial, branch=branch)
    with pytest.raises(ValueError):
        control.adopt(terminal, branch=branch)
    assert control.selected(env, branch=branch) is None or control.selected(env, branch=branch) != terminal


def test_stale_basis_and_duplicate_initial_completion_abort_branch_publication(control):
    basis = control.head()
    _, initial, terminal, _, env = terminal_fixture(control)
    current = control.head()
    with pytest.raises(ValueError):
        control.adopt(terminal, expected=basis)
    assert control.head() == current
    reference = control.terminal(terminal)[3]
    with pytest.raises(ValueError):
        control.finish(initial, reference['name'], reference['sha256'])
    assert control.head() == current
    with pytest.raises(ValueError):
        control.request(env, 'fresh', expected=basis)
    assert control.head() == current


@pytest.mark.parametrize('fault', ['outcome-link', 'stage-key', 'role', 'artifact'])
def test_found_invalid_selection_fails_closed_not_fresh_miss(control, fault):
    branch = 'invalid-' + fault
    control.fork(branch, control.head())
    _, _, terminal, _, env = terminal_fixture(control, branch=branch)
    selection, _ = control.adopt(terminal, branch=branch)
    producing_request = control.terminal(terminal)[0]['request']
    with control.dml.Repository(control.path) as repo, repo.write() as tx:
        basis = tx.get_ref(branch)
        entries = dict(tx.get_tree(tx.get_commit(basis).tree))
        fields = read_record(tx, control.dml, selection, 'selection')
        if fault == 'outcome-link':
            fields['outcome'] = terminal  # native-valid link, wrong semantic authority
        elif fault == 'stage-key':
            fields['key'] = digest(b'wrong selected key')
        if fault == 'role':
            bad = write_record(tx, 'satisfaction', {'request': producing_request,
                                                  'attempt': terminal, 'outcome': fields['outcome']})
        else:
            bad = write_record(tx, 'selection', fields)
        entries[control.slot(env['stage'], key(env))] = bad
        commit = tx.put_commit(tx.put_tree(entries), parents=(basis,))
        tx.update_ref(branch, commit)
    if fault == 'artifact':
        reference = control.terminal(terminal)[3]
        (control.artifact_root / reference['name'] / 'data.json').write_bytes(b'tampered CONTROL')
    with pytest.raises(ValueError):
        control.selected(env, branch=branch)


def test_wrong_producer_rejected_before_terminal_and_unrelated_slot_preserved(control):
    branch = 'producer-and-other-slot'
    control.fork(branch, control.head())
    _, _, old_terminal, _, env = terminal_fixture(control, branch=branch)
    control.adopt(old_terminal, branch=branch)
    other = fixture_envelope('P')
    _, _, other_terminal, _, _ = terminal_fixture(control, branch=branch, env=other)
    control.adopt(other_terminal, branch=branch)
    request, _ = control.request(env, 'fresh', branch=branch)
    initial, occurrence, _ = control.begin(request, branch=branch)
    name = 'wrong-producer-' + occurrence.rsplit('-', 1)[-1]
    fingerprint, _ = artifact(control.artifact_root, name, producer='CONTROL/equal-value-wrong-producer',
                              dependencies=env['dependencies'], key=key(env))
    before = control.head(branch)
    with pytest.raises(ValueError):
        control.finish(initial, name, fingerprint, branch=branch)
    assert control.head(branch) == before
    assert control.selected(other, branch=branch) == other_terminal
    assert control.selected(env, branch=branch) == old_terminal


def test_allocator_not_reset_by_branch_fork_and_reserved_interruption(control):
    basis = control.head()
    control.fork('allocator-fork', basis)
    first = control.reserve()
    second = control.reserve()  # unassociated reservation gap remains valid
    request, _ = control.request(fixture_envelope(), 'fresh', branch='allocator-fork')
    with control.dml.Repository(control.path) as repo, repo.read() as tx:
        third = read_record(tx, control.dml, request, 'request')['occurrence']
    assert len({first, second, third}) == 3
    reopened = type(control)(control.dml, control.path, control.artifact_root, control.namespace)
    assert reopened.run != control.run
    assert reopened.reserve() not in {first, second, third}
