"""Measured maintained caller-Q story, full typed population/bytes and ordinary CLI."""

import runpy

import daggerml as d
import pytest

from test_exchange import ROOT, job, exchange_runtime, tree
import test_asynchronous_example as existing

EXAMPLE = ROOT / "examples/caller_requests.py"


def test_caller_story_host_helpers_full_typed_bytes_cli(
    tmp_path, exchange_runtime, monkeypatch
):
    # Reuse independent all-parent byte/CLI assertions, not a second traversal.
    monkeypatch.setattr(existing, "EXAMPLE", EXAMPLE)
    existing.test_maintained_async_story_host_client_helpers_full_bytes_cli(
        tmp_path, exchange_runtime, monkeypatch
    )
    story = tmp_path / "story"
    functions = runpy.run_path(str(EXAMPLE))
    manifest = functions["inspect"](story)
    with d.Repository(story / "caller.dml") as repo, repo.write() as tx:
        q = manifest["unstarted"]
        cq = d.ObjectId.from_hex(q["commit"])
        assert set(tree(tx, cq)) - set(
            tree(tx, d.ObjectId.from_hex(manifest["base"]))
        ) == {"request-" + q["request_id"]}
        tx.create_ref("work", d.ObjectId.from_hex(manifest["runs"][0][-1]["commit"]))
    with pytest.raises(AssertionError, match="worker refs"):
        functions["inspect"](story)


def test_caller_example_fresh_client_and_finite_errors(job, monkeypatch):
    monkeypatch.setattr(existing, "EXAMPLE", EXAMPLE)
    existing.test_example_actual_short_lived_client(job)
    existing.test_example_client_failure_and_finite_poll_errors(monkeypatch)
