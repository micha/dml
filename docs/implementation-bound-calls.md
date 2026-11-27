# Implementation-bound calls

## Authority boundary

This page owns the installed `daggerml.calls` closure and call-scope API. Its
walkthrough describes an opt-in profile of the checkout-only
[captured ordinary calls example](captured-ordinary-calls.md). The
[built-in recorder](internal-builtins.md) owns the value, argument, and trace
profiles. There is no installed dispatcher, worker protocol, or cache index.

## Closure and invocation API

- `put_closure(txn, intent=..., implementation=..., captures=...)` writes an
  immutable DAG and returns its ID. Its root is a `role` STRING with value
  `implementation-call-closure-v1`. The `intent` and `implementation` fields
  are URI literals. Up to 16 other named fields link exact dependency DAGs;
  they cannot shadow the three metadata fields. The intent identifies a
  computational contract, not another closure. Captures belong to the
  implementation and do not change when a defaults ref moves.
- `inspect_closure(txn, dag, names=...)` verifies the exact profile and capture
  slots supplied by the adapter and returns an immutable `Closure` with the
  two URI values and sorted `(name, DAG ID)` pairs. It does not resolve code,
  validate dependency semantics, or authorize execution. A workflow must
  validate its supported implementations and the retained dependency records.
- Within `with calls.Scope() as scope`, trusted code creates owned copied nodes
  using `scope.copy(datum)` and binds an ordinary adapter using
  `with scope.bind(adapter) as target`. `scope.invoke(target, arguments)` takes
  an owned MAP `Node` and returns an owned `Node`. For a fixed built-in, use
  `with scope.bind_builtin(recorder, func_uri, binding_dag, prepared) as (target, arguments)`
  and call the same `invoke`. This delegates to `Recorder.call` on the exact
  prepared argument node; it does not open another transaction or change dispatch.
- A scope is single-use, synchronous, and belongs to the thread that entered
  it. Adapters and target tokens expire when their binding ends. A failed
  invocation on the owning thread poisons the scope, including a nested failure
  caught by an adapter. Copied `.value` data can outlive a scope; nodes cannot be passed to
  another scope as authority. The scope does not commit or abort transactions.
  Trusted wrappers own the native node associations and must separately
  validate ordinary results before publishing or returning them. Give logical
  Python code only the bound targets and restricted operations it needs.
  This is a cooperative interface, not a sandbox or execution attestation.

## Walkthrough: request B, reuse A, then run B

**Informative.** With the [wheel installed](../README.md#install-the-python-binding),
start in the checkout and choose a new repository path. Here A is v1 and B is
v2. Both implement the same contract but capture different getter versions.

```sh
repo=./implementation-demo
ordinary() { python examples/recorded_ordinary_calls.py "$1" "$repo" "${@:2}"; }
initial=$(ordinary defaults defaults 1 --implementation-bound)
a=$(ordinary capture defaults "$initial" cap-a)
first=$(ordinary invoke cap-a "$a" first 13 29)
selected=$(ordinary select-double first "$first" selected-double)

promoted=$(ordinary defaults defaults 2 --expected "$initial")
b=$(ordinary capture defaults "$promoted" cap-b)
ordinary invoke cap-b "$b" hit 13 29 --named-inputs \
  --mode require-selected --selected-ref first --selected "$first"
ordinary inspect hit
ordinary invoke cap-b "$b" fresh-b 13 29 --named-inputs
ordinary inspect fresh-b
ordinary invoke cap-b "$b" inner-hit 13 29 \
  --double-mode require-selected --double-selected-ref selected-double --double-selected "$selected"
ordinary inspect inner-hit
ordinary invoke cap-a "$a" still-a 13 30
```

At both selectable boundaries, reuse matches the same **intent URI and full
canonical MAP value**. It never compares just the return value or drops an
argument. `--named-inputs` gives `hit` different source DAGs than `first`, without
changing the MAP. The report identifies B in `requested`, A in `producing`, and
the original A attempt. No new attempt, getter, or leaf runs on that hit.
`fresh-b` records B actually running, with v2 getter traces. `inner-hit` runs
B's add and records a new B double request, but uses A's selected double
attempt and its original add source. Add always runs fresh when the outer
callable runs. `still-a` uses the old capture after promotion and returns `86`.

The example retains exact selection and capture pins, durable phase prefixes,
and read-only inspection, including after transferring a finished or reuse
commit. It does not look for reusable results or adopt them automatically.
Intent equality is a declared contract, not a proof that implementations are
equivalent. Without `--implementation-bound` at defaults creation the example
uses the original exact-environment reuse rules; the two profiles do not share
reuse authority.
