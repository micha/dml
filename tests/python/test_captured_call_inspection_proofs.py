"""Inspection-local proof reuse must preserve authority, custody and budgets."""

import pytest

from test_captured_calls import app


def test_success_reuses_complete_union_but_new_inspection_rechecks(tmp_path):
    calls = []

    @app._inspection_proof
    def child(path, *, commit, seen=None, depth=0):
        calls.append(commit)
        seen.update({1, 2})
        return {"semantic_ids": frozenset(seen)}

    @app._inspection_proof
    def parent(path, *, commit, seen=None, depth=0):
        first = child(path, commit=commit, seen=seen, depth=depth)
        assert first["semantic_ids"] == frozenset({1, 2})
        seen.add(3)
        second = child(path, commit=commit, seen=seen, depth=depth)
        assert second["semantic_ids"] == frozenset({1, 2, 3})
        # Cached proof must contribute IDs even to a different empty caller set.
        other = set()
        child(path, commit=commit, seen=other, depth=depth)
        assert other == {1, 2}
        return {"semantic_ids": frozenset(seen)}

    incoming = {4}
    assert parent(tmp_path, commit="first", seen=incoming)["semantic_ids"] == frozenset({1, 2, 3, 4})
    assert incoming == {1, 2, 3, 4}
    assert calls == ["first"]
    parent(tmp_path, commit="first")
    assert calls == ["first", "first"]
    assert app._inspection_proofs.get() is None


def test_repository_commit_and_depth_are_separate_proofs(tmp_path):
    calls = []

    @app._inspection_proof
    def child(path, *, commit, seen=None, depth=0):
        calls.append((path, commit, depth))
        app.authority_depth(depth + 1)
        return commit

    @app._inspection_proof
    def parent(path, *, commit, seen=None, depth=0):
        child(path, commit=commit)
        child(path, commit="other")
        child(path / "other", commit=commit)
        child(path, commit=commit, depth=1)
        with pytest.raises(ValueError, match="too deep"):
            child(path, commit=commit, depth=8)
        with pytest.raises(ValueError, match="too deep"):
            child(path, commit=commit, depth=9)

    parent(tmp_path, commit="first")
    assert len(calls) == 5
    assert app._inspection_proofs.get() is None


def test_cached_union_still_enforces_aggregate_budget(tmp_path):
    calls = []

    @app._inspection_proof
    def child(path, *, commit, seen=None, depth=0):
        calls.append(commit)
        seen.add(100)

    @app._inspection_proof
    def parent(path, *, commit, seen=None, depth=0):
        child(path, commit=commit)
        with pytest.raises(ValueError, match="exceeds64"):
            child(path, commit=commit, seen=set(range(64)))
        with pytest.raises(ValueError, match="exceeds64"):
            child(path, commit=commit, seen=set(range(65)))

    parent(tmp_path, commit="first")
    assert calls == ["first"]
    assert app._inspection_proofs.get() is None


def test_failure_is_not_cached_and_reached_ids_and_cleanup_survive(tmp_path):
    calls = []

    @app._inspection_proof
    def child(path, *, commit, seen=None, depth=0):
        calls.append(commit)
        seen.add(1)
        raise ValueError("invalid history")

    @app._inspection_proof
    def parent(path, *, commit, seen=None, depth=0):
        for _ in range(2):
            reached = set()
            with pytest.raises(ValueError, match="invalid history"):
                child(path, commit=commit, seen=reached)
            assert reached == {1}
        raise ValueError("parent failure")

    with pytest.raises(ValueError, match="parent failure"):
        parent(tmp_path, commit="first")
    assert calls == ["first", "first"]
    assert app._inspection_proofs.get() is None
