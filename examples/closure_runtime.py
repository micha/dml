"""Captured trusted wrapper/profile code over public DML APIs; no checkout imports."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import tempfile
import unicodedata

import daggerml as d
from daggerml import builtin as b, exchange as ex, local, transfer

INTENT = "urn:example:captured-scaled-sum"
F_ROLE = "example-captured-builtin-v1"
E_ROLE = "example-capture-environment-v1"
K_ROLE = "example-capture-key-v1"
C_ROLE = "example-captured-closure-v1"
D_ROLE = "example-capture-decision-v1"
SLOT = "selected-scaled-sum"


def name(value):
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None:
        raise ValueError("explicit name outside native profile")
    return value


def tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def capture(environment, runtime_source, logical_source):
    """E predates B. Exact shipped helper/logical bytes; never C's future hash."""
    return ("import types\nfrom daggerml import local,ObjectId\n"
            "runtime_source=%r\nlogical_source=%r\n"
            "runtime=types.ModuleType('captured_closure_runtime')\n"
            "import sys\nsys.modules[runtime.__name__]=runtime\n"
            "exec(compile(runtime_source,'closure_runtime.py','exec'),runtime.__dict__)\n"
            "logical=types.ModuleType('captured_closure_funcs')\n"
            "exec(compile(logical_source,'closure_funcs.py','exec'),logical.__dict__)\n"
            "runtime.publish(local.child_context(),ObjectId.from_hex(%r),"
            "runtime_source,logical_source,logical.scaled_sum)\n"
            % (runtime_source, logical_source, str(environment))).encode()


def inspect_dependency(tx, inspector, dag, func):
    if dag not in inspector.retained:
        raise ValueError("dependency not retained by pinned history")
    fields = b.shape(tx, dag, ("role", "func", "binding"), F_ROLE)
    binding = b.link(tx, fields["binding"])
    if binding not in inspector.retained:
        raise ValueError("dependency binding not retained")
    uri = b.inspect_binding(tx, binding).source_uri
    allowed = ("dml://source/builtin/map/get/v1", "dml://source/builtin/map/get/v2") if func == b.MAP_GET else ("dml://source/builtin/list/get/v1",)
    if b.scalar(tx, fields["func"], "uri") != func or uri not in allowed:
        raise ValueError("unsupported captured func/binding pair")
    return binding


@dataclass(frozen=True)
class Environment:
    dag: d.ObjectId
    map_dependency: d.ObjectId
    list_dependency: d.ObjectId
    map_binding: d.ObjectId
    list_binding: d.ObjectId
    scale: b.Description


def inspect_environment(tx, commit, dag):
    inspector = b.Inspector(tx, commit=commit)
    if dag not in inspector.retained:
        raise ValueError("environment not retained")
    fields = b.shape(tx, dag, ("role", "map-get", "list-get", "scale"), E_ROLE)
    map_dep, list_dep, scale_id = (b.link(tx, fields[n]) for n in ("map-get", "list-get", "scale"))
    map_binding = inspect_dependency(tx, inspector, map_dep, b.MAP_GET)
    list_binding = inspect_dependency(tx, inspector, list_dep, b.LIST_GET)
    scale = inspect_scale(tx, inspector, scale_id)
    return Environment(dag, map_dep, list_dep, map_binding, list_binding, scale)


def inspect_scale(tx, inspector, dag):
    scale = inspector.node(dag)
    role = b.scalar(tx, tx.get_dag(dag).bindings["role"], "string")
    if role not in (b.LITERAL_ROLE, b.SOURCE_ROLE) or scale.value.kind != "i64":
        raise ValueError("captured scale requires retained literal/source I64")
    return scale


@dataclass(frozen=True)
class Closure:
    dag: d.ObjectId
    binding: d.ObjectId
    environment: Environment
    key: d.ObjectId
    interpreter: str
    timeout: int


def inspect_closure(tx, commit, dag, runtime_source, logical_source):
    inspector = b.Inspector(tx, commit=commit)
    if dag not in inspector.retained:
        raise ValueError("closure not retained")
    fields = b.shape(tx, dag, ("role", "intent", "binding", "environment", "capture-key"), C_ROLE)
    if b.scalar(tx, fields["intent"], "uri") != INTENT:
        raise ValueError("closure intent differs")
    binding, environment, key = (b.link(tx, fields[n]) for n in ("binding", "environment", "capture-key"))
    env = inspect_environment(tx, commit, environment)
    keys = b.shape(tx, key, ("role", "map-get", "list-get", "scale"), K_ROLE)
    if (b.scalar(tx, keys["map-get"], "uri"), b.scalar(tx, keys["list-get"], "uri"), b.node_value(tx, keys["scale"])[0]) != (b.MAP_GET, b.LIST_GET, env.scale.datum):
        raise ValueError("capture key differs from recomputed environment")
    normal = b.shape(tx, binding, ("role", "adapter", "source", "interpreter", "timeout-ms"), "local-python-binding-v1")
    if (b.scalar(tx, normal["adapter"], "uri") != local.ADAPTER_URI
        or b.scalar(tx, normal["source"], "bytes") != capture(environment, runtime_source, logical_source)):
        raise ValueError("exact captured environment/helper/logical binding differs")
    interpreter = b.scalar(tx, normal["interpreter"], "string")
    timeout = b.scalar(tx, normal["timeout-ms"], "i64")
    if (not os.path.isabs(interpreter) or "\0" in interpreter
        or unicodedata.normalize("NFC", interpreter) != interpreter or not 1 <= timeout <= 3600000):
        raise ValueError("closure interpreter/timeout differs")
    interpreter.encode("utf-8")
    return Closure(dag, binding, env, key, interpreter, timeout)


def inspect_arguments(tx, commit, dag):
    inspector = b.Inspector(tx, commit=commit)
    full = inspector.arguments(dag)
    fields = tx.get_dag(dag).bindings
    ledger = tx.get_dag(b.link(tx, fields["entries"]))
    sources = {}
    for n in sorted(set(ledger.bindings) - {"role"}):
        row = b.shape(tx, b.link(tx, ledger.bindings[n]), ("role", "key", "source"), b.ENTRY_ROLE)
        sources[b.scalar(tx, row["key"], "string")] = inspector.node(b.link(tx, row["source"]))
    if set(sources) != {"a", "b"} or any(v.value.kind != "i64" for v in sources.values()):
        raise ValueError("invocation requires EXACT a,b I64; no scale override")
    return full


def decision_fields(tx, commit, decision_name, runtime_source, logical_source):
    """Actual authored one-parent/tree delta and requested pinned capture, no flags."""
    name(decision_name)
    parents = tx.get_commit(commit).parents
    if len(parents) != 1:
        raise ValueError("decision requires one actual parent")
    base = parents[0]
    old, entries = tree(tx, base), tree(tx, commit)
    dag = entries.pop(decision_name)
    if decision_name in old or entries != old:
        raise ValueError("decision must add ONLY named D")
    fields = tx.get_dag(dag).bindings
    names = ("intent", "closure-name", "binding-name", "inputs-name", "control", "action", "reason")
    values = {n: b.scalar(tx, fields[n], "uri" if n == "intent" else "string") for n in names}
    links = {n: b.link(tx, fields[n]) for n in ("closure", "binding", "environment", "capture-key", "inputs")}
    if "selection" in fields:
        links["selection"] = b.link(tx, fields["selection"])
    b.shape(tx, dag, ("role", "value", *names, *links), D_ROLE, "inputs")
    for n in ("closure-name", "binding-name", "inputs-name"):
        name(values[n])
    closure = inspect_closure(tx, base, old[values["closure-name"]], runtime_source, logical_source)
    full = inspect_arguments(tx, base, old[values["inputs-name"]])
    expected = {"closure": closure.dag, "binding": closure.binding, "environment": closure.environment.dag,
                "capture-key": closure.key, "inputs": full.dag}
    if SLOT in old:
        expected["selection"] = old[SLOT]
    if (values["intent"] != INTENT or old[values["binding-name"]] != closure.binding or links != expected
        or b.node_value(tx, fields["value"])[0] != full.datum
        or values["control"] not in ("fresh", "try-selected", "require-selected")
        or (values["action"], values["reason"]) not in {
            "fresh": (("execute-fresh", "explicit-fresh"),),
            "require-selected": (("reuse-selected", "selected-capture-value"),),
            "try-selected": (("execute-fresh", "no-selection"),
                ("execute-fresh", "capture-value-mismatch"),
                ("reuse-selected", "selected-capture-value")),
        }[values["control"]]):
        raise ValueError("decision actual basis/capture/value/claims differ")
    return base, dag, values, closure, full


def publish(context, environment, runtime_source, logical_source, factory):
    """Native Q/D/capture association checked BEFORE the ONE publication write.

    Host decision resolution separately validates full original successful S eligibility.
    Child checks strict pinned structure/control coherence, not public S re-resolution.
    """
    path = context.repository_path
    transfer.export_commit(path, commit=context.pre_dispatch)
    with d.Repository(path) as repo, repo.read() as tx:
        pre = tx.get_commit(context.pre_dispatch)
        if len(pre.parents) != 1:
            raise ValueError("pre-dispatch must have one caller Q parent")
        cq = pre.parents[0]
        parents = tx.get_commit(cq).parents
        if len(parents) != 1:
            raise ValueError("caller Q must have one decision parent")
        dc = parents[0]
        basis = tx.get_commit(dc).parents
        if len(basis) != 1:
            raise ValueError("decision must have one basis")
        additions = set(tree(tx, dc)) - set(tree(tx, basis[0]))
        if len(additions) != 1:
            raise ValueError("child requires exactly one authored decision")
        base, dag, values, closure, full = decision_fields(tx, dc, additions.pop(), runtime_source, logical_source)
        if (closure.environment.dag, closure.binding, full.dag, values["action"]) != (environment, context.binding, context.inputs, "execute-fresh"):
            raise ValueError("child exact Q/B/C/E/K association differs")
    with tempfile.TemporaryDirectory(prefix="dml-closure-child-validation-") as scratch:
        spec = ex.prepare_exchange(path, commit=cq, request=context.request,
            binding_name=values["binding-name"], inputs_name=values["inputs-name"], intent_uri=INTENT,
            worker_ref="validation", workspace=Path(scratch) / "input")
    if (spec.binding, spec.inputs) != (closure.binding, full.dag):
        raise ValueError("child actual native submission differs")
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=context.pre_dispatch) as rec:
            arguments = rec.load(context.inputs)
            scale = rec.load(closure.environment.scale.dag)
            ops = rec.operations(map_binding=closure.environment.map_binding, list_binding=closure.environment.list_binding)
            result = factory(scale, ops)(arguments)
            returned = rec.returned(result, request=context.request, inputs=context.inputs)
            return local.publish_result(tx, context, rec.dag(returned))
