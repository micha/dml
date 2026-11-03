"""Short owned recording scopes and ONE application-owned synchronous leaf bridge."""

from functools import wraps
from pathlib import Path
import uuid

import daggerml as d
from daggerml import builtin as b, exchange as ex, local, transfer
import captured_calls as p
import captured_call_leaf as leaf
import reuse_selection as selection


class SessionError(ValueError):
    """Known cooperative interface error; never represents uncertain native persistence."""


class LeafFailure(SessionError):
    """Public recorded leaf failure after synchronous runner established disposition."""


class Node:
    __slots__ = ("__value",)

    def __init__(self, value):
        self.__value = value

    @property
    def value(self):
        return self.__value


class Nodes:
    __slots__ = ("__get", "__arguments")

    def __init__(self, get, arguments):
        self.__get, self.__arguments = get, arguments

    def map_get(self, node, key):
        return self.__get(node, key)

    def arguments(self, entries):
        return self.__arguments(entries)


class Calls:
    __slots__ = ("__invoke",)

    def __init__(self, invoke):
        self.__invoke = invoke

    def invoke(self, target, arguments):
        return self.__invoke(target, arguments)


def guarded(method):
    @wraps(method)
    def invoke(self, *args, **kwargs):
        if self.ended or self.poisoned:
            raise SessionError("session ended or poisoned")
        try:
            return method(self, *args, **kwargs)
        except BaseException as error:
            self.poisoned = True
            if not isinstance(error, SessionError):
                self.unknown = True
            raise
    return invoke


class Session:
    """No repository/transaction/native handle survives a method or dispatch boundary.

    `seen` accumulates ORIGINAL/requested semantic IDs across ALL scopes/validators.
    Native Recorder reservations stay unchanged; aggregate conservative reservation
    happens BEFORE new semantic puts. Public S validation precedes handle delivery.
    """

    def __init__(self, path, request, workspace, receipt=None):
        self.path, self.q, self.workspace = Path(path), request, Path(workspace)
        self.receipt = receipt or (lambda kind, row: None)
        self.seen, self.handles, self.getters, self.calls = set(), {}, [], []
        self.maps, self.index = 1, 0
        self.poisoned = self.unknown = self.ended = False
        self.failed_call = self.returned = None
        self.upstream_slot = None
        self.current = request.commit
        actual = p.inspect_request(path, commit=request.commit, request=request.request, seen=self.seen)
        if actual != request or actual.action != "execute-fresh":
            raise SessionError("only actual pending fresh outer Q may execute")
        self.seen.update((request.closure["map_binding"], request.closure["add"]["list_binding"],
                          request.closure["double"]["map_binding"], request.closure["add"]["map_binding"]))
        p.budget(self.seen)
        self.tokens = (object(), object())
        self.nodes, self.invoker = Nodes(self.map_get, self.arguments), Calls(self.invoke)
        self.workspace.mkdir()
        self.aid = "ca-" + uuid.uuid4().hex
        with d.Repository(path) as repo, repo.write() as tx:
            entries = p.tree(tx, self.current)
            if tx.get_ref("outer-request-" + request.request_id) != request.commit:
                raise ValueError("actual outer request reservation differs before attempt")
            self.initial = p.event(tx, p.T_ROLE, self.aid, links={"request": request.request, "plan": request.plan})
            entries["outer-attempt-" + self.aid] = self.initial
            authored = tx.put_commit(tx.put_tree(entries), parents=(self.current,))
            tx.create_ref("outer-head-" + self.aid, authored)
            self.current = authored
        self.input = self._load(request.inputs.dag)
        self.receipt("initial", dict(commit=str(self.current), request=str(request.request), initial=str(self.initial), attempt_id=self.aid))

    def _reserve(self, count):
        if len(self.seen) + count > b.MAX_RECORDS:
            raise SessionError("prospective aggregate semantic reservation exceeds64")

    def _load(self, dag):
        with d.Repository(self.path) as repo, repo.read() as tx:
            inspector = b.Inspector(tx, commit=self.current)
            actual = inspector.node(dag)
            self.seen.update(inspector.seen)
        p.budget(self.seen)
        node = Node(actual.value)
        self.handles[node] = (dag, actual.datum)
        return node

    def _owned(self, node):
        if type(node) is not Node or node not in self.handles:
            raise SessionError("foreign/fabricated/ended session node")
        dag, datum = self.handles[node]
        with d.Repository(self.path) as repo, repo.read() as tx:
            inspector = b.Inspector(tx, commit=self.current)
            actual = inspector.node(dag)
            self.seen.update(inspector.seen)
        p.budget(self.seen)
        if actual.datum != datum or actual.value != node.value:
            raise SessionError("copied node/native association differs")
        return dag

    def _advance(self, target):
        # External public Q/S/W publication and this navigation update are separate boundaries.
        with d.Repository(self.path) as repo, repo.write() as tx:
            if tx.get_ref("outer-head-" + self.aid) != self.current:
                raise ValueError("outer phase head changed")
            tx.update_ref("outer-head-" + self.aid, target)
        self.current = target

    def _phase(self, kind, *, links=(), values=(), second=None, author=None):
        """One exact checked batch, optional semantic author callback in THIS short scope."""
        previous = self.current
        with d.Repository(self.path) as repo, repo.write() as tx:
            if tx.get_ref("outer-head-" + self.aid) != previous:
                raise ValueError("outer phase head changed")
            actual_links = dict(links)
            if author is not None:
                actual_links.update(author(tx, previous))
            entries = p.tree(tx, previous)
            payloads = p.payload_names(self.aid, self.index, kind)
            phase = p.phase_name(self.aid, self.index)
            if set(actual_links) != set(p.PHASE_LINKS[kind]) or set(dict(values)) != set(p.PHASE_VALUES[kind]):
                raise ValueError("phase fields differ from fixed kind")
            if any(n in entries for n in (*payloads.values(), phase)):
                raise ValueError("phase name already present")
            fields = dict(request=self.q.request, **{"initial-attempt": self.initial}, **actual_links)
            metadata = dict(kind=kind, index=self.index, previous=previous.bytes, **dict(values))
            entries[phase] = b.record(tx, p.PHASE_ROLE, values=metadata, links=fields)
            entries.update((payloads[n], target) for n, target in actual_links.items())
            parents = (previous,) if second is None else (previous, second)
            authored = tx.put_commit(tx.put_tree(entries), parents=parents)
            tx.update_ref("outer-head-" + self.aid, authored)
            response = (authored, actual_links)
        self.current = authored
        self.index += 1
        self.receipt("phase", dict(commit=str(authored), previous=str(previous), kind=kind, links={n: str(v) for n, v in actual_links.items()}, index=self.index - 1))
        return response[1]

    @guarded
    def map_get(self, node, key):
        if len(self.getters) >= 2 or node is not self.input or key not in ("a", "b") or key != ("a", "b")[len(self.getters)] or self.calls:
            raise SessionError("two ordered input getters must precede calls")
        dag = self._owned(node)
        self._reserve(6)
        def author(tx, commit):
            with b.Recorder(tx, commit=commit) as rec:
                arguments = rec.arguments({"map": rec.load(dag), "key": rec.literal(d.Datum.string(key))})
                result = rec.call(b.MAP_GET, self.q.closure["map_binding"], arguments)
                target = rec.dag(result)
                self.seen.update(rec.inspector.seen)
                p.budget(self.seen)
                return {"node": target}
        target = self._phase("get-" + key, author=author)["node"]
        self.getters.append(target)
        return self._load(target)

    @guarded
    def arguments(self, entries):
        if (type(entries) is not dict or self.maps != 1 or len(self.calls) != 1 or set(entries) != {"x"}
            or entries["x"] is not self.last_result):
            raise SessionError("only double map from THIS exact returned add node is supported")
        source = self._owned(entries["x"])
        self._reserve(3)
        def author(tx, commit):
            with b.Recorder(tx, commit=commit) as rec:
                target = rec.dag(rec.arguments({"x": rec.load(source)}))
                self.seen.update(rec.inspector.seen)
                p.budget(self.seen)
                return {"inputs": target}
        target = self._phase("double-input", author=author)["inputs"]
        self.maps += 1
        self.double_input = self._load(target)
        return self.double_input

    @guarded
    def invoke(self, token, node):
        slot = len(self.calls)
        if slot >= 2 or token is not self.tokens[slot] or len(self.getters) != 2:
            raise SessionError("unbound target/call order/getter dispatch guard")
        expected_node = self.input if slot == 0 else getattr(self, "double_input", None)
        if node is not expected_node:
            raise SessionError("ordinary call must consume exact declared input node")
        inputs = self._owned(node)
        spine = p.inspect_spine(self.path, self.current, self.q.request, self.initial, self.aid, self.seen)
        if tuple(spine["getters"]) != tuple(self.getters) or tuple(spine["calls"]) != tuple(self.calls) or spine["failed"] is not None:
            raise ValueError("actual getter/call guard differs before dispatch")
        with d.Repository(self.path) as repo, repo.read() as tx:
            for getter, key in zip(self.getters, ("a", "b")):
                p.inspect_getter(tx, self.current, getter, self.q.inputs.dag, key, self.q.closure["map_binding"], self.seen)
        # Actual logical getter results must be I64; revalidate guard before any own leaf Q.
        target = self.q.closure["add" if slot == 0 else "double"]
        with d.Repository(self.path) as repo, repo.read() as tx:
            pf = tx.get_dag(self.q.plan).bindings
            control = "fresh" if slot == 0 else b.scalar(tx, pf["double-control"], "string")
            has_selected = "double-selection" in pf
            pinned = b.link(tx, pf["double-selection"]) if has_selected else None
            basis = p.oid(tx, pf["basis"])
            requested, _ = p.arguments(tx, self.current, inputs, leaf.contract(target["intent"])[1], self.seen)
        selected = p.inspect_leaf_success(self.path, commit=basis, slot=p.DOUBLE_SLOT, seen=self.seen)[0] if slot == 1 and has_selected else None
        if selected is not None and selected.dag != pinned:
            raise ValueError("pinned double selection changed")
        if selected is not None:
            with d.Repository(self.path) as repo, repo.read() as tx:
                old, _ = p.arguments(tx, basis, selected.inputs, ("x",), self.seen)
            hit = selected.binding == target["binding"] and old.datum == requested.datum
        else:
            hit = False
        reuse = control != "fresh" and hit
        if control == "require-selected" and not hit:
            raise SessionError("required double selection does not match")
        bn = p.payload_names(self.aid, self.index, "leaf-prepare")["binding"]
        inn = p.payload_names(self.aid, self.index, "leaf-prepare")["inputs"]
        basis = self.current
        def author(tx, commit):
            links = {"outer-request": self.q.request, "outer-attempt": self.initial, "closure": target["dag"],
                     "binding": target["binding"], "environment": target["environment"], "key": target["key"], "inputs": inputs}
            values = {"slot": slot, "control": "reuse-selected" if reuse else "fresh", "binding-name": bn, "inputs-name": inn, "basis": commit.bytes}
            if slot == 1:
                links["upstream"] = self.upstream.dag
                values["upstream-slot"] = self.upstream_slot
            return {"binding": target["binding"], "inputs": inputs,
                    "decision": b.record(tx, p.LEAF_D_ROLE, values=values, links=links)}
        self._phase("leaf-prepare", values={"slot": slot}, author=author)
        preparation = self.current
        submission_ref = "leaf-submission-" + self.aid + "-%d" % slot
        recorded = ex.record_exchange_request(self.path, commit=preparation, binding_name=bn, inputs_name=inn,
                                             intent_uri=target["intent"], ref=submission_ref)
        p.validate_recorded(self.path, recorded, preparation, bn, inn, target, inputs, submission_ref)
        self._advance(recorded.commit)
        def pending(tx, commit):
            return {"call": b.record(tx, p.CALL_ROLE, values={"slot": slot, "control": "reuse-selected" if reuse else "fresh"},
                links={"outer-request": self.q.request, "outer-attempt": self.initial, "closure": target["dag"], "inputs": inputs, "request": recorded.request})}
        pending_id = self._phase("leaf-pending", values={"submission": recorded.commit.bytes}, author=pending)["call"]
        self.receipt("leaf-request", dict(request=str(recorded.request), submission=str(recorded.commit), slot=slot,
            inputs=str(inputs), action="reuse-selected" if reuse else "execute-fresh", pending=str(pending_id)))
        # Independently reread THIS persisted preparation/pending/public Q before either
        # external dispatch or OLD witness satisfaction; descriptions are not authority.
        p.inspect_spine(self.path, self.current, self.q.request, self.initial, self.aid, self.seen)
        if reuse:
            self._reuse(recorded, selected)
            witness_slot = p.DOUBLE_SLOT
        else:
            # Fixed add getters share already certified original-input operations;
            # reserve result literal+trace+return before ANY fresh child dispatch.
            # Double reserves its getter preparation/operation6 plus return3.
            self._reserve(3 if slot == 0 else 9)
            selected, witness_slot = self._execute(recorded, pending_id, slot)
        done = self._phase("leaf-done", author=lambda tx, commit: {"call": b.record(tx, p.CALL_ROLE,
            values={"status": "success", "selection-slot": witness_slot},
            links={"pending": pending_id, "selection": selected.dag, "attempt": selected.attempt, "result": selected.result})})["call"]
        self.calls.append(done)
        self.last_result = self._load(selected.result)
        if slot == 0:
            self.upstream, self.upstream_slot = selected, witness_slot
        return self.last_result

    def _reuse(self, recorded, selected):
        with d.Repository(self.path) as repo, repo.write() as tx:
            entries = p.tree(tx, self.current)
            wn = "reuse-" + recorded.request_id
            entries[wn] = b.record(tx, "example-explicit-reuse-v1", links={"request": recorded.request,
                "attempt": selected.attempt, "result": selected.result}, root="result")
            authored = tx.put_commit(tx.put_tree(entries), parents=(self.current,))
            tx.create_ref("leaf-reuse-" + recorded.request_id, authored)
        self._advance(authored)
        self._phase("leaf-reused", values={"reuse-commit": authored.bytes}, links={"reuse": entries[wn]})

    def _execute(self, recorded, pending, slot):
        workspace = self.workspace / ("leaf-%d" % slot)
        spec = ex.prepare_exchange(self.path, commit=recorded.commit, request=recorded.request,
            binding_name=recorded.binding_name, inputs_name=recorded.inputs_name,
            intent_uri=recorded.intent_uri, worker_ref="work", workspace=workspace)
        expected = self.workspace / ("expected-%d.json" % slot)
        handle = ex.ExchangeHandle(workspace, spec)
        ex.save_exchange_handle(expected, handle)
        self.receipt("dispatch", dict(slot=slot, request=str(recorded.request), workspace=str(workspace), expected=str(expected)))
        # Exactly one synchronous direct child; no outer subprocess or async owner.
        run = ex.execute_exchange(workspace)
        self.receipt("leaf-run", dict(slot=slot, outcome=run.outcome, completion=str(run.final_commit), attempt_id=run.attempt_id,
            cleanup=run.cleanup, request=str(run.context.request), pre_dispatch=str(run.context.pre_dispatch),
            initial_attempt=str(run.context.attempt), binding=str(run.context.binding), inputs=str(run.context.inputs)))
        packet = self.workspace / ("packet-%d" % slot)
        observed = ex.observe_exchange(handle, packet=packet)
        received = ex.receive_exchange(self.path, workspace=workspace, expected=spec, ref="leaf-F-" + self.aid + "-%d" % slot)
        if received.commit != run.final_commit or observed.snapshot.commit != received.commit:
            raise ValueError("public completion/observation differs")
        self._phase("leaf-join", values={"completion": received.commit.bytes}, second=received.commit)
        if received.outcome != "success":
            headers = tuple(f.read_bytes() for f in (expected, packet / "job.json", packet / "observation.json"))
            def fail(tx, commit):
                witness = b.record(tx, p.PREFIX + "failure-witness-v1", values=dict(zip(("expected", "job", "observation"), headers), completion=received.commit.bytes), links={"request": recorded.request})
                return {"call": b.record(tx, p.CALL_ROLE, values={"status": "failure"}, links={"pending": pending, "witness": witness})}
            self.failed_call = self._phase("leaf-done", author=fail)["call"]
            self.calls.append(self.failed_call)
            raise LeafFailure("recorded leaf failure: " + str(received.reason))
        slot_name = "leaf-witness-" + self.aid + "-%d" % slot
        basis = self.current
        ref = "leaf-selected-" + self.aid + "-%d" % slot
        selected = selection.select(self.path, commit=basis, slot=slot_name, binding_name=recorded.binding_name,
            inputs_name=recorded.inputs_name, intent_uri=recorded.intent_uri, packet=packet, expected_file=expected,
            ref=ref)
        with d.Repository(self.path) as repo, repo.read() as tx:
            if p.single_delta(tx, selected.commit, (slot_name,)) != basis or tx.get_ref(ref) != selected.commit:
                raise ValueError("actual S must follow THIS joined phase")
        self._advance(selected.commit)
        self._phase("leaf-selected", values={"selection-commit": selected.commit.bytes, "selection-slot": slot_name}, links={"selection": selected.dag})
        actual, _ = p.inspect_leaf_success(self.path, commit=self.current, slot=slot_name, seen=self.seen)
        return actual, slot_name

    @guarded
    def finish(self, node):
        if len(self.calls) != 2 or node is not self.last_result or self.failed_call is not None:
            raise SessionError("outer success requires both actual calls/exact returned node")
        result = self._owned(node)
        # Native associations, not logical response flags, authorize terminal publication.
        spine = p.inspect_spine(self.path, self.current, self.q.request, self.initial, self.aid, self.seen)
        if tuple(spine["calls"]) != tuple(self.calls) or tuple(spine["getters"]) != tuple(self.getters) or spine["failed"] is not None:
            raise ValueError("actual successful spine differs before return")
        with d.Repository(self.path) as repo, repo.read() as tx:
            actual = b.Inspector(tx, commit=self.current).node(result)
        links = {"request": self.q.request, "initial-attempt": self.initial, "inputs": self.q.inputs.dag, "returned": result,
            "call0": self.calls[0], "call1": self.calls[1], "getter0": self.getters[0], "getter1": self.getters[1]}
        self.returned = self._phase("returned", author=lambda tx, commit: {"return": b.record(tx, p.RETURN_ROLE,
            links=links, nodes={"value": tx.put_literal(actual.datum)}, root="value")})["return"]
        return self._complete(p.SUCCESS_ROLE)

    def fail(self, error):
        if self.ended or self.unknown:
            raise RuntimeError("partial outer outcome UNKNOWN; no terminal publication") from error
        role = p.FAILURE_ROLE if self.failed_call is not None else p.ERROR_ROLE
        return self._complete(role, error)

    def _complete(self, role, error=None):
        previous = self.current
        with d.Repository(self.path) as repo, repo.write() as tx:
            if tx.get_ref("outer-head-" + self.aid) != previous:
                raise ValueError("terminal head changed")
            entries = p.tree(tx, previous)
            calls = b.record(tx, p.LEDGER_ROLE, links={"slot-%02d" % i: dag for i, dag in enumerate(self.calls)})
            links = {"request": self.q.request, "initial-attempt": self.initial, "plan": self.q.plan, "calls": calls}
            values = {}
            if role == p.SUCCESS_ROLE:
                links["return"] = self.returned
            elif role == p.FAILURE_ROLE:
                links["failed-call"] = self.failed_call
            else:
                values = {"reason": "session-error", "detail": str(error).encode("utf-8", "replace")[:4096].decode("utf-8", "ignore")}
            completion = b.record(tx, role, values=values, links=links)
            initial = tx.get_dag(self.initial).bindings
            fields = dict(initial)
            fields.update({"initial-attempt": tx.put_subdag(self.initial), "status": b.literal(tx, "done"), "completion": tx.put_subdag(completion)})
            final = tx.put_dag(root=tx.get_dag(self.initial).root, bindings=fields)
            entries["outer-attempt-" + self.aid] = final
            entries["outer-completion-" + self.aid] = completion
            authored = tx.put_commit(tx.put_tree(entries), parents=(previous,))
            tx.update_ref("outer-head-" + self.aid, authored)
        self.current, self.ended = authored, True
        self.receipt("completion", dict(commit=str(authored), role=role, final_attempt=str(final), semantic_ids=sorted(str(v) for v in self.seen)))
        return authored
