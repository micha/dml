"""Measured finite application story, full public typed bytes and existing CLI."""

import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, local
import pytest

from test_exchange import (
    ROOT,
    job,
    exchange_runtime,
    typed_oracle,
    bundle_oracle,
    tree,
    literal,
    prepare,
)

EXAMPLE = ROOT / "examples/asynchronous_execution.py"
SLOW = ROOT / "examples/local_slow_add.py"


def test_maintained_async_story_host_client_helpers_full_bytes_cli(
    tmp_path, exchange_runtime, monkeypatch
):
    functions = runpy.run_path(str(EXAMPLE))
    globals = functions["main"].__globals__

    def host_client(args):
        # Host helper coverage is explicitly separate from real fresh-process tests.
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            functions["main"](args)
        return json.loads(output.getvalue())

    monkeypatch.setitem(globals, "client", host_client)
    story = tmp_path / "story"
    functions["main"]([str(story)])
    manifest = functions["inspect"](story)
    functions["main"](["--inspect", str(story)])
    with pytest.raises(SystemExit):
        functions["main"]([])
    native = Path(os.environ.get("DML_BIN", ROOT / "build/check/dml"))
    for index, run in enumerate(manifest["runs"], 1):
        for got in run:
            root = d.ObjectId.from_hex(got["commit"])
            expected = typed_oracle(
                story / ("workspace-" + str(index)) / "worker.offline", (root,)
            )
            packet = story / ("packet-" + str(index) + "-" + got["phase"])
            assert bundle_oracle(packet / "snapshot.bundle") == expected
            assert typed_oracle(story / "caller.dml", (root,)) == expected
            result = subprocess.run(
                [
                    str(native),
                    "--json",
                    "--repo",
                    str(story / "caller.dml"),
                    "log",
                    "--commit",
                    str(root),
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            commits = json.loads(result.stdout)
            assert not commits["truncated"] and commits["commits"][0]["id"] == str(root)
    # Cover maintained script main guard from the already complete inspect path.
    monkeypatch.setattr(sys, "argv", [str(EXAMPLE), "--inspect", str(story)])
    runpy.run_path(str(EXAMPLE), run_name="__main__")


def test_example_actual_short_lived_client(job):
    functions = runpy.run_path(str(EXAMPLE))
    saved = job[1].parent / "saved"
    ex.save_exchange_handle(saved, ex.ExchangeHandle(job[1], job[2]))
    assert (
        functions["client"](["--observe", str(saved), str(job[1].parent / "packet")])[
            "phase"
        ]
        == "bootstrap"
    )


def test_example_client_failure_and_finite_poll_errors(monkeypatch):
    functions = runpy.run_path(str(EXAMPLE))
    globals = functions["poll"].__globals__
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 2, "")
    )
    with pytest.raises(RuntimeError):
        functions["client"](["--inspect", "absent"])
    monkeypatch.setitem(globals, "client", lambda args: {"phase": "completion"})
    with pytest.raises(RuntimeError):
        functions["poll"]("saved", Path("/unused"), "initial")
    # Deterministic host-only clock substitution exercises finite timeout handler.
    clocks = iter((0, 1, 16))
    monkeypatch.setattr(globals["time"], "monotonic", lambda: next(clocks))
    monkeypatch.setattr(globals["time"], "sleep", lambda _: None)
    monkeypatch.setitem(globals, "client", lambda args: {"phase": "bootstrap"})
    with pytest.raises(TimeoutError):
        functions["poll"]("saved", Path("/unused"), "initial")


@pytest.mark.parametrize("bad", (False, True), ids=("i64", "wrong-type"))
def test_slow_child_host_main_uses_real_public_context_and_publication(
    job, monkeypatch, bad
):
    path, workspace, spec, state = job
    gates = workspace.parent / "gates"
    gates.mkdir()
    for phase in ("initial", "publication"):
        (gates / (phase + "-release")).touch()
    with d.Repository(path) as repo, repo.write() as tx:
        values = {
            "left": literal(tx, "wrong" if bad else 4),
            "right": literal(tx, 7),
            "gate": literal(tx, str(gates)),
        }
        inputs = tx.put_dag(root=values["left"], bindings=values)
        selected = tree(tx, spec.commit)
        selected["inputs"] = inputs
        commit = tx.put_commit(tx.put_tree(selected), parents=(spec.commit,))
    workspace = workspace.parent / "direct"
    spec = prepare(path, workspace, commit)
    functions = runpy.run_path(str(SLOW))
    globals = functions["main"].__globals__
    monkeypatch.setattr(globals["time"], "sleep", lambda _: None)

    def direct(context, *args):
        monkeypatch.setitem(globals, "child_context", lambda: context)
        if bad:
            with pytest.raises(ValueError):
                functions["main"]()
            return local._Observation(1, "child-exit", "test wrong type", None, None)
        # Main guard also measured; replace the public function at imported seam.
        monkeypatch.setattr(local, "child_context", lambda: context)
        runpy.run_path(str(SLOW), run_name="__main__")
        return local._Observation(0, None, "", None, None)

    monkeypatch.setattr(local, "_execute", direct)
    result = ex.execute_exchange(workspace)
    assert result.outcome == ("failure" if bad else "success")


def test_slow_example_gate_finite_timeout_and_wait(tmp_path, monkeypatch):
    functions = runpy.run_path(str(SLOW))
    clocks = iter((0, 1, 16))
    events = []
    monkeypatch.setattr(
        functions["gate"].__globals__["time"], "monotonic", lambda: next(clocks)
    )
    monkeypatch.setattr(
        functions["gate"].__globals__["time"],
        "sleep",
        lambda delay: events.append(delay),
    )
    with pytest.raises(TimeoutError):
        functions["gate"](tmp_path, "initial")
    assert events == [0.02]
