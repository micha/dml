"""Fixed implementation-bound LOCAL leaves; one writer only across internal builtin work."""

from pathlib import Path

import daggerml as d
from daggerml import builtin as b, calls as c, local, transfer

ADD = "urn:example:implementation-add"
DOUBLE = "urn:example:implementation-double"


def contract(intent):
    if intent == ADD:
        return "add", ("a", "b")
    if intent == DOUBLE:
        return "double", ("x",)
    raise ValueError("unsupported fixed leaf intent")


def sources():
    here = Path(__file__).parent
    return (here.joinpath("implementation_call_leaf.py").read_bytes(),
            here.joinpath("implementation_leaf_funcs.py").read_bytes())


def capture(environment, intent, wrapper, logical):
    func, _ = contract(intent)
    return ("import types,sys\nfrom daggerml import local,ObjectId\n"
            "wrapper_source=%r\nlogical_source=%r\n"
            "wrapper=types.ModuleType('implementation_leaf_runtime')\n"
            "sys.modules[wrapper.__name__]=wrapper\n"
            "exec(compile(wrapper_source,'implementation_call_leaf.py','exec'),wrapper.__dict__)\n"
            "logical=types.ModuleType('implementation_leaf_funcs')\n"
            "exec(compile(logical_source,'implementation_leaf_funcs.py','exec'),logical.__dict__)\n"
            "wrapper.publish(local.child_context(),ObjectId.from_hex(%r),%r,"
            "wrapper_source,logical_source,logical.%s)\n"
            % (wrapper, logical, str(environment), intent, func)).encode()


def shallow_scalar(tx, node, kind, maximum):
    """Native raw-size guard BEFORE copied scalar materialization; no packed parsing."""
    if len(tx.get_record("node", node)) != 40:
        raise ValueError("native shallow node size differs")  # pragma: no cover
    literal = tx.get_node(node)
    if not isinstance(literal, d.LiteralNode):
        raise ValueError("shallow scalar requires literal")
    if len(tx.get_record("datum", literal.datum)) > maximum:
        raise ValueError("native shallow scalar exceeds profile size")
    value = tx.get_datum(literal.datum)
    if value.kind != kind:
        raise ValueError("native shallow scalar kind differs")
    return value.value


def shallow_link(tx, node, maximum):
    if len(tx.get_record("node", node)) != 40:
        raise ValueError("native shallow node size differs")  # pragma: no cover
    target = tx.get_node(node)
    if not isinstance(target, d.SubDAGNode):
        raise ValueError("shallow link requires SubDAG")
    if len(tx.get_record("dag", target.dag)) > maximum:
        raise ValueError("native shallow target exceeds profile size")
    return b.link(tx, node)  # Only after guarding its eager get_dag.


def shallow_shape(tx, dag, role, names, maximum):
    if len(tx.get_record("dag", dag)) > maximum:
        raise ValueError("native shallow DAG exceeds profile size")
    got = tx.get_dag(dag)
    if set(got.bindings) != set(names) or got.root != got.bindings.get("role"):
        raise ValueError("fixed shallow capture fields/root differ")
    if shallow_scalar(tx, got.bindings["role"], "string", 40 + len(role)) != role:
        raise ValueError("fixed shallow role differs")
    return got.bindings


def shallow_environment(tx, dag, expected):
    fields = shallow_shape(tx, dag, c.ENVIRONMENT_ROLE, ("role", *expected), 64 + 148 * c.MAX_CAPTURES)
    captures = {}
    for name, (kind, intent) in expected.items():
        row = shallow_link(tx, fields[name], 140)
        parts = shallow_shape(tx, row, c.CAPTURE_ROLE, ("role", "kind", "intent", "target"), 140)
        if (shallow_scalar(tx, parts["kind"], "string", 48),
            shallow_scalar(tx, parts["intent"], "uri", 40 + len(intent))) != (kind, intent):
            raise ValueError("fixed shallow capture kind/intent differs")
        captures[name] = shallow_link(tx, parts["target"], 209 if kind == "builtin" else 148)
    return captures


def shallow_closure(tx, dag, intent, expected):
    fields = shallow_shape(tx, dag, c.CLOSURE_ROLE, ("role", "intent", "binding", "environment"), 148)
    if shallow_scalar(tx, fields["intent"], "uri", 40 + len(intent)) != intent:
        raise ValueError("fixed shallow closure intent differs")
    env = shallow_link(tx, fields["environment"], 64 + 148 * c.MAX_CAPTURES)
    return shallow_environment(tx, env, expected)


def environment(tx, dag):
    shallow_environment(tx, dag, {"map-get": ("builtin", b.MAP_GET), "list-get": ("builtin", b.LIST_GET)})
    captures = dict(c.inspect_environment(tx, dag))
    if set(captures) != {"map-get", "list-get"}:
        raise ValueError("leaf requires exact getter captures")  # pragma: no cover
    for name, intent in (("map-get", b.MAP_GET), ("list-get", b.LIST_GET)):
        if (captures[name].kind, captures[name].intent) != ("builtin", intent):
            raise ValueError("leaf captured func kind/intent differs")  # pragma: no cover
    map_binding, list_binding = (captures[n].target for n in ("map-get", "list-get"))
    if (b.inspect_binding(tx, map_binding).source_uri not in
        ("dml://source/builtin/map/get/v1", "dml://source/builtin/map/get/v2")
        or b.inspect_binding(tx, list_binding).source_uri != "dml://source/builtin/list/get/v1"):
        raise ValueError("unsupported captured getter pair")
    return map_binding, list_binding


def inspect(tx, dag, wrapper, logical):
    intent_field = shallow_shape(tx, dag, c.CLOSURE_ROLE, ("role", "intent", "binding", "environment"), 148)["intent"]
    intent = shallow_scalar(tx, intent_field, "uri", 40 + max(len(ADD), len(DOUBLE)))
    contract(intent)
    shallow_closure(tx, dag, intent, {"map-get": ("builtin", b.MAP_GET), "list-get": ("builtin", b.LIST_GET)})
    closure = c.inspect_closure(tx, dag)
    contract(closure.intent)
    map_binding, list_binding = environment(tx, closure.environment)
    normal = b.shape(tx, closure.binding, ("role", "adapter", "source", "interpreter", "timeout-ms"),
                     "local-python-binding-v1")
    if b.scalar(tx, normal["source"], "bytes") != capture(closure.environment, closure.intent, wrapper, logical):
        raise ValueError("exact captured leaf source differs")
    return dict(dag=dag, intent=closure.intent, binding=closure.binding, environment=closure.environment,
                map_binding=map_binding, list_binding=list_binding)


class RecorderBackend:
    """Trusted single-publication integration. NO ordinary dispatch while writer is live.

    perform's receipt is not authority: verify independently derives exact operation
    from THIS Recorder's ordered positions, arguments, binding and fixed semantics.
    The writer ends before any ordinary/public-S/import/wait operation.
    """

    def __init__(self, recorder):
        self.recorder = recorder
        self.last = None

    def bind(self, bound):
        if bound.kind != "builtin":
            raise c.CallError("ordinary dispatch forbidden in leaf publication writer")
        source = b.inspect_binding(self.recorder.tx, bound.target).source_uri
        supported = {b.MAP_GET: ("dml://source/builtin/map/get/v1", "dml://source/builtin/map/get/v2"),
                     b.LIST_GET: ("dml://source/builtin/list/get/v1",)}
        if source not in supported.get(bound.intent, ()):
            raise c.CallError("unsupported exact builtin capture")
        self.recorder.inspector.seen.add(bound.target)
        self.recorder.inspector.reserve(0)

    def read(self, dag):
        return self.recorder.inspector.node(dag)

    def literal(self, value):
        return self.read(self.recorder.dag(self.recorder.literal(value)))

    def arguments(self, entries):
        nodes = [(key, self.recorder.load(actual.dag)) for key, actual in entries]
        return self.read(self.recorder.dag(self.recorder.arguments(nodes)))

    def perform(self, bound, arguments):
        if bound.kind != "builtin":
            raise c.CallError("ordinary dispatch forbidden in leaf publication writer")
        position = len(self.recorder.positions)
        result = self.recorder.call(bound.intent, bound.target, self.recorder.load(arguments.dag))
        self.last = (position, self.recorder.dag(result))
        return self.last

    def verify(self, bound, arguments, receipt):
        if receipt is not self.last:
            raise c.CallError("response not THIS builtin invocation receipt")
        position, dag = receipt
        if len(self.recorder.positions) != position + 1 or self.recorder.positions[position] != dag:
            raise c.CallError("actual ordered builtin position differs")
        fields = b.shape(self.recorder.tx, dag,
            ("role", "func", "binding", "arguments", "value"), b.OPERATION_ROLE, "value")
        if (b.scalar(self.recorder.tx, fields["func"], "uri"), b.link(self.recorder.tx, fields["binding"]),
            b.link(self.recorder.tx, fields["arguments"])) != (bound.intent, bound.target, arguments.dag):
            raise c.CallError("THIS builtin native target/arguments differ")
        return self.read(dag)  # Fresh fixed-semantic derivation, not callback Datum/ID/flags.


def publish(context, env, intent, wrapper, logical, func):
    """One native batch: only fixed internal work can run while Recorder writer is live."""
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
    # All public transfer validation is already finished; no public-S scratch/ordinary wait here.
    with d.Repository(context.repository_path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=context.pre_dispatch) as recorder:
            with c.Context(RecorderBackend(recorder)) as calls:
                map_target = calls.bind(kind="builtin", intent=b.MAP_GET, target=map_binding)
                list_target = calls.bind(kind="builtin", intent=b.LIST_GET, target=list_binding)
                operations = calls.operations(map_target=map_target, list_target=list_target)
                arguments = calls.load(context.inputs)
                result = func(arguments, operations)
                actual = calls.describe(result)
            returned = recorder.returned(recorder.load(actual.dag), request=context.request, inputs=context.inputs)
            return local.publish_result(tx, context, recorder.dag(returned))
