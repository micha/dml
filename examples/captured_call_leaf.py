"""Fixed captured local leaf profile/wrapper. No ordinary nested invoker or private codec."""

from pathlib import Path
import types

import daggerml as d
from daggerml import builtin as b, local, transfer

ADD = "urn:example:captured-call-add"
DOUBLE = "urn:example:captured-call-double"
E_ROLE = "example-call-leaf-environment-v1"
C_ROLE = "example-call-leaf-closure-v1"
K_ROLE = "example-call-identity-v1"


def contract(intent):
    if intent == ADD:
        return "add", ("a", "b")
    if intent == DOUBLE:
        return "double", ("x",)
    raise ValueError("unsupported fixed leaf intent")


def sources():
    here = Path(__file__).parent
    return (here.joinpath("captured_call_leaf.py").read_bytes(),
            here.joinpath("composed_node_funcs.py").read_bytes())


def capture(environment, intent, wrapper, logical):
    func, _ = contract(intent)
    return ("import types,sys\nfrom daggerml import local,ObjectId\n"
            "wrapper_source=%r\nlogical_source=%r\n"
            "wrapper=types.ModuleType('captured_leaf_runtime')\n"
            "sys.modules[wrapper.__name__]=wrapper\n"
            "exec(compile(wrapper_source,'captured_call_leaf.py','exec'),wrapper.__dict__)\n"
            "logical=types.ModuleType('captured_leaf_funcs')\n"
            "exec(compile(logical_source,'composed_node_funcs.py','exec'),logical.__dict__)\n"
            "wrapper.publish(local.child_context(),ObjectId.from_hex(%r),%r,"
            "wrapper_source,logical_source,logical.%s)\n"
            % (wrapper, logical, str(environment), intent, func)).encode()


def environment(tx, dag):
    fields = b.shape(tx, dag, ("role", "map-get", "list-get"), E_ROLE)
    map_binding, list_binding = (b.link(tx, fields[n]) for n in ("map-get", "list-get"))
    if (b.inspect_binding(tx, map_binding).source_uri not in
        ("dml://source/builtin/map/get/v1", "dml://source/builtin/map/get/v2")
        or b.inspect_binding(tx, list_binding).source_uri != "dml://source/builtin/list/get/v1"):
        raise ValueError("unsupported captured getter pair")
    return map_binding, list_binding


def inspect(tx, dag, wrapper, logical):
    fields = b.shape(tx, dag, ("role", "intent", "binding", "environment", "key"), C_ROLE)
    intent = b.scalar(tx, fields["intent"], "uri")
    contract(intent)
    binding, env, key = (b.link(tx, fields[n]) for n in ("binding", "environment", "key"))
    map_binding, list_binding = environment(tx, env)
    keys = b.shape(tx, key, ("role", "binding", "environment"), K_ROLE)
    if tuple(b.link(tx, keys[n]) for n in ("binding", "environment")) != (binding, env):
        raise ValueError("leaf identity ignores exact binding/environment")
    normal = b.shape(tx, binding, ("role", "adapter", "source", "interpreter", "timeout-ms"),
                     "local-python-binding-v1")
    if (b.scalar(tx, normal["adapter"], "uri") != local.ADAPTER_URI or
        b.scalar(tx, normal["source"], "bytes") != capture(env, intent, wrapper, logical)):
        raise ValueError("exact captured leaf source differs")
    # Public local/exchange validates interpreter/timeout before dispatch and S use.
    interpreter = b.scalar(tx, normal["interpreter"], "string")
    timeout = b.scalar(tx, normal["timeout-ms"], "i64")
    import os
    import unicodedata
    if (not os.path.isabs(interpreter) or "\0" in interpreter
        or unicodedata.normalize("NFC", interpreter) != interpreter or not 1 <= timeout <= 3600000):
        raise ValueError("leaf interpreter/timeout differs")
    interpreter.encode("utf-8")
    return dict(dag=dag, intent=intent, binding=binding, environment=env, key=key,
                map_binding=map_binding, list_binding=list_binding)


def publish(context, env, intent, wrapper, logical, func):
    """Revalidate exact Q binding/E before ONE unchanged normal publication scope."""
    transfer.export_commit(context.repository_path, commit=context.pre_dispatch)
    with d.Repository(context.repository_path) as repo, repo.read() as tx:
        normal = b.shape(tx, context.binding,
            ("role", "adapter", "source", "interpreter", "timeout-ms"), "local-python-binding-v1")
        if b.scalar(tx, normal["source"], "bytes") != capture(env, intent, wrapper, logical):
            raise ValueError("child captured binding/environment differs")
        q = tx.get_dag(context.request)
        if (set(q.bindings) != {"role", "intent", "binding", "inputs"}
            or b.scalar(tx, q.bindings["intent"], "uri") != intent
            or b.link(tx, q.bindings["binding"]) != context.binding
            or b.link(tx, q.bindings["inputs"]) != context.inputs):
            raise ValueError("child Q exact computational association differs")
        map_binding, list_binding = environment(tx, env)
    return b.publish_callable(context, func, map_binding=map_binding, list_binding=list_binding)
