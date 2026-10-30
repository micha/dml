"""Explicit three-job installed gate: original add/double, OFFLINE reuse, fresh double.

No default startup, private runtime hook or fourth reuse job. Existing finite
controllers own submit/reap/profile; normal ephemeral final B is not archived F.
"""

from dataclasses import asdict
import hashlib
import importlib.util
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
import composed_integration as composed
from retained_integration import prove_profile

ROOT = Path(__file__).resolve().parents[2]


def load_application(source):
    spec = importlib.util.spec_from_file_location("installed_reuse_app", source)
    app = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = app
    spec.loader.exec_module(app)
    return app


def service_census(archive, expected):
    """Independent persisted service job inventory, NOT controller mock/count."""
    raw = (Path(archive) / "batch-jobs.json").read_bytes()
    rows = json.loads(raw)
    assert {row["jobId"] for row in rows.values()} == set(expected)
    assert len(rows) == len(expected)
    for row in rows.values():
        assert row["status"] in ("SUCCEEDED", "FAILED")
        assert row["retryStrategy"]["attempts"] == 1 and len(row["attempts"]) == 1
    return raw


class CommandEvidence(list):
    """Persist each client result immediately, including failure/unknown disposition."""

    def __init__(self, path):
        super().__init__()
        self.path = Path(path)

    def append(self, row):
        super().append(row)
        self.path.write_text(json.dumps(self, indent=2))


OFFLINE_REUSE = """import runpy,sys
sys.argv=sys.argv[1:]
try:runpy.run_path(sys.argv[0],run_name='__main__')
except SystemExit as error:assert error.code==0
assert not {'http.client','daggerml.floci','daggerml.floci_http','docker'} & set(sys.modules)
"""


def run_fresh(command, evidence):
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=30,
            env=environment,
        )
    except BaseException as error:
        evidence.append(
            dict(
                command=command,
                exit=None,
                disposition="unknown",
                error=type(error).__name__,
            )
        )
        raise
    evidence.append(
        dict(
            command=command,
            exit=result.returncode,
            stdout=result.stdout.decode(),
            stderr=result.stderr.decode(),
        )
    )
    assert result.returncode == 0, "fresh installed client error retained"
    return json.loads(result.stdout)


def run(root, story):
    fixture = Fixture(root)
    assert not fixture.state["stopped"] and not fixture.children()
    prove_profile(fixture)
    story = Path(story).resolve()
    story.mkdir()
    artifacts = json.loads((fixture.root / "artifacts.json").read_bytes())
    site = Path(d.__file__).resolve().parent.parent
    for row in artifacts:
        assert (
            hashlib.sha256((site / row["file"]).read_bytes()).hexdigest()
            == row["sha256"]
        )
    remote = f.FlociRemote(
        "http://floci:4566",
        "dml-local",
        "iteration13/scope",
        "local",
        "installed:1",
        fixture.state["image"],
        "/opt/dml/bin/python",
    )
    add_gate, double_gate = (
        "reuse-" + name + "/" + fixture.state["owner"] for name in ("add", "double")
    )
    caller, base, sentinel = composed.setup(story, artifacts, add_gate)
    old = normal.typed(caller, base)
    old.update(normal.typed(caller, sentinel))
    expected1, recorded1 = composed.request(
        caller, base, story, "add", "add-binding", "add-inputs"
    )
    first = composed.run_step(
        fixture, caller, story, "add", expected1, remote, add_gate, artifacts
    )
    basis = composed.app.consumer_basis(
        caller,
        producer_packet=first["packets"][-1]["packet"],
        producer_expected=expected1,
        remote=remote,
        gate=double_gate,
        artifacts=json.dumps(artifacts).encode(),
    )
    expected2, recorded2 = composed.request(
        caller, basis.commit, story, "double", "double-binding", "double-inputs"
    )
    second = composed.run_step(
        fixture, caller, story, "double", expected2, remote, double_gate, artifacts
    )
    selected = ex.read_observation(second["packets"][-1]["packet"], expected=expected2)
    assert selected.completion.outcome == "success"
    with d.Repository(caller) as repo, repo.read() as tx:
        assert composed.app.i64_root(tx, selected.result) == 84
        composed.app.input_association(
            tx,
            expected2.inputs,
            ex.read_observation(first["packets"][-1]["packet"], expected=expected1),
        )
    # Explicit independent head movement and nonfirst retained parent are fixture
    # authoring, not automatic merge/adoption. Both immutable histories stay fixed.
    with d.Repository(caller) as repo, repo.write() as tx:
        later = tx.put_commit(
            tx.put_tree(
                {
                    "note": tx.put_dag(
                        root=tx.put_literal(tx.put_datum("independent head"))
                    )
                }
            ),
            parents=(base,),
        )
        tx.update_ref("main", later)
        containing = tx.put_commit(
            tx.get_commit(selected.commit).tree, parents=(later, selected.commit)
        )
        tx.create_ref("retained-basis", containing)
    refs = {
        "main": later,
        "sentinel": sentinel,
        "double-basis": basis.commit,
        "retained-basis": containing,
    }
    for recorded in (recorded1, recorded2):
        refs[recorded.ref] = refs["request-" + recorded.request_id] = recorded.commit
    for row in (first, second):
        for phase in row["packets"]:
            refs[row["label"] + "-" + phase["phase"]] = d.ObjectId.from_hex(
                phase["commit"]
            )
    before_objects = normal.typed(caller, containing)
    before_objects.update(old)
    fixture.stop()  # Exact terminal jobs/all clients/empty namespace THEN archive/stop.
    assert not fixture.inspect(fixture.state["service_id"])["State"]["Running"]
    assert not fixture.children()
    census_before = service_census(
        fixture.root / "service-data", [first["job_id"], second["job_id"]]
    )
    offline = story / "offline"
    offline.mkdir()
    source = offline / "explicit_reuse.py"
    shutil.copyfile(ROOT / "examples/explicit_reuse.py", source)
    packet = offline / "historical-F"
    shutil.copytree(second["packets"][-1]["packet"], packet)
    expected_file = offline / "independent-expected.json"
    ex.save_exchange_handle(
        expected_file, ex.ExchangeHandle(story / "inert-unavailable-input", expected2)
    )
    commands = CommandEvidence(story / "fresh-commands.json")
    report = run_fresh(
        [
            sys.executable,
            "-B",
            "-c",
            OFFLINE_REUSE,
            str(source),
            str(caller),
            str(containing),
            "double-binding",
            "double-inputs",
            "urn:example:double",
            str(expected_file),
            str(packet),
            "reuse-submission",
            "reused-double",
        ],
        commands,
    )
    app = load_application(source)
    reused_commit, association, qcommit = (
        d.ObjectId.from_hex(report[k])
        for k in ("commit", "association", "request_commit")
    )
    q = d.ObjectId.from_hex(report["request"])
    with d.Repository(caller) as repo, repo.read() as tx:

        def nested(dag, name):
            node = tx.get_node(tx.lookup_node(dag, name))
            assert isinstance(node, d.SubDAGNode)
            return node.dag

        assert tx.get_commit(qcommit).parents == (containing,)
        assert tx.get_commit(reused_commit).parents == (qcommit,)
        qentries = dict(tx.get_tree(tx.get_commit(qcommit).tree))
        assert qentries.pop("request-" + report["request_id"]) == q
        assert qentries == dict(tx.get_tree(tx.get_commit(containing).tree))
        entries = dict(tx.get_tree(tx.get_commit(reused_commit).tree))
        assert entries.pop("reuse-" + report["request_id"]) == association
        assert entries == dict(tx.get_tree(tx.get_commit(qcommit).tree))
        assert nested(association, "attempt") == selected.completion.final_attempt
        assert nested(association, "request") == q != expected2.request
        assert nested(association, "result") == selected.result
        assert nested(selected.completion.final_attempt, "request") == expected2.request
        assert all(tx.get_ref(name) == target for name, target in refs.items())
        assert all(tx.get_record(*key) == raw for key, raw in before_objects.items())
        assert {name for name in entries if name.startswith("attempt-")} == {
            name for name in qentries if name.startswith("attempt-")
        }
    retained = normal.typed(caller, reused_commit)
    refs.update(
        {
            "reuse-submission": qcommit,
            "request-" + report["request_id"]: qcommit,
            "reused-double": reused_commit,
        }
    )
    # Fresh installed inspection/return and bounded CLI: source/B/input/service offline.
    inspected = run_fresh(
        [
            sys.executable,
            "-B",
            "-c",
            "import json,sys;from daggerml import exchange as e;h=e.load_exchange_handle(sys.argv[2]);s=e.read_observation(sys.argv[3],expected=h.expected);g=e.receive_observation(sys.argv[1],packet=sys.argv[3],expected=h.expected,ref='offline-old-F');assert g.commit==s.commit;assert not {'http.client','daggerml.floci','docker'} & set(sys.modules);print(json.dumps({'commit':str(g.commit),'attempt':str(g.completion.final_attempt)}))",
            str(caller),
            str(expected_file),
            str(packet),
        ],
        commands,
    )
    assert inspected["attempt"] == str(selected.completion.final_attempt)
    cli = site / "daggerml/_bin/dml"
    for arguments in (
        ["walk", str(association), "--limit", "200"],
        ["log", "--ref", "reused-double", "--limit", "100"],
        ["snapshot", "--ref", "reused-double"],
    ):
        run_fresh([str(cli), "--json", "--repo", str(caller), *arguments], commands)
    # Compare actual persisted service job inventory byte-for-byte while OFFLINE,
    # not merely controller len/mock submit count; reuse has no new token/started B.
    offline_census = story / "offline-service-census"
    offline_census.mkdir()
    fixture.docker(
        "cp",
        fixture.state["service_id"] + ":/app/data/batch-jobs.json",
        offline_census / "batch-jobs.json",
    )
    assert (
        service_census(offline_census, [first["job_id"], second["job_id"]])
        == census_before
    )
    assert not fixture.inspect(fixture.state["service_id"])["State"]["Running"]
    fixture.clients_stopped()
    assert not fixture.children()
    assert len(fixture.state["jobs"]) == 2
    # Only this explicit fixture action resumes KNOWN-STOPPED endpoint. Reset same
    # declared gate keys after terminal proof, preserving exact full input identity.
    fixture.resume()
    prove_profile(fixture)
    fresh_expected, fresh_recorded = composed.request(
        caller, reused_commit, story, "fresh-double", "double-binding", "double-inputs"
    )
    assert (
        fresh_expected.intent_uri,
        fresh_expected.binding,
        fresh_expected.inputs,
    ) == (expected2.intent_uri, expected2.binding, expected2.inputs)
    third = composed.run_step(
        fixture,
        caller,
        story,
        "fresh-double",
        fresh_expected,
        remote,
        double_gate,
        artifacts,
    )
    fresh = ex.read_observation(third["packets"][-1]["packet"], expected=fresh_expected)
    assert len({fresh.request, q, selected.request}) == 3
    assert fresh.attempt_id != selected.attempt_id and fresh.result == selected.result
    with d.Repository(caller) as repo, repo.read() as tx:
        assert (
            tx.get_node(tx.lookup_node(association, "attempt")).dag
            == selected.completion.final_attempt
        )
        assert all(tx.get_record(*key) == raw for key, raw in retained.items())
        assert all(tx.get_ref(name) == target for name, target in refs.items())
    for phase in third["packets"]:
        root_id = d.ObjectId.from_hex(phase["commit"])
        actual = normal.typed(caller, root_id)
        assert all(actual[key] == raw for key, raw in retained.items())
        assert actual == normal.typed(Path(phase["validation"]), root_id)
    fixture.stop()
    archives = sorted(fixture.root.glob("service-data*"))
    assert len(archives) == 2
    service_census(
        fixture.root / "service-data-1",
        [first["job_id"], second["job_id"], third["job_id"]],
    )
    assert len(fixture.state["jobs"]) == 3
    result = dict(
        actual_installed_reuse=True,
        jobs=3,
        phase_packets=9,
        no_reuse_job=True,
        reuse=report,
        trials=[first, second, third],
        commands=commands,
        artifacts=artifacts,
        old_objects=len(before_objects),
        retained_objects=len(retained),
        census_sha256=hashlib.sha256(census_before).hexdigest(),
        endpoint_stopped=True,
        normal_ephemeral_final_B=True,
    )
    (story / "summary.json").write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            dict(
                actual_installed_reuse=True,
                jobs=3,
                phase_packets=9,
                no_reuse_job=True,
                endpoint_stopped=True,
            )
        )
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]))
