"""Maintained runnable story, independent bytes, CLI and direct helper coverage."""

import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex
import pytest

from test_exchange import ROOT, job, exchange_runtime, typed_oracle, bundle_oracle

EXAMPLE = ROOT / "examples/repository_execution.py"


def test_maintained_story_host_helpers_and_cli(tmp_path, exchange_runtime, monkeypatch):
    story = tmp_path / "story"
    monkeypatch.setattr(sys, "argv", [str(EXAMPLE), str(story)])
    functions = runpy.run_path(str(EXAMPLE), run_name="__main__")
    manifest = functions["inspect"](story)
    functions["main"](["--inspect", str(story)])
    functions["main"](
        [
            "--receive",
            str(story / "caller.dml"),
            str(story / "packet-1"),
            str(story / "expected-1.json"),
            "trial-1",
        ]
    )
    with pytest.raises(SystemExit):
        functions["main"]([])
    native = Path(os.environ.get("DML_BIN", ROOT / "build/check/dml"))
    for index, run in enumerate(manifest["runs"], 1):
        expected = typed_oracle(
            story / ("workspace-" + str(index)) / "worker.offline",
            (d.ObjectId.from_hex(run["final"]),),
        )
        assert (
            typed_oracle(story / "caller.dml", (d.ObjectId.from_hex(run["final"]),))
            == expected
        )
        assert (
            bundle_oracle(story / ("packet-" + str(index)) / "output.bundle")
            == expected
        )
        commands = (
            ("ref", "get", run["ref"]),
            ("snapshot", "--ref", run["ref"]),
            ("snapshot", "--commit", run["pre"]),
            ("walk", run["final_attempt"], "--limit", "100"),
            ("log", "--ref", run["ref"]),
        )
        if run["result"] is not None:
            commands += (("show", "dag", run["result"]),)
        for args in commands:
            process = subprocess.run(
                [str(native), "--json", "--repo", str(story / "caller.dml"), *args],
                capture_output=True,
                text=True,
                timeout=20,
                check=True,
            )
            result = json.loads(process.stdout)
            if args[0] == "ref":
                assert result["target"] == run["final"]
            if args[0] == "log":
                commits = {c["id"]: c for c in result["commits"]}
                with d.Repository(story / "caller.dml") as repo, repo.read() as tx:
                    for oid in commits:
                        assert commits[oid]["parents"] == [
                            str(p)
                            for p in tx.get_commit(d.ObjectId.from_hex(oid)).parents
                        ]
                assert not result["truncated"]
    with d.Repository(story / "caller.dml") as repo, repo.write() as tx:
        tx.create_ref("work", d.ObjectId.from_hex(manifest["runs"][0]["final"]))
    with pytest.raises(AssertionError, match="worker refs"):
        functions["inspect"](story)


def test_example_worker_direct_branch(job):
    path, workspace, spec, state = job
    functions = runpy.run_path(str(EXAMPLE))
    functions["main"](["--worker", str(workspace)])
    assert (
        ex.receive_exchange(
            path, workspace=workspace, expected=spec, ref="trial"
        ).outcome
        == "success"
    )


@pytest.mark.parametrize("mode", ("nonzero", "terminate", "kill"))
def test_example_finite_direct_supervision_only(monkeypatch, mode):
    functions = runpy.run_path(str(EXAMPLE))
    events = []

    class Process:
        def wait(self, timeout):
            events.append(("wait", timeout))
            if mode == "nonzero":
                return 2
            if timeout == 30 or (mode == "kill" and len(events) == 3):
                raise subprocess.TimeoutExpired("worker", timeout)
            return -9

        def poll(self):
            return 2 if mode == "nonzero" else None

        def terminate(self):
            events.append(("terminate",))

        def kill(self):
            events.append(("kill",))

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: Process())
    with pytest.raises((RuntimeError, subprocess.TimeoutExpired)):
        functions["supervise"](["--worker", "owned"])
    assert events == (
        [("wait", 30)]
        if mode == "nonzero"
        else (
            [("wait", 30), ("terminate",), ("wait", 5)]
            if mode == "terminate"
            else [("wait", 30), ("terminate",), ("wait", 5), ("kill",), ("wait", 5)]
        )
    )
