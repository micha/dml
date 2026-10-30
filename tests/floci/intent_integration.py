"""Mandatory current-installed FOUR-job/TWELVE-phase defaults/override gate.

Explicit init while service OFFLINE, then reviewed private fixture start/run only.
Never default-started/packaged. No private computational hook or fifth policy job.
"""

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import uuid

import daggerml as d
from daggerml import exchange as ex, floci as f, transfer
from fixture import Fixture
import composed_integration as composed
import integration as normal
from retained_integration import prove_profile
from reuse_integration import CommandEvidence, run_fresh, service_census
from selection_integration import (
    external_census,
    census_offline,
    verify_choice,
    capture_headers,
    attempt_population,
    tree,
    nested,
)

ROOT = Path(__file__).resolve().parents[2]
SLOT = "selected-double"
OFFLINE = """import importlib.abc,runpy,sys
from pathlib import Path
families=('http','urllib','requests','httpx','aiohttp','boto3','botocore','docker','daggerml.floci')
def blocked(name):return any(name==family or name.startswith(family+'.') or family=='daggerml.floci' and name.startswith(family) for family in families)
assert not any(blocked(name) for name in sys.modules)
class NoService(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if blocked(fullname):raise AssertionError('offline policy cannot import service runtime')
sys.meta_path.insert(0,NoService())
def no_spawn(event,args):
 if event in ('subprocess.Popen','os.posix_spawn','os.fork','os.forkpty','os.exec','os.system'):raise AssertionError('offline policy cannot spawn')
sys.addaudithook(no_spawn)
sys.argv=sys.argv[1:]
sys.path.insert(0,str(Path(sys.argv[0]).resolve().parent))
try:runpy.run_path(sys.argv[0],run_name='__main__')
except SystemExit as error:assert error.code==0
assert not any(blocked(name) for name in sys.modules)
"""


def invoke(source, evidence, mode, caller, commit, *arguments):
    return run_fresh(
        [
            sys.executable,
            "-B",
            "-c",
            OFFLINE,
            str(source),
            mode,
            str(caller),
            str(commit),
            *map(str, arguments),
        ],
        evidence,
    )


def policy(source, evidence, caller, commit, label, *, override="default", reuse=False):
    return invoke(
        source,
        evidence,
        "request",
        caller,
        commit,
        "double-intent",
        "double-binding",
        "double-inputs",
        SLOT,
        "decision-" + label,
        override,
        "decision-" + label,
        "submission-" + label,
        *(("--reuse-ref", "reuse-" + label) if reuse else ()),
    )


def native_population(caller, roots):
    records = {}
    for root in roots:
        records.update(normal.typed(caller, root))
    found = {"requests": {}, "attempts": {}}
    with d.Repository(caller) as repository, repository.read() as tx:
        for kind, oid in records:
            if kind != "dag":
                continue
            description = tx.get_dag(oid)
            if "role" not in description.bindings:
                continue
            node = tx.get_node(description.bindings["role"])
            if not isinstance(node, d.LiteralNode):
                continue
            role = tx.get_datum(node.datum)
            family = (
                "requests"
                if role == d.Datum.string("local-request-v1")
                else "attempts" if role == d.Datum.string("local-attempt-v1") else None
            )
            if family:
                root_node = tx.get_node(description.root)
                assert isinstance(root_node, d.LiteralNode)
                occurrence = tx.get_datum(root_node.datum)
                assert occurrence.kind == "string"
                found[family].setdefault(occurrence.value, set()).add(str(oid))
    return {
        family: {key: sorted(values) for key, values in rows.items()}
        for family, rows in found.items()
    }


def verify_definition(caller, commit, definition, default):
    with d.Repository(caller) as repository, repository.read() as tx:
        assert tree(tx, commit)["double-intent"] == definition
        description = tx.get_dag(definition)
        assert set(description.bindings) == {"role", "intent", "default"}
        assert description.root == description.bindings["intent"]
        for name, value in (
            ("role", d.Datum.string("example-intent-default-v1")),
            ("intent", d.Datum.uri("urn:example:double")),
            ("default", d.Datum.string(default)),
        ):
            node = tx.get_node(description.bindings[name])
            assert isinstance(node, d.LiteralNode)
            assert tx.get_datum(node.datum) == value


def verify_policy(caller, basis, report, reason, selected=None):
    cdec, dag, cq, q, final = (
        d.ObjectId.from_hex(report[name])
        for name in (
            "decision_commit",
            "decision",
            "request_commit",
            "request",
            "commit",
        )
    )
    with d.Repository(caller) as repository, repository.read() as tx:
        assert tx.get_commit(cdec).parents == (basis,)
        entries = tree(tx, basis)
        entries[report["decision_name"]] = dag
        assert tree(tx, cdec) == entries
        description = tx.get_dag(dag)
        required = {
            "role",
            "intent-definition",
            "binding",
            "inputs",
            "intent-name",
            "binding-name",
            "inputs-name",
            "selection-slot",
            "override",
            "action",
            "reason",
        }
        assert set(description.bindings) == required | (
            {"selection"} if selected else set()
        )
        assert description.root == tx.lookup_node(dag, "intent-definition")
        for name, value in (
            ("role", "example-request-policy-decision-v1"),
            ("reason", reason),
            ("override", report["override"]),
            ("action", "reuse-selected" if selected else "execute-fresh"),
            ("intent-name", "double-intent"),
            ("binding-name", "double-binding"),
            ("inputs-name", "double-inputs"),
            ("selection-slot", SLOT),
        ):
            assert tx.get_datum(
                tx.get_node(tx.lookup_node(dag, name)).datum
            ) == d.Datum.string(value)
        definition = tx.get_tree(tx.get_commit(basis).tree)["double-intent"]
        assert (
            nested(tx, dag, "intent-definition")
            == definition
            == d.ObjectId.from_hex(report["definition"])
        )
        assert nested(tx, dag, "binding") == entries["double-binding"]
        assert nested(tx, dag, "inputs") == entries["double-inputs"]
        assert tx.get_commit(cq).parents == (cdec,)
        entries = tree(tx, cdec)
        assert "request-" + report["request_id"] not in entries
        entries["request-" + report["request_id"]] = q
        assert tree(tx, cq) == entries
        assert q != (None if selected is None else selected.request)
        if selected:
            assert nested(tx, dag, "selection") == tree(tx, basis)[SLOT]
            assert report["attempt"] == str(selected.completion.final_attempt)
            assert report["result"] == str(selected.result)
            w = d.ObjectId.from_hex(report["association"])
            description = tx.get_dag(w)
            assert set(description.bindings) == {"role", "request", "attempt", "result"}
            assert tx.get_datum(
                tx.get_node(description.bindings["role"]).datum
            ) == d.Datum.string("example-explicit-reuse-v1")
            assert description.root == tx.lookup_node(w, "result")
            assert nested(tx, w, "request") == q
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
            assert "selection" not in tx.get_dag(dag).bindings
    assert report["reason"] == reason
    assert attempt_population(caller, final) == attempt_population(caller, basis)
    return final


def read_policy(source, evidence, caller, report):
    cq = d.ObjectId.from_hex(report["request_commit"])
    root = d.ObjectId.from_hex(report["commit"])
    before, physical = (
        normal.typed(caller, root),
        (Path(caller) / "data.mdb").read_bytes(),
    )
    arguments = [report["request"], report["decision_name"]]
    if report["association"] is not None:
        arguments += ["--satisfaction-commit", report["commit"]]
    inspected = invoke(source, evidence, "inspect-request", caller, cq, *arguments)
    for name in (
        "decision_commit",
        "decision",
        "decision_name",
        "base",
        "definition",
        "default",
        "intent",
        "override",
        "action",
        "reason",
        "binding",
        "inputs",
        "selection",
        "attempt",
        "result",
    ):
        assert inspected[name] == report[name], (
            "pinned reader captured claim differs: " + name
        )
    assert normal.typed(caller, root) == before
    assert (Path(caller) / "data.mdb").read_bytes() == physical
    return inspected


def prepare_policy(caller, story, label, report):
    # Separate adapter client, NOT offline policy process; owns actual supplied Q.
    return ex.prepare_exchange(
        caller,
        commit=d.ObjectId.from_hex(report["request_commit"]),
        request=d.ObjectId.from_hex(report["request"]),
        binding_name="double-binding",
        inputs_name="double-inputs",
        intent_uri=report["intent"],
        worker_ref="work",
        workspace=story / (label + "-input"),
    )


def selection_action(
    source, evidence, mode, caller, commit, expected_file, packet, ref
):
    return run_fresh(
        [
            sys.executable,
            "-B",
            "-c",
            OFFLINE,
            str(source),
            mode,
            str(caller),
            str(commit),
            SLOT,
            "double-binding",
            "double-inputs",
            "urn:example:double",
            str(expected_file),
            str(packet),
            ref,
        ],
        evidence,
    )


def hide_original(trial, story):
    for path in (
        Path(trial["packets"][-1]["packet"]),
        Path(trial["saved"]),
        story / (trial["label"] + "-input.offline"),
    ):
        assert path.exists()
        path.rename(path.with_name(path.name + ".unavailable"))
        assert not path.exists()


def initialize(root, story):
    fixture = Fixture(root)
    assert not fixture.state, "initial definition requires NEW service-OFFLINE fixture"
    story = Path(story).resolve()
    story.mkdir()
    offline = story / "offline"
    offline.mkdir()
    for name in ("intent_defaults.py", "reuse_selection.py", "explicit_reuse.py"):
        shutil.copyfile(ROOT / "examples" / name, offline / name)
    artifacts = json.loads((fixture.root / "artifacts.json").read_bytes())
    scope = uuid.uuid4().hex
    add_gate, double_gate = "intent-add/" + scope, "intent-double/" + scope
    caller, base, sentinel = composed.setup(story, artifacts, add_gate)
    commands = CommandEvidence(story / "initial-commands.json")
    defined = invoke(
        offline / "intent_defaults.py",
        commands,
        "define",
        caller,
        base,
        "double-intent",
        "urn:example:double",
        "reuse-by-default",
        "intent-default",
    )
    commit = d.ObjectId.from_hex(defined["commit"])
    verify_definition(
        caller, commit, d.ObjectId.from_hex(defined["definition"]), "reuse-by-default"
    )
    assert attempt_population(caller, commit) == attempt_population(caller, base)
    with d.Repository(caller) as repository, repository.read() as tx:
        assert tx.get_commit(commit).parents == (base,)
        entries = tree(tx, base)
        entries["double-intent"] = d.ObjectId.from_hex(defined["definition"])
        assert tree(tx, commit) == entries
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
    caller, base, sentinel = (
        Path(initial["caller"]),
        d.ObjectId.from_hex(initial["commit"]),
        d.ObjectId.from_hex(initial["sentinel"]),
    )
    artifacts = initial["artifacts"]
    assert artifacts == json.loads((fixture.root / "artifacts.json").read_bytes())
    site = Path(d.__file__).resolve().parent.parent
    import hashlib

    for row in artifacts:
        assert (
            hashlib.sha256((site / row["file"]).read_bytes()).hexdigest()
            == row["sha256"]
        )
    remote = f.FlociRemote(
        "http://floci:4566",
        "dml-local",
        "iteration15/scope",
        "local",
        "installed:1",
        fixture.state["image"],
        "/opt/dml/bin/python",
    )
    source, selection_source = (
        story / "offline/intent_defaults.py",
        story / "offline/reuse_selection.py",
    )
    commands = CommandEvidence(story / "fresh-commands.json")
    expected1, recorded1 = composed.request(
        caller, base, story, "add", "add-binding", "add-inputs"
    )
    first = composed.run_step(
        fixture, caller, story, "add", expected1, remote, initial["add_gate"], artifacts
    )
    basis = composed.app.consumer_basis(
        caller,
        producer_packet=first["packets"][-1]["packet"],
        producer_expected=expected1,
        remote=remote,
        gate=initial["double_gate"],
        artifacts=json.dumps(artifacts).encode(),
    )
    # Extra finite stop after producer makes absence-driven pending-Q authoring
    # genuinely service-OFFLINE too; terminal/ALLclient/namespace proof is unchanged.
    jobs = [first["job_id"]]
    external_census(fixture, jobs)
    fixture.stop()
    census1 = service_census(fixture.root / "service-data", jobs)
    miss = policy(source, commands, caller, basis.commit, "miss")
    verify_policy(caller, basis.commit, miss, "default-no-selection")
    read_policy(source, commands, caller, miss)
    census_offline(fixture, story / "offline-census-one", jobs, census1)
    fixture.resume()
    prove_profile(fixture)
    expected2 = prepare_policy(caller, story, "double", miss)
    second = composed.run_step(
        fixture,
        caller,
        story,
        "double",
        expected2,
        remote,
        initial["double_gate"],
        artifacts,
    )
    old = ex.read_observation(second["packets"][-1]["packet"], expected=expected2)
    assert old.completion.outcome == "success"
    with d.Repository(caller) as repository, repository.read() as tx:
        assert SLOT not in tree(tx, old.commit)  # First fresh F STILL no adoption.
    jobs.append(second["job_id"])
    external_census(fixture, jobs)
    fixture.stop()
    census2 = service_census(fixture.root / "service-data-1", jobs)
    saved_old = story / "offline/independent-old.json"
    shutil.copyfile(Path(second["saved"]) / "expected.json", saved_old)
    headers = capture_headers(saved_old, second["packets"][-1]["packet"])
    chosen_report = selection_action(
        selection_source,
        commands,
        "select",
        caller,
        old.commit,
        saved_old,
        second["packets"][-1]["packet"],
        "selection-old",
    )
    chosen, s0, v0 = verify_choice(caller, chosen_report, expected2, old, headers)
    hide_original(second, story)
    saved_old.rename(saved_old.with_name(saved_old.name + ".unavailable"))
    hit_old = policy(source, commands, caller, chosen, "hit-old", reuse=True)
    hit_old_commit = verify_policy(caller, chosen, hit_old, "default-selection", old)
    read_policy(source, commands, caller, hit_old)
    fresh_report = policy(
        source, commands, caller, hit_old_commit, "fresh", override="fresh"
    )
    verify_policy(caller, hit_old_commit, fresh_report, "override-fresh")
    read_policy(source, commands, caller, fresh_report)
    retained = normal.typed(caller, d.ObjectId.from_hex(fresh_report["commit"]))
    census_offline(fixture, story / "offline-census-two", jobs, census2)
    fixture.resume()
    prove_profile(fixture)
    expected3 = prepare_policy(caller, story, "fresh-double", fresh_report)
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
        initial["double_gate"],
        artifacts,
    )
    fresh = ex.read_observation(third["packets"][-1]["packet"], expected=expected3)
    assert fresh.result == old.result and fresh.attempt_id != old.attempt_id
    for phase in third["packets"]:
        commit = d.ObjectId.from_hex(phase["commit"])
        actual = normal.typed(caller, commit)
        assert all(actual[key] == raw for key, raw in retained.items())
        with d.Repository(caller) as repository, repository.read() as tx:
            assert tree(tx, commit)[SLOT] == s0
            assert (
                nested(tx, d.ObjectId.from_hex(hit_old["association"]), "attempt")
                == old.completion.final_attempt
            )
    jobs.append(third["job_id"])
    external_census(fixture, jobs)
    fixture.stop()
    census3 = service_census(fixture.root / "service-data-2", jobs)
    saved_fresh = story / "offline/independent-fresh.json"
    shutil.copyfile(Path(third["saved"]) / "expected.json", saved_fresh)
    headers = capture_headers(saved_fresh, third["packets"][-1]["packet"])
    adopted_report = selection_action(
        selection_source,
        commands,
        "adopt",
        caller,
        fresh.commit,
        saved_fresh,
        third["packets"][-1]["packet"],
        "adopt-fresh",
    )
    adopted, s1, v1 = verify_choice(caller, adopted_report, expected3, fresh, headers)
    hide_original(third, story)
    saved_fresh.rename(saved_fresh.with_name(saved_fresh.name + ".unavailable"))
    hit_fresh = policy(source, commands, caller, adopted, "hit-fresh", reuse=True)
    branch = verify_policy(caller, adopted, hit_fresh, "default-selection", fresh)
    read_policy(source, commands, caller, hit_fresh)
    with d.Repository(caller) as repository, repository.write() as tx:
        keep = tx.put_commit(tx.get_commit(branch).tree, parents=(branch,))
        tx.create_ref("keep-default", keep)
    execute_definition = invoke(
        source,
        commands,
        "define",
        caller,
        branch,
        "double-intent",
        "urn:example:double",
        "execute-by-default",
        "execute-default",
        "--update",
    )
    execute_branch = d.ObjectId.from_hex(execute_definition["commit"])
    verify_definition(
        caller,
        execute_branch,
        d.ObjectId.from_hex(execute_definition["definition"]),
        "execute-by-default",
    )
    verify_definition(
        caller,
        keep,
        d.ObjectId.from_hex(initial["definition"]["definition"]),
        "reuse-by-default",
    )
    with d.Repository(caller) as repository, repository.read() as tx:
        assert (
            tx.get_commit(keep).parents
            == tx.get_commit(execute_branch).parents
            == (branch,)
        )
        old_entries, new_entries = tree(tx, keep), tree(tx, execute_branch)
        assert old_entries[SLOT] == new_entries[SLOT] == s1
        old_entries.pop("double-intent")
        new_entries.pop("double-intent")
        assert old_entries == new_entries
    keep_hit = policy(source, commands, caller, keep, "keep-hit", reuse=True)
    verify_policy(caller, keep, keep_hit, "default-selection", fresh)
    read_policy(source, commands, caller, keep_hit)
    execute_report = policy(source, commands, caller, execute_branch, "execute")
    verify_policy(caller, execute_branch, execute_report, "default-execution")
    read_policy(source, commands, caller, execute_report)
    census_offline(fixture, story / "offline-census-three", jobs, census3)
    retained4 = normal.typed(caller, d.ObjectId.from_hex(execute_report["commit"]))
    fixture.resume()
    prove_profile(fixture)
    expected4 = prepare_policy(caller, story, "execute-double", execute_report)
    assert (expected4.intent_uri, expected4.binding, expected4.inputs) == (
        expected2.intent_uri,
        expected2.binding,
        expected2.inputs,
    )
    fourth = composed.run_step(
        fixture,
        caller,
        story,
        "execute-double",
        expected4,
        remote,
        initial["double_gate"],
        artifacts,
    )
    executed = ex.read_observation(fourth["packets"][-1]["packet"], expected=expected4)
    assert len({old.attempt_id, fresh.attempt_id, executed.attempt_id}) == 3
    assert executed.result == fresh.result == old.result
    for phase in fourth["packets"]:
        commit = d.ObjectId.from_hex(phase["commit"])
        actual = normal.typed(caller, commit)
        assert all(actual[key] == raw for key, raw in retained4.items())
        with d.Repository(caller) as repository, repository.read() as tx:
            assert tree(tx, commit)[SLOT] == s1
            assert tree(tx, commit)["double-intent"] == d.ObjectId.from_hex(
                execute_definition["definition"]
            )
    jobs.append(fourth["job_id"])
    external_census(fixture, jobs)
    fixture.stop()
    census4 = service_census(fixture.root / "service-data-3", jobs)
    override_report = policy(
        source,
        commands,
        caller,
        executed.commit,
        "selected-override",
        override="reuse-selected",
        reuse=True,
    )
    verify_policy(
        caller, executed.commit, override_report, "override-selected-reuse", fresh
    )
    # None of the pending/reuse/definition/branch readers can use ORIGINAL input,
    # packet/expected paths or original B even for the other retained trials.
    first_attempt = ex.read_observation(
        first["packets"][-1]["packet"], expected=expected1
    ).attempt_id
    hide_original(first, story)
    hide_original(fourth, story)
    read_policy(source, commands, caller, override_report)
    assert override_report["attempt"] != str(executed.completion.final_attempt)
    for report in (miss, hit_old, fresh_report, hit_fresh, keep_hit, execute_report):
        read_policy(
            source, commands, caller, report
        )  # Pinned historical reasons unchanged.
    replicas = []
    for label, report, override in (
        ("keep", keep_hit, "default"),
        ("execute", override_report, "reuse-selected"),
    ):
        root_id = d.ObjectId.from_hex(report["commit"])
        replica = story / "offline" / (label + ".dml")
        with d.Repository(replica, create=True):
            pass
        transfer.import_commit(replica, transfer.export_commit(caller, commit=root_id))
        assert normal.typed(replica, root_id) == normal.typed(caller, root_id)
        read_policy(source, commands, replica, report)
        another = policy(
            source,
            commands,
            replica,
            root_id,
            "replica-" + label,
            override=override,
            reuse=True,
        )
        verify_policy(
            replica,
            root_id,
            another,
            "default-selection" if override == "default" else "override-selected-reuse",
            fresh,
        )
        read_policy(source, commands, replica, another)
        replicas.append(another)
    reports = [
        miss,
        hit_old,
        fresh_report,
        hit_fresh,
        keep_hit,
        execute_report,
        override_report,
    ]
    roots = [d.ObjectId.from_hex(report["commit"]) for report in reports] + [
        executed.commit,
        sentinel,
    ]
    population = native_population(caller, roots)
    batch_attempts = {
        first_attempt,
        old.attempt_id,
        fresh.attempt_id,
        executed.attempt_id,
    }
    assert (
        len(population["attempts"]) == 5
    )  # genuine host-prior + FOUR actual Batch trials.
    assert batch_attempts <= set(population["attempts"])
    assert all(len(versions) == 2 for versions in population["attempts"].values())
    expected_requests = {report["request_id"] for report in reports} | {
        recorded1.request_id
    }
    assert len(population["requests"]) == 9 and expected_requests <= set(
        population["requests"]
    )
    assert all(len(versions) == 1 for versions in population["requests"].values())
    census_offline(fixture, story / "offline-census-four", jobs, census4)
    fixed_refs = {
        "main": d.ObjectId.from_hex(initial["base"]),
        "sentinel": sentinel,
        "intent-default": base,
        "double-basis": basis.commit,
        "selection-old": chosen,
        "adopt-fresh": adopted,
        "keep-default": keep,
        "execute-default": execute_branch,
        recorded1.ref: recorded1.commit,
        "request-" + recorded1.request_id: recorded1.commit,
    }
    for report in reports:
        label = report["decision_name"][len("decision-") :]
        fixed_refs[report["decision_name"]] = d.ObjectId.from_hex(
            report["decision_commit"]
        )
        fixed_refs["submission-" + label] = fixed_refs[
            "request-" + report["request_id"]
        ] = d.ObjectId.from_hex(report["request_commit"])
        if report["association"] is not None:
            fixed_refs["reuse-" + label] = d.ObjectId.from_hex(report["commit"])
    for trial in (first, second, third, fourth):
        for phase in trial["packets"]:
            fixed_refs[trial["label"] + "-" + phase["phase"]] = d.ObjectId.from_hex(
                phase["commit"]
            )
    with d.Repository(caller) as repository, repository.read() as tx:
        assert all(tx.get_ref(name) == target for name, target in fixed_refs.items())
        for name in ("work", *("attempt-" + aid for aid in batch_attempts)):
            try:
                tx.get_ref(name)
            except d.NotFoundError:
                pass
            else:
                raise AssertionError("copied B operational ref")
    result = dict(
        actual_installed_defaults=True,
        jobs=4,
        phase_packets=12,
        endpoint_stopped=True,
        trials=[first, second, third, fourth],
        reports=reports,
        selection=chosen_report,
        adoption=adopted_report,
        definition=initial["definition"],
        execute_definition=execute_definition,
        keep=str(keep),
        replicas=replicas,
        population=population,
        fixed_refs={name: str(target) for name, target in fixed_refs.items()},
        commands=commands,
        original_evidence_unavailable=True,
        normal_ephemeral_final_B=True,
    )
    (story / "summary.json").write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            dict(
                actual_installed_defaults=True,
                jobs=4,
                phase_packets=12,
                endpoint_stopped=True,
            )
        )
    )


if __name__ == "__main__":
    action, root, story = sys.argv[1:]
    assert action in ("init", "run")
    (initialize if action == "init" else run)(Path(root), Path(story))
