"""Supplemental fresh installed receive/CLI after known endpoint/job disposition.

No computation/fixture resume. Copies immutable packets, advances only fixture main,
uses independent saved expectations and compares complete native bytes/parents.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import daggerml as d
from daggerml import exchange as ex, floci as f
from fixture import Fixture
import integration as normal

RECEIVE = """import json,sys
from daggerml import exchange as ex,floci as f
job=f.load_floci_job(sys.argv[2])
got=ex.receive_observation(sys.argv[1],packet=sys.argv[3],expected=job.expected,ref=sys.argv[4])
assert ex.receive_observation(sys.argv[1],packet=sys.argv[3],expected=job.expected,ref=sys.argv[4])==got
print(json.dumps(dict(commit=str(got.commit),request=str(got.request),attempt=got.attempt_id,phase=got.phase)))
"""


def run(root, story):
    fixture = Fixture(root)
    assert fixture.state["stopped"]
    assert not fixture.inspect(fixture.state["service_id"])["State"]["Running"]
    fixture.clients_stopped()
    assert not fixture.children()
    story = Path(story).resolve()
    report = json.loads((story / "summary.json").read_bytes())
    supplemental = story / "offline-fresh"
    supplemental.mkdir()
    caller = story / "A.dml"
    refs = {
        "main",
        "sentinel",
        "never-started",
        "latest",
        "double-basis",
        "experiment-result",
    }
    roots = []
    for row in report["trials"]:
        refs.add("submission-" + row["label"])
        job = f.load_floci_job(row["saved"])
        assert (story / (row["label"] + "-input.offline")).exists()
        assert not (story / (row["label"] + "-input")).exists()
        for packet in row["packets"]:
            got = ex.read_observation(packet["packet"], expected=job.expected)
            refs.update(
                (row["label"] + "-" + packet["phase"], "request-" + got.request_id)
            )
            roots.append(got.commit)
    with d.Repository(caller) as repo, repo.read() as tx:
        fixed = {name: tx.get_ref(name) for name in refs}
        for name in tx.get_tree(tx.get_commit(fixed["never-started"]).tree):
            if name.startswith("request-"):
                fixed[name] = tx.get_ref(name)
        roots.extend(fixed.values())
    old = {}
    for root in roots:
        old.update(normal.typed(caller, root))
    with d.Repository(caller) as repo, repo.write() as tx:
        node = tx.put_literal(tx.put_datum("independent fixture main advancement"))
        advanced = tx.put_commit(
            tx.put_tree({"later": tx.put_dag(root=node)}), parents=(fixed["main"],)
        )
        tx.update_ref("main", advanced)
    fixed["main"] = advanced
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    commands = []
    for row in report["trials"]:
        saved = supplemental / (row["label"] + "-saved")
        shutil.copytree(row["saved"], saved)
        job = f.load_floci_job(saved)
        for phase in row["packets"]:
            packet = supplemental / (row["label"] + "-" + phase["phase"])
            shutil.copytree(phase["packet"], packet)
            command = [
                sys.executable,
                "-B",
                "-c",
                RECEIVE,
                str(caller),
                str(saved),
                str(packet),
                row["label"] + "-" + phase["phase"],
            ]
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                env=environment,
                timeout=30,
            )
            commands.append(
                dict(
                    command=command,
                    exit=result.returncode,
                    stdout=result.stdout.decode(),
                    stderr=result.stderr.decode(),
                )
            )
            assert result.returncode == 0, "fresh offline client failure retained"
            received = json.loads(result.stdout)
            assert received["commit"] == phase["commit"]
            got = ex.read_observation(packet, expected=job.expected)
            assert normal.typed(caller, got.commit) == normal.typed(
                Path(phase["validation"]), got.commit
            )
    private_b = story / "double-actual-final-B"
    consumer = d.ObjectId.from_hex(report["trials"][-1]["packets"][-1]["commit"])
    assert normal.typed(caller, consumer) == normal.typed(private_b, consumer)
    with d.Repository(caller) as repo, repo.read() as tx:
        assert all(tx.get_ref(name) == target for name, target in fixed.items())
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
        summary_commit = tx.get_ref("experiment-result")
        summary = tx.get_tree(tx.get_commit(summary_commit).tree)["experiment"]
    cli = Path(d.__file__).resolve().parent / "_bin/dml"
    for arguments in (
        ["snapshot", "--ref", "experiment-result"],
        ["walk", str(summary), "--limit", "200"],
        ["log", "--ref", "experiment-result", "--limit", "100"],
    ):
        command = [str(cli), "--json", "--repo", str(caller), *arguments]
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            env=environment,
            timeout=30,
        )
        commands.append(
            dict(
                command=command,
                exit=result.returncode,
                stdout=result.stdout.decode(),
                stderr=result.stderr.decode(),
            )
        )
        assert result.returncode == 0
    (supplemental / "evidence.json").write_text(
        json.dumps(
            dict(
                fresh_installed_receivers=9,
                service_stopped=True,
                input_offline=True,
                main_advanced=str(advanced),
                old_objects=len(old),
                fixed_refs={k: str(v) for k, v in fixed.items()},
                commands=commands,
            ),
            indent=2,
        )
    )
    print(
        json.dumps(
            dict(
                fresh_installed_receivers=9,
                native_cli_readers=3,
                old_objects=len(old),
                endpoint_stopped=True,
            )
        )
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]))
