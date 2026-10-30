"""Mandatory current-installed three-job/nine-phase durable selection/branch gate.

Explicit NEW owned fixture only; no default startup/private computational hook.
Service/original-packet-independent S/V revalidation, existing Q/W delegation,
explicit fresh (no selection change), offline adoption and sibling choices.
"""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys

import daggerml as d
from daggerml import exchange as ex, floci as f, transfer
from fixture import Fixture
import integration as normal
import composed_integration as composed
from retained_integration import prove_profile
from reuse_integration import CommandEvidence, OFFLINE_REUSE, run_fresh, service_census

ROOT = Path(__file__).resolve().parents[2]
SLOT = "selected-double"
DIMENSIONS = ["double-binding", "double-inputs", "urn:example:double"]
OFFLINE_POLICY = """import importlib.abc,sys
from pathlib import Path
class NoService(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname == 'http' or fullname.startswith('http.') or fullname == 'docker' or fullname.startswith('docker.') or fullname.startswith('daggerml.floci'):
   raise AssertionError('offline selection cannot import service runtime')
sys.meta_path.insert(0,NoService())
sys.path.insert(0,str(Path(sys.argv[1]).resolve().parent))
"""
OFFLINE_SELECTION = (
    OFFLINE_POLICY
    + OFFLINE_REUSE
    + "\nassert not any(n == 'http' or n.startswith('http.') or n == 'docker' or n.startswith('docker.') or n.startswith('daggerml.floci') for n in sys.modules)\n"
)


def external_census(fixture, expected):
    """Released ListJobs defaults RUNNING; enumerate ALL seven explicit states."""
    identifiers = []
    for status in (
        "SUBMITTED",
        "PENDING",
        "RUNNABLE",
        "STARTING",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
    ):
        response = fixture.batch(
            "ListJobs", dict(jobQueue="local", jobStatus=status, maxResults=100)
        )
        assert not response.get("nextToken"), "bounded fixture census must be complete"
        identifiers.extend(row["jobId"] for row in response["jobSummaryList"])
    assert len(identifiers) == len(expected) and set(identifiers) == set(expected)
    return identifiers


def invoke(source, evidence, mode, caller, commit, *arguments):
    return run_fresh(
        [
            sys.executable,
            "-B",
            "-c",
            OFFLINE_SELECTION,
            str(source),
            mode,
            str(caller),
            str(commit),
            SLOT,
            *map(str, arguments),
        ],
        evidence,
    )


def nested(tx, dag, name):
    node = tx.get_node(tx.lookup_node(dag, name))
    assert isinstance(node, d.SubDAGNode)
    return node.dag


def tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def attempt_population(caller, commit):
    """Complete typed native occurrence/version census, not service/mock counts."""
    records = normal.typed(caller, commit)
    found = {}
    with d.Repository(caller) as repository, repository.read() as tx:
        for kind, oid in records:
            if kind != "dag":
                continue
            description = tx.get_dag(oid)
            if "role" not in description.bindings:
                continue
            node = tx.get_node(description.bindings["role"])
            if not isinstance(node, d.LiteralNode) or tx.get_datum(
                node.datum
            ) != d.Datum.string("local-attempt-v1"):
                continue
            occurrence = tx.get_datum(tx.get_node(description.root).datum).value
            found.setdefault(occurrence, set()).add(str(oid))
    return {key: sorted(values) for key, values in found.items()}


def capture_headers(expected_file, packet):
    """Independent bounded evidence copies BEFORE original paths disappear."""
    copies = []
    for path in (
        expected_file,
        Path(packet) / "job.json",
        Path(packet) / "observation.json",
    ):
        with open(path, "rb") as stream:
            data = stream.read(ex.MAX_DESCRIPTOR_BYTES + 1)
        assert len(data) <= ex.MAX_DESCRIPTOR_BYTES
        copies.append(data)
    return tuple(copies)


def inspect_client(source, evidence, caller, commit):
    original = normal.typed(caller, commit)
    physical = (Path(caller) / "data.mdb").read_bytes()
    report = invoke(source, evidence, "inspect", caller, commit)
    assert normal.typed(caller, commit) == original
    assert (
        Path(caller) / "data.mdb"
    ).read_bytes() == physical, "inspect-only A bytes changed"
    return report


def verify_choice(caller, report, expected, snapshot, headers):
    commit, dag, validation = (
        d.ObjectId.from_hex(report[key])
        for key in ("commit", "selection", "validation")
    )
    with d.Repository(caller) as repository, repository.read() as tx:
        assert tree(tx, commit)[SLOT] == dag
        assert set(tx.get_dag(dag).bindings) == {
            "role",
            "intent",
            "binding",
            "inputs",
            "request",
            "attempt",
            "result",
            "completion",
            "validation",
        }
        assert tx.get_datum(
            tx.get_node(tx.lookup_node(dag, "role")).datum
        ) == d.Datum.string("example-reuse-selection-v1")
        assert tx.get_datum(
            tx.get_node(tx.lookup_node(dag, "intent")).datum
        ) == d.Datum.uri(expected.intent_uri)
        assert nested(tx, dag, "validation") == validation
        assert nested(tx, dag, "request") == snapshot.request == expected.request
        assert nested(tx, dag, "attempt") == snapshot.completion.final_attempt
        assert nested(tx, dag, "result") == snapshot.result
        assert nested(tx, dag, "binding") == expected.binding
        assert nested(tx, dag, "inputs") == expected.inputs
        assert tx.get_dag(dag).root == tx.lookup_node(dag, "result")
        assert tx.get_datum(
            tx.get_node(tx.lookup_node(dag, "completion")).datum
        ) == d.Datum.bytes(snapshot.commit.bytes)
        assert tx.get_dag(validation).root == tx.lookup_node(validation, "expected")
        assert set(tx.get_dag(validation).bindings) == {
            "expected",
            "job",
            "observation",
        }
        for name, data in zip(("expected", "job", "observation"), headers):
            node = tx.get_node(tx.lookup_node(validation, name))
            assert isinstance(node, d.LiteralNode)
            assert tx.get_datum(node.datum) == d.Datum.bytes(data)
    return commit, dag, validation


def verify_reuse(caller, basis, report, snapshot):
    commit, dag, qcommit, request = (
        d.ObjectId.from_hex(report[key])
        for key in ("commit", "association", "request_commit", "request")
    )
    with d.Repository(caller) as repository, repository.read() as tx:
        assert tx.get_commit(qcommit).parents == (basis,)
        assert tx.get_commit(commit).parents == (qcommit,)
        entries = tree(tx, qcommit)
        assert entries.pop("request-" + report["request_id"]) == request
        assert entries == tree(tx, basis)
        entries = tree(tx, commit)
        assert entries.pop("reuse-" + report["request_id"]) == dag
        assert entries == tree(tx, qcommit)
        assert nested(tx, dag, "request") == request != snapshot.request
        assert nested(tx, dag, "attempt") == snapshot.completion.final_attempt
        assert nested(tx, dag, "result") == snapshot.result
        assert (
            nested(tx, snapshot.completion.final_attempt, "request") == snapshot.request
        )
        assert {n for n in entries if n.startswith("attempt-")} == {
            n for n in tree(tx, basis) if n.startswith("attempt-")
        }
    assert attempt_population(caller, commit) == attempt_population(caller, basis)
    return commit, dag


def census_offline(fixture, archive, jobs, original):
    archive.mkdir()
    fixture.docker(
        "cp",
        fixture.state["service_id"] + ":/app/data/batch-jobs.json",
        archive / "batch-jobs.json",
    )
    assert service_census(archive, jobs) == original
    assert not fixture.inspect(fixture.state["service_id"])["State"]["Running"]
    fixture.clients_stopped()
    assert not fixture.children()


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
        "iteration14/scope",
        "local",
        "installed:1",
        fixture.state["image"],
        "/opt/dml/bin/python",
    )
    add_gate, double_gate = (
        "selection-" + name + "/" + fixture.state["owner"] for name in ("add", "double")
    )
    caller, base, sentinel = composed.setup(story, artifacts, add_gate)
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
    old = ex.read_observation(second["packets"][-1]["packet"], expected=expected2)
    assert old.completion.outcome == "success"
    with d.Repository(caller) as repository, repository.write() as tx:
        annotation = tx.put_commit(
            tx.put_tree(
                {
                    "annotation": tx.put_dag(
                        root=tx.put_literal(tx.put_datum("independent containing head"))
                    )
                }
            ),
            parents=(base,),
        )
        tx.update_ref("main", annotation)
        containing = tx.put_commit(
            tx.get_commit(old.commit).tree, parents=(annotation, old.commit)
        )
        tx.create_ref("retained-basis", containing)
    old_objects = normal.typed(caller, containing)
    old_population = attempt_population(caller, containing)
    assert len(old_population) == 3  # one genuine host prior + add + old double
    old_objects.update(normal.typed(caller, sentinel))
    with d.Repository(caller) as repository, repository.read() as tx:
        refs = {
            "main": annotation,
            "sentinel": sentinel,
            "retained-basis": containing,
            "double-basis": basis.commit,
        }
        for recorded in (recorded1, recorded2):
            refs[recorded.ref] = refs["request-" + recorded.request_id] = (
                recorded.commit
            )
        for trial in (first, second):
            for phase in trial["packets"]:
                refs[trial["label"] + "-" + phase["phase"]] = d.ObjectId.from_hex(
                    phase["commit"]
                )
    jobs = [first["job_id"], second["job_id"]]
    external_census(fixture, jobs)
    fixture.stop()  # terminal identities/ALL stopped clients/empty namespace BEFORE offline.
    census2 = service_census(fixture.root / "service-data", jobs)
    offline = story / "offline"
    offline.mkdir()
    for name in ("reuse_selection.py", "explicit_reuse.py"):
        shutil.copyfile(ROOT / "examples" / name, offline / name)
    source = offline / "reuse_selection.py"
    expected_file = offline / "independent-old-expected.json"
    shutil.copyfile(Path(second["saved"]) / "expected.json", expected_file)
    commands = CommandEvidence(story / "fresh-commands.json")
    headers2 = capture_headers(expected_file, second["packets"][-1]["packet"])
    selection_report = invoke(
        source,
        commands,
        "select",
        caller,
        containing,
        *DIMENSIONS,
        expected_file,
        second["packets"][-1]["packet"],
        "selection-old",
    )
    selection, s0, v0 = verify_choice(
        caller, selection_report, expected2, old, headers2
    )
    assert attempt_population(caller, selection) == old_population
    with d.Repository(caller) as repository, repository.read() as tx:
        assert tx.get_commit(selection).parents == (containing,)
        entries = tree(tx, containing)
        entries[SLOT] = s0
        assert tree(tx, selection) == entries
        assert all(tx.get_record(*key) == raw for key, raw in old_objects.items())
    # ORIGINAL evidence is unavailable; only persisted S/V/native F is usable now.
    for path in (
        Path(second["packets"][-1]["packet"]),
        Path(second["saved"]),
        expected_file,
    ):
        path.rename(path.with_name(path.name + ".unavailable"))
    assert not (story / "double-input").exists()
    assert (
        story / "double-input.offline"
    ).is_dir()  # unavailable to saved original path
    assert not fixture.children()  # original ephemeral B/job namespace absent
    inspected = inspect_client(source, commands, caller, selection)
    assert inspected["attempt"] == str(old.completion.final_attempt)
    reused_report = invoke(
        source,
        commands,
        "reuse-selected",
        caller,
        selection,
        *DIMENSIONS,
        "reuse-submission",
        "reused-double",
    )
    reused, w0 = verify_reuse(caller, selection, reused_report, old)
    retained = normal.typed(caller, reused)
    refs.update(
        {
            "selection-old": selection,
            "reuse-submission": d.ObjectId.from_hex(reused_report["request_commit"]),
            "request-"
            + reused_report["request_id"]: d.ObjectId.from_hex(
                reused_report["request_commit"]
            ),
            "reused-double": reused,
        }
    )
    # Repository transfer ALONE reconstructs old selection in a fresh installed reader.
    replica = offline / "old-replica.dml"
    with d.Repository(replica, create=True):
        pass
    transfer.import_commit(replica, transfer.export_commit(caller, commit=reused))
    assert normal.typed(replica, reused) == retained
    assert inspect_client(source, commands, replica, reused)["attempt"] == str(
        old.completion.final_attempt
    )
    census_offline(fixture, story / "offline-census-two", jobs, census2)
    # Known-stopped fixture reset of SAME declared finite keys only; not runtime recovery.
    fixture.resume()
    prove_profile(fixture)
    expected3, recorded3 = composed.request(
        caller, reused, story, "fresh-double", "double-binding", "double-inputs"
    )
    assert (expected3.intent_uri, expected3.binding, expected3.inputs) == (
        expected2.intent_uri,
        expected2.binding,
        expected2.inputs,
    )
    third = composed.run_step(
        fixture,
        caller,
        story,
        "fresh-double",
        expected3,
        remote,
        double_gate,
        artifacts,
    )
    fresh = ex.read_observation(third["packets"][-1]["packet"], expected=expected3)
    assert fresh.completion.outcome == "success" and fresh.result == old.result
    assert (
        len({fresh.request, old.request, d.ObjectId.from_hex(reused_report["request"])})
        == 3
    )
    assert fresh.completion.final_attempt != old.completion.final_attempt
    fresh_population = attempt_population(caller, fresh.commit)
    assert set(fresh_population) == set(old_population) | {fresh.attempt_id}
    assert all(fresh_population[key] == value for key, value in old_population.items())
    for phase in third["packets"]:
        root_id = d.ObjectId.from_hex(phase["commit"])
        actual = normal.typed(caller, root_id)
        assert actual == normal.typed(Path(phase["validation"]), root_id)
        assert all(actual[key] == raw for key, raw in retained.items())
        with d.Repository(caller) as repository, repository.read() as tx:
            assert tree(tx, root_id)[SLOT] == s0
            assert nested(tx, w0, "attempt") == old.completion.final_attempt
    jobs.append(third["job_id"])
    external_census(fixture, jobs)
    fixture.stop()
    census3 = service_census(fixture.root / "service-data-1", jobs)
    expected_fresh = offline / "independent-fresh-expected.json"
    shutil.copyfile(Path(third["saved"]) / "expected.json", expected_fresh)
    headers3 = capture_headers(expected_fresh, third["packets"][-1]["packet"])
    adoption_report = invoke(
        source,
        commands,
        "adopt",
        caller,
        fresh.commit,
        *DIMENSIONS,
        expected_fresh,
        third["packets"][-1]["packet"],
        "adopt-fresh",
    )
    adoption, s1, v1 = verify_choice(
        caller, adoption_report, expected3, fresh, headers3
    )
    assert attempt_population(caller, adoption) == fresh_population
    with d.Repository(caller) as repository, repository.write() as tx:
        keep = tx.put_commit(tx.get_commit(fresh.commit).tree, parents=(fresh.commit,))
        tx.create_ref("keep-old", keep)
    with d.Repository(caller) as repository, repository.read() as tx:
        assert (
            tx.get_commit(adoption).parents
            == tx.get_commit(keep).parents
            == (fresh.commit,)
        )
        entries = tree(tx, fresh.commit)
        entries[SLOT] = s1
        assert tree(tx, adoption) == entries and tree(tx, keep) == tree(
            tx, fresh.commit
        )
        assert all(tx.get_record(*key) == raw for key, raw in retained.items())
        assert all(tx.get_ref(name) == target for name, target in refs.items())
    for path in (
        Path(third["packets"][-1]["packet"]),
        Path(third["saved"]),
        expected_fresh,
    ):
        path.rename(path.with_name(path.name + ".unavailable"))
    branch_reports = []
    for label, branch, snapshot in (("old", keep, old), ("fresh", adoption, fresh)):
        assert inspect_client(source, commands, caller, branch)["attempt"] == str(
            snapshot.completion.final_attempt
        )
        copied = offline / (label + "-branch.dml")
        with d.Repository(copied, create=True):
            pass
        transfer.import_commit(copied, transfer.export_commit(caller, commit=branch))
        assert normal.typed(copied, branch) == normal.typed(caller, branch)
        assert inspect_client(source, commands, copied, branch)["attempt"] == str(
            snapshot.completion.final_attempt
        )
        copied_reuse = invoke(
            source,
            commands,
            "reuse-selected",
            copied,
            branch,
            *DIMENSIONS,
            "replica-submission-" + label,
            "replica-reuse-" + label,
        )
        verify_reuse(copied, branch, copied_reuse, snapshot)
        assert copied_reuse["attempt"] == str(snapshot.completion.final_attempt)
        report = invoke(
            source,
            commands,
            "reuse-selected",
            caller,
            branch,
            *DIMENSIONS,
            "branch-submission-" + label,
            "branch-reuse-" + label,
        )
        verify_reuse(caller, branch, report, snapshot)
        assert report["result"] == str(old.result)
        branch_reports.append(report)
    assert branch_reports[0]["attempt"] != branch_reports[1]["attempt"]
    census_offline(fixture, story / "offline-census-three", jobs, census3)
    cli = site / "daggerml/_bin/dml"
    for arguments in (
        ["walk", str(s1), "--limit", "200"],
        ["snapshot", "--ref", "keep-old"],
        ["log", "--ref", "adopt-fresh", "--limit", "100"],
    ):
        run_fresh([str(cli), "--json", "--repo", str(caller), *arguments], commands)
    result = dict(
        actual_installed_selection=True,
        jobs=3,
        phase_packets=9,
        no_selection_reuse_adoption_job=True,
        selection=selection_report,
        reuse=reused_report,
        adoption=adoption_report,
        keep=str(keep),
        branches=branch_reports,
        trials=[first, second, third],
        commands=commands,
        artifacts=artifacts,
        old_objects=len(old_objects),
        retained_objects=len(retained),
        attempt_population=fresh_population,
        endpoint_stopped=True,
        original_evidence_unavailable=True,
        normal_ephemeral_final_B=True,
    )
    (story / "summary.json").write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            dict(
                actual_installed_selection=True,
                jobs=3,
                phase_packets=9,
                endpoint_stopped=True,
                durable_offline_branches=True,
            )
        )
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]))
