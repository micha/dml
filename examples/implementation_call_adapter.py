"""Fixed in-process outer adapter and common-facade entry; not an executable registry."""

from dataclasses import dataclass
from pathlib import Path
import types

import daggerml as d
from daggerml import builtin as b, calls as c
import implementation_calls as p
from implementation_call_session import Session, SessionError


@dataclass(frozen=True)
class Invocation:
    request: p.Request
    commit: d.ObjectId
    node: c.Node
    semantic_ids: frozenset


def execute(path, request, *, workspace, receipt=None):
    """Trusted fixed adapter, reached only by outer Context.invoke integration.

    Leaf single-publication writers contain ONLY builtin work. Session scopes end
    before public ordinary dispatch/S scratch/import/wait. Native uncertainty leaves
    durable partial history, never fabricated local outer cleanup or success.
    """
    if request.action != "execute-fresh" or request.reused is not None:
        raise ValueError("outer hit cannot enter adapter or create an attempt")
    session = Session(path, request, workspace, receipt)
    logical = types.ModuleType("implementation_sum_then_double")
    try:
        source = p.outer_sources()[0]
        exec(compile(source, str(Path(__file__).with_name("implementation_call_funcs.py")), "exec"), logical.__dict__)
        with session.context:
            session.start()
            func = logical.double_sum(*session.tokens, session.nodes, session.invoker)
            result = func(session.input)
            return session.finish(result)
    except (SessionError, c.CallError, ValueError, OverflowError) as error:
        return session.fail(error)
    finally:
        session.ended = True


class EntryBackend:
    """Trusted outer entry integration. All outer entries actually traverse Context.invoke.

    The response commit is not proof: verify freshly derives THIS native own Q,
    fixed target/input and either actual completion or precisely pinned OLD S/W.
    An independently valid OLD result cannot replace THIS association.
    """

    def __init__(self, path, commit, closure_name, inputs_name, controls, ref, workspace, receipt):
        self.path, self.current = Path(path), commit
        self.closure_name, self.inputs_name = closure_name, inputs_name
        self.controls, self.ref = controls, ref
        self.workspace, self.receipt = workspace, receipt
        self.seen, self.request, self.last = set(), None, None
        with d.Repository(path) as repo, repo.read() as tx:
            entries = p.tree(tx, commit)
            self.closure = p.inspect_closure(tx, commit, entries[closure_name])
            self.inputs = entries[inputs_name]
        p.requested_bindings(self.closure, self.seen)

    def bind(self, bound):
        if (bound.kind, bound.intent, bound.target) != ("ordinary", p.INTENT, self.closure["dag"]):
            raise c.CallError("only THIS explicitly selected outer closure may bind")
        with d.Repository(self.path) as repo, repo.read() as tx:
            if p.inspect_closure(tx, self.current, bound.target) != self.closure:
                raise c.CallError("native requested outer closure changed")
        p.requested_bindings(self.closure, self.seen)

    def read(self, dag):
        if dag == self.inputs:
            with d.Repository(self.path) as repo, repo.read() as tx:
                actual, _ = p.arguments(tx, self.current, dag, ("a", "b"), self.seen)
                return actual
        if self.last is None or self.request is None:
            raise c.CallError("entry cannot load arbitrary result")
        got = self._authority()
        if dag != got["result"]:
            raise c.CallError("result is not THIS native invocation or pinned OLD S")
        with d.Repository(self.path) as repo, repo.read() as tx:
            return b.Description(dag, got["datum"], tx.get_datum(got["datum"]))

    def literal(self, value):
        raise c.CallError("entry logical interface cannot fabricate argument values")

    def arguments(self, entries):
        raise c.CallError("entry must consume prepared exact input node")

    def perform(self, bound, arguments):
        if self.request is not None or (bound.target, arguments.dag) != (self.closure["dag"], self.inputs):
            raise c.CallError("entry invocation target/input or once-only boundary differs")
        # ALL selections are validated by record_request even fresh/mismatch.
        self.request = p.record_request(self.path, commit=self.current, closure_name=self.closure_name,
            inputs_name=self.inputs_name, ref=self.ref, **self.controls)
        if self.receipt is not None:
            self.receipt("outer-request", dict(request=str(self.request.request), submission=str(self.request.commit),
                closure=str(bound.target), inputs=str(arguments.dag), action=self.request.action))
        self.current = self.request.reused if self.request.reused is not None else execute(
            self.path, self.request, workspace=self.workspace, receipt=self.receipt)
        self.last = (self.request.request, self.current)
        return self.last

    def _authority(self):
        q = p.inspect_request(self.path, commit=self.request.commit, request=self.request.request, seen=self.seen)
        if (q.closure, q.inputs.dag, q.plan, q.action) != (
            self.closure, self.inputs, self.request.plan, self.request.action):
            raise c.CallError("THIS native own outer request differs")
        if q.action == "reuse-selected":
            reused = p.inspect_reuse(self.path, commit=self.current, seen=self.seen)
            if reused.request != q.request or reused.selected["dag"] != q.selected["dag"]:
                raise c.CallError("THIS outer W does not consume pinned OLD S")
            return reused.selected
        got = p.inspect_completion(self.path, commit=self.current, seen=self.seen)
        if (got["request"], got["closure"], got["outcome"]) != (q.request, q.closure, "success"):
            raise c.CallError("THIS fresh outer completion/Q/closure/success differs")
        return got

    def verify(self, bound, arguments, receipt):
        if receipt is not self.last or receipt != (self.request.request, self.current):
            raise c.CallError("callback response is not THIS outer invocation")
        if (bound.kind, bound.intent, bound.target, arguments.dag) != (
            "ordinary", p.INTENT, self.closure["dag"], self.inputs):
            raise c.CallError("THIS outer expected target/input differs")
        got = self._authority()  # Fresh actual Q/phase/completion or pinned OLD S, not value equality.
        return self.read(got["result"])


def invoke(path, *, commit, closure_name="outer-A", inputs_name="inputs", control="fresh",
           add_control="fresh", double_control="fresh", ref, workspace, receipt=None):
    """Trusted application entry. Outer, nested ordinary calls and getters share Context.invoke."""
    backend = EntryBackend(path, commit, closure_name, inputs_name,
        dict(control=control, add_control=add_control, double_control=double_control), ref, workspace, receipt)
    with c.Context(backend) as context:
        target = context.bind(kind="ordinary", intent=p.INTENT, target=backend.closure["dag"])
        arguments = context.load(backend.inputs)
        result = context.calls.invoke(target, arguments)
        context.describe(result)
    return Invocation(backend.request, backend.current, result, frozenset(backend.seen))
