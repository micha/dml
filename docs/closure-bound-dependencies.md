# Closure-bound dependencies

## Authority boundary

This document describes the checkout-only
[`recorded_closures.py`](../examples/recorded_closures.py) example. The
[installed built-in module](internal-builtins.md) owns the node and recorder
profiles. A closure here is a convention over ordinary records, not a new
native type, installed evaluator, or worker protocol.

## Capture first; supply arguments later

The example computes `(a + b) * scale`. A defaults snapshot stores an
environment with exact map and list getter bindings and a named I64 scale
source. `capture` pins the expected defaults commit and publishes a closure
that links its environment and a computational capture key. It also identifies
the fixed `scaled-sum-python-v1` implementation. Creating a closure prepares
metadata; it doesn't invoke a getter or record a request.

`defaults --expected` advances a convenience ref to a new snapshot. This
changes what a future capture can select, not what an existing closure uses.
A request pins the exact closure commit separately from its argument node. The
argument MAP contains only the exact I64 arguments `a` and `b`; it cannot
override `scale`.

On fresh `work`, the wrapper loads the captured scale node and binds operations
to the captured getter versions. The logical callable receives the argument
node, uses two map reads, and returns an I64 literal. It doesn't receive a
repository or resolve defaults. The list getter is captured but not called.
Both the subtotal and product must fit I64; overflow aborts the work batch.
The example selects a fixed, trusted Python implementation by version; it
neither embeds a Python interpreter nor preserves arbitrary Python code or
external resources.

## Reuse compares values without replacing capture history

For this fixed func, reuse compares the **capture key and the full invocation
MAP datum ID**. The key contains the typed scale datum and the two builtin func
URIs. Two different sources for scale `2` are value-equivalent, as are the two
supported implementations of `map/get` for this profile. Exact source and
binding IDs still belong to the capture. This rule doesn't infer equivalence
for other implementations or change the reuse keys of earlier examples.

- `fresh` ignores selections. `try-selected` leaves a pending request when the
  selection is absent or valid but mismatched. `require-selected` rejects a
  miss. To consult a selection, supply `--selected-ref` and the exact
  `--selected` attempt ID, or omit `--selected` to pin expected absence.
- A present selection must validate its original request, capture, result and
  getter trace **even on a mismatch**. An inconsistent history isn't a miss.
- Every successful decision records its own request. A hit rejects a request
  that would be identical to the producing request. It publishes the decision
  and updates `main` to the old result in one transaction without creating
  pending work or a new attempt or trace. A miss publishes a decision and
  pending request together, leaving `main` alone. Use distinct invocation and
  attempt IDs if supplying them explicitly; the CLI generates UUIDs by default.
- `work` is explicit and requires the exact pending ref and request commit. It
  does not consume the ref or change which attempt you select for reuse.

Inspection uses immutable records, including after transferring a decision
without its original refs. On a hit it shows the **requested** and **producing**
captures separately. It checks the actual commit ancestry, dependency links,
canonical key, exact getter bindings and inputs, and numeric result without
running the logical callable. This is structural validation, not execution
attestation or a security sandbox.

## Walkthrough

**Informative.** With the [wheel installed](../README.md#install-the-python-binding),
run from the checkout in Bash. Choose a new repository path.

```sh
repo=./closures-demo
closure() { python examples/recorded_closures.py "$1" "$repo" "${@:2}"; }
request_id() {
  closure inspect "$1" | python -c 'import json,sys; print(json.load(sys.stdin)["requested"]["request"])'
}

base=$(closure defaults defaults 1 2 origin-A)
a=$(closure capture defaults "$base" closure-a)
closure request closure-a "$a" first-pending first-decision 13 29
first=$(closure work first-pending "$(request_id first-decision)" first-attempt)

# Move defaults to v2/scale 3. The pinned closure still executes v1/scale 2.
promoted=$(closure defaults defaults 2 3 origin-C --expected "$base")
closure request closure-a "$a" old-pending old-decision 13 29
closure work old-pending "$(request_id old-decision)" old-attempt
closure inspect old-attempt

# A different source for scale 2, captured with v2, can reuse the v1 result.
other=$(closure defaults other-defaults 2 2 origin-B)
b=$(closure capture other-defaults "$other" closure-b)
hit=$(closure request closure-b "$b" unused hit-decision 13 29 \
  --mode require-selected --selected-ref first-attempt --selected "$first")
closure inspect hit-decision --expected "$hit"

# v2/scale 3 changes the key even though the invocation MAP is identical.
c=$(closure capture defaults "$promoted" closure-c)
closure request closure-c "$c" changed-pending changed-decision 13 29 \
  --mode try-selected --selected-ref first-attempt --selected "$first"
closure work changed-pending "$(request_id changed-decision)" changed-attempt
closure inspect changed-attempt
```

The old closure still returns `84` with v1 after the defaults move. On the hit,
`requested.capture` reports v2/origin-B while `producing.capture` reports
v1/origin-A and the trace still records v1. No `unused` ref is created. The
changed capture returns `126` with v2. Swapping `13` and `29` changes the full
invocation MAP, so the same sum isn't sufficient for reuse.
