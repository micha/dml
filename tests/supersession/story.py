"""Finite installed FOUR-Q/TWO-local-attempt acceptance; never default-started.

Run with installed Python, env -u PYTHONPATH, and fresh existing parent root.
Copies example-local policies; fresh clients, public operations, no service fixture.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

# Copied beside this controller by run(); library always comes from installed DML.
if __name__ == "__main__" and sys.argv[1] != "run":
    sys.path.insert(0, str(Path(sys.argv[2]).resolve() / "policy"))

import daggerml as d
from daggerml import exchange as ex, local, transfer

SOURCE = b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.read() as t:
 n=t.get_datum(t.get_node(t.lookup_node(c.inputs,'n')).datum)
 assert n.kind=='i64'
 answer=2*n.value
with d.Repository(c.repository_path) as r,r.write() as t:
 node=t.put_literal(t.put_datum(answer))
 publish_result(t,c,t.put_dag(root=node,bindings={'result':node}))
"""
BUGGY = SOURCE.replace(b"answer=2*n.value", b"answer=max(0,2*n.value)")
OFFLINE = """import runpy,sys
from pathlib import Path
families=('http','urllib','requests','httpx','aiohttp','boto3','botocore','docker','daggerml.floci')
def blocked(name):
 if name in ('urllib','urllib.parse'):return False
 return any(name==f or name.startswith(f+'.') or f=='daggerml.floci' and name.startswith(f) for f in families)
assert not any(blocked(n) for n in sys.modules)
class NoTransport:
 def find_spec(self,fullname,path=None,target=None):
  if blocked(fullname):raise AssertionError('offline client cannot import transport')
sys.meta_path.insert(0,NoTransport())
def no_spawn(event,args):
 if event in ('subprocess.Popen','os.posix_spawn','os.fork','os.forkpty','os.exec','os.system'):raise AssertionError('offline client cannot spawn')
sys.addaudithook(no_spawn)
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
assert not any(blocked(n) for n in sys.modules)
"""


def oid(value):
    return d.ObjectId.from_hex(value)


def tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def lit(tx, value):
    return tx.put_literal(tx.put_datum(value))


def link(tx, dag, name):
    node = tx.get_node(tx.lookup_node(dag, name))
    assert isinstance(node, d.SubDAGNode)
    return node.dag


def value(tx, dag, name=None):
    node = tx.get_node(
        tx.get_dag(dag).root if name is None else tx.lookup_node(dag, name)
    )
    assert isinstance(node, d.LiteralNode)
    return tx.get_datum(node.datum)


def rows(path, roots):
    """Independent public breadth-first typed closure, ALL ordered parents/composites."""
    found, pending = {}, [("commit", c) for c in roots]
    with d.Repository(path) as repo, repo.read() as tx:
        while pending:
            kind, selected = pending.pop(0)
            key = (kind, selected)
            if key in found:
                continue
            found[key] = tx.get_record(kind, selected)
            if kind == "commit":
                got = tx.get_commit(selected)
                pending += [("tree", got.tree)] + [("commit", c) for c in got.parents]
            elif kind == "tree":
                pending += [
                    ("dag", dag) for dag in dict(tx.get_tree(selected)).values()
                ]
            elif kind == "dag":
                got = tx.get_dag(selected)
                pending += [("node", n) for n in (got.root, *got.bindings.values())]
            elif kind == "node":
                got = tx.get_node(selected)
                pending += (
                    [("datum", got.datum)]
                    if isinstance(got, d.LiteralNode)
                    else [("dag", got.dag)]
                )
            else:
                got = tx.get_datum(selected)
                if got.kind in ("list", "set"):
                    pending += [("datum", n) for n in got.value]
                elif got.kind == "map":
                    pending += [("datum", n) for pair in got.value for n in pair]
    return found


def save(root, state):
    (root / "state.json").write_text(json.dumps(state, indent=2))


def init(root, app):
    path = root / "caller.dml"
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        entries = {
            "binding-a": local.put_local_binding(
                tx, source=BUGGY, interpreter=sys.executable, timeout_ms=10000
            ),
            "binding-b": local.put_local_binding(
                tx, source=SOURCE, interpreter=sys.executable, timeout_ms=10000
            ),
        }
        node = lit(tx, -3)
        entries["inputs"] = tx.put_dag(root=node, bindings={"n": node})
        composite = tx.put_datum(
            d.Datum.list([tx.put_datum(d.Datum.list([tx.put_datum("composite-only")]))])
        )
        side = tx.put_commit(
            tx.put_tree({"side": tx.put_dag(root=tx.put_literal(composite))})
        )
        first = tx.put_commit(tx.put_tree(entries), parents=(side,))
        tx.create_ref("main", first)
    definition = app.policy.define(
        path,
        commit=first,
        intent_name="intent",
        intent_uri="urn:example:double",
        default="reuse-by-default",
        implementations=(
            ("a", "binding-a", "selected-a"),
            ("b", "binding-b", "selected-b"),
        ),
        default_implementation="a",
        ref="definition",
    )
    return {
        "definition": str(definition.commit),
        "path": str(path),
        "requests": {},
        "runs": {},
    }


def request(path, app, state, label, basis, implementation="default", reuse=False):
    got = app.policy.record_policy_request(
        path,
        commit=oid(basis),
        intent_name="intent",
        inputs_name="inputs",
        decision_name="decision-" + label,
        implementation_override=implementation,
        decision_ref="decision-" + label,
        submission_ref="submission-" + label,
        reuse_ref="reuse-" + label if reuse else None,
    )
    assert got.decision.implementation_override == implementation
    assert got.decision.implementation_reason == (
        "default-implementation"
        if implementation == "default"
        else "explicit-implementation"
    )
    assert got.decision.implementation.label == ("b" if label == "b" else "a")
    assert got.decision.reason == (
        "default-selection" if reuse else "default-no-selection"
    )
    assert (got.reused is not None) == reuse
    item = dict(
        commit=str(got.recorded.commit),
        request=str(got.recorded.request),
        decision=got.decision.name,
        base=basis,
        binding=str(got.decision.binding),
        inputs=str(got.decision.inputs),
        implementation=got.decision.implementation.label,
        implementation_override=implementation,
        reason=got.decision.reason,
        satisfaction=None if got.reused is None else str(got.reused.commit),
    )
    if reuse:
        selected = app.policy.selection.inspect(
            path, commit=oid(basis), slot="selected-a"
        )
        assert (
            got.reused.attempt == selected.attempt
            and got.reused.result == selected.result
        )
        assert got.recorded.request != selected.request
        with d.Repository(path) as repo, repo.read() as tx:
            assert set(tx.get_dag(got.reused.dag).bindings) == {
                "role",
                "request",
                "attempt",
                "result",
            }
            assert link(tx, got.reused.dag, "request") == got.recorded.request
            assert link(tx, selected.attempt, "request") == selected.request
        item.update(attempt=str(selected.attempt), result=str(selected.result))
    state["requests"][label] = item
    return item


def execute(root, path, state, label):
    item = state["requests"][label]
    workspace, packet = root / ("workspace-" + label), root / ("packet-" + label)
    spec = ex.prepare_exchange(
        path,
        commit=oid(item["commit"]),
        request=oid(item["request"]),
        binding_name="binding-" + label,
        inputs_name="inputs",
        intent_uri="urn:example:double",
        worker_ref="work",
        workspace=workspace,
    )
    expected_file = root / ("expected-" + label + ".json")
    ex.save_exchange_handle(expected_file, ex.ExchangeHandle(workspace, spec))
    # Test-controller observation of actual direct children, not a runtime hook.
    spawning = subprocess.Popen
    children = []

    def spawn(*a, **k):
        child = spawning(*a, **k)
        children.append(child)
        return child

    subprocess.Popen = spawn
    try:
        run = ex.execute_exchange(workspace)
    finally:
        subprocess.Popen = spawning
    assert len(children) == 1 and all(c.poll() == 0 for c in children)
    assert run.outcome == "success" and run.cleanup == "ok"
    # Only AFTER actual synchronous child reaping: completed PUBLIC packet authority.
    observed = ex.observe_exchange(ex.ExchangeHandle(workspace, spec), packet=packet)
    assert observed.phase == "completion" and observed.lifecycle == "done"
    received = ex.receive_observation(
        path, packet=packet, expected=spec, ref="received-" + label
    )
    assert (
        received.request == oid(item["request"])
        and received.completion.final_attempt == run.final_attempt
    )
    assert (
        received.completion.outcome == "success" and received.completion.cleanup == "ok"
    )
    with d.Repository(path) as repo, repo.read() as tx:
        actual = value(tx, received.result)
        assert (actual.kind, actual.value) == ("i64", 0 if label == "a" else -6)
        assert link(tx, run.final_attempt, "request") == oid(item["request"])
        assert value(tx, link(tx, oid(item["request"]), "inputs"), "n").value == -3
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        publication = tx.get_ref("attempt-" + run.attempt_id)
        assert tx.get_commit(received.commit).parents == (
            received.pre_dispatch,
            publication,
        )
        assert tx.get_commit(publication).parents == (received.pre_dispatch,)
    # Independent entire typed native B/A closure equality including parent order.
    assert rows(path, (received.commit,)) == rows(
        workspace / "worker.dml", (run.final_commit,)
    )
    state["runs"][label] = dict(
        commit=str(received.commit),
        attempt=str(run.final_attempt),
        result=str(run.result),
        request=str(received.request),
        attempt_id=run.attempt_id,
        pre_dispatch=str(received.pre_dispatch),
        child_pid=children[0].pid,
        child_exit=children[0].returncode,
        child_reaped=True,
        packet=str(packet),
        expected=str(expected_file),
        workspace=str(workspace),
    )


def evidence(root, path, app, state):
    selected = app.policy.selection.inspect(
        path, commit=oid(state["common"]), slot="selected-a"
    )
    assert selected.attempt == oid(state["runs"]["a"]["attempt"])
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, oid(state["common"]))
        assert (
            selected.binding == entries["binding-a"]
            and selected.inputs == entries["inputs"]
        )
        assert (
            value(tx, selected.inputs, "n").kind,
            value(tx, selected.inputs, "n").value,
        ) == ("i64", -3)
        assert (value(tx, selected.result).kind, value(tx, selected.result).value) == (
            "i64",
            0,
        )
        assert link(tx, selected.attempt, "request") == selected.request
        fields = {
            "selected": tx.put_subdag(selected.dag),
            "attempt": tx.put_subdag(selected.attempt),
            "result": tx.put_subdag(selected.result),
            "inputs": tx.put_subdag(selected.inputs),
            "expected": lit(tx, -6),
            "assessment": lit(
                tx,
                "negative-input counterexample; expected value is researcher assertion",
            ),
        }
        entries["evidence-fix"] = tx.put_dag(root=fields["result"], bindings=fields)
        authored = tx.put_commit(tx.put_tree(entries), parents=(oid(state["common"]),))
        tx.create_ref("evidence-fix", authored)
    state["evidence"] = str(authored)


def declare(path, app, state, operational=False):
    basis = state["common"] if operational else state["evidence"]
    if operational:
        with d.Repository(path) as repo, repo.write() as tx:
            entries = tree(tx, oid(basis))
            entries["evidence-op"] = tx.put_dag(
                root=lit(tx, "operational motivation, not measurement or certification")
            )
            authored = tx.put_commit(tx.put_tree(entries), parents=(oid(basis),))
            tx.create_ref("evidence-op", authored)
        basis = str(authored)
    got = app.record_supersession(
        path,
        commit=oid(basis),
        intent_name="intent",
        slot="supersession",
        predecessor_label="a",
        successor_label="b",
        reason="operational-replacement" if operational else "correctness-fix",
        evidence_name="evidence-op" if operational else "evidence-fix",
        ref="operational" if operational else "declared",
    )
    assert (
        app.policy.inspect_definition(
            path, commit=got.commit, intent_name="intent"
        ).default_implementation
        == "a"
    )
    state["operational" if operational else "declared"] = str(got.commit)


def read(path, app, state, label, knowledge):
    item = state["requests"][label]
    before = (path / "data.mdb").read_bytes()
    got = app.inspect_request_context(
        path,
        commit=oid(item["commit"]),
        request=oid(item["request"]),
        decision_name=item["decision"],
        slot="supersession",
        satisfaction_commit=(
            None if item["satisfaction"] is None else oid(item["satisfaction"])
        ),
        knowledge_commit=oid(knowledge),
    )
    assert str(got.decision.base) == item["base"]
    assert str(got.as_known_then.commit) == item["base"]
    historical = (
        "no-recorded-declaration"
        if label in ("a", "old")
        else ("successor" if label == "b" else "predecessor")
    )
    explicit = "successor" if label == "b" else "predecessor"
    assert got.as_known_then.relation == historical
    if historical == "no-recorded-declaration":
        assert got.as_known_then.declaration is None
    else:
        with d.Repository(path) as repo, repo.read() as tx:
            expected_L = tree(tx, oid(state["declared"]))["supersession"]
        assert got.as_known_then.declaration.dag == expected_L
        assert got.as_known_then.declaration.reason == "correctness-fix"
        assert got.as_known_then.declaration.basis == oid(state["evidence"])
        assert got.as_known_then.declaration.commit == oid(item["base"])
    assert got.explicit_knowledge.relation == explicit
    assert str(got.explicit_knowledge.commit) == knowledge
    assert got.decision.binding == oid(item["binding"]) and got.decision.inputs == oid(
        item["inputs"]
    )
    assert (
        got.decision.implementation_override == item["implementation_override"]
        and got.decision.reason == item["reason"]
    )
    assert got.explicit_knowledge.declaration.reason == (
        "operational-replacement"
        if knowledge == state["operational"]
        else "correctness-fix"
    )
    assert (path / "data.mdb").read_bytes() == before
    return dict(
        label=label,
        as_known_then=str(got.as_known_then.commit),
        historical=historical,
        knowledge=knowledge,
        explicit=explicit,
        reason=got.explicit_knowledge.declaration.reason,
        read_only=True,
    )


def finish(root, path, state):
    roots = [oid(state[k]) for k in ("promoted", "operational", "keep")]
    roots += [
        oid(item["satisfaction"] or item["commit"])
        for item in state["requests"].values()
    ]
    all_rows = rows(path, roots)
    requests, attempts = {}, {}
    with d.Repository(path) as repo, repo.read() as tx:
        for kind, selected in all_rows:
            if kind != "dag":
                continue
            description = tx.get_dag(selected)
            if "role" not in description.bindings:
                continue
            role = value(tx, selected, "role").value
            if role == "local-request-v1":
                requests.setdefault(value(tx, selected).value, []).append(str(selected))
            elif role == "local-attempt-v1":
                attempts.setdefault(value(tx, selected).value, []).append(str(selected))
        assert len(requests) == 4 and all(len(v) == 1 for v in requests.values())
        assert len(attempts) == 2 and all(len(v) == 2 for v in attempts.values())
        assert {item["request"] for item in state["requests"].values()} == {
            v[0] for v in requests.values()
        }
        assert "selected-b" not in tree(tx, oid(state["runs"]["b"]["commit"]))
        assert tx.get_commit(oid(state["keep"])).parents == (oid(state["common"]),)
        assert tree(tx, oid(state["keep"])) == tree(tx, oid(state["common"]))
        assert (
            tree(tx, oid(state["promoted"]))["supersession"]
            == tree(tx, oid(state["declared"]))["supersession"]
        )
        for kind, selected, raw in state["old_rows"]:
            assert tx.get_record(kind, oid(selected)) == base64.b64decode(raw)
        for name, selected in state["old_refs"].items():
            assert str(tx.get_ref(name)) == selected
        for label, item in state["requests"].items():
            qid = value(tx, oid(item["request"])).value
            assert tx.get_ref("request-" + qid) == oid(item["commit"])
            assert tx.get_ref("submission-" + label) == oid(item["commit"])
            assert (
                tx.get_ref("decision-" + label)
                == tx.get_commit(oid(item["commit"])).parents[0]
            )
            if item["satisfaction"] is not None:
                assert tx.get_ref("reuse-" + label) == oid(item["satisfaction"])
        initial = tree(tx, oid(state["definition"]))
        assert value(tx, initial["binding-a"], "source").value == BUGGY
        assert value(tx, initial["binding-b"], "source").value == SOURCE
        assert value(tx, initial["binding-a"], "interpreter").value == sys.executable
        assert value(tx, initial["binding-b"], "interpreter").value == sys.executable
        assert value(tx, initial["binding-a"], "timeout-ms").value == 10000
        assert value(tx, initial["binding-b"], "timeout-ms").value == 10000
    return dict(
        requests=requests,
        attempts=attempts,
        normal_Q=4,
        real_local_attempts=2,
        old_records_preserved=len(state["old_rows"]),
        old_refs_preserved=len(state["old_refs"]),
        children_reaped=state["runs"],
    )


def phase(root, mode):
    import implementation_supersession as app

    if mode == "init":
        state = init(root, app)
    else:
        state = json.loads((root / "state.json").read_bytes())
    path = Path(state["path"])
    if mode == "fresh-a":
        request(path, app, state, "a", state["definition"])
    elif mode.startswith("execute-"):
        execute(root, path, state, mode[-1])
    elif mode == "select-a":
        run = state["runs"]["a"]
        got = app.policy.selection.select(
            path,
            commit=oid(run["commit"]),
            slot="selected-a",
            binding_name="binding-a",
            inputs_name="inputs",
            intent_uri="urn:example:double",
            packet=run["packet"],
            expected_file=run["expected"],
            ref="selected-a",
        )
        state["common"] = str(got.commit)
        with d.Repository(path) as repo, repo.write() as tx:
            keep = tx.put_commit(tx.get_commit(got.commit).tree, parents=(got.commit,))
            tx.create_ref("keep", keep)
        state["keep"] = str(keep)
        state["old_rows"] = [
            [kind, str(selected), base64.b64encode(raw).decode()]
            for (kind, selected), raw in rows(path, (got.commit, keep)).items()
        ]
        with d.Repository(path) as repo, repo.read() as tx:
            state["old_refs"] = dict(
                (name, str(tx.get_ref(name)))
                for name in (
                    "main",
                    "definition",
                    "decision-a",
                    "submission-a",
                    "received-a",
                    "selected-a",
                    "keep",
                )
            )
    elif mode == "evidence":
        evidence(root, path, app, state)
    elif mode == "declare":
        declare(path, app, state)
    elif mode == "promote":
        got = app.policy.update_default(
            path,
            commit=oid(state["declared"]),
            intent_name="intent",
            default_implementation="b",
            ref="promoted",
        )
        state["promoted"] = str(got.commit)
        with d.Repository(path) as repo, repo.read() as tx:
            old, new = tree(tx, oid(state["declared"])), tree(tx, got.commit)
            old.pop("intent")
            new.pop("intent")
            assert old == new
    elif mode == "fresh-b":
        request(path, app, state, "b", state["promoted"])
    elif mode == "hide":
        assert all(
            r["child_reaped"] and r["child_exit"] == 0 for r in state["runs"].values()
        )
        for run in state["runs"].values():
            for name in ("packet", "expected", "workspace"):
                original = Path(run[name])
                original.rename(original.with_name(original.name + ".unavailable"))
    elif mode == "reuse-a":
        request(
            path,
            app,
            state,
            "again",
            state["runs"]["b"]["commit"],
            implementation="a",
            reuse=True,
        )
    elif mode == "old-reuse":
        request(path, app, state, "old", state["keep"], reuse=True)
    elif mode == "operational":
        declare(path, app, state, operational=True)
    elif mode == "transfer":
        replica = root / "replica.dml"
        with d.Repository(replica, create=True):
            pass
        for selected in [state["promoted"], state["operational"]] + [
            item["satisfaction"] or item["commit"]
            for item in state["requests"].values()
        ]:
            bundle = transfer.export_commit(path, commit=oid(selected))
            transfer.import_commit(replica, bundle)
            assert transfer.export_commit(replica, commit=oid(selected)) == bundle
        state["replica"] = str(replica)
    elif mode.startswith("read-"):
        label = mode[len("read-") :]
        result = read(path, app, state, label, state["promoted"])
        assert (
            read(Path(state["replica"]), app, state, label, state["promoted"]) == result
        )
        read(Path(state["replica"]), app, state, label, state["operational"])
        print(json.dumps(result))
        return
    elif mode == "finish":
        print(json.dumps(finish(root, path, state)))
        return
    save(root, state)
    print(json.dumps(dict(phase=mode, complete=True)))


def run(root):
    assert "PYTHONPATH" not in os.environ
    assert not root.exists()
    root.mkdir()
    policy = root / "policy"
    policy.mkdir()
    repo = Path(__file__).resolve().parents[2]
    sources = [
        "implementation_supersession.py",
        "implementation_selection.py",
        "reuse_selection.py",
        "explicit_reuse.py",
    ]
    identity = {}
    for name in sources:
        source = repo / "examples" / name
        data = source.read_bytes()
        (policy / name).write_bytes(data)
        identity[name] = hashlib.sha256(data).hexdigest()
    controller = root / "story.py"
    controller.write_bytes(Path(__file__).read_bytes())
    identity["story.py"] = hashlib.sha256(controller.read_bytes()).hexdigest()
    (root / "source-identity.json").write_text(json.dumps(identity, indent=2))
    results = []
    for mode in (
        "init",
        "fresh-a",
        "execute-a",
        "select-a",
        "evidence",
        "declare",
        "promote",
        "fresh-b",
        "execute-b",
        "hide",
        "reuse-a",
        "old-reuse",
        "operational",
        "transfer",
        "read-a",
        "read-b",
        "read-again",
        "read-old",
        "finish",
    ):
        command = (
            [sys.executable, "-B"]
            + ([] if mode.startswith("execute-") else ["-c", OFFLINE])
            + [str(controller), mode, str(root)]
        )
        # Never kill an execute owner with an uncertain computational child. The
        # unchanged captured timeout bounds the child; synchronous run owns/reaps it.
        with (root / (mode + ".stdout")).open("wb") as out, (
            root / (mode + ".stderr")
        ).open("wb") as err:
            result = subprocess.run(
                command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, check=False
            )
        (root / (mode + ".exit")).write_text(str(result.returncode) + "\n")
        results.append(dict(mode=mode, command=command, exit=result.returncode))
        (root / "commands.json").write_text(json.dumps(results, indent=2))
        assert result.returncode == 0, (mode, (root / (mode + ".stderr")).read_text())
    summary = json.loads((root / "finish.stdout").read_bytes())
    assert summary["normal_Q"] == 4 and summary["real_local_attempts"] == 2
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        json.dumps(
            dict(phases=len(results), normal_Q=4, real_local_attempts=2, root=str(root))
        )
    )


if __name__ == "__main__":
    mode, root = sys.argv[1:]
    (run if mode == "run" else lambda p: phase(p, mode))(Path(root).resolve())
