# Captured ordinary calls

## Authority boundary

This page describes the checkout-only
[`recorded_ordinary_calls.py`](../examples/recorded_ordinary_calls.py) example.
It uses [the installed built-in node profiles](internal-builtins.md) and
[public Python storage operations](spec-next/python.md). Its ordinary call
profiles are examples, not native types, an installed dispatcher, or a worker
protocol.

## The callable supplies the control flow

A capture retains its exact defaults snapshot and links that snapshot's
immutable environment: the outer getter binding and the two fixed leaf
closures for `add(a,b)` and `double(x)`. Each leaf descriptor pins its getter
binding and identifies the fixed Python implementation by its versioned role.
Changing the defaults ref only changes future captures. This example does not
capture arbitrary Python source or interpreter state.

On a fresh invocation, the trusted wrapper gives `double_sum` an argument node,
value operations, and a call interface with two captured targets. `double_sum`
checks `a` and `b` using two recorded getters, invokes add on **the original
argument node**, builds `{x:…}` from **the exact returned add node**, and invokes
double. It returns the node supplied by that second call. It never resolves a
ref or sees a repository handle. The bridge keeps the associations between
copied session nodes and exact DAGs, reloading them into each recorder as needed.
These are cooperative interfaces for fixed trusted code, not a sandbox.

## Separate the request from the producing attempt

Outer reuse matches the exact captured environment and the full invocation MAP
datum. Inner reuse matches the exact captured double descriptor and the full
`{x:…}` MAP datum. Argument source links are not part of the MAP value. An
unchanged source or an equal-valued result alone is not permission to reuse.
There is no general closure-equivalence rule, cache discovery, or automatic
adoption. Add always runs fresh when the outer callable runs.

Both levels accept `fresh` (no selection), `try-selected` (reuse on a match,
otherwise run), and `require-selected` (error on a miss). To consult a
selection, supply its ref and the exact expected commit ID, or omit the ID to
pin absence. The outer selection must point to a finished attempt. Use
`select-double` to pin an independently selectable fresh double attempt from a
finished outer call. All consulted pins and their original histories are
validated before starting, even on mismatch or an outer hit. Neither leaf
rereads a selection ref. An outer hit records a new outer request and no new
attempt, getters, or inner calls. An inner hit records a new double request
with the current add as its input source while retaining the old double
attempt and its original add chain.

## Publication and inspection

Each invocation starts at a new output ref. A fresh invocation first records
its outer request and start. The add batch records its own request, attempt,
return, and the outer getter positions. The double batch records either a fresh
attempt or a reuse decision with a new request. Each batch advances the
invocation ref only from its exact preceding phase. A final batch retains the
exact returned double node and moves `main`. An outer hit moves `main` to the
old finished commit in the same batch that records the hit.

A failed batch does not undo earlier batches. For example, if double overflows
I64 or a required double selection does not match, the successful add remains
at the output ref and `main` is unchanged. An incomplete prefix is neither a
successful result nor proof of why execution stopped. This example does not
resume, retry, or run code in another process.

`inspect` checks ordered commit parents, pinned capture descriptors, getter
bindings, MAP sources, and fixed arithmetic without invoking the logical
callables or writing records. The requested and producing histories are
reported separately and can be read after transferring the invocation commit
without its original refs. Readers bound proof traversal to 32 nested commit
reads and 128 distinct commits and retain the built-in semantic DAG limit
across the composed return evidence. This validates the records; it does not
attest to execution outside this example.

## Walkthrough

**Informative.** With the [wheel installed](../README.md#install-the-python-binding),
run from the checkout in Bash. Choose a new repository path.

```sh
repo=./ordinary-demo
ordinary() { python examples/recorded_ordinary_calls.py "$1" "$repo" "${@:2}"; }
initial=$(ordinary defaults defaults 1)
captured=$(ordinary capture defaults "$initial" cap)
first=$(ordinary invoke cap "$captured" first 13 29)
double=$(ordinary select-double first "$first" selected-double)

ordinary defaults defaults 2 --expected "$initial"
ordinary invoke cap "$captured" outer-hit 13 29 \
  --mode require-selected --selected-ref first --selected "$first"
ordinary invoke cap "$captured" inner-hit 29 13 \
  --mode try-selected --selected-ref first --selected "$first" \
  --double-mode require-selected --double-selected-ref selected-double --double-selected "$double"
ordinary inspect inner-hit

ordinary invoke cap "$captured" still-v1 13 29
ordinary inspect still-v1
```

All four requests return `84`. `outer-hit` skips both leaves. `inner-hit` runs a
new add because the outer MAP differs. Its double input still has value
`{x:42}`. In the report, `double.requested.upstream_attempt` identifies the new
add, and `double.producing.upstream_attempt` identifies the old one. `still-v1`
executes both captured v1 leaves despite the defaults having moved to v2.

To see a durable prefix, invoke with `4611686018427387904` and `0` under a new
output ref. Double fails, but `inspect` shows the successful add and no outer
result.
