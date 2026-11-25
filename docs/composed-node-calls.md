# Composed recorded node calls

## Authority boundary

This document describes the checkout example
[`recorded_composition.py`](../examples/recorded_composition.py). The
[installed built-in module](internal-builtins.md) owns the recorder and its
value-node profiles. This example uses public Python storage operations and
ordinary records; it adds no native layout, installed dispatcher, or worker
protocol.

## Pass the node, not the scalar

The example has two fixed ordinary funcs: `urn:example:node-add` takes exact I64
arguments `a` and `b`, and `urn:example:node-double` takes exact I64 argument `x`.
Each gets a recorded argument-map node and returns a recorded value node. The
funcs read named arguments through pinned `map/get/v1` operations and perform
arithmetic in Python. I64 overflow fails work; it does not publish a result.

Each fresh request pins its input node. `work` records the return DAG, including
the actual ordered getters, in a result commit whose parent is the request. A
successful attempt has ordered parents `(request, result)`. The CLI generates
new request and attempt UUIDs by default; use distinct UUIDs if supplying them
explicitly. Two fresh adds with identical inputs can share a return DAG even
though their request, attempt, and result commits differ.

`compose` takes a ref and the exact expected successful add attempt. It validates
the attempt, result ownership, and return profile, then loads the **outer
return DAG** as the `x` source. It publishes a single composition snapshot:

- Its `inputs` link pins the double argument node, whose `x` source links the
  producer's return DAG rather than a newly copied scalar or the inner literal.
- Its `producer` literal stores the selected attempt ID, and its sole commit
  parent is that attempt. The parent retains the add request and result, even
  after transfer without the original refs. The reader checks the pin against
  the parent, including when distinct attempts share the same return DAG.

A double request has the composition as its sole parent and pins those exact
inputs. The composition is not part of the MAP datum. This distinction lets
readers tell apart both different sources with equal values and different
producing attempts with identical source content.

## Explicit downstream reuse

Only `double` can consult a selection. A supplied selection must be the exact
expected ref target and a valid successful double attempt, including its
original composition and add producer, even when its arguments do not match.
Matching uses the fixed double intent and the full canonical argument MAP datum
ID, not the input DAG or producer ID. The example never treats `add(a, b)` and
`add(b, a)` as interchangeable argument maps.

- `fresh` does not consult a selection. `try-selected` records a pending request
  on absence or a valid value mismatch; `require-selected` rejects a miss.
  Supply `--selected-ref` when consulting a selection. Omit `--selected` only
  when the ref is expected to be absent.
- A hit records a **new request** and a decision naming the historical attempt.
  It rejects an invocation ID that would recreate the producing request. It
  publishes the decision and updates `main` to the old result atomically,
  without creating a pending ref, attempt, result, or getter trace. A miss
  publishes the decision and pending request together, leaving `main` alone.
  A present valid selection is retained by the decision even on a miss.
- Work is an explicit command, not automatic scheduling. A pending ref pins a
  request; work does not consume that ref. Each write command is one transaction;
  a later command's failure does not undo an earlier successful command.

On a hit, `inspect` labels the requested double and its newly supplied add
producer separately from the producing double, its original add producer,
and its trace. It validates exact getter bindings, inputs, and key paths and
checks the expected result without invoking either logical callable. Inspection
can use only a transferred decision and its immutable closure. These checks
validate the recorded structure and arithmetic, not who executed the code or
whether execution took place outside this example.

## Walkthrough

**Informative.** With the [wheel installed](../README.md#install-the-python-binding),
run from the checkout in Bash with Python. Choose a new repository path.

```sh
repo=./composition-demo
composition() { python examples/recorded_composition.py "$1" "$repo" "${@:2}"; }
config=$(composition define config)

q1=$(composition request-add config "$config" add-first 13 29)
t1=$(composition work add-first "$q1" added-first)
c1=$(composition compose added-first "$t1" from-first)
composition request-double from-first "$c1" double-first first-decision
q2=$(composition inspect first-decision | python -c 'import json,sys; print(json.load(sys.stdin)["requested"]["request"])')
t2=$(composition work double-first "$q2" doubled-first)

q3=$(composition request-add config "$config" add-swapped 29 13)
t3=$(composition work add-swapped "$q3" added-swapped)
c3=$(composition compose added-swapped "$t3" from-swapped)
hit=$(composition request-double from-swapped "$c3" unused reuse-decision \
  --mode require-selected --selected-ref doubled-first --selected "$t2")
composition inspect reuse-decision --expected "$hit"
```

The swapped add has a different argument MAP and return DAG. Both double
argument maps are `{x: 42}`, so the hit reports `84`. The `requested.upstream`
attempt is `t3`; the `producing.upstream` attempt is `t1`. There is no `unused`
ref. A fresh repeat of the first add can share both the original return DAG and
`{x: 42}` input DAG, while its composition still pins its own add attempt. An add
with `13` and `30` gives `{x: 43}`: `try-selected` leaves a fresh double pending,
and an explicit `work` returns `86`.
