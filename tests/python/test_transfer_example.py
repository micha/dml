"""Two real attempts, source-offline import and ordinary CLI/history inspection."""

import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

import daggerml as dml
from daggerml import transfer as tr
import pytest

from test_transfer_process import transfer_runtime

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/pinned_transfer.py"


def load():
    return runpy.run_path(str(EXAMPLE))


def test_example_driver_and_host_helpers(tmp_path, transfer_runtime, monkeypatch):
    story = tmp_path / "story"
    monkeypatch.setattr(sys, "argv", [str(EXAMPLE), str(story)])
    runpy.run_path(str(EXAMPLE), run_name="__main__")
    functions = load()
    # Host-side helpers measured separately from real uninstrumented fresh children.
    functions["main"](["--receive", str(story)])
    functions["main"](["--inspect", str(story)])
    with pytest.raises(SystemExit):
        functions["main"]([])
    manifest = functions["inspect"](story)
    # Recreate test-owned historical scratch as a sentinel: transfer has no deletion authority.
    historical = []
    with dml.Repository(story / "source.dml") as repo, repo.read() as tx:
        for run in manifest["runs"]:
            attempt = dml.ObjectId.from_hex(run["attempt"])
            scratch = Path(functions["scalar"](tx, attempt, "scratch"))
            assert scratch.parent == story
            scratch.mkdir()
            sentinel = scratch / "retained"
            sentinel.write_bytes(b"historical path is data")
            historical.append(sentinel)
    bundle = (story / "bundle.json").read_bytes()
    (story / "source.dml").rename(story / "source.offline")

    def no_execution(*args, **kwargs):
        pytest.fail("transfer/inspection must not execute source")

    with monkeypatch.context() as guard:
        guard.setattr(subprocess, "Popen", no_execution)
        assert functions["receive"](story).commit == dml.ObjectId.from_hex(manifest["root"])
        assert functions["inspect"](story) == manifest
        assert all(path.read_bytes() == b"historical path is data" for path in historical)
    native = Path(os.environ.get("DML_BIN", ROOT / "build/check/dml"))
    first = manifest["runs"][0]
    commands = [
        ("ref", "get", "received"),
        ("snapshot", "--ref", "received"),
        ("snapshot", "--commit", first["pre"]),
        ("walk", first["final_attempt"], "--limit", "100"),
        ("show", "dag", first["result"]),
        ("log", "--ref", "received"),
    ]
    for args in commands:
        output = subprocess.run(
            [str(native), "--json", "--repo", str(story / "destination.dml"), *args],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        result = json.loads(output.stdout)
        if args[0] == "log":
            commits = {c["id"]: c for c in result["commits"]}
            for run in manifest["runs"]:
                assert commits[run["final"]]["parents"] == [run["pre"], run["publication"]]
            assert result["truncated"] is False
    assert (
        tr.export_commit(story / "destination.dml", commit=dml.ObjectId.from_hex(manifest["root"]))
        == bundle
    )


@pytest.mark.parametrize("violation", ["publication", "request", "unrelated", "main"], ids=str)
def test_example_inspection_rejects_inferred_state(tmp_path, transfer_runtime, violation):
    functions = load()
    story = functions["produce"](tmp_path / "story")
    functions["receive"](story)
    manifest = json.loads((story / "manifest.json").read_text(encoding="utf-8"))
    with dml.Repository(story / "destination.dml") as repo, repo.write() as tx:
        root = dml.ObjectId.from_hex(manifest["root"])
        if violation == "unrelated":
            assert str(tx.put_datum("unrelated source branch sentinel")) == manifest["unrelated"]
        else:
            ref = {
                "publication": manifest["runs"][0]["publication_ref"],
                "request": "request-" + manifest["runs"][0]["request_id"],
                "main": "main",
            }[violation]
            tx.create_ref(ref, root)
    with pytest.raises(AssertionError, match="copied|inferred"):
        functions["inspect"](story)
