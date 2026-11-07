"""Frozen setup amortization must not share mutable stores or native locks."""

import hashlib

import daggerml as d
from daggerml import transfer

from test_recorded_maps import map_state_seed, map_success_seed, reuse, app as maps, story


def restore(path, seed):
    bundle, refs, fields = seed
    with d.Repository(path, create=True):
        pass
    transfer.import_commit(path, bundle)
    with d.Repository(path) as repo, repo.write() as tx:
        for name, commit in refs:
            tx.create_ref(name, commit)
    return fields


def test_metadata_seed_pinned_native_identity_refs_and_isolation(tmp_path, map_state_seed):
    bundle, refs, fields = map_state_seed
    original = hashlib.sha256(bundle).hexdigest()
    a, b = tmp_path / "a", tmp_path / "b"
    assert restore(a, map_state_seed) == restore(b, map_state_seed) == fields
    root = fields[-1].commit
    assert transfer.export_commit(a, commit=root) == bundle
    assert transfer.export_commit(b, commit=root) == bundle
    with d.Repository(a) as repo, repo.write() as tx:
        tx.update_ref("main", root)
    with d.Repository(b) as repo, repo.read() as tx:
        for name, commit in refs:
            assert tx.get_ref(name) == commit
    assert hashlib.sha256(bundle).hexdigest() == original


def test_real_success_seed_exact_public_authority_then_branch_local_ref_change(tmp_path, map_success_seed):
    bundle, refs, fields = map_success_seed
    original = hashlib.sha256(bundle).hexdigest()
    a, b = tmp_path / "a", tmp_path / "b"
    q, selected, indexed, child = restore(a, map_success_seed)
    assert restore(b, map_success_seed) == fields
    assert child["exit"] == 0 and child["reaped"] and child["pid"] > 0
    for path in (a, b):
        got = reuse.inspect_table(path, commit=indexed.commit, table_name="double-table")
        assert len(got.entries) == 1 and got.intent_uri == story.DOUBLE
        output = maps.inspect_returned(path, commit=selected.commit, slot=selected.slot)
        assert output.request == q.recorded.request
        assert maps.Inspector(path, selected.commit).selected(selected.slot).attempt == selected.attempt
        assert transfer.export_commit(path, commit=indexed.commit) == bundle
    # Explicit fixture metadata mutation is confined to the first fresh store.
    with d.Repository(a) as repo, repo.write() as tx:
        tx.update_ref("indexed", q.recorded.commit)
        tx.create_ref("only-a", indexed.commit)
    with d.Repository(b) as repo, repo.read() as tx:
        for name, commit in refs:
            assert tx.get_ref(name) == commit
    assert hashlib.sha256(bundle).hexdigest() == original
