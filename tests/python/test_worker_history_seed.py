"""Stash belongs to one worker config; sharing survives imported FixtureDefs."""

from types import SimpleNamespace

import pytest

from worker_history_seed import worker_seed


def config():
    return SimpleNamespace(stash=pytest.Stash())


def test_same_builder_reuses_success_but_not_across_configs():
    calls = []

    @worker_seed
    def seed(pytestconfig):
        calls.append(pytestconfig)
        return object()

    first, second = config(), config()
    got = seed(pytestconfig=first)
    assert seed(pytestconfig=first) is got
    assert seed(pytestconfig=second) is not got
    assert calls == [first, second]


def test_failure_not_published_and_builder_keys_distinct():
    calls = []

    @worker_seed
    def seed(pytestconfig):
        calls.append(1)
        if len(calls) == 1:
            raise ValueError("incomplete seed")
        return object()

    owner = config()
    with pytest.raises(ValueError, match="incomplete seed"):
        seed(pytestconfig=owner)
    got = seed(pytestconfig=owner)
    assert seed(pytestconfig=owner) is got and calls == [1, 1]
    other = worker_seed(lambda pytestconfig: object())
    assert other(pytestconfig=owner) is not got
