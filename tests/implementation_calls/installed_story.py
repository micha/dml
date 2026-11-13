"""Opt-in I25 readiness/sole13Q10T6DIRECT-LOCAL17getter controller. NO default computation."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

DIRECTORY = Path(__file__).resolve().parent
EXAMPLES = DIRECTORY.parents[1] / "examples"
if not EXAMPLES.is_dir():
    EXAMPLES = DIRECTORY
sys.path.insert(0, str(EXAMPLES))

import daggerml as d
from daggerml import builtin as b, calls as c, exchange as ex, local, transfer
import implementation_calls as p
import implementation_call_adapter as adapter
import implementation_call_session as bridge
import implementation_call_leaf as leaf
import implementation_call_funcs as logical
import implementation_leaf_funcs as funcs
import reuse_selection as selection
import explicit_reuse

SOURCE_NAMES = ("installed_story.py", "offline_read.py", "implementation_calls.py", "implementation_call_session.py",
                "implementation_call_adapter.py", "implementation_call_leaf.py", "implementation_call_funcs.py",
                "implementation_leaf_funcs.py", "reuse_selection.py", "explicit_reuse.py")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def append_event(root, events, category, row):
    if "event" in row:
        raise RuntimeError("reserved event category key in receipt payload")
    record = dict(event=category, **row)
    events.append(record)
    with open(Path(root) / "events.jsonl", "a") as stream:
        stream.write(json.dumps(record) + "\n")
    return record


def metadata_controls():
    permission = {"popen": False}
    def audit(event, args):
        if event in ("socket.connect", "socket.bind", "socket.getaddrinfo"):
            raise RuntimeError("story forbids transport")
        if event in ("subprocess.Popen", "os.posix_spawn", "os.fork", "os.forkpty", "os.exec", "os.system") and not permission["popen"]:
            raise RuntimeError("metadata/outer-hit forbids spawn")
    sys.addaudithook(audit)
    import socket
    import urllib.request
    blocked = []
    for label, action in (("spawn", lambda: subprocess.Popen([sys.executable, "-c", "raise SystemExit(99)"])),
        ("connect", lambda: socket.create_connection(("127.0.0.1", 1))),
        ("urllib-transport", lambda: urllib.request.urlopen("http://127.0.0.1:1", timeout=1))):
        try:
            action()
        except RuntimeError:
            blocked.append(label)
        else:
            raise RuntimeError("metadata blocker missed " + label)
    return permission, dict(blockers=blocked, before_any_Q_T=True)


def identities():
    modules = {"daggerml": d, "builtin": b, "calls": c, "exchange": ex, "local": local, "transfer": transfer, "native": d._core}
    prefix = Path(sys.prefix).resolve()
    result = {}
    for name, module in modules.items():
        path = Path(module.__file__).resolve()
        if prefix not in path.parents:
            raise ValueError("runtime imported outside isolated installed prefix")
        result[name] = dict(path=str(path), sha256=digest(path))
    cli = Path(d.__file__).parent / "_bin" / "dml"
    result["cli"] = dict(path=str(cli), sha256=digest(cli))
    return result


def helper_identities(directory):
    modules = {"implementation_calls.py": p, "implementation_call_session.py": bridge,
        "implementation_call_adapter.py": adapter, "implementation_call_leaf.py": leaf,
        "implementation_call_funcs.py": logical, "implementation_leaf_funcs.py": funcs,
        "reuse_selection.py": selection, "explicit_reuse.py": explicit_reuse}
    result = {}
    for filename, module in modules.items():
        actual = Path(module.__file__).resolve()
        if actual != directory / filename:
            raise ValueError("actual helper not from measured owned source copy")
        result[filename] = dict(path=str(actual), sha256=digest(actual))
    return result


def readiness(root):
    """Metadata ONLY, no Q/T/Context.invoke/getter/ordinary call/OS child."""
    root = Path(root).resolve()
    root.mkdir()
    permission, controls = metadata_controls()
    installed = identities()
    if EXAMPLES != DIRECTORY:
        raise ValueError("readiness requires isolated measured launch-source copy")
    helpers = helper_identities(DIRECTORY)
    path = root / "metadata.dml"
    base = p.initialize(path, sys.executable)
    base = p.prepare_arguments(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs", ref="inputs")
    base = p.prepare_source_arguments(path, commit=base, values={"a": 13, "b": 29}, inputs_name="new-sources", ref="new-sources")
    base = p.prepare_arguments(path, commit=base, values={"a": 13, "b": 30}, inputs_name="changed", ref="changed")
    with d.Repository(path) as repo, repo.read() as tx:
        entries, seen = p.tree(tx, base), set()
        first, _ = p.arguments(tx, base, entries["inputs"], ("a", "b"), seen)
        different_sources, _ = p.arguments(tx, base, entries["new-sources"], ("a", "b"), seen)
        changed, _ = p.arguments(tx, base, entries["changed"], ("a", "b"), seen)
        closures = {label: p.inspect_closure(tx, base, entries["outer-" + label]) for label in ("A", "B")}
        if first.datum != different_sources.datum or first.dag == different_sources.dag or changed.datum == first.datum:
            raise ValueError("actual equal/changed MAP or source associations differ")
        if any(n.startswith(("request-", "outer-request-", "attempt-", "outer-attempt-")) for n in entries):
            raise ValueError("readiness must create zero occurrences")
        descriptors = {label: {n: str(got[n]) for n in ("dag", "binding", "environment", "map_binding")}
                       for label, got in closures.items()}
    bundle = transfer.export_commit(path, commit=base)
    framing = json.loads(bundle)
    result = dict(metadata_only=True, Q=0, T=0, getters=0, OS_children=0, controls=controls,
        installed=installed, helpers=helpers, sources={n: digest(DIRECTORY / n) for n in SOURCE_NAMES},
        interpreter=sys.executable, interpreter_sha256=digest(sys.executable), prefix=sys.prefix,
        source_directory=str(DIRECTORY), descriptors=descriptors,
        first_input=str(first.dag), different_source_input=str(different_sources.dag), changed_input=str(changed.dag),
        full_MAP_datum=str(first.datum), input_semantic_union=sorted(str(x) for x in seen),
        native_rows=len(framing["objects"]), encoded_bytes=len(bundle),
        limits=dict(semantic=b.MAX_RECORDS, arguments=b.MAX_ARGUMENTS, positions=b.MAX_POSITIONS,
            ORIGINAL_depth=p.MAX_AUTHORITY_DEPTH, structure_depth=c.MAX_STRUCTURE_DEPTH),
        preactivation_requirement="review exact current native per-row requested+ALL-OLD sets/reservations/depth; metadata is NOT computational/custody proof")
    save(root / "readiness.json", result)
    return result


def verify_leaf_run(expected, children, row):
    """Actual native F + this owned direct child's wait0 BEFORE observation/import/S."""
    if expected is None or not expected.get("spawned") or "child_index" not in expected:
        raise RuntimeError("leaf-run lacks THAT owned dispatched child")
    process, child = children[expected["child_index"]]
    if (child.get("verified") or child["waits"] != [dict(returned=True, exit=0)] or process.returncode != 0
        or row["outcome"] != "success" or row["cleanup"] != "ok"
        or row["request"] != expected["request"] or row["request"] != child["request"]
        or row["attempt_id"] != child["attempt_id"] or row["pre_dispatch"] != child["pre_dispatch"]):
        raise RuntimeError("leaf-run disposition/Q/attempt UNKNOWN-or-failed: STOP")
    with d.Repository(Path(expected["workspace"]) / "worker.dml") as repo, repo.read() as tx:
        completion = d.ObjectId.from_hex(row["completion"])
        entries = p.tree(tx, completion)
        final_t = tx.get_dag(entries["attempt-" + row["attempt_id"]]).bindings
        outcome = tx.get_dag(b.link(tx, final_t["outcome"])).bindings
        cleanup = tx.get_dag(b.link(tx, final_t["cleanup"])).bindings
        if (tx.get_ref("work") != completion or tx.get_commit(completion).parents[0] != d.ObjectId.from_hex(row["pre_dispatch"])
            or b.link(tx, final_t["request"]) != d.ObjectId.from_hex(row["request"])
            or b.scalar(tx, final_t["status"], "string") != "done"
            or b.scalar(tx, outcome["role"], "string") != "local-success-v1"
            or b.scalar(tx, outcome["exit-code"], "i64") != 0
            or b.scalar(tx, cleanup["disposition"], "string") != "ok"):
            raise RuntimeError("native successful leaf-run barrier differs")
    child["verified"], child["completion"] = True, row["completion"]


def run(root):
    """Requires separate explicit installed-readiness/activation approval before invocation."""
    root = Path(root).resolve()
    if DIRECTORY != root.parent / "launch-source" or EXAMPLES != DIRECTORY:
        raise ValueError("launch ONLY measured isolated owned source copy")
    if "PYTHONPATH" in os.environ or "PYTHONHOME" in os.environ:
        raise ValueError("parent AND plain child environment must be sanitized")
    root.mkdir()
    permission, controls = metadata_controls()
    installed, helpers = identities(), helper_identities(DIRECTORY)
    sources = {n: digest(DIRECTORY / n) for n in SOURCE_NAMES}
    captured = root / "captured-source"
    captured.mkdir()
    for n in SOURCE_NAMES:
        shutil.copyfile(DIRECTORY / n, captured / n)
    save(root / "prelaunch-source.json", dict(sources=sources, installed=installed, helpers=helpers,
        interpreter=sys.executable, interpreter_sha256=digest(sys.executable), prefix=sys.prefix,
        operational_source=str(DIRECTORY), controller=str(Path(__file__).resolve()), controls=controls))
    events, children, expected_dispatch, current_request = [], [], [None], [None]
    results, descriptions = [], []
    real_popen = subprocess.Popen
    caller = root / "caller.dml"
    def event(category, row):
        append_event(root, events, category, row)
        if category == "outer-request":
            current_request[0] = p.inspect_request(caller, commit=d.ObjectId.from_hex(row["submission"]),
                request=d.ObjectId.from_hex(row["request"]))
        if category == "dispatch":
            if expected_dispatch[0] is not None:
                raise RuntimeError("overlapping/unconsumed dispatch permission")
            expected_dispatch[0] = dict(row)
        if category == "leaf-run":
            verify_leaf_run(expected_dispatch[0], children, row)
            event("leaf-disposition-verified", dict(request=row["request"], attempt_id=row["attempt_id"],
                pre_dispatch=row["pre_dispatch"], completion=row["completion"], child_index=expected_dispatch[0]["child_index"]))
            expected_dispatch[0] = None
    def tracked(command, **kwargs):
        expected = expected_dispatch[0]
        if (expected is None or expected.get("spawned", False) or len(children) >= 6
            or type(command) is not list or len(command) != 6 or command[0] != sys.executable or kwargs.get("shell", False)):
            raise RuntimeError("only six declared direct LOCAL children allowed")
        workspace = Path(expected["workspace"])
        if command[-4] != str(workspace / "worker.dml"):
            raise RuntimeError("direct child targets unexpected repository")
        spec = ex.read_exchange_spec(workspace)
        context = local.child_context(command[-4:])
        target = current_request[0].closure["add" if expected["slot"] == 0 else "double"]
        if (str(spec.request) != expected["request"] or (context.request, context.binding, context.inputs) != (spec.request, target["binding"], spec.inputs)
            or command != [sys.executable, str(Path(context.scratch) / "entry.py"), context.repository_path,
                           str(context.pre_dispatch), context.attempt_id, context.publication_ref]):
            raise RuntimeError("expected native Q/B/input/exact command differs")
        with d.Repository(context.repository_path) as repo, repo.read() as tx:
            actual = b.scalar(tx, tx.get_dag(context.binding).bindings["source"], "bytes")
            if tx.get_commit(context.pre_dispatch).parents != (spec.commit,):
                raise RuntimeError("actual pre-dispatch parent differs")
        if actual != leaf.capture(target["environment"], target["intent"], *leaf.sources()) or Path(command[1]).read_bytes() != actual:
            raise RuntimeError("actual captured child entry/source differs")
        expected["spawned"], permission["popen"] = True, True
        try:
            process = real_popen(command, **kwargs)
        finally:
            permission["popen"] = False
        row = dict(pid=process.pid, command=command, request=str(context.request), attempt_id=context.attempt_id,
            pre_dispatch=str(context.pre_dispatch), source_sha256=hashlib.sha256(actual).hexdigest(), waits=[],
            binding=str(context.binding), inputs=str(context.inputs), initial_attempt=str(context.attempt),
            workspace=str(workspace), slot=expected["slot"])
        expected["child_index"] = len(children)
        children.append((process, row))
        event("spawn", dict(row))  # PID durable before assertions/wait.
        actual_wait = process.wait
        def wait(*args, **options):
            try:
                code = actual_wait(*args, **options)
            except BaseException as error:
                row["waits"].append(dict(returned=False, error=type(error).__name__))
                event("wait", dict(pid=process.pid, receipt=row["waits"][-1]))
                raise
            row["waits"].append(dict(returned=True, exit=code))
            event("wait", dict(pid=process.pid, receipt=row["waits"][-1]))
            return code
        process.wait = wait
        return process
    subprocess.Popen = tracked
    try:
        commit = p.initialize(caller, sys.executable)
        commit = p.prepare_arguments(caller, commit=commit, values={"a": 13, "b": 29}, inputs_name="inputs", ref="inputs")
        commit = p.prepare_source_arguments(caller, commit=commit, values={"a": 13, "b": 29}, inputs_name="new-sources", ref="new-sources")
        commit = p.prepare_arguments(caller, commit=commit, values={"a": 13, "b": 30}, inputs_name="changed", ref="changed")
        for number, label, inputs, control, inner in ((1, "A", "inputs", "fresh", "fresh"),
            (2, "B", "new-sources", "require-selected", "fresh"), (3, "B", "inputs", "fresh", "fresh"),
            (4, "B", "inputs", "fresh", "require-selected"), (5, "A", "changed", "try-selected", "try-selected")):
            if number == 4:
                commit = p.promote_defaults(caller, commit=commit, ref="defaults-B")
            before = len(children)
            result = adapter.invoke(caller, commit=commit, closure_name="outer-" + label, inputs_name=inputs,
                control=control, add_control=inner, double_control=inner, ref="outer-%d" % number,
                workspace=root / ("execution-%d" % number), receipt=event)
            results.append(result)
            commit = result.commit
            if len(children) - before != (0 if number in (2, 4) else 2) or expected_dispatch[0] is not None:
                raise RuntimeError("actual row launch population differs")
            if result.node.value != d.Datum.i64(86 if number == 5 else 84):
                raise RuntimeError("actual returned outer value differs")
            got = None if number == 2 else p.inspect_completion(caller, commit=commit)
            descriptions.append(got)
            event("outer-completed", dict(number=number, commit=str(commit), request=str(result.request.request),
                semantic_ids=sorted(str(x) for x in result.semantic_ids)))
            if number == 1:
                commit = p.select_outer(caller, commit=commit, completion=commit, ref="selected-outer")
                for call, slot, ref in zip(got["calls"], (p.ADD_SLOT, p.DOUBLE_SLOT), ("selected-add", "selected-double")):
                    commit = p.pin_leaf(caller, commit=commit, call=call, slot=slot, ref=ref)
        if len(children) != 6:
            raise RuntimeError("actual six-child census differs")
        for process, row in children:
            if not row.get("verified") or row["waits"] != [dict(returned=True, exit=0)] or process.returncode != 0:
                raise RuntimeError("direct disposition UNKNOWN-or-failed; STOP")
            try:
                os.kill(process.pid, 0)
            except ProcessLookupError:
                row["absent"] = True
            else:
                raise RuntimeError("owned waited PID still present/uncertain; STOP")
        save(root / "custody.json", dict(children=[row for _, row in children], direct=6, descendants=0,
            qualification="fixed source/direct-child custody, not general process-tree supervision"))
        with d.Repository(caller) as repo, repo.write() as tx:
            entries = p.tree(tx, commit)
            links = {"outer-q%d" % (i + 1): r.request.request for i, r in enumerate(results)}
            for i, got in enumerate(descriptions):
                if got is not None:
                    links["outer-t%d" % (i + 1)], links["outer-r%d" % (i + 1)] = got["attempt"], got["result"]
            entries["summary"] = b.record(tx, p.PREFIX + "summary-v1", values={"outer-requests": 5, "outer-attempts": 4,
                "leaf-requests": 8, "leaf-attempts": 6, "ordinary-positions": 8, "getters": 17}, links=links)
            final = tx.put_commit(tx.put_tree(entries), parents=(commit,))
            tx.create_ref("story", final)
        bundle = transfer.export_commit(caller, commit=final)
        (root / "full-history.bundle").write_bytes(bundle)
        with d.Repository(root / "replica.dml", create=True):
            pass
        transfer.import_commit(root / "replica.dml", bundle, ref="story")
        receipt = dict(final=str(final), sources=sources, installed=installed, helpers=helpers, controls=controls,
            interpreter=sys.executable, interpreter_sha256=digest(sys.executable),
            bundle_sha256=hashlib.sha256(bundle).hexdigest(),
            rows=[dict(request=str(r.request.request), submission=str(r.request.commit), commit=str(r.commit),
                satisfaction=None if r.request.reused is None else str(r.request.reused),
                semantic_ids=sorted(str(x) for x in r.semantic_ids)) for r in results])
        save(root / "receipt.json", receipt)
        for number in (1, 3, 4, 5):
            original = root / ("execution-%d" % number)
            original.rename(original.with_name(original.name + ".unavailable"))
        captured.rename(root / "captured-source.unavailable")
        DIRECTORY.rename(DIRECTORY.with_name("launch-source.unavailable"))
        return receipt
    finally:
        subprocess.Popen = real_popen
        permission["popen"] = False
        save(root / "final-disposition.json", dict(children=[dict(row, poll=process.poll()) for process, row in children],
            no_automatic_retry=True, outer_computation_finished=len(results) == 5))


def read(root):
    """SAME stopped native history only; caller enables blockers before helper imports."""
    root = Path(root)
    receipt = json.loads((root / "receipt.json").read_bytes())
    expected = d.ObjectId.from_hex(receipt["final"])
    result = {}
    for repository in (root / "caller.dml", root / "replica.dml"):
        with d.Repository(repository) as repo, repo.read() as tx:
            if tx.get_ref("story") != expected:
                raise ValueError("retained story root differs")
            entries = p.tree(tx, expected)
            outer_q, leaf_q, outer_t, local_t = set(), set(), set(), {}
            for commit in p.history(tx, expected):
                for name, dag in p.tree(tx, commit).items():
                    fields = tx.get_dag(dag).bindings
                    if name.startswith("outer-request-iq-"):
                        outer_q.add(dag)
                    elif name.startswith("request-q-"):
                        leaf_q.add(dag)
                    elif name.startswith("outer-attempt-ia-"):
                        outer_t.add(b.scalar(tx, tx.get_dag(dag).root, "string"))
                    elif name.startswith("attempt-a-") and "status" in fields:
                        aid = b.scalar(tx, tx.get_dag(dag).root, "string")
                        if aid in local_t and local_t[aid] != dag:
                            raise ValueError("same LOCAL occurrence has conflicting final descriptions")
                        local_t[aid] = dag
            if tuple(map(len, (outer_q, leaf_q, outer_t, local_t))) != (5, 8, 4, 6):
                raise ValueError("actual ALL-parent Q/T census differs")
            closures = {label: p.inspect_closure(tx, expected, entries["outer-" + label]) for label in ("A", "B")}
            if entries["default-add"] != entries["add-B"] or entries["default-double"] != entries["double-B"]:
                raise ValueError("defaultB promotion missing")
            for label, got in closures.items():
                if (got["add"]["dag"], got["double"]["dag"]) != (entries["add-" + label], entries["double-" + label]):
                    raise ValueError("captured ordinary dependencies not pinned")
        selected = p.inspect_selection(repository, commit=expected)
        selected_add, _ = p.inspect_leaf_success(repository, commit=expected, slot=p.ADD_SLOT)
        selected_double, _ = p.inspect_leaf_success(repository, commit=expected, slot=p.DOUBLE_SLOT)
        descriptions, pending_requests, producers = [], set(), set()
        getters = calls = 0
        for i, row in enumerate(receipt["rows"]):
            row_seen = set()
            q = p.inspect_request(repository, commit=d.ObjectId.from_hex(row["submission"]), request=d.ObjectId.from_hex(row["request"]), seen=row_seen)
            if q.closure != closures["A" if i in (0, 4) else "B"]:
                raise ValueError("actual requested closure differs by row")
            final = d.ObjectId.from_hex(row["commit"])
            if i == 1:
                reused = p.inspect_reuse(repository, commit=final, seen=row_seen)
                if frozenset(str(x) for x in row_seen) != frozenset(row["semantic_ids"]):
                    raise ValueError("outer hit requested+ALL ORIGINAL semantic union differs")
                if row["satisfaction"] != row["commit"] or reused.request != q.request or reused.selected["attempt"] != selected["attempt"]:
                    raise ValueError("outer NEW B Q/pinned OLD A T association differs")
                descriptions.append(None)
                continue
            got = p.inspect_completion(repository, commit=final, seen=row_seen)
            if got["outcome"] != "success" or got["closure"] != q.closure or got["request"] != q.request:
                raise ValueError("fresh outer actual ownQ/closure/success differs")
            if frozenset(str(x) for x in got["semantic_ids"]) != frozenset(row["semantic_ids"]):
                raise ValueError("SAME requested+OLD semantic union differs")
            getters += len(got["getters"])
            calls += len(got["calls"])
            descriptions.append(got)
            with d.Repository(repository) as repo, repo.read() as tx:
                if tx.get_datum(got["datum"]) != d.Datum.i64(86 if i == 4 else 84):
                    raise ValueError("actual recorded outer value differs")
                for slot, call in enumerate(got["calls"]):
                    fields = tx.get_dag(call).bindings
                    pending = tx.get_dag(b.link(tx, fields["pending"])).bindings
                    pending_requests.add(b.link(tx, pending["request"]))
                    producers.add(b.scalar(tx, tx.get_dag(b.link(tx, fields["attempt"])).root, "string"))
                    if b.link(tx, pending["closure"]) != q.closure["add" if slot == 0 else "double"]["dag"]:
                        raise ValueError("THIS requested captured target differs")
                    if i == 3:
                        old = selected_add if slot == 0 else selected_double
                        if tuple(b.link(tx, fields[n]) for n in ("selection", "attempt", "result")) != (old.dag, old.attempt, old.result):
                            raise ValueError("NEW B inner Q must consume pinned OLD A authority")
                        if b.link(tx, pending["request"]) == old.request:
                            raise ValueError("inner reuse must have own NEW Q")
        facts = {}
        with d.Repository(repository) as repo, repo.read() as tx:
            for aid, final_t in local_t.items():
                fields = tx.get_dag(final_t).bindings
                request = b.link(tx, fields["request"])
                qfields = tx.get_dag(request).bindings
                binding = b.link(tx, qfields["binding"])
                outcome = tx.get_dag(b.link(tx, fields["outcome"])).bindings
                if b.scalar(tx, outcome["role"], "string") != "local-success-v1":
                    raise ValueError("actual final LOCAL attempt not successful")
                returned = tx.get_dag(b.link(tx, outcome["result"])).bindings
                getters += len(b.Inspector(tx, commit=expected).trace(b.link(tx, returned["trace"]),
                    request=request, inputs=b.link(tx, qfields["inputs"])))
                selections = [v for v in entries.values() if "role" in tx.get_dag(v).bindings
                    and b.scalar(tx, tx.get_dag(v).bindings["role"], "string") == "example-reuse-selection-v1"
                    and b.link(tx, tx.get_dag(v).bindings["attempt"]) == final_t]
                if not selections:
                    raise ValueError("actual LOCAL attempt lacks retained S")
                sf = tx.get_dag(selections[0]).bindings
                completion = p.oid(tx, sf["completion"])
                pre = tx.get_commit(completion).parents[0]
                facts[aid] = dict(request=str(request), attempt_id=aid, pre_dispatch=str(pre), binding=str(binding),
                    inputs=str(b.link(tx, qfields["inputs"])), initial_attempt=str(p.tree(tx, pre)["attempt-" + aid]),
                    publication_ref=b.scalar(tx, fields["publication-ref"], "string"), scratch=b.scalar(tx, fields["scratch"], "string"),
                    source_sha256=hashlib.sha256(b.scalar(tx, tx.get_dag(binding).bindings["source"], "bytes")).hexdigest(), completion=str(completion))
            if pending_requests != leaf_q or producers != set(local_t) or getters != 17 or calls != 8:
                raise ValueError("actual ownQ/producer/getter/call ledger census differs")
            if selected["closure"] != closures["A"]:
                raise ValueError("selected outer was automatically adopted or relabelled")
            first_call, last_call = (tx.get_dag(descriptions[i]["calls"][0]).bindings for i in (0, 3))
            if entries[p.ADD_SLOT] != b.link(tx, first_call["selection"]) or entries[p.DOUBLE_SLOT] != b.link(tx, tx.get_dag(descriptions[0]["calls"][1]).bindings["selection"]):
                raise ValueError("known leaf selections changed automatically")
            # Row4's exact add source is OLD R, but own B inner requests/outer association are NEW.
            double_pending = tx.get_dag(b.link(tx, tx.get_dag(descriptions[3]["calls"][1]).bindings["pending"])).bindings
            _, sources = p.arguments(tx, expected, b.link(tx, double_pending["inputs"]), ("x",), set())
            if sources["x"].dag != b.link(tx, last_call["result"]) or sources["x"].dag != b.link(tx, first_call["result"]):
                raise ValueError("reused addR actual downstream source association differs")
            summary_names = ("role", "outer-requests", "outer-attempts", "leaf-requests", "leaf-attempts", "ordinary-positions", "getters",
                *("outer-q%d" % i for i in range(1, 6)), *("outer-t%d" % i for i in (1, 3, 4, 5)), *("outer-r%d" % i for i in (1, 3, 4, 5)))
            summary = b.shape(tx, entries["summary"], summary_names, p.PREFIX + "summary-v1")
            for n, value in (("outer-requests", 5), ("outer-attempts", 4), ("leaf-requests", 8), ("leaf-attempts", 6), ("ordinary-positions", 8), ("getters", 17)):
                if b.scalar(tx, summary[n], "i64") != value:
                    raise ValueError("summary count differs")
            for i, row in enumerate(receipt["rows"]):
                if b.link(tx, summary["outer-q%d" % (i + 1)]) != d.ObjectId.from_hex(row["request"]):
                    raise ValueError("summary exact ownQ link differs")
                if descriptions[i] is not None:
                    for name, field in (("outer-t", "attempt"), ("outer-r", "result")):
                        if b.link(tx, summary[name + str(i + 1)]) != descriptions[i][field]:
                            raise ValueError("summary exact T/R link differs")
        verify_custody(root, facts, receipt["interpreter"])
        result[str(repository)] = dict(requests=13, outer_attempts=4, local_attempts=6, ordinary_positions=calls, getters=getters)
    return result


def verify_custody(root, facts, interpreter):
    """Historical inspection NEVER signals PIDs; compare retained primary/native receipts."""
    custody = json.loads((Path(root) / "custody.json").read_bytes())
    events = [json.loads(line) for line in (Path(root) / "events.jsonl").read_text().splitlines()]
    rows = custody["children"]
    if (custody["direct"] != 6 or len(rows) != 6 or len({r["pid"] for r in rows}) != 6
        or {r["attempt_id"] for r in rows} != set(facts) or len({r["request"] for r in rows}) != 6):
        raise ValueError("custody PID/attempt/request census differs")
    for row in rows:
        actual = facts[row["attempt_id"]]
        names = ("request", "attempt_id", "pre_dispatch", "binding", "inputs", "initial_attempt", "source_sha256", "completion")
        if (any(row[n] != actual[n] for n in names) or row["waits"] != [dict(returned=True, exit=0)]
            or row.get("verified") is not True or row.get("absent") is not True):
            raise ValueError("custody actual native Q/T/P/source/wait differs")
        command = [interpreter, str(Path(actual["scratch"]) / "entry.py"), str(Path(row["workspace"]) / "worker.dml"),
                   actual["pre_dispatch"], actual["attempt_id"], actual["publication_ref"]]
        if row["command"] != command:
            raise ValueError("custody exact native command differs")
        matching = ([e for e in events if e["event"] == "dispatch" and e["request"] == row["request"]],
            [e for e in events if e["event"] == "spawn" and e["pid"] == row["pid"]],
            [e for e in events if e["event"] == "wait" and e["pid"] == row["pid"]],
            [e for e in events if e["event"] == "leaf-disposition-verified" and e["attempt_id"] == row["attempt_id"]])
        if any(len(found) != 1 for found in matching):
            raise ValueError("incremental custody primary receipt missing/duplicate")
        dispatch, spawn, wait, verified = [found[0] for found in matching]
        if (dispatch["workspace"] != row["workspace"] or spawn["command"] != command
            or any(spawn[n] != row[n] for n in names if n != "completion")
            or wait["receipt"] != dict(returned=True, exit=0) or verified["completion"] != actual["completion"]):
            raise ValueError("incremental custody primary/native associations differ")
        order = [events.index(e) for e in (dispatch, spawn, wait, verified)]
        if order != sorted(order) or len(set(order)) != 4:
            raise ValueError("primary custody ordering differs")


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] not in ("controls", "readiness", "run"):
        raise ValueError("expected controls|readiness|run ROOT")
    result = metadata_controls()[1] if args[0] == "controls" else readiness(args[1]) if args[0] == "readiness" else run(args[1])
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
