"""Opt-in sole10Q/8T/five direct LOCAL/14getter story; NO default execution."""

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
from daggerml import builtin as b, exchange as ex, local, transfer
import captured_calls as p
import captured_call_adapter as adapter
import captured_call_session as bridge
import captured_call_leaf as leaf
import captured_call_funcs as logical
import composed_node_funcs as funcs
import reuse_selection as selection
import explicit_reuse

SOURCE_NAMES = ("installed_story.py", "offline_read.py", "captured_calls.py", "captured_call_session.py",
                "captured_call_adapter.py", "captured_call_leaf.py", "captured_call_funcs.py",
                "composed_node_funcs.py", "reuse_selection.py", "explicit_reuse.py")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def append_event(root, events, category, row):
    """Controller envelope category is separate from native phase payload `kind`."""
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
    modules = {"daggerml": d, "builtin": b, "exchange": ex, "local": local, "transfer": transfer, "native": d._core}
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
    modules = {"captured_calls.py": p, "captured_call_session.py": bridge, "captured_call_adapter.py": adapter,
               "captured_call_leaf.py": leaf, "captured_call_funcs.py": logical, "composed_node_funcs.py": funcs,
               "reuse_selection.py": selection, "explicit_reuse.py": explicit_reuse}
    result = {}
    for filename, module in modules.items():
        actual = Path(module.__file__).resolve()
        if actual != directory / filename:
            raise ValueError("actual helper not from measured owned source copy")
        result[filename] = dict(path=str(actual), sha256=digest(actual))
    return result


def readiness(root):
    """Metadata-only isolated install/profile readiness: zero Q/T/getter/ordinary invocation."""
    root = Path(root).resolve()
    root.mkdir()
    permission, controls = metadata_controls()
    installed = identities()
    if EXAMPLES != DIRECTORY:
        raise ValueError("readiness requires measured isolated launch-source copy")
    helpers = helper_identities(DIRECTORY)
    sources = {n: digest(DIRECTORY / n) for n in SOURCE_NAMES}
    path = root / "metadata.dml"
    base = p.initialize(path, sys.executable)
    prepared = p.prepare_arguments(path, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs", ref="prepared")
    swapped = p.prepare_arguments(path, commit=prepared, values={"a": 29, "b": 13}, inputs_name="swapped", ref="swapped")
    with d.Repository(path) as repo, repo.read() as tx:
        entries = p.tree(tx, swapped)
        closure = p.inspect_closure(tx, swapped, entries["outer"])
        seen = set()
        original, _ = p.arguments(tx, swapped, entries["inputs"], ("a", "b"), seen)
        changed, _ = p.arguments(tx, swapped, entries["swapped"], ("a", "b"), seen)
        if original.datum == changed.datum or len(seen) != 10 or any(n.startswith(("request-", "outer-request-", "attempt-", "outer-attempt-")) for n in entries):
            raise ValueError("metadata input values/source profiles or zero occurrences differ")
        descriptors = dict(closure=str(closure["dag"]), binding=str(closure["binding"]), environment=str(closure["environment"]),
            key=str(closure["key"]), add=str(closure["add"]["dag"]), double=str(closure["double"]["dag"]),
            original_inputs=str(original.dag), swapped_inputs=str(changed.dag))
    bundle = transfer.export_commit(path, commit=swapped)
    framing = json.loads(bundle)
    result = dict(controls=controls, installed=installed, sources=sources, helpers=helpers, descriptors=descriptors,
        interpreter=sys.executable, interpreter_sha256=digest(sys.executable), prefix=sys.prefix,
        source_directory=str(DIRECTORY), metadata_only=True, semantic_input_union=10,
        native_rows=len(framing["objects"]), encoded_bytes=len(bundle),
        required_prelaunch_review=dict(actual_host_original_union=34, actual_host_requested_old_union=50,
            fixed_host_max_depth=5, authority_limit=p.MAX_AUTHORITY_DEPTH, semantic_limit=b.MAX_RECORDS,
            maps=2, map_upper_bound=3, ordinary_positions=2, outer_getters=2,
            prospective_add_additions=3, prospective_double_additions=9,
            declaration_NOT_installed_receipt=True))
    save(root / "readiness.json", result)
    return result


def pin_double(path, commit, call, ref):
    with d.Repository(path) as repo, repo.read() as tx:
        fields = tx.get_dag(call).bindings
        slot = b.scalar(tx, fields["selection-slot"], "string")
    selected, _ = p.inspect_leaf_success(path, commit=commit, slot=slot)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = p.tree(tx, commit)
        if p.DOUBLE_SLOT in entries:
            raise ValueError("initial double selection must be absent")
        entries[p.DOUBLE_SLOT] = selected.dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
    return authored


def verify_leaf_run(expected, children, row):
    """Successful-story barrier BEFORE observation/import/S; no historical PID actions."""
    if expected is None or not expected.get("spawned") or "child_index" not in expected:
        raise RuntimeError("leaf-run lacks THAT owned dispatched child")
    process, child = children[expected["child_index"]]
    if (child.get("verified") or child["waits"] != [dict(returned=True, exit=0)] or process.returncode != 0
        or row["outcome"] != "success" or row["cleanup"] != "ok"
        or row["request"] != expected["request"] or row["request"] != child["request"]
        or row["attempt_id"] != child["attempt_id"] or row["pre_dispatch"] != child["pre_dispatch"]):
        raise RuntimeError("leaf-run disposition/Q/attempt UNKNOWN-or-failed: STOP before observation/import")
    worker = Path(expected["workspace"]) / "worker.dml"
    with d.Repository(worker) as repo, repo.read() as tx:
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
    child["verified"] = True
    child["completion"] = row["completion"]


def run(root):
    root = Path(root).resolve()
    if DIRECTORY != root.parent / "launch-source" or EXAMPLES != DIRECTORY:
        raise ValueError("launch ONLY measured owned isolated source copy")
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
    events, children, expected_dispatch = [], [], [None]
    outer_requests, outer_finals, final_descriptions = [], [], []
    real_popen = subprocess.Popen
    def event(kind, row):
        append_event(root, events, kind, row)
        if kind == "dispatch":
            if expected_dispatch[0] is not None:
                raise RuntimeError("overlapping/unconsumed dispatch permission")
            expected_dispatch[0] = dict(row, outer=current_request[0])
        if kind == "leaf-run":
            verify_leaf_run(expected_dispatch[0], children, row)
            event("leaf-disposition-verified", dict(request=row["request"], attempt_id=row["attempt_id"],
                pre_dispatch=row["pre_dispatch"], completion=row["completion"], child_index=expected_dispatch[0]["child_index"]))
            expected_dispatch[0] = None
    current_request = [None]
    def tracked(command, **kwargs):
        expected = expected_dispatch[0]
        if expected is None or expected.get("spawned", False) or len(children) >= 5 or type(command) is not list or len(command) != 6 or command[0] != sys.executable or kwargs.get("shell", False):
            raise RuntimeError("only five declared direct LOCAL children allowed")
        workspace = Path(expected["workspace"])
        if command[-4] != str(workspace / "worker.dml"):
            raise RuntimeError("direct child targets unexpected repository")
        spec = ex.read_exchange_spec(workspace)
        context = local.child_context(command[-4:])
        target = current_request[0].closure["add" if expected["slot"] == 0 else "double"]
        if (str(spec.request) != expected["request"]
            or (context.request, context.binding, context.inputs) != (spec.request, target["binding"], spec.inputs)
            or command != [sys.executable, str(Path(context.scratch) / "entry.py"), context.repository_path,
                           str(context.pre_dispatch), context.attempt_id, context.publication_ref]):
            raise RuntimeError("actual expected request/native Q/B/input/exact command differs")
        with d.Repository(context.repository_path) as repo, repo.read() as tx:
            actual = b.scalar(tx, tx.get_dag(context.binding).bindings["source"], "bytes")
            if tx.get_commit(context.pre_dispatch).parents != (spec.commit,):
                raise RuntimeError("actual pre-dispatch parent differs")
        if actual != leaf.capture(target["environment"], target["intent"], *leaf.sources()) or Path(command[1]).read_bytes() != actual:
            raise RuntimeError("actual captured child entry/source differs")
        expected["spawned"] = True
        permission["popen"] = True
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
        event("spawn", dict(row))  # BEFORE later assertions/wait.
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
    caller = root / "caller.dml"
    try:
        base = p.initialize(caller, sys.executable)
        base = p.prepare_arguments(caller, commit=base, values={"a": 13, "b": 29}, inputs_name="inputs", ref="inputs")
        base = p.prepare_arguments(caller, commit=base, values={"a": 29, "b": 13}, inputs_name="swapped", ref="swapped")
        commit = base
        for number, inputs, control, double_control in ((1, "inputs", "fresh", "fresh"),
            (2, "inputs", "require-selected", "require-selected"),
            (3, "swapped", "try-selected", "require-selected"), (4, "inputs", "fresh", "fresh")):
            q = p.record_request(caller, commit=commit, inputs_name=inputs, control=control, double_control=double_control, ref="outer-%d" % number)
            current_request[0] = q
            outer_requests.append(q)
            event("outer-request", dict(number=number, request=str(q.request), submission=str(q.commit), basis=str(q.base), action=q.action,
                inputs=str(q.inputs.dag), datum=str(q.inputs.datum), closure=str(q.closure["dag"]), plan=str(q.plan)))
            if q.reused is not None:
                before = len(children)
                p.inspect_reuse(caller, commit=q.reused)
                if len(children) != before or expected_dispatch[0] is not None:
                    raise RuntimeError("outer hit invoked work")
                commit = q.reused
                outer_finals.append(commit)
                final_descriptions.append(None)
            else:
                commit = adapter.execute(caller, q, workspace=root / ("execution-%d" % number), receipt=event)
                outer_finals.append(commit)
                got = p.inspect_completion(caller, commit=commit)
                if got["outcome"] != "success":
                    raise RuntimeError("actual outer failure: STOP/no second story")
                final_descriptions.append(got)
                event("outer-completed", dict(number=number, completion=str(commit), attempt=str(got["attempt"]), result=str(got["result"]),
                    semantic_ids=sorted(str(v) for v in got["semantic_ids"])))
                if number == 1:
                    commit = p.select_outer(caller, commit=commit, completion=commit, ref="selected-outer")
                    commit = pin_double(caller, commit, got["calls"][1], "selected-double")
                    commit = p.promote_defaults(caller, commit=commit, ref="defaults")
        if len(children) != 5 or expected_dispatch[0] is not None:
            raise RuntimeError("direct launch population/permission differs")
        for process, row in children:
            if not row.get("verified") or row["waits"] != [dict(returned=True, exit=0)] or process.returncode != 0:
                raise RuntimeError("direct disposition not known zero/reaped: STOP")
            try:
                os.kill(process.pid, 0)
            except ProcessLookupError:
                row["absent"] = True
            else:
                raise RuntimeError("owned waited PID still present/uncertain; STOP")
        save(root / "custody.json", dict(children=[r for process, r in children], direct=5, descendants=0,
            qualification="fixed reviewed source; not a generic process-tree supervision guarantee"))
        # Ordinary summary, NOT another request/execution.
        with d.Repository(caller) as repo, repo.write() as tx:
            entries = p.tree(tx, commit)
            links = {"outer-q%d" % (i + 1): q.request for i, q in enumerate(outer_requests)}
            for i, got in enumerate(final_descriptions):
                if got is not None:
                    links["outer-t%d" % (i + 1)] = got["attempt"]
                    links["outer-r%d" % (i + 1)] = got["result"]
            entries["summary"] = b.record(tx, "example-captured-call-summary-v1", values={"outer-requests": 4, "outer-attempts": 3,
                "leaf-requests": 6, "leaf-attempts": 5, "ordinary-positions": 6, "getters": 14}, links=links)
            final = tx.put_commit(tx.put_tree(entries), parents=(commit,))
            tx.create_ref("story", final)
        bundle = transfer.export_commit(caller, commit=final)
        root.joinpath("full-history.bundle").write_bytes(bundle)
        with d.Repository(root / "replica.dml", create=True):
            pass
        transfer.import_commit(root / "replica.dml", bundle, ref="story")
        receipt = dict(final=str(final), sources=sources, installed=installed, helpers=helpers,
            requests=[dict(request=str(q.request), submission=str(q.commit), satisfaction=None if q.reused is None else str(q.reused)) for q in outer_requests],
            finals=[str(v) for v in outer_finals], bundle_sha256=hashlib.sha256(bundle).hexdigest(), controls=controls,
            interpreter=sys.executable, interpreter_sha256=digest(sys.executable), original_union=len(final_descriptions[0]["semantic_ids"]),
            swapped_union=len(final_descriptions[2]["semantic_ids"]))
        save(root / "receipt.json", receipt)
        # ONLY operational originals owned by this invocation; native histories remain inert.
        for number in (1, 3, 4):
            original = root / ("execution-%d" % number)
            original.rename(original.with_name(original.name + ".unavailable"))
        captured.rename(root / "captured-source.unavailable")
        DIRECTORY.rename(DIRECTORY.with_name("launch-source.unavailable"))
        return receipt
    finally:
        subprocess.Popen = real_popen
        permission["popen"] = False
        save(root / "final-disposition.json", dict(children=[dict(row, poll=process.poll()) for process, row in children],
            no_automatic_retry=True, outer_computation_finished=len(outer_finals) == 4))


def read(root):
    """SAME retained history inspection only. Caller activates blockers BEFORE importing."""
    root = Path(root)
    receipt = json.loads((root / "receipt.json").read_bytes())
    expected = d.ObjectId.from_hex(receipt["final"])
    result = {}
    for repository in (root / "caller.dml", root / "replica.dml"):
        with d.Repository(repository) as repo, repo.read() as tx:
            if tx.get_ref("story") != expected:
                raise ValueError("retained story root differs")
            entries = p.tree(tx, expected)
            qids, leaf_qids = set(), set()
            outer_attempts, leaf_attempts = set(), set()
            for current in p.history(tx, expected):
                for name, dag in p.tree(tx, current).items():
                    if name.startswith("outer-request-cq-") or name.startswith("request-q-"):
                        qids.add(dag)
                        if name.startswith("request-q-"):
                            leaf_qids.add(dag)
                    if name.startswith("outer-attempt-ca-"):
                        outer_attempts.add(b.scalar(tx, tx.get_dag(dag).root, "string"))
                    if name.startswith("attempt-a-"):
                        leaf_attempts.add(b.scalar(tx, tx.get_dag(dag).root, "string"))
            if (len(qids), len(outer_attempts), len(leaf_attempts)) != (10, 3, 5):
                raise ValueError("actual ALL-parent Q/T population differs")
        selected = p.inspect_selection(repository, commit=expected)
        getters = calls = 0
        descriptions = []
        pending_requests, producing_attempts = set(), set()
        with d.Repository(repository) as repo, repo.read() as tx:
            captured = p.inspect_closure(tx, expected, entries["outer"])
            if (captured["add"]["dag"], captured["double"]["dag"]) != (entries["add-A"], entries["double-A"]):
                raise ValueError("actual retained outer/add-A/double-A captures differ")
            if selected["closure"] != captured:
                raise ValueError("selected ORIGINAL closure not capturedA")
        for i, row in enumerate(receipt["requests"]):
            q = p.inspect_request(repository, commit=d.ObjectId.from_hex(row["submission"]), request=d.ObjectId.from_hex(row["request"]))
            final = d.ObjectId.from_hex(receipt["finals"][i])
            if row["satisfaction"] is not None:
                if i != 1 or p.inspect_reuse(repository, commit=final).selected["attempt"] != selected["attempt"]:
                    raise ValueError("outer hit OLD selected attempt differs")
                descriptions.append(None)
                continue
            got = p.inspect_completion(repository, commit=final)
            if got["outcome"] != "success" or got["closure"] != selected["closure"]:
                raise ValueError("actual fresh captured closure/outcome differs")
            getters += len(got["getters"])
            calls += len(got["calls"])
            descriptions.append(got)
            with d.Repository(repository) as repo, repo.read() as tx:
                if tx.get_datum(got["datum"]) != d.Datum.i64(84):
                    raise ValueError("actual recorded outer result is not84")
                for call in got["calls"]:
                    fields = tx.get_dag(call).bindings
                    # Public original-S validation already finished outside these read scopes.
                    if b.scalar(tx, fields["status"], "string") != "success":
                        raise ValueError("successful summary contains failed call")
                    pending = tx.get_dag(b.link(tx, fields["pending"])).bindings
                    pending_requests.add(b.link(tx, pending["request"]))
                    producing = b.link(tx, fields["attempt"])
                    producing_attempts.add(b.scalar(tx, tx.get_dag(producing).root, "string"))
                    slot = b.scalar(tx, pending["slot"], "i64")
                    target = captured["add" if slot == 0 else "double"]
                    if b.link(tx, pending["closure"]) != target["dag"]:
                        raise ValueError("actual call target not capturedA")
        # Actual unique leaf attempts contribute their normal trace positions once EACH,
        # outer getters are additional even where their immutable operation DAG IDs share.
        with d.Repository(repository) as repo, repo.read() as tx:
            original_requests, final_attempts = set(), {}
            for current in p.history(tx, expected):
                for name, dag in p.tree(tx, current).items():
                    if name.startswith("attempt-a-") and "status" in tx.get_dag(dag).bindings:
                        fields = tx.get_dag(dag).bindings
                        original_requests.add(b.link(tx, fields["request"]))
                        final_attempts[b.scalar(tx, tx.get_dag(dag).root, "string")] = dag
            for final_attempt in final_attempts.values():
                fields = tx.get_dag(final_attempt).bindings
                request = b.link(tx, fields["request"])
                qfields = tx.get_dag(request).bindings
                outcome = tx.get_dag(b.link(tx, fields["outcome"])).bindings
                if b.scalar(tx, outcome["role"], "string") != "local-success-v1":
                    raise ValueError("actual final LOCAL attempt not successful")
                returned = tx.get_dag(b.link(tx, outcome["result"])).bindings
                actual_trace = b.Inspector(tx, commit=expected).trace(b.link(tx, returned["trace"]),
                    request=request, inputs=b.link(tx, qfields["inputs"]))
                getters += len(actual_trace)
            if pending_requests != leaf_qids or producing_attempts != leaf_attempts:
                raise ValueError("census must EQUAL actual pending ownQ/producing T ledger sets")
            if getters != 14 or calls != 6 or len(original_requests) != 5:
                raise ValueError("actual independent getter/call positions differ")
            facts = {}
            for aid, final_attempt in final_attempts.items():
                fields = tx.get_dag(final_attempt).bindings
                request = b.link(tx, fields["request"])
                qfields = tx.get_dag(request).bindings
                binding = b.link(tx, qfields["binding"])
                source = b.scalar(tx, tx.get_dag(binding).bindings["source"], "bytes")
                # Find the exact ORIGINAL successful selection/F for this final attempt.
                selections = [v for v in entries.values() if "role" in tx.get_dag(v).bindings and
                    b.scalar(tx, tx.get_dag(v).bindings["role"], "string") == "example-reuse-selection-v1"
                    and b.link(tx, tx.get_dag(v).bindings["attempt"]) == final_attempt]
                if not selections:
                    raise ValueError("original LOCAL attempt lacks retained successful S")
                sf = tx.get_dag(selections[0]).bindings
                completion = p.oid(tx, sf["completion"])
                pre = tx.get_commit(completion).parents[0]
                initial = p.tree(tx, pre)["attempt-" + aid]
                scratch = b.scalar(tx, fields["scratch"], "string")
                facts[aid] = dict(request=str(request), attempt_id=aid, pre_dispatch=str(pre),
                    binding=str(binding), inputs=str(b.link(tx, qfields["inputs"])), initial_attempt=str(initial),
                    publication_ref=b.scalar(tx, fields["publication-ref"], "string"), scratch=scratch,
                    source_sha256=hashlib.sha256(source).hexdigest(), completion=str(completion))
            verify_custody(root, facts, receipt["interpreter"])
            first_call = tx.get_dag(descriptions[0]["calls"][1]).bindings
            reused_call = tx.get_dag(descriptions[2]["calls"][1]).bindings
            if tuple(b.link(tx, first_call[n]) for n in ("attempt", "result")) != tuple(b.link(tx, reused_call[n]) for n in ("attempt", "result")):
                raise ValueError("swapped double must retain OLD producing T/R")
            if entries[p.DOUBLE_SLOT] != b.link(tx, first_call["selection"]):
                raise ValueError("fresh work adopted double automatically")
            if entries["default-add"] != entries["add-B"] or entries["default-double"] != entries["double-B"]:
                raise ValueError("actual convenience default promotion missing")
            requested = tx.get_dag(b.link(tx, reused_call["pending"])).bindings
            original = tx.get_dag(b.link(tx, first_call["pending"])).bindings
            if b.link(tx, requested["request"]) == b.link(tx, original["request"]):
                raise ValueError("swapped reuse must have own NEW leaf Q")
            new_inputs, new_sources = p.arguments(tx, expected, b.link(tx, requested["inputs"]), ("x",), set())
            old_inputs, old_sources = p.arguments(tx, expected, b.link(tx, original["inputs"]), ("x",), set())
            actual_new_add = b.link(tx, tx.get_dag(descriptions[2]["calls"][0]).bindings["result"])
            actual_old_add = b.link(tx, tx.get_dag(descriptions[0]["calls"][0]).bindings["result"])
            if (new_inputs.datum != old_inputs.datum or new_sources["x"].dag != actual_new_add
                or old_sources["x"].dag != actual_old_add or actual_new_add == actual_old_add):
                raise ValueError("requested versus ORIGINAL exact add R source chains differ")
            summary = b.shape(tx, entries["summary"], ("role", "outer-requests", "outer-attempts", "leaf-requests", "leaf-attempts", "ordinary-positions", "getters",
                "outer-q1", "outer-q2", "outer-q3", "outer-q4", "outer-t1", "outer-t3", "outer-t4", "outer-r1", "outer-r3", "outer-r4"), "example-captured-call-summary-v1")
            for n, value in (("outer-requests", 4), ("outer-attempts", 3), ("leaf-requests", 6), ("leaf-attempts", 5), ("ordinary-positions", 6), ("getters", 14)):
                if b.scalar(tx, summary[n], "i64") != value:
                    raise ValueError("summary counts differ")
            for i, row in enumerate(receipt["requests"]):
                if b.link(tx, summary["outer-q%d" % (i + 1)]) != d.ObjectId.from_hex(row["request"]):
                    raise ValueError("summary actual request links differ")
                if descriptions[i] is not None:
                    for prefix, field in (("outer-t", "attempt"), ("outer-r", "result")):
                        if b.link(tx, summary[prefix + str(i + 1)]) != descriptions[i][field]:
                            raise ValueError("summary actual attempt/result links differ")
        result[str(repository)] = dict(requests=10, outer_attempts=3, local_attempts=5, ordinary_positions=calls, getters=getters,
            original_union=len(descriptions[0]["semantic_ids"]), swapped_union=len(descriptions[2]["semantic_ids"]))
    return result


def verify_custody(root, facts, interpreter):
    """Match retained primary PID receipts to actual native attempts; NEVER signal historical PIDs."""
    custody = json.loads((Path(root) / "custody.json").read_bytes())
    events = [json.loads(line) for line in (Path(root) / "events.jsonl").read_text().splitlines()]
    rows = custody["children"]
    if len(rows) != 5 or len({r["pid"] for r in rows}) != 5 or {r["attempt_id"] for r in rows} != set(facts):
        raise ValueError("custody unique PID/actual native attempt census differs")
    if len({r["request"] for r in rows}) != 5:
        raise ValueError("custody requests must be unique original fresh Q")
    for row in rows:
        actual = facts[row["attempt_id"]]
        names = ("request", "attempt_id", "pre_dispatch", "binding", "inputs", "initial_attempt", "source_sha256", "completion")
        if (any(row[n] != actual[n] for n in names) or row["waits"] != [dict(returned=True, exit=0)]
            or row.get("verified") is not True or row.get("absent") is not True):
            raise ValueError("custody row does not match actual original native Q/T/P/source/wait")
        command = [interpreter, str(Path(actual["scratch"]) / "entry.py"), str(Path(row["workspace"]) / "worker.dml"),
                   actual["pre_dispatch"], actual["attempt_id"], actual["publication_ref"]]
        if row["command"] != command:
            raise ValueError("custody exact command/native tail/interpreter differs")
        dispatch = [e for e in events if e["event"] == "dispatch" and e["request"] == row["request"]]
        spawn = [e for e in events if e["event"] == "spawn" and e["pid"] == row["pid"]]
        wait = [e for e in events if e["event"] == "wait" and e["pid"] == row["pid"]]
        verified = [e for e in events if e["event"] == "leaf-disposition-verified" and e["attempt_id"] == row["attempt_id"]]
        if (len(dispatch) != 1 or len(spawn) != 1 or len(wait) != 1 or len(verified) != 1
            or dispatch[0]["workspace"] != row["workspace"] or spawn[0]["command"] != command
            or any(spawn[0][n] != row[n] for n in names if n != "completion")
            or wait[0]["receipt"] != dict(returned=True, exit=0)
            or verified[0]["completion"] != actual["completion"]):
            raise ValueError("incremental dispatch/spawn/wait/verified primary receipts differ")
        order = [events.index(e[0]) for e in (dispatch, spawn, wait, verified)]
        if order != sorted(order) or len(set(order)) != 4:
            raise ValueError("primary disposition ordering differs")


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] not in ("controls", "readiness", "run"):
        raise ValueError("expected controls|readiness|run ROOT")
    result = metadata_controls()[1] if args[0] == "controls" else readiness(args[1]) if args[0] == "readiness" else run(args[1])
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
