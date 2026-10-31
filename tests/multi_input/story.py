"""Explicit installed SEVEN-Q/THREE synchronous LOCAL-attempt acceptance.

Default tests never run this workflow. Copies application policies, not DML runtime.
Every nonexecuting fresh phase blocks transport imports and process spawning.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

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
OFFLINE = """import runpy,sys
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


def literal(tx, value):
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
    """Independent public typed breadth-first closure: ALL parents/composites."""
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
                pending += [("dag", c) for c in dict(tx.get_tree(selected)).values()]
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


def init(root, app):
    path = root / "caller.dml"
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        entries = {
            "binding-a": local.put_local_binding(
                tx, source=SOURCE, interpreter=sys.executable, timeout_ms=10000
            ),
            "binding-b": local.put_local_binding(
                tx,
                source=SOURCE + b"\n# distinct B\n",
                interpreter=sys.executable,
                timeout_ms=10000,
            ),
        }
        for n in (2, 3):
            node = literal(tx, n)
            entries["inputs-" + str(n)] = tx.put_dag(root=node, bindings={"n": node})
        leaf = tx.put_datum(b"composite-only")
        side = tx.put_commit(
            tx.put_tree(
                {
                    "side": tx.put_dag(
                        root=tx.put_literal(tx.put_datum(d.Datum.list([leaf])))
                    )
                }
            )
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
            ("a", "binding-a", "old-a-slot"),
            ("b", "binding-b", "old-b-slot"),
        ),
        default_implementation="a",
        ref="definition",
    )
    table = app.define_table(
        path,
        commit=definition.commit,
        table_name="table",
        binding_name="binding-a",
        intent_uri=definition.intent_uri,
        ref="table-empty",
    )
    return dict(
        path=str(path),
        definition=str(definition.commit),
        empty=str(table.commit),
        requests={},
        runs={},
    )


def request(
    path, app, state, label, basis, n, *, fresh=False, reuse=None, expected_reason
):
    got = app.record_policy_request(
        path,
        commit=oid(basis),
        intent_name="intent",
        inputs_name="inputs-" + str(n),
        table_name="table",
        decision_name="decision-" + label,
        override="fresh" if fresh else "default",
        decision_ref="decision-" + label,
        submission_ref="submission-" + label,
        reuse_ref="reuse-" + label if reuse else None,
    )
    assert got.decision.base == oid(basis)
    assert got.decision.implementation.label == "a"
    assert got.decision.implementation_override == "default"
    assert got.decision.implementation_reason == "default-implementation"
    assert got.decision.reason == expected_reason
    assert got.decision.override == ("fresh" if fresh else "default")
    assert (got.reused is not None) == (reuse is not None)
    item = dict(
        commit=str(got.recorded.commit),
        request=str(got.recorded.request),
        request_id=got.recorded.request_id,
        decision=got.decision.name,
        decision_commit=str(got.decision.commit),
        base=basis,
        n=n,
        binding=str(got.decision.binding),
        inputs=str(got.decision.inputs),
        reason=expected_reason,
        override=got.decision.override,
        table=None if got.decision.table is None else str(got.decision.table.dag),
        entry=None if got.decision.entry is None else str(got.decision.entry.dag),
        selection=(
            None if got.decision.selected is None else str(got.decision.selected.dag)
        ),
        satisfaction=None if got.reused is None else str(got.reused.commit),
    )
    if reuse is not None:
        run = state["runs"][reuse]
        assert got.reused.attempt == oid(run["attempt"]) and got.reused.result == oid(
            run["result"]
        )
        assert got.recorded.request != oid(run["request"])
        item.update(
            attempt=str(got.reused.attempt),
            result=str(got.reused.result),
            owning_run=reuse,
            association=str(got.reused.dag),
        )
        with d.Repository(path) as repo, repo.read() as tx:
            assert set(tx.get_dag(got.reused.dag).bindings) == {
                "role",
                "request",
                "attempt",
                "result",
            }
            assert link(tx, got.reused.dag, "request") == got.recorded.request
            assert link(tx, got.reused.attempt, "request") == oid(run["request"])
    state["requests"][label] = item


def execute(root, path, state, label):
    item = state["requests"][label]
    workspace, packet = root / ("workspace-" + label), root / ("packet-" + label)
    spec = ex.prepare_exchange(
        path,
        commit=oid(item["commit"]),
        request=oid(item["request"]),
        binding_name="binding-a",
        inputs_name="inputs-" + str(item["n"]),
        intent_uri="urn:example:double",
        worker_ref="work",
        workspace=workspace,
    )
    expected_file = root / ("expected-" + label + ".json")
    ex.save_exchange_handle(expected_file, ex.ExchangeHandle(workspace, spec))
    spawning, children = subprocess.Popen, []

    def spawn(*a, **k):
        child = spawning(*a, **k)
        children.append(child)
        return child

    subprocess.Popen = spawn
    try:
        run = ex.execute_exchange(workspace)
    finally:
        subprocess.Popen = spawning
    assert (
        len(children) == 1 and children[0].poll() == 0 and children[0].returncode == 0
    )
    assert run.outcome == "success" and run.cleanup == "ok"
    # Synchronous execute owns/reaps the direct child BEFORE completion observation.
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
        got = value(tx, received.result)
        assert (got.kind, got.value) == ("i64", 2 * item["n"])
        got = value(tx, spec.inputs, "n")
        assert (got.kind, got.value) == ("i64", item["n"])
        assert link(tx, run.final_attempt, "request") == oid(item["request"])
    with d.Repository(workspace / "worker.dml") as repo, repo.read() as tx:
        publication = tx.get_ref("attempt-" + run.attempt_id)
        assert tx.get_commit(received.commit).parents == (
            received.pre_dispatch,
            publication,
        )
        assert tx.get_commit(publication).parents == (received.pre_dispatch,)
    assert rows(path, (received.commit,)) == rows(
        workspace / "worker.dml", (run.final_commit,)
    )
    state["runs"][label] = dict(
        commit=str(received.commit),
        attempt=str(run.final_attempt),
        result=str(run.result),
        request=str(received.request),
        attempt_id=run.attempt_id,
        child_pid=children[0].pid,
        child_exit=children[0].returncode,
        child_reaped=True,
        packet=str(packet),
        expected=str(expected_file),
        workspace=str(workspace),
    )


def capture(path, app, state, label, basis):
    run = state["runs"][label]
    got = app.selection.select(
        path,
        commit=oid(basis),
        slot="selected-" + label,
        binding_name="binding-a",
        inputs_name="inputs-" + str(state["requests"][label]["n"]),
        intent_uri="urn:example:double",
        packet=run["packet"],
        expected_file=run["expected"],
        ref="captured-" + label,
    )
    state["capture-" + label] = str(got.commit)
    state["selection-" + label] = str(got.dag)
    return got


def hide(state, labels):
    for label in labels:
        run = state["runs"][label]
        assert run["child_reaped"] and run["child_exit"] == 0
        for name in ("packet", "expected", "workspace"):
            original = Path(run[name])
            original.rename(original.with_name(original.name + ".unavailable"))


def read(path, app, state, label):
    item = state["requests"][label]
    before = (path / "data.mdb").read_bytes()
    got = app.inspect_request(
        path,
        commit=oid(item["commit"]),
        request=oid(item["request"]),
        decision_name=item["decision"],
        satisfaction_commit=(
            None if item["satisfaction"] is None else oid(item["satisfaction"])
        ),
    )
    assert got.base == oid(item["base"]) and got.commit == oid(item["decision_commit"])
    assert got.binding == oid(item["binding"]) and got.inputs == oid(item["inputs"])
    assert (
        got.implementation.label == "a"
        and got.implementation_override == "default"
        and got.implementation_reason == "default-implementation"
    )
    assert got.override == item["override"] and got.reason == item["reason"]
    assert (None if got.table is None else str(got.table.dag)) == item["table"]
    assert (None if got.entry is None else str(got.entry.dag)) == item["entry"]
    assert (None if got.selected is None else str(got.selected.dag)) == item[
        "selection"
    ]
    if item["satisfaction"] is not None:
        assert got.selected.attempt == oid(
            item["attempt"]
        ) and got.selected.result == oid(item["result"])
        assert got.selected.request == oid(state["runs"][item["owning_run"]]["request"])
    assert (path / "data.mdb").read_bytes() == before
    return dict(label=label, base=str(got.base), reason=got.reason, read_only=True)


def verify_branches(path, app, state):
    keep = app.inspect_table(path, commit=oid(state["keep"]), table_name="table")
    adopted = app.inspect_table(path, commit=oid(state["adopted"]), table_name="table")
    old = {r.inputs: r for r in keep.entries}
    new = {r.inputs: r for r in adopted.entries}
    i2 = oid(state["requests"]["two"]["inputs"])
    i3 = oid(state["requests"]["three"]["inputs"])
    assert set(old) == set(new) == {i2, i3}
    assert old[i3].dag == new[i3].dag and old[i3].selected.dag == new[
        i3
    ].selected.dag == oid(state["selection-three"])
    assert old[i2].selected.attempt == oid(state["runs"]["two"]["attempt"])
    assert new[i2].selected.attempt == oid(state["runs"]["fresh"]["attempt"])
    assert old[i2].selected.attempt_id != new[i2].selected.attempt_id
    assert old[i2].selected.result == new[i2].selected.result
    with d.Repository(path) as repo, repo.read() as tx:
        common = oid(state["common"])
        assert (
            tx.get_commit(oid(state["keep"])).parents
            == tx.get_commit(oid(state["adopted"])).parents
            == (common,)
        )
        before = tree(tx, common)
        after = tree(tx, oid(state["adopted"]))
        assert tree(tx, oid(state["keep"])) == before
        assert before.pop("table") == oid(state["table-two"])
        after.pop("table")
        assert before == after
        for label in ("two", "three", "fresh"):
            assert before["selected-" + label] == oid(state["selection-" + label])
    return dict(entries=2, true_siblings=True, only_I2_adopted=True)


def finish(root, path, app, state):
    roots = [oid(state[k]) for k in ("keep", "adopted")]
    roots += [oid(i["satisfaction"] or i["commit"]) for i in state["requests"].values()]
    native = rows(path, roots)
    requests, attempts = {}, {}
    with d.Repository(path) as repo, repo.read() as tx:
        for kind, dag in native:
            if kind != "dag" or "role" not in tx.get_dag(dag).bindings:
                continue
            role = value(tx, dag, "role").value
            if role == "local-request-v1":
                requests.setdefault(value(tx, dag).value, []).append(str(dag))
            elif role == "local-attempt-v1":
                attempts.setdefault(value(tx, dag).value, []).append(str(dag))
        assert len(requests) == 7 and all(len(v) == 1 for v in requests.values())
        assert len(attempts) == 3 and all(len(v) == 2 for v in attempts.values())
        assert {i["request"] for i in state["requests"].values()} == {
            v[0] for v in requests.values()
        }
        assert {r["attempt_id"] for r in state["runs"].values()} == set(attempts)
        for kind, selected, raw in state["old_rows"]:
            assert tx.get_record(kind, oid(selected)) == base64.b64decode(raw)
        for name, selected in state["old_refs"].items():
            assert tx.get_ref(name) == oid(selected)
        initial = tree(tx, oid(state["definition"]))
        assert value(tx, initial["binding-a"], "source").value == SOURCE
        assert (
            value(tx, initial["binding-b"], "source").value
            == SOURCE + b"\n# distinct B\n"
        )
        for name in ("binding-a", "binding-b"):
            assert value(tx, initial[name], "interpreter").value == sys.executable
            assert value(tx, initial[name], "timeout-ms").value == 10000
        for label, item in state["requests"].items():
            assert (
                tx.get_ref("request-" + item["request_id"])
                == tx.get_ref("submission-" + label)
                == oid(item["commit"])
            )
            assert tx.get_ref("decision-" + label) == oid(item["decision_commit"])
            if item["satisfaction"] is not None:
                assert tx.get_ref("reuse-" + label) == oid(item["satisfaction"])
    verify_branches(path, app, state)
    return dict(
        normal_Q=7,
        real_local_attempts=3,
        support_occurrences=0,
        requests=requests,
        attempts=attempts,
        children_reaped=state["runs"],
        old_records_preserved=len(state["old_rows"]),
        old_refs_preserved=len(state["old_refs"]),
    )


def phase(root, mode):
    import multi_input_reuse as app

    state = (
        init(root, app)
        if mode == "init"
        else json.loads((root / "state.json").read_bytes())
    )
    path = Path(state["path"])
    if mode == "request-two":
        request(
            path,
            app,
            state,
            "two",
            state["empty"],
            2,
            expected_reason="default-no-entry",
        )
    elif mode.startswith("execute-"):
        execute(root, path, state, mode[len("execute-") :])
    elif mode in ("capture-two", "capture-three"):
        label = mode[len("capture-") :]
        chosen = capture(path, app, state, label, state["runs"][label]["commit"])
        got = app.select_entry(
            path,
            commit=chosen.commit,
            table_name="table",
            selection_slot=chosen.slot,
            ref="indexed-" + label,
        )
        state["indexed-" + label] = str(got.commit)
        assert len(got.entries) == (1 if label == "two" else 2)
        assert app.inspect_table(path, commit=got.commit, table_name="table") == got
        if label == "three":
            state["table-two"] = str(got.dag)
    elif mode == "request-three":
        request(
            path,
            app,
            state,
            "three",
            state["indexed-two"],
            3,
            expected_reason="default-no-entry",
        )
    elif mode == "hide-first":
        hide(state, ("two", "three"))
    elif mode == "reuse-two":
        request(
            path,
            app,
            state,
            "two-again",
            state["indexed-three"],
            2,
            reuse="two",
            expected_reason="default-entry",
        )
    elif mode == "reuse-three":
        request(
            path,
            app,
            state,
            "three-again",
            state["requests"]["two-again"]["satisfaction"],
            3,
            reuse="three",
            expected_reason="default-entry",
        )
    elif mode == "request-fresh":
        request(
            path,
            app,
            state,
            "fresh",
            state["requests"]["three-again"]["satisfaction"],
            2,
            fresh=True,
            expected_reason="override-fresh",
        )
    elif mode == "capture-fresh":
        run = state["runs"]["fresh"]
        with d.Repository(path) as repo, repo.read() as tx:
            assert tree(tx, oid(run["commit"]))["table"] == oid(state["table-two"])
        chosen = capture(path, app, state, "fresh", run["commit"])
        state["common"] = str(chosen.commit)
        # Save immutable old proof BEFORE branch/adoption/new requests.
        state["old_rows"] = [
            [kind, str(selected), base64.b64encode(raw).decode()]
            for (kind, selected), raw in rows(path, (chosen.commit,)).items()
        ]
        with d.Repository(path) as repo, repo.read() as tx:
            names = [
                "main",
                "definition",
                "table-empty",
                "indexed-two",
                "indexed-three",
                "captured-two",
                "captured-three",
                "captured-fresh",
            ]
            names += [
                prefix + label
                for label in state["requests"]
                for prefix in ("decision-", "submission-")
            ]
            state["old_refs"] = {name: str(tx.get_ref(name)) for name in names}
        hide(state, ("fresh",))
    elif mode == "branches":
        got = app.adopt_entry(
            path,
            commit=oid(state["common"]),
            table_name="table",
            selection_slot="selected-fresh",
            ref="adopted",
        )
        state["adopted"] = str(got.commit)
        with d.Repository(path) as repo, repo.write() as tx:
            keep = tx.put_commit(
                tx.get_commit(oid(state["common"])).tree,
                parents=(oid(state["common"]),),
            )
            tx.create_ref("keep", keep)
        state["keep"] = str(keep)
        verify_branches(path, app, state)
    elif mode == "reuse-adopted":
        request(
            path,
            app,
            state,
            "adopted",
            state["adopted"],
            2,
            reuse="fresh",
            expected_reason="default-entry",
        )
    elif mode == "reuse-keep":
        request(
            path,
            app,
            state,
            "keep",
            state["keep"],
            2,
            reuse="two",
            expected_reason="default-entry",
        )
    elif mode == "transfer":
        replica = root / "replica.dml"
        with d.Repository(replica, create=True):
            pass
        roots = [state[k] for k in ("keep", "adopted")] + [
            i["satisfaction"] or i["commit"] for i in state["requests"].values()
        ]
        for selected in roots:
            bundle = transfer.export_commit(path, commit=oid(selected))
            transfer.import_commit(replica, bundle)
            assert transfer.export_commit(replica, commit=oid(selected)) == bundle
            assert rows(path, (oid(selected),)) == rows(replica, (oid(selected),))
        state["replica"] = str(replica)
    elif mode.startswith("read-"):
        label = mode[len("read-") :]
        got = read(path, app, state, label)
        assert read(Path(state["replica"]), app, state, label) == got
        verify_branches(Path(state["replica"]), app, state)
        print(json.dumps(got))
        return
    elif mode == "finish":
        print(json.dumps(finish(root, path, app, state)))
        return
    (root / "state.json").write_text(json.dumps(state, indent=2))
    print(json.dumps(dict(phase=mode, complete=True)))


def run(root):
    assert "PYTHONPATH" not in os.environ and not root.exists()
    root.mkdir()
    policy = root / "policy"
    policy.mkdir()
    repo = Path(__file__).resolve().parents[2]
    identity = {}
    for name in (
        "multi_input_reuse.py",
        "implementation_selection.py",
        "reuse_selection.py",
        "explicit_reuse.py",
    ):
        data = (repo / "examples" / name).read_bytes()
        (policy / name).write_bytes(data)
        identity[name] = hashlib.sha256(data).hexdigest()
    controller = root / "story.py"
    controller.write_bytes(Path(__file__).read_bytes())
    identity["story.py"] = hashlib.sha256(controller.read_bytes()).hexdigest()
    # Original copy + hash are durable BEFORE any phase or computational launch.
    (root / "source-identity.json").write_text(json.dumps(identity, indent=2))
    modes = (
        "init",
        "request-two",
        "execute-two",
        "capture-two",
        "request-three",
        "execute-three",
        "capture-three",
        "hide-first",
        "reuse-two",
        "reuse-three",
        "request-fresh",
        "execute-fresh",
        "capture-fresh",
        "branches",
        "reuse-adopted",
        "reuse-keep",
        "transfer",
        "read-two",
        "read-three",
        "read-two-again",
        "read-three-again",
        "read-fresh",
        "read-adopted",
        "read-keep",
        "finish",
    )
    results = []
    for mode in modes:
        command = (
            [sys.executable, "-B"]
            + ([] if mode.startswith("execute-") else ["-c", OFFLINE])
            + [str(controller), mode, str(root)]
        )
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
    assert summary["normal_Q"] == 7 and summary["real_local_attempts"] == 3
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        json.dumps(
            dict(phases=len(results), normal_Q=7, real_local_attempts=3, root=str(root))
        )
    )


if __name__ == "__main__":
    mode, root = sys.argv[1:]
    (run if mode == "run" else lambda p: phase(p, mode))(Path(root).resolve())
