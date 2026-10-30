"""Explicit current-installed THREE-job/NINE-phase captured A/B selection gate.

Offline initial definition and default/override/reuse/branch readers; no default
fixture start, package/private runtime hook, fourth job or final-B hold.
"""

import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid

import daggerml as d
from daggerml import exchange as ex, floci as f, local, transfer
from fixture import Fixture
import composed_integration as composed
import integration as normal
from intent_integration import OFFLINE, invoke, native_population, hide_original
from retained_integration import prove_profile
from reuse_integration import CommandEvidence, service_census
from selection_integration import (
    external_census,
    census_offline,
    attempt_population,
    tree,
    nested,
    capture_headers,
)

ROOT = Path(__file__).resolve().parents[2]
OPTIONS = (
    ("double-a", "double-a-binding", "selected-double-a"),
    ("double-b", "double-b-binding", "selected-double-b"),
)


def double_b_source(source):
    """Capture genuine alternative standalone code, not a label/comment identity."""
    old = "result = tx.put_literal(tx.put_datum(number.value * factor))"
    assert source.count(old.encode()) == 1
    new = "if factor != 2:\n            raise ValueError('addition implementation requires demo factor two')\n        result = tx.put_literal(tx.put_datum(number.value + number.value))"
    return source.replace(old.encode(), new.encode())


def scalar(tx, dag, name):
    node = tx.get_node(tx.lookup_node(dag, name))
    assert isinstance(node, d.LiteralNode)
    return tx.get_datum(node.datum)


def verify_definition(caller, report):
    commit, dag, menu = (
        d.ObjectId.from_hex(report[n]) for n in ("commit", "definition", "menu")
    )
    with d.Repository(caller) as repository, repository.read() as tx:
        entries = tree(tx, commit)
        assert entries["double-intent"] == dag
        desc = tx.get_dag(dag)
        assert set(desc.bindings) == {
            "role",
            "intent",
            "reuse-default",
            "implementations",
            "default-implementation",
        }
        assert desc.root == desc.bindings["intent"]
        assert scalar(tx, dag, "role") == d.Datum.string(
            "example-implementation-definition-v1"
        )
        assert scalar(tx, dag, "intent") == d.Datum.uri("urn:example:double")
        assert scalar(tx, dag, "reuse-default") == d.Datum.string("reuse-by-default")
        assert scalar(tx, dag, "default-implementation") == d.Datum.string(
            report["default_implementation"]
        )
        assert nested(tx, dag, "implementations") == menu
        desc = tx.get_dag(menu)
        assert (
            set(desc.bindings) == {"role", "double-a", "double-b"}
            and desc.root == desc.bindings["role"]
        )
        assert scalar(tx, menu, "role") == d.Datum.string(
            "example-implementation-menu-v1"
        )
        for label, name, slot in OPTIONS:
            choice = nested(tx, menu, label)
            desc = tx.get_dag(choice)
            assert set(desc.bindings) == {
                "role",
                "binding",
                "binding-name",
                "selection-slot",
            }
            assert desc.root == desc.bindings["binding"]
            assert scalar(tx, choice, "role") == d.Datum.string(
                "example-implementation-choice-v1"
            )
            assert scalar(tx, choice, "binding-name") == d.Datum.string(name)
            assert scalar(tx, choice, "selection-slot") == d.Datum.string(slot)
            assert nested(tx, choice, "binding") == entries[name]
        assert entries["double-a-binding"] != entries["double-b-binding"]
        a_source = scalar(tx, entries["double-a-binding"], "source").value
        b_source = scalar(tx, entries["double-b-binding"], "source").value
        assert b_source == double_b_source(a_source)
    return commit


def policy(
    source, commands, caller, commit, label, *, implementation="default", reuse=False
):
    return invoke(
        source,
        commands,
        "request",
        caller,
        commit,
        "double-intent",
        "double-inputs",
        "decision-" + label,
        implementation,
        "default",
        "decision-" + label,
        "submission-" + label,
        *(("--reuse-ref", "reuse-" + label) if reuse else ()),
    )


def verify_policy(
    caller, basis, report, label, selected=None, *, requested_override="default"
):
    assert report["implementation_override"] == requested_override
    expected_implementation_reason = (
        "default-implementation"
        if requested_override == "default"
        else "explicit-implementation"
    )
    assert report["implementation_reason"] == expected_implementation_reason
    cdec, dag, cq, q, final = (
        d.ObjectId.from_hex(report[n])
        for n in ("decision_commit", "decision", "request_commit", "request", "commit")
    )
    binding_name, slot = label + "-binding", "selected-" + label
    with d.Repository(caller) as repository, repository.read() as tx:
        assert tx.get_commit(cdec).parents == (basis,)
        old = tree(tx, basis)
        entries = dict(old)
        entries[report["decision_name"]] = dag
        assert tree(tx, cdec) == entries
        desc = tx.get_dag(dag)
        required = {
            "role",
            "intent-definition",
            "implementation-choice",
            "binding",
            "inputs",
            "intent-name",
            "binding-name",
            "inputs-name",
            "selection-slot",
            "implementation",
            "implementation-override",
            "implementation-reason",
            "override",
            "action",
            "reason",
        }
        assert set(desc.bindings) == required | ({"selection"} if selected else set())
        assert desc.root == desc.bindings["intent-definition"]
        definition = old["double-intent"]
        menu = nested(tx, definition, "implementations")
        assert nested(tx, dag, "intent-definition") == definition
        assert nested(tx, dag, "implementation-choice") == nested(tx, menu, label)
        assert (
            nested(tx, dag, "binding")
            == old[binding_name]
            == d.ObjectId.from_hex(report["binding"])
        )
        assert (
            nested(tx, dag, "inputs")
            == old["double-inputs"]
            == d.ObjectId.from_hex(report["inputs"])
        )
        for name, value in {
            "role": "example-implementation-decision-v1",
            "intent-name": "double-intent",
            "binding-name": binding_name,
            "inputs-name": "double-inputs",
            "selection-slot": slot,
            "implementation": label,
            "implementation-override": requested_override,
            "implementation-reason": expected_implementation_reason,
            "override": "default",
            "action": "reuse-selected" if selected else "execute-fresh",
            "reason": "default-selection" if selected else "default-no-selection",
        }.items():
            assert scalar(tx, dag, name) == d.Datum.string(value)
        assert tx.get_commit(cq).parents == (cdec,)
        entries["request-" + report["request_id"]] = q
        assert tree(tx, cq) == entries
        assert nested(tx, q, "binding") == old[binding_name]
        assert nested(tx, q, "inputs") == old["double-inputs"]
        if selected:
            assert nested(tx, dag, "selection") == old[slot]
            w = d.ObjectId.from_hex(report["association"])
            desc = tx.get_dag(w)
            assert (
                set(desc.bindings) == {"role", "request", "attempt", "result"}
                and desc.root == desc.bindings["result"]
            )
            assert scalar(tx, w, "role") == d.Datum.string("example-explicit-reuse-v1")
            assert nested(tx, w, "request") == q != selected.request
            assert nested(tx, w, "attempt") == selected.completion.final_attempt
            assert nested(tx, w, "result") == selected.result
            assert (
                nested(tx, selected.completion.final_attempt, "request")
                == selected.request
            )
            entries["reuse-" + report["request_id"]] = w
            assert tx.get_commit(final).parents == (cq,) and tree(tx, final) == entries
        else:
            assert final == cq and report["association"] is None
            assert slot not in old
    assert report["implementation"] == label
    assert attempt_population(caller, final) == attempt_population(caller, basis)
    return final


def read_policy(source, commands, caller, report):
    root = d.ObjectId.from_hex(report["commit"])
    physical, before = (Path(caller) / "data.mdb").read_bytes(), normal.typed(
        caller, root
    )
    args = [report["request"], report["decision_name"]]
    if report["association"] is not None:
        args += ["--satisfaction-commit", report["commit"]]
    got = invoke(
        source, commands, "inspect-request", caller, report["request_commit"], *args
    )
    claims = {
        "decision_commit",
        "decision",
        "decision_name",
        "base",
        "definition",
        "default",
        "default_implementation",
        "intent",
        "implementation",
        "implementation_choice",
        "implementation_override",
        "implementation_reason",
        "binding_name",
        "inputs_name",
        "selection_slot",
        "override",
        "action",
        "reason",
        "binding",
        "inputs",
        "selection",
        "attempt",
        "result",
    }
    assert set(got) == claims | {"mode"}, "reader claim set differs"
    assert got["mode"] == "inspect-request"
    assert all(
        got[name] == report[name] for name in claims
    ), "pinned reader claim differs"
    assert (Path(caller) / "data.mdb").read_bytes() == physical and normal.typed(
        caller, root
    ) == before


def prepare_policy(caller, story, label, report):
    return ex.prepare_exchange(
        caller,
        commit=d.ObjectId.from_hex(report["request_commit"]),
        request=d.ObjectId.from_hex(report["request"]),
        binding_name=report["binding_name"],
        inputs_name="double-inputs",
        intent_uri=report["intent"],
        worker_ref="work",
        workspace=story / (label + "-input"),
    )


def select(source, commands, caller, snapshot, trial, expected, label):
    saved = Path(trial["saved"]) / "expected.json"
    packet = Path(trial["packets"][-1]["packet"])
    headers = capture_headers(saved, packet)
    report = invoke(
        source,
        commands,
        "select",
        caller,
        snapshot.commit,
        "selected-" + label,
        label + "-binding",
        "double-inputs",
        "urn:example:double",
        saved,
        packet,
        "selection-" + label,
    )
    commit, dag, validation = (
        d.ObjectId.from_hex(report[n]) for n in ("commit", "selection", "validation")
    )
    with d.Repository(caller) as repository, repository.read() as tx:
        entries = tree(tx, snapshot.commit)
        entries["selected-" + label] = dag
        assert (
            tx.get_commit(commit).parents == (snapshot.commit,)
            and tree(tx, commit) == entries
        )
        assert nested(tx, dag, "binding") == expected.binding
        assert nested(tx, dag, "inputs") == expected.inputs
        assert nested(tx, dag, "request") == snapshot.request
        assert nested(tx, dag, "attempt") == snapshot.completion.final_attempt
        assert nested(tx, dag, "result") == snapshot.result
        assert nested(tx, dag, "validation") == validation
        for name, data in zip(("expected", "job", "observation"), headers):
            assert scalar(tx, validation, name) == d.Datum.bytes(data)
    return commit, report


def initialize(root, story):
    fixture = Fixture(root)
    assert not fixture.state, "initial definition requires NEW offline fixture"
    story = Path(story).resolve()
    story.mkdir()
    offline = story / "offline"
    offline.mkdir()
    for name in (
        "implementation_selection.py",
        "reuse_selection.py",
        "explicit_reuse.py",
    ):
        shutil.copyfile(ROOT / "examples" / name, offline / name)
    artifacts = json.loads((fixture.root / "artifacts.json").read_bytes())
    scope = uuid.uuid4().hex
    add_gate, double_gate = (
        "implementation-add/" + scope,
        "implementation-double/" + scope,
    )
    caller, base, sentinel = composed.setup(story, artifacts, add_gate)
    with d.Repository(caller) as repository, repository.write() as tx:
        entries = tree(tx, base)
        a = entries.pop("double-binding")
        entries["double-a-binding"] = a
        entries["double-b-binding"] = local.put_local_binding(
            tx,
            source=double_b_source(scalar(tx, a, "source").value),
            interpreter="/opt/dml/bin/python",
            timeout_ms=360000,
        )
        base = tx.put_commit(tx.put_tree(entries), parents=(base,))
        tx.update_ref("main", base)
    commands = CommandEvidence(story / "initial-commands.json")
    args = [
        "double-intent",
        "urn:example:double",
        "reuse-by-default",
        "double-a",
        "intent-default",
    ]
    for choice in OPTIONS:
        args += ["--implementation", *choice]
    defined = invoke(
        offline / "implementation_selection.py", commands, "define", caller, base, *args
    )
    commit = verify_definition(caller, defined)
    assert attempt_population(caller, commit) == attempt_population(caller, base)
    (story / "initial.json").write_text(
        json.dumps(
            dict(
                caller=str(caller),
                base=str(base),
                commit=str(commit),
                sentinel=str(sentinel),
                definition=defined,
                add_gate=add_gate,
                double_gate=double_gate,
                artifacts=artifacts,
            ),
            indent=2,
        )
    )
    print(json.dumps(dict(initialized=True, service_offline=True, commit=str(commit))))


def run(root, story):
    fixture = Fixture(root)
    assert not fixture.state["stopped"] and not fixture.children()
    prove_profile(fixture)
    story = Path(story).resolve()
    initial = json.loads((story / "initial.json").read_bytes())
    caller, base = Path(initial["caller"]), d.ObjectId.from_hex(initial["commit"])
    artifacts = initial["artifacts"]
    assert artifacts == json.loads((fixture.root / "artifacts.json").read_bytes())
    site = Path(d.__file__).resolve().parent.parent
    for row in artifacts:
        assert (
            hashlib.sha256((site / row["file"]).read_bytes()).hexdigest()
            == row["sha256"]
        )
    remote = f.FlociRemote(
        "http://floci:4566",
        "dml-local",
        "iteration16/scope",
        "local",
        "installed:1",
        fixture.state["image"],
        "/opt/dml/bin/python",
    )
    source, selection_source = (
        story / "offline/implementation_selection.py",
        story / "offline/reuse_selection.py",
    )
    commands = CommandEvidence(story / "fresh-commands.json")
    expected1, recorded1 = composed.request(
        caller, base, story, "add", "add-binding", "add-inputs"
    )
    first = composed.run_step(
        fixture, caller, story, "add", expected1, remote, initial["add_gate"], artifacts
    )
    producer = ex.read_observation(first["packets"][-1]["packet"], expected=expected1)
    basis = composed.app.consumer_basis(
        caller,
        producer_packet=first["packets"][-1]["packet"],
        producer_expected=expected1,
        remote=remote,
        gate=initial["double_gate"],
        artifacts=json.dumps(artifacts).encode(),
    )
    jobs = [first["job_id"]]
    external_census(fixture, jobs)
    fixture.stop()
    census1 = service_census(fixture.root / "service-data", jobs)
    miss_a = policy(source, commands, caller, basis.commit, "a-miss")
    verify_policy(caller, basis.commit, miss_a, "double-a")
    read_policy(source, commands, caller, miss_a)
    census_offline(fixture, story / "offline-census-one", jobs, census1)
    fixture.resume()
    prove_profile(fixture)
    expected_a = prepare_policy(caller, story, "double-a", miss_a)
    second = composed.run_step(
        fixture,
        caller,
        story,
        "double-a",
        expected_a,
        remote,
        initial["double_gate"],
        artifacts,
    )
    a = ex.read_observation(second["packets"][-1]["packet"], expected=expected_a)
    assert a.completion.outcome == "success"
    with d.Repository(caller) as repository, repository.read() as tx:
        assert all(
            "selected-" + label not in tree(tx, a.commit)
            for label in ("double-a", "double-b")
        )
        composed.app.input_association(tx, expected_a.inputs, producer)
        assert composed.app.i64_root(tx, a.result) == 84
    jobs.append(second["job_id"])
    external_census(fixture, jobs)
    fixture.stop()
    census2 = service_census(fixture.root / "service-data-1", jobs)
    chosen_a, selection_a = select(
        selection_source, commands, caller, a, second, expected_a, "double-a"
    )
    hide_original(second, story)
    defined_b = invoke(
        source,
        commands,
        "update-default",
        caller,
        chosen_a,
        "double-intent",
        "double-b",
        "default-b",
    )
    default_b = verify_definition(caller, defined_b)
    assert defined_b["menu"] == initial["definition"]["menu"]
    with d.Repository(caller) as repository, repository.read() as tx:
        entries = tree(tx, chosen_a)
        entries["double-intent"] = d.ObjectId.from_hex(defined_b["definition"])
        assert (
            tx.get_commit(default_b).parents == (chosen_a,)
            and tree(tx, default_b) == entries
        )
    miss_b = policy(source, commands, caller, default_b, "b-miss")
    verify_policy(caller, default_b, miss_b, "double-b")
    read_policy(source, commands, caller, miss_b)
    retained = normal.typed(caller, d.ObjectId.from_hex(miss_b["commit"]))
    census_offline(fixture, story / "offline-census-two", jobs, census2)
    fixture.resume()
    prove_profile(fixture)
    expected_b = prepare_policy(caller, story, "double-b", miss_b)
    assert (
        expected_a.binding != expected_b.binding
        and expected_a.inputs == expected_b.inputs
    )
    third = composed.run_step(
        fixture,
        caller,
        story,
        "double-b",
        expected_b,
        remote,
        initial["double_gate"],
        artifacts,
    )
    b = ex.read_observation(third["packets"][-1]["packet"], expected=expected_b)
    assert (
        b.completion.outcome == "success"
        and a.result == b.result
        and a.attempt_id != b.attempt_id
    )
    for phase in third["packets"]:
        actual = normal.typed(caller, d.ObjectId.from_hex(phase["commit"]))
        assert all(actual[key] == raw for key, raw in retained.items())
    with d.Repository(caller) as repository, repository.read() as tx:
        assert "selected-double-b" not in tree(tx, b.commit)
        assert tree(tx, b.commit)["selected-double-a"] == d.ObjectId.from_hex(
            selection_a["selection"]
        )
        composed.app.input_association(tx, expected_b.inputs, producer)
        assert composed.app.i64_root(tx, b.result) == 84
    jobs.append(third["job_id"])
    external_census(fixture, jobs)
    fixture.stop()
    census3 = service_census(fixture.root / "service-data-2", jobs)
    common, selection_b = select(
        selection_source, commands, caller, b, third, expected_b, "double-b"
    )
    hide_original(third, story)
    hide_original(first, story)
    hit_b = policy(source, commands, caller, common, "b-hit", reuse=True)
    verify_policy(caller, common, hit_b, "double-b", b)
    hit_a = policy(
        source,
        commands,
        caller,
        common,
        "a-explicit",
        implementation="double-a",
        reuse=True,
    )
    verify_policy(caller, common, hit_a, "double-a", a, requested_override="double-a")
    with d.Repository(caller) as repository, repository.write() as tx:
        keep = tx.put_commit(tx.get_commit(common).tree, parents=(common,))
        tx.create_ref("keep-b", keep)
    defined_a = invoke(
        source,
        commands,
        "update-default",
        caller,
        common,
        "double-intent",
        "double-a",
        "default-a",
    )
    branch_a = verify_definition(caller, defined_a)
    with d.Repository(caller) as repository, repository.read() as tx:
        assert (
            tx.get_commit(keep).parents == tx.get_commit(branch_a).parents == (common,)
        )
        entries, changed = tree(tx, keep), tree(tx, branch_a)
        assert entries.pop("double-intent") == d.ObjectId.from_hex(
            defined_b["definition"]
        )
        assert changed.pop("double-intent") == d.ObjectId.from_hex(
            initial["definition"]["definition"]
        )
        assert entries == changed
    sibling_b = policy(source, commands, caller, keep, "sibling-b", reuse=True)
    sibling_a = policy(source, commands, caller, branch_a, "sibling-a", reuse=True)
    verify_policy(caller, keep, sibling_b, "double-b", b)
    verify_policy(caller, branch_a, sibling_a, "double-a", a)
    reports = [miss_a, miss_b, hit_b, hit_a, sibling_b, sibling_a]
    for report in reports:
        read_policy(source, commands, caller, report)
    replicas = []
    for label, report, snapshot in (("a", sibling_a, a), ("b", sibling_b, b)):
        replica = story / "offline" / (label + ".dml")
        root_id = d.ObjectId.from_hex(report["commit"])
        with d.Repository(replica, create=True):
            pass
        transfer.import_commit(replica, transfer.export_commit(caller, commit=root_id))
        assert normal.typed(replica, root_id) == normal.typed(caller, root_id)
        read_policy(source, commands, replica, report)
        another = policy(
            source, commands, replica, root_id, "replica-" + label, reuse=True
        )
        verify_policy(replica, root_id, another, "double-" + label, snapshot)
        read_policy(source, commands, replica, another)
        replicas.append(another)
    roots = [d.ObjectId.from_hex(row["commit"]) for row in reports]
    population = native_population(
        caller, roots + [common, d.ObjectId.from_hex(initial["sentinel"])]
    )
    batch_attempts = {producer.attempt_id, a.attempt_id, b.attempt_id}
    assert len(population["attempts"]) == 4 and batch_attempts <= set(
        population["attempts"]
    )
    assert all(len(versions) == 2 for versions in population["attempts"].values())
    assert len(population["requests"]) == 8
    assert {recorded1.request_id, *(row["request_id"] for row in reports)} <= set(
        population["requests"]
    )
    assert all(len(versions) == 1 for versions in population["requests"].values())
    census_offline(fixture, story / "offline-census-three", jobs, census3)
    fixed = {
        "main": initial["base"],
        "sentinel": initial["sentinel"],
        "intent-default": initial["commit"],
        "double-basis": str(basis.commit),
        "selection-double-a": str(chosen_a),
        "default-b": str(default_b),
        "selection-double-b": str(common),
        "keep-b": str(keep),
        "default-a": str(branch_a),
        recorded1.ref: str(recorded1.commit),
        "request-" + recorded1.request_id: str(recorded1.commit),
    }
    for report in reports:
        label = report["decision_name"][len("decision-") :]
        fixed[report["decision_name"]] = report["decision_commit"]
        fixed["submission-" + label] = fixed["request-" + report["request_id"]] = (
            report["request_commit"]
        )
        if report["association"] is not None:
            fixed["reuse-" + label] = report["commit"]
    for trial in (first, second, third):
        for phase in trial["packets"]:
            fixed[trial["label"] + "-" + phase["phase"]] = phase["commit"]
    with d.Repository(caller) as repository, repository.read() as tx:
        assert all(str(tx.get_ref(name)) == value for name, value in fixed.items())
        for name in ("work", *("attempt-" + aid for aid in batch_attempts)):
            try:
                tx.get_ref(name)
            except d.NotFoundError:
                pass
            else:
                raise AssertionError("copied B operational ref")
    (story / "summary.json").write_text(
        json.dumps(
            dict(
                actual_installed_implementation_selection=True,
                jobs=3,
                phase_packets=9,
                endpoint_stopped=True,
                trials=[first, second, third],
                reports=reports,
                replicas=replicas,
                population=population,
                initial=initial,
                definition_b=defined_b,
                definition_a=defined_a,
                selections=[selection_a, selection_b],
                fixed_refs=fixed,
                commands=commands,
                original_evidence_unavailable=True,
                normal_ephemeral_final_B=True,
            ),
            indent=2,
        )
    )
    print(
        json.dumps(
            dict(
                actual_installed_implementation_selection=True,
                jobs=3,
                phase_packets=9,
                endpoint_stopped=True,
            )
        )
    )


if __name__ == "__main__":
    action, root, story = sys.argv[1:]
    assert action in ("init", "run")
    (initialize if action == "init" else run)(Path(root), Path(story))
