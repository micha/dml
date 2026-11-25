# DML

DML currently provides a C library for content-addressed data and history in a local
transactional repository, with [binary commit transfer](docs/spec-next/transfer.md)
and an optional [Python core binding](docs/spec-next/python.md).
See the [as-built specification](docs/spec-next/README.md)
for the implemented contracts and [architecture](docs/architecture.md) for the module
boundaries.

The earlier Python package, CLI, test suites, and spike evidence are preserved at
[`feasibility-complete`](https://github.com/micha/dml/tree/feasibility-complete).
That package and its application layers are not maintained or run on this branch.

## Build and validation

Use a C11 compiler, Meson 1.4 or newer, and Ninja. Meson uses the pinned dependency
wraps from `subprojects/`. Run the [build check](docs/validation-policy.md) with:

```sh
scripts/check.sh
```

This configures and compiles a debug build in `build/core-check/` without running
tests. The CI matrix uses `--quint` to build and run the checks below.

### Quint behavior checks

The opt-in Nix shell supplies Python and pins [Quint](https://quint.sh/) 0.33.1
for the TypeScript backend:

```sh
nix develop .#quint -c ./scripts/check.sh --quint
```

Without Nix, use CPython 3.10+ with its development headers and install Quint
locally with Node.js and npm:

```sh
npm install --prefix build/quint-tool --no-save --ignore-scripts @informalsystems/quint@0.33.1
PATH="$PWD/build/quint-tool/node_modules/.bin:$PATH" scripts/check.sh --quint
```

On Windows, use the MSYS2 UCRT64 toolchain, including Python and Node. To bypass
npm launchers, point `DML_QUINT_SCRIPT` at the installed JavaScript entry point
(as CI does on every runner):

```sh
DML_QUINT_SCRIPT=build/quint-tool/node_modules/@informalsystems/quint/dist/src/cli.js \
  ./scripts/check.sh --quint
```

Pass `DML_QUINT_SCRIPT=` to switch an existing build back to `quint` on `PATH`.

This builds the test executables in `build/core-check-quint/` and runs
`quint-refs`, `quint-transfer`, `quint-gc`, `quint-staged-import`, the
[provenance handoff and recorded workflow integrations](tests/README.md#process-integration),
and focused interpreter, Python binding, integrity, boundary, and fault tests.
The [shared trace interpreter](tests/README.md) replays one core function per
Quint request. Ref replay uses public `daggerml.core`; the other core replay
suites still use a private test binding. Quint checks observations against the
[ref contract](docs/spec-next/repository.md#refs), [transfer contract](docs/spec-next/transfer.md),
and [garbage collection contract](docs/spec-next/repository.md#explicit-garbage-collection).
Reopened read transactions and independent LMDB scans check snapshot publication,
rollback, datum readback from imported history, and recording, transferring back,
conditionally publishing a caller's result, and guarded staging-ref release.
The transfer history also checks exact unreachable IDs before staging an import and
retention after releasing `incoming`. The staging suite checks that a staged
result survives collection even when publication is stale, and that a rejected
import leaves no new objects or refs. The collection suite checks ref ordering,
rollback, and exact persisted removals. Native checks exercise damaged repositories,
allocation failures, and deletion failures. These checks run in CI on Linux and
macOS (x86-64 and ARM64) and Windows (x86-64). CI does not measure coverage or
build a Python wheel.

### Install the Python binding

With GIL-enabled CPython 3.10 or newer, Python development headers, and the native
build tools above, build and install a local wheel from the checkout. For example,
with an active virtual environment:

```sh
python -m pip install .
python -c 'from daggerml import core; print(core.TXN_READ)'
```

The wheel targets the CPython ABI and platform used to build it. It includes
[`daggerml.builtin`](docs/internal-builtins.md), a fixed versioned node-call
module. It contains no CLI, C development files, or historical `daggerml`
application modules. The
standalone C build does not require Python headers; pass `-Dpython_bindings=true`
to also build and install the binding with Meson. See the
[Python contract](docs/spec-next/python.md) for supported operations and an example.

### Record two composed calls in Python

With the [public binding installed](#install-the-python-binding), run the
[recorded-calls example](examples/recorded_calls.py) from the checkout. Use a new
repository path with an existing parent directory:

```sh
python examples/recorded_calls.py record ./calls-repo 7 5 3
python examples/recorded_calls.py inspect ./calls-repo
```

`record` computes `sum(7, 5)` and then `scale(sum_result, 3)`. It prints the ID of
an initial commit published to `main` in the same write transaction as both calls.
The inputs and results must fit signed 64-bit integers. Arithmetic overflow aborts
the write and leaves the initialized repository without a published snapshot.

This is an application convention using ordinary DML objects, not a new core
record type. The commit's sole tree entry, `recorded-calls-v1`, selects the scale
DAG. Each call DAG's root is its result literal and its `implementation` binding
names the versioned operation. Sum binds `a` and `b`. Scale binds `factor` and an
`input` sub-DAG node that points to the exact sum DAG. Scale reads its first
argument through this edge, not by looking up the scalar value.

`inspect` opens a read transaction and prints JSON with the commit ID and both
calls in dependency order. It follows the stored edge and reports argument and
result values and node IDs without executing or verifying either operation. The
versioned names identify implementations by example convention, not by code
fingerprint or attestation. IDs identify immutable records, not distinct execution
attempts; recording identical calls can produce the same IDs. Inspection leaves
committed data unchanged; the repository still uses LMDB's normal locking.

#### Compose from an already committed call

Use separate invocations to record a sum and later scale its stored result:

```sh
producer=$(python examples/recorded_calls.py record-sum ./split-repo producer 7 5)
python examples/recorded_calls.py record-sum ./split-repo decoy 8 4
python examples/recorded_calls.py record-scale ./split-repo producer "$producer" result 3
python examples/recorded_calls.py inspect ./split-repo result
```

`record-sum REPO PIN A B` initializes the repository if needed and publishes a
parentless `recorded-sum-v1` commit under a new ref. `record-scale REPO PIN COMMIT
RESULT_REF FACTOR` requires an existing repository. In one write transaction it
checks that `PIN` still names the supplied commit ID and that the commit has the
expected sum layout. It multiplies the stored result without rerunning the sum.
The `recorded-scale-v1` commit has that exact producer commit as its sole parent,
and its `input` node points directly to the producer DAG. Both write commands
print the committed ID and refuse to replace an existing ref. A missing or stale
pin, invalid producer, overflow, or occupied result ref leaves committed data
unchanged. A failed first `record-sum` can still leave an initialized repository.

`inspect REPO [REF]` defaults to `main`. For a split scale commit it reports
`producer_commit` and checks that the stored input edge matches the parent
commit's DAG. The result remains readable after the producer pin moves or is
released: inspection follows committed links, not the original pin name. The
example uses only the explicitly selected stored input; it does not search for
reusable results.

#### Compose from a producer in another repository

Use fresh source and worker paths and a new bundle filename:

```sh
producer=$(python examples/recorded_calls.py record-sum ./origin producer 7 5)
python examples/recorded_calls.py export-sum ./origin producer "$producer" ./sum.dml
python examples/recorded_calls.py stage-input ./worker incoming ./sum.dml
result=$(python examples/recorded_calls.py record-scale ./worker incoming "$producer" result 3)
python examples/recorded_calls.py release-input ./worker incoming "$producer" result
python examples/recorded_calls.py collect ./worker
python examples/recorded_calls.py inspect ./worker result
```

Only the bundle and the originally selected commit ID need to cross between
repositories. `export-sum` checks the source pin and exports by immutable ID;
if collection removes the commit between the check and export, export fails
rather than substituting another commit. Use regular binary bundle files. Export
never overwrites a file, but a failed write can leave a partial file. Discard it
and retry to a fresh output path.

`stage-input` atomically imports a bundle and creates a new local ref. It prints
the bundle's actual root ID, not proof that it is the selected sum. Pass the
original ID, not the staging receipt, to `record-scale`. A valid wrong bundle
can be staged for inspection, but scale rejects it without writing a result,
even if the stored numbers agree. Staging a different bundle under an existing
ref is rejected; use a new staging name. Failed staging can leave a newly
initialized worker without refs.

`release-input` checks in one write transaction that `result` has the expected
producer commit as its sole parent and links to that parent's sum DAG. It deletes
`incoming` only if it still points to that producer. The result ref then retains
both calls through explicit `collect`, which prints the number of objects
removed. The final read reports `36` and the original producer ID, without
opening the source or executing either call. Export and the worker steps leave
the source unchanged.

#### Return and publish a recorded scale

Continue from the previous example with a new bundle filename:

```sh
python examples/recorded_calls.py export-scale ./worker result "$result" ./scale.dml
python examples/recorded_calls.py stage-input ./origin returned ./scale.dml
python examples/recorded_calls.py inspect ./origin returned
python examples/recorded_calls.py publish-scale ./origin returned "$result" "$producer" 3 -
python examples/recorded_calls.py collect ./origin
python examples/recorded_calls.py inspect ./origin
```

`export-scale` checks the selected worker result and exports its immutable
commit and full producer closure. The file rules are the same as for `export-sum`.
Use a separate staging ref, not `main`. Staging reports the actual bundle root;
keep the selected result and producer IDs independently of that receipt.

`publish-scale` checks that the result's sole parent is the expected producer
commit and that its input links to that parent's exact sum DAG. It also checks
the recorded factor against the signed 64-bit factor from the original request
(`3` above). Supply that expectation independently; do not copy the factor from
the returned result. The last argument is `-` to require an absent `main`, or the
expected current commit ID if `main` already exists.

This is a conditional ref update, not a merge. Updating `main` and deleting
`returned` at its expected result ID commit together. A factor mismatch or stale
ref expectation leaves both refs unchanged. The source's other refs and all
worker refs are untouched.

After collection, `main` retains both calls. Publication checks what the result
records; it does not rerun the calls, verify the arithmetic, or authenticate the
worker. There is no automatic reuse.

#### Save a scale request before sending it

Use a fresh source and worker for this variant. Instead of passing the factor
again at publication, save the request and the current `main` expectation on
the source before dispatch:

```sh
producer=$(python examples/recorded_calls.py record-sum ./origin producer 7 5)
plan=$(python examples/recorded_calls.py request-scale ./origin producer "$producer" pending 3)
request=$(python examples/recorded_calls.py export-request ./origin pending "$plan" ./request.dml)
python examples/recorded_calls.py stage-input ./worker incoming ./request.dml
result=$(python examples/recorded_calls.py work-scale ./worker incoming "$request" result)
python examples/recorded_calls.py export-scale ./worker result "$result" ./scale.dml
python examples/recorded_calls.py stage-input ./origin returned ./scale.dml
python examples/recorded_calls.py publish-requested-scale ./origin pending "$plan" returned "$result"
python examples/recorded_calls.py collect ./origin
python examples/recorded_calls.py inspect ./origin
```

`request-scale` checks the exact producer selection, records the implementation
(`example.scale@1` by default) and the typed factor in a portable request commit,
and creates a new source-local plan ref. The request has the producer as its sole parent. The
plan points to the request and, if `main` exists, to the exact `main` commit at
request creation; one parent means `main` was absent. `inspect ./origin pending` shows the saved
expectations. `export-request` follows only the portable request's closure, not
the plan or its `main` edge. Keep request bundles under staging refs, not
`main`; planning rejects `main` already pointing to that exact request. The
same no-overwrite file rules apply as for `export-sum`.

Use the request ID from `export-request`, not the worker's staging receipt.
`work-scale` checks the pinned request and uses its stored factor and producer
result. Its new result commit has the request as its parent and a direct
sub-DAG edge to the producer's sum. The worker keeps its refs in this variant.

After staging on the source, publication needs only the repository, the two
ref names, the saved plan ID and the selected result ID from the worker. Keep
these IDs independently of the staging receipt if you resume in a new shell.
Publication checks the exact request, recorded implementation, factor, and
producer edge without rerunning either call, verifying arithmetic, or
authenticating the worker. The
three ref names must be distinct. If the saved `main` expectation and both pin
targets still match, one transaction sets `main` to the exact worker result and
deletes `pending` and `returned`. A rejection leaves all three refs unchanged. The comparison uses current IDs; it
does not detect a ref that moved away and back. After collection, `main` keeps
the request and both calls. The consumed plan no longer retains the old tip.
These are content IDs, not attempt IDs, and the example does not search for or
automatically reuse results.

#### Select a scale implementation version

To plan the same scale under a different version, choose it explicitly when
creating the plan:

```sh
plan=$(python examples/recorded_calls.py request-scale ./origin producer "$producer" next-plan 3 \
  --implementation example.scale@2)
python examples/recorded_calls.py inspect ./origin next-plan
```

The example supports `example.scale@1` and `example.scale@2`. Both use the same
signed 64-bit multiplication, but their requests and results have different
commit IDs even when the producer, factor, and output are identical. `inspect`
reports the plan's saved version, and `work-scale` uses that exact version from
the portable request. Planning and work reject unsupported versions rather than
falling back. The defaults and layouts of existing `@1` records are unchanged.

Publication and reuse require an explicitly pinned result with the exact
request parent and a recorded implementation that matches that request. A
result from the other version cannot substitute, even if both results share the
same output node. The version is an application label, not a code fingerprint
or proof of execution.

#### Retry publication if its acknowledgment was lost

For a publication you may need to retry, choose a fresh source-local receipt ref
before the first attempt. Save the ref name with the exact plan and result IDs
and their pin names. Use the following command **instead of** the one-shot
publication above:

```sh
python examples/recorded_calls.py publish-requested-scale ./origin pending "$plan" returned "$result" \
  --receipt-ref scale-ack-001
```

The first successful call creates the receipt in the same transaction that
updates `main` and consumes both pins. If the process exits before you see its
output, rerun the same command. It prints the same result ID without changing
committed state, even if `main` has moved, the old pin names have been reused, or
collection has removed the result. Success acknowledges the prior publication;
it does not mean the result is still current. If the first transaction did not
commit, there is no receipt, and all the original publication guards still apply.

`inspect ./origin scale-ack-001` reports the saved IDs and pin names. The four
ref names (`main`, plan, staging, and receipt) must be distinct. An occupied
receipt ref with different names, IDs, or an invalid receipt rejects without
changes. Keep the receipt ref intact and use a fresh name for each new attempt.
Receipts record IDs as literals, so they do not keep the plan, old `main`, or
superseded result alive. They are not part of the worker bundles and are not
proof against someone who can write arbitrary refs or objects in the source.
Omitting `--receipt-ref` keeps one-shot behavior; you cannot add a receipt to
recover a publication that already committed without one.

#### Abandon a scale request without publishing

Instead of publishing a request, you can abandon it using its saved
source-local plan name and commit ID:

```sh
python examples/recorded_calls.py abandon-scale-request ./origin pending "$plan"
```

The command prints the plan ID after removing only that ref in one transaction.
It requires a valid plan at the exact selected ID and rejects a missing or
changed ref, and `main` itself. It works even if `main` has moved. It leaves
`main`, staging refs, publication receipts, and bundles alone, and does not
stop workers or collect objects. A later `collect` can reclaim objects no
longer retained by any ref.

If abandonment wins, a late result cannot publish through the removed pin.
If publication wins, abandonment rejects; a retained publication receipt can
still acknowledge that success. Abandonment itself creates no receipt. Use
fresh plan names for new requests: recreating the same name at the same content
ID makes an old selection valid again.

#### Reuse an explicitly selected local scale result

If a result for the exact request is already pinned in the source repository,
you can skip dispatch, execution, and bundle transfer for the new plan. To
retain a result in the durable-request example, import `scale.dml` under
`saved-result` instead of `returned`, then stage it for publication like this:

```sh
python examples/recorded_calls.py stage-reused-scale ./origin pending "$plan" saved-result "$result" returned
python examples/recorded_calls.py publish-requested-scale ./origin pending "$plan" returned "$result"
```

Keep `saved-result` and the original result ID for later plans. The plan ID may
change when a new plan captures a different `main`; the portable request ID must
still match exactly. The command does not search for a result, match by numeric
value, rerun a call, verify arithmetic, or authenticate a worker.

Staging checks both pins at their supplied IDs and validates the result against
the plan's request in one transaction. It prints the existing result ID and
creates only the new staging ref. The plan, result, staging, and `main` names
must be distinct. An occupied staging ref is rejected even if it already
points to the result. Neither success nor rejection consumes the original
result pin.

Staging does not check or update `main`. Publication still uses the plan's
saved `main` expectation and removes the plan and staging pins, not the
retained result pin. A plan pin that is absent or changed after abandonment
blocks reuse and fresh publication of that selection. Abandonment does not
remove staging refs already created.

#### Save a result selection before publication

Once the [durable request's result](#save-a-scale-request-before-sending-it) is
staged locally under `returned`, you can save the choice without publishing it:

```sh
selection=$(python examples/recorded_calls.py select-scale-result ./origin pending "$plan" returned "$result" chosen)
python examples/recorded_calls.py inspect ./origin chosen
```

Creation checks the exact plan and result pins, including the request parent,
implementation, factor, and producer edge. It creates only the fresh `chosen`
ref and does not check or update `main` or consume either input pin. The new
commit has the portable request and selected result as ordered parents. Keeping
`chosen` retains both through collection; it adds no edge to the original plan
or its saved `main`. Inspection reports the saved request, version, and result
IDs and the historical result ref name; it does not resolve that name.

To publish from the saved selection, supply its exact ref and commit ID. The
original result pin need not exist. You can use a different plan for the same
exact portable request, for example after abandoning the original plan:

```sh
python examples/recorded_calls.py abandon-scale-request ./origin pending "$plan"
new_plan=$(python examples/recorded_calls.py request-scale ./origin producer "$producer" next-plan 3)
python examples/recorded_calls.py publish-selected-scale ./origin next-plan "$new_plan" chosen "$selection" reuse-001
python examples/recorded_calls.py inspect ./origin reuse-001
```

This example uses the default implementation; keep the original version when
creating the new plan. Publication rechecks the exact selection, request and
implementation and the new plan's saved `main`. In one transaction it sets
`main` to the original result, consumes only the publishing plan, and creates a
fresh reuse record with that plan and the selection as ordered parents. A
stale pin, mismatched request or version, changed `main`, or occupied output ref
rejects without changes. For each command the three supplied ref names must be
distinct from one another and from `main`. Even an identical occupied output
rejects; neither command is a retry receipt.

Selections do not run work, verify arithmetic, search for alternatives, or
change automatically when a result is staged or published.

#### Distinguish two executions of the same request

Use the [saved request workflow](#save-a-scale-request-before-sending-it) through
`export-request`, then run it in two fresh worker repositories. Each worker
writes a result and an attempt commit together, but only the attempt gets a ref:

```sh
for worker in worker-a worker-b; do
  python examples/recorded_calls.py stage-input "./$worker" incoming ./request.dml
  attempt_id=$(python -c 'from uuid import uuid4; print(uuid4())')
  attempt=$(python examples/recorded_calls.py work-scale-attempt "./$worker" incoming "$request" attempt "$attempt_id")
  python examples/recorded_calls.py export-scale-attempt "./$worker" attempt "$attempt" "./$worker.dml"
  python examples/recorded_calls.py stage-input ./origin "$worker" "./$worker.dml"
  python examples/recorded_calls.py inspect ./origin "$worker"
  if [ "$worker" = worker-a ]; then first_attempt=$attempt; else second_attempt=$attempt; fi
done
```

`work-scale-attempt` takes a caller-supplied lowercase UUIDv4. Generate a fresh
one for each independent execution. An attempt's ordered parents are the
portable request and the unchanged `requested-scale-v1` result, so the two runs
can have the same `result_commit` but different attempt commit IDs. Reusing the
UUID with the same request and result yields the same attempt commit ID; there
is no UUID registry, retry protocol, or proof of execution. `export-scale-attempt`
exports the exact attempt with its full closure to a new file. Keep the attempt
commit ID from the worker independently of the staging receipt.

Choose the first attempt by its exact commit ID, then publish from the choice:

```sh
chosen=$(python examples/recorded_calls.py select-scale-attempt ./origin pending "$plan" worker-a "$first_attempt" chosen)
python examples/recorded_calls.py publish-selected-scale ./origin pending "$plan" chosen "$chosen" reuse-001
python examples/recorded_calls.py inspect ./origin reuse-001
```

The selection retains the request and the chosen attempt, not the plan or the
other attempt. Its `attempt_ref` is historical: the selection works after the
original attempt pin disappears and collection runs. When both attempt pins
are gone, retaining a shared result does not keep the unselected attempt alive.
As with result selections, selection does not check `main` or consume either
input pin. Publication checks the exact plan, selection, request, result and
implementation, and the plan's saved `main`. It publishes the original result
and consumes only the plan. The reuse record identifies the selected attempt;
publication neither runs work nor records another attempt. Work, selection and
publication require distinct refs (also distinct from `main`) and reject an
occupied output, even at the same ID.

#### Record a new version of an attempt selection

After [selecting the first attempt](#distinguish-two-executions-of-the-same-request),
keep `chosen` for the original choice. If you want to select the second attempt
instead on another branch, use its commit ID from the worker:

```sh
adopted=$(python examples/recorded_calls.py adopt-scale-attempt ./origin chosen "$chosen" worker-b "$second_attempt" adopted)
python examples/recorded_calls.py inspect ./origin adopted
next_plan=$(python examples/recorded_calls.py request-scale ./origin producer "$producer" next-plan 3)
python examples/recorded_calls.py publish-selected-scale ./origin next-plan "$next_plan" adopted "$adopted" reuse-002
python examples/recorded_calls.py inspect ./origin reuse-002
```

The new selection commit has ordered parents `(previous selection, replacement
attempt)`. `inspect` shows its `previous_selection_commit` and the exact attempt
chosen now. The input pins are checked against the supplied IDs but are not
moved or consumed. The fresh output ref must differ from both input refs and
`main`, and it cannot already exist. The replacement must match the exact
portable request and differ from the current attempt commit; equal results are
allowed. You can explicitly reselect an older attempt if it differs from the
current choice. A result-only selection cannot be used as a basis.

These are named branches of a single selection history, not changes to `main`.
Adoption neither needs a plan nor runs work. Fresh work never adopts its own
result. Each branch keeps its own choice; publishing still takes an exact
selection ref and commit ID, revalidates its history, and consumes only the
publishing plan. An adopted version retains its predecessor versions and their
attempts through collection even without the original pins. A reuse record in
turn retains the exact version used, not whatever its old ref points to later.

#### Set a reuse default for the scale intent

Continue from [versioned attempt selection](#record-a-new-version-of-an-attempt-selection).
Create two policy versions under different refs. The second version retains the
first as its parent but does not replace it. The policy belongs to the example's
scale intent, not to an implementation version or a particular input.

```sh
reuse_policy=$(python examples/recorded_calls.py define-scale-policy ./origin reuse-default reuse-by-default)
execute_policy=$(python examples/recorded_calls.py define-scale-policy ./origin execute-default execute-by-default \
  --basis-ref reuse-default --basis-commit "$reuse_policy")

python examples/recorded_calls.py request-policy-scale ./origin producer "$producer" \
  reuse-default "$reuse_policy" unused-plan policy-hit 3 --selection adopted --selection-commit "$adopted"
python examples/recorded_calls.py inspect ./origin policy-hit

python examples/recorded_calls.py request-policy-scale ./origin producer "$producer" \
  execute-default "$execute_policy" pending-fresh policy-fresh 3
python examples/recorded_calls.py inspect ./origin policy-fresh
```

| Request override | Pinned default | Decision |
| --- | --- | --- |
| `default` (omitted) | `reuse-by-default` | Reuse the exact selected result, or prepare fresh work if the named slot is absent. |
| `default` (omitted) | `execute-by-default` | Prepare fresh work without reading a selection. |
| `fresh` | Either | Prepare fresh work without reading a selection. |
| `reuse-selected` | Either | Require and reuse the exact selected result. |

On a reuse path, give `--selection REF` and the exact `--selection-commit ID`.
For a default reuse request that expects the slot to be absent, give only
`--selection REF`. A moved, unexpectedly present or missing, malformed, or
wrong-request selection rejects; none is treated as an absent slot. The match
still requires the exact portable request (producer, implementation, and
factor). Fresh-only paths don't read any supplied selection slot.

The command prints a **decision commit ID** on both paths. Reuse publishes the
original result to `main` and retains the decision in one transaction. It does
not create a live plan or an attempt. Fresh work leaves `main` unchanged and
creates a normal plan at `pending-fresh`: use its `plan_commit` from `inspect`
with the [existing export and worker commands](#save-a-scale-request-before-sending-it).
The decision does not dispatch work or record what a later worker does. No
path automatically installs or changes a selection. All supplied refs must be
mutually distinct and different from `main`; both output names must be unused,
even on the reuse path where the plan name remains unused.

Each decision has its own UUID and retains the local plan (including its
saved `main`, if any), the exact policy version, and, on reuse, the exact
selection version. Inspection explains the route after the original refs are
gone, without executing or consulting current defaults. An absence decision
records the slot observed at request time, not a claim about its current
contents. Policy versions and decisions do not change the portable request or
result IDs. The legacy commands do not consult policies.

#### Choose an implementation from a pinned intent definition

Continue with the v1 selection at `adopted` from
[versioned attempt selection](#record-a-new-version-of-an-attempt-selection).
An intent definition pins the reuse mode, a default scale implementation, and
one named selection slot per implementation. Publish a new version to change
the default without moving the old definition or changing either slot:

```sh
calls() { python examples/recorded_calls.py "$@"; }
intent_v1=$(calls define-scale-intent ./origin intent-v1 example.scale@1 \
  --reuse-default reuse-by-default --v1-selection adopted --v2-selection selected-v2)
intent_v2=$(calls define-scale-intent ./origin intent-v2 example.scale@2 \
  --basis-ref intent-v1 --basis-commit "$intent_v1")

# v2 is the default. Its slot is absent, so this creates a fresh v2 plan.
calls request-intent-scale ./origin producer "$producer" intent-v2 "$intent_v2" plan-v2 decision-v2 3
calls inspect ./origin decision-v2

# Explicitly choose v1 without overriding the reuse mode.
calls request-intent-scale ./origin producer "$producer" intent-v2 "$intent_v2" unused-v1 decision-v1 3 \
  --implementation example.scale@1 --selection-commit "$adopted"
calls inspect ./origin decision-v1
```

Pinning `intent-v1` and omitting `--implementation` still chooses v1. The
implementation override is independent of `--override default|fresh|reuse-selected`.
When the reuse path consults a slot, supply the exact `--selection-commit`, or
omit it to require absence. A v1 selection in the v2 slot is an error, even if
both implementations return the same value. Fresh-only paths read neither
slot, and a reuse path never reads the other implementation's slot.

The command prints a decision commit ID. Inspection explains the implementation
choice and the reuse decision from retained history, not live refs. The
[policy request rules](#set-a-reuse-default-for-the-scale-intent) still apply to
atomic publication and fresh plans; both declared slot names must also be
separate from the other refs in the request. Use the existing export and worker
commands for fresh work, and select its result explicitly if wanted. Neither
command dispatches work or changes a selection, and neither changes the IDs or
layouts of portable requests and results.

#### Record advisory implementation supersession

Continue from [the pinned intent example](#choose-an-implementation-from-a-pinned-intent-definition).
Record an operational replacement, using the earlier recorded attempt as
example evidence. Both scale implementations still multiply the same way;
this example does not claim a defect.

```sh
noted=$(calls declare-scale-supersession ./origin intent-v1 "$intent_v1" noted \
  example.scale@1 example.scale@2 operational-replacement worker-a "$first_attempt")
calls inspect ./origin noted  # v1 is still the default

# The old decision knew no declaration. This supplies a separate knowledge view.
calls inspect ./origin decision-v1 --knowledge-commit "$noted"

# Promote v2 explicitly on the branch carrying the declaration.
promoted=$(calls define-scale-intent ./origin promoted example.scale@2 \
  --basis-ref noted --basis-commit "$noted")
calls request-intent-scale ./origin producer "$producer" promoted "$promoted" next-v2 decision-promoted 3
calls inspect ./origin decision-promoted
```

The declaration is an intent version with ordered parents `(exact basis,
exact evidence)`. The two input refs must match their supplied IDs, the IDs
must differ, and the output ref must be new. All three refs must differ from
each other, `main`, and both selection slots. The endpoints must be distinct supported versions; the
reason is `correctness-fix` or `operational-replacement`. Evidence is an ordinary
commit with a nonempty tree. Its link retains the evidence, but does not certify
its relevance or the recorded assessment. A branch inherits its declaration
and cannot add a second one; a sibling from an undeclared basis can record its
own. Declaring does not move existing refs, promote a default, execute work,
or affect which results are eligible for reuse. You can still explicitly select v1 under
`promoted` and reuse a matching result from the v1 slot.

Decision inspection reports `as_known_then` from the exact intent parent, not
from a current ref or a claim that the requester consulted the declaration.
`--knowledge-commit` adds a separate `knowledge_view` for an exact intent
version with the same initial definition, including a compatible sibling.
Each view relates the actual request implementation to the declaration as
`predecessor`, `successor`, or `none`. `none` means no declaration at that
snapshot, not that the implementation has no defects. Malformed declarations
and unrelated knowledge are errors, not absence.

#### Keep reusable results for multiple scale requests

Continue from [versioned attempt selection](#record-a-new-version-of-an-attempt-selection)
with `chosen` and `adopted` for factor `3` and an intent such as `intent-v1`
from [the pinned intent example](#choose-an-implementation-from-a-pinned-intent-definition).
A reuse table is separate from the intent's single-selection slots:

```sh
empty=$(calls define-scale-reuse-table ./origin intent-v1 "$intent_v1" example.scale@1 table-empty)
one=$(calls update-scale-reuse-table ./origin table-empty "$empty" chosen "$chosen" table-one insert)

# This exact request has no entry yet. The decision leaves a fresh plan.
calls request-table-scale ./origin producer "$producer" intent-v1 "$intent_v1" plan-two miss-two 2 \
  --table table-one --table-commit "$one"
calls inspect ./origin miss-two
```

Use `plan_commit` from that inspection with the [request export and worker
steps](#distinguish-two-executions-of-the-same-request) to run and return one
attempt for factor `2`. Select it as `selected-two`, using the `plan-two` pin.
With its selection commit ID in `selected_two`:

```sh
two=$(calls update-scale-reuse-table ./origin table-one "$one" selected-two "$selected_two" table-two insert)
new=$(calls update-scale-reuse-table ./origin table-two "$two" adopted "$adopted" table-new adopt)

# Reuse the newer factor-3 attempt or the unchanged factor-2 attempt.
calls request-table-scale ./origin producer "$producer" intent-v1 "$intent_v1" unused-three hit-three 3 \
  --table table-new --table-commit "$new"
calls request-table-scale ./origin producer "$producer" intent-v1 "$intent_v1" unused-two hit-two 2 \
  --table table-new --table-commit "$new"
calls inspect ./origin hit-three
calls inspect ./origin table-two   # still selects the original factor-3 attempt
calls inspect ./origin table-new
```

The key is the exact **portable request commit** (producer commit,
implementation version, and factor), not the caller's plan, result value, or
attempt ID. An empty table retains its defining intent version and is scoped to
that intent's lineage and one implementation. Each update retains the exact
previous table and an attempt selection as ordered parents. `insert` requires
an absent key; `adopt` requires a present key and a different attempt commit,
even if both attempts produced the same result. The 16-key limit bounds the
number of entries, not the number of updates; there is no eviction.
Result-only selections are not table entries. Updates neither
run work nor modify a previous table, an input pin, or `main`.

| Route | Effect |
| --- | --- |
| `default` with `reuse-by-default`, exact hit | Publish the existing result and retain a new decision, without leaving a live plan or recording another attempt. |
| `default` with `reuse-by-default`, valid miss or expected absent table | Retain a fresh plan and decision; leave `main` unchanged. |
| `reuse-selected` | Require an exact hit, regardless of the pinned reuse default. |
| `fresh` or `default` with `execute-by-default` | Retain a fresh plan and decision without looking up the supplied table ref. |

On paths that consult the table, give its expected commit, or omit
`--table-commit` to require that `--table` name an absent ref. A pin mismatch,
wrong lineage or implementation, or a malformed delta anywhere in the table
history is an error, not a miss. The other implementation's slot and any
other tables are never searched. `--implementation` is independent of the
reuse override. Refs in each operation must be distinct and not `main`;
only an explicit selection input to a table update can use a reserved
legacy slot. Both request output names must be unused even on a hit.
Each request is one transaction; it never updates a table or dispatches work.

The decision retains the plan, exact intent, and table when a present table
was consulted, even on a miss. `inspect` explains the choice from this history
without resolving old refs. It supports the same historical and supplied
supersession views as the single-slot intent decision. An absent-table decision
records the name with no table parent; it says nothing about the name today.
Portable requests and results, single-slot commands, and native record layouts
are unchanged.

#### Share selected scale results across implementations of one intent

An intent-scoped table lets you explicitly declare that a selected attempt is
reusable across implementations in that lineage. This is a policy choice, not
proof that the implementations are equivalent. The exact key is the producer
**commit** and signed factor. Matching output values do not make two producer
commits interchangeable.

Continue with `intent-v1`, `producer`, and the factor-3 v1 attempt selection
`chosen` from the previous example:

```sh
intent_empty=$(calls define-scale-intent-reuse-table ./origin intent-v1 "$intent_v1" shared-empty)
shared=$(calls update-scale-intent-reuse-table ./origin shared-empty "$intent_empty" shared insert \
  --selection chosen --selection-commit "$chosen")

calls request-intent-table-scale ./origin producer "$producer" intent-v1 "$intent_v1" unused-v2 shared-hit 3 \
  --implementation example.scale@2 --table shared --table-commit "$shared"
calls inspect ./origin shared-hit
calls inspect ./origin main

removed=$(calls update-scale-intent-reuse-table ./origin shared "$shared" shared-removed remove \
  --producer-commit "$producer" --factor 3)
calls request-intent-table-scale ./origin producer "$producer" intent-v1 "$intent_v1" next-v2 shared-miss 3 \
  --implementation example.scale@2 --table shared-removed --table-commit "$removed"
calls inspect ./origin shared-miss
calls inspect ./origin shared-hit  # still explains the original v1 reuse
```

On the hit, the plan retained by the decision describes the requested v2
work; `main` points to the original v1 result. `inspect` reports
`request_commit` and `request_implementation` separately from
`producing_request_commit` and `producing_implementation`. No v2 attempt ran.
The exact intent, plan, and consulted table are retained, so inspection doesn't
need the original refs. Advisory supersession does not block reuse; the
historical and supplied knowledge views still describe the requested version.

Updates are create-only: `insert` requires an absent key, `adopt` requires a
present key and a different attempt, and `remove` requires a present key and
no selection argument. Adoption can change the producing implementation.
Removal affects only that key in the new table version. It frees a slot under
the 16-key cap and preserves previous versions, attempts, and old decisions.
It does not ban a result: you can deliberately insert its selection again.
`inspect` on a table lists the current keys, selections, and producing requests.
Requests never search other tables or automatically select newly produced results.

The route and pin rules are the same as for the
[implementation-scoped table](#keep-reusable-results-for-multiple-scale-requests), except that the
table must be intent-scoped and match the exact intent lineage; it need not
match the requested implementation. After removal, a reuse-by-default miss
leaves a fresh plan and `main` unchanged; `--override reuse-selected` fails.
Use unused output names as in the previous example. Existing single-slot and
implementation-scoped commands still require an exact implementation match.

For reuse across different derivations of the same typed value, see the separate
[recorded argument maps example](docs/recorded-argument-maps.md). It keeps both
constructions and distinguishes the new request from the attempt that ran.
For shipped built-in operations on recorded nodes, see the [versioned built-ins
walkthrough](docs/internal-builtins.md#example-promote-a-getter-and-reuse-an-ordinary-result).
The [composed node calls walkthrough](docs/composed-node-calls.md#walkthrough)
passes the recorded result of one call to the next and reuses downstream work
without losing the distinction between the requested and original producers.
The [closure-bound dependencies walkthrough](docs/closure-bound-dependencies.md#walkthrough)
pins getter versions and a scale source before invocation, then reuses by
captured value without replacing the producer's capture.
The [captured ordinary calls walkthrough](docs/captured-ordinary-calls.md#walkthrough)
lets the callable itself invoke captured add and double, with separate reuse
and producer history at each level.

#### Publish reuse with a durable record

Continue from the [durable request handoff](#save-a-scale-request-before-sending-it).
Keep the original result pinned locally (skip `stage-input` if it is already
under `saved-result`), then make a new plan for the same producer and factor:

```sh
python examples/recorded_calls.py stage-input ./origin saved-result ./scale.dml
plan=$(python examples/recorded_calls.py request-scale ./origin producer "$producer" next-plan 3)
python examples/recorded_calls.py publish-reused-scale ./origin next-plan "$plan" saved-result "$result" reuse-001
python examples/recorded_calls.py inspect ./origin
python examples/recorded_calls.py inspect ./origin reuse-001
```

There is no new dispatch, execution, or staging step for the new plan. Supply
its exact ID and the original worker result ID, not the import receipt. In one
transaction, `publish-reused-scale` checks the exact plan and result pins, the
request and its producer edge and factor, and the plan's saved `main`. It sets
`main` to the same result commit, consumes only the plan pin, and creates a
fresh reuse ref. All four ref names must be distinct. A stale selection or
occupied reuse ref leaves committed state unchanged, even if the occupied ref
already holds the same record. This is not a retry acknowledgment.

`inspect ./origin` still reports the original result. `inspect ./origin reuse-001`
reports `publication_mode: "reuse"`, the original pin names, and the exact plan,
request, result, and captured `main`. The separate record is an ordinary commit
with the plan and result as its ordered parents. Keep its ref to retain those
commits, their dependencies, and the captured old `main` (if any) through
collection, even after the live refs move. This records how publication selected
the result; it does not prove the result's age, authenticate a worker, or verify
arithmetic. Ordinary staged publication does not create this record.

### Install and link the C library

For example, install the headers and static library under a local prefix:

```sh
meson setup build/release --buildtype=release --prefix="$PWD/build/install" --libdir=lib
meson compile -C build/release
meson install -C build/release
```

The archive includes the pinned vendor libraries. On a Unix compiler driver that
accepts `-pthread`, build and run the [standalone transfer example](examples/transfer_history.c)
against the installed headers and archive:

```sh
run_dir=$(mktemp -d "$PWD/build/transfer-example.XXXXXX")
cc -std=c11 -Ibuild/install/include examples/transfer_history.c \
  build/install/lib/libdml.a -pthread -o "$run_dir/transfer_history"
"$run_dir/transfer_history" "$run_dir/source" "$run_dir/destination"
```

The program creates two revisions in the source repository and transfers the tip
and its history. It [atomically stages the import](docs/spec-next/transfer.md#atomic-staging)
under `incoming` and reopens the destination to inspect it while `main` is still
absent. It then explicitly publishes the inspected commit to `main` and reopens
again. Through both refs it verifies that the tip reads `43` and its first parent
reads `42`. Use two distinct paths that do not yet exist, with existing parent
directories. The program leaves both repositories and the staging ref for inspection.

Alternatively, use two fresh paths to [record a result without publishing to `main`](docs/spec-next/transfer.md#record-a-result-without-publishing-to-main):

```sh
"$run_dir/transfer_history" --lineage "$run_dir/input" "$run_dir/worker"
```

The worker reopens and verifies that `result-pin` yields `44`, that its sole parent
is the exact staged input (`43`), and that the recorded implementation ID is
`example.add-one@1`. The worker's `main` remains absent.

To [return and publish that result](docs/spec-next/transfer.md#return-and-publish-the-recorded-result),
run the full workflow from two new paths:

```sh
"$run_dir/transfer_history" --round-trip "$run_dir/original" "$run_dir/compute"
```

The original repository stages the result under `returned` and inspects it without
recomputing it. It conditionally moves `main` to the inspected commit and releases
`returned` only after successful publication. After reopening, its `main` yields
`44`. The worker releases `incoming` only if it still points at the inspected
input, then reopens and reads the same result and input through `result-pin`.

To run [explicit garbage collection](docs/spec-next/repository.md#explicit-garbage-collection)
after each staged import and again after releasing the staging refs, use
`--round-trip --collect` with two fresh paths. The example expects zero removals
and verifies the pinned and published lineage again.

To diagnose a repository without modifying it, use the
[read-only integrity and reachability API](docs/spec-next/repository.md#snapshot-integrity-and-reachability).
It distinguishes damage from intact objects that no ref retains. It does not
perform garbage collection.

### Three-process provenance handoff

Using the installed library and `$run_dir/source` from the first example above,
run the [handoff](docs/spec-next/transfer.md#resume-a-handoff-across-processes) as
three separate processes:

```sh
cc -std=c11 -Ibuild/install/include examples/provenance_handoff.c \
  build/install/lib/libdml.a -pthread -o "$run_dir/provenance_handoff"
"$run_dir/provenance_handoff" request "$run_dir/source" "$run_dir/request.dml" \
  example.add-one@1 snapshot value
"$run_dir/provenance_handoff" work "$run_dir/handoff-worker" "$run_dir/result.dml" "$run_dir/request.dml"
"$run_dir/provenance_handoff" publish "$run_dir/source" "$run_dir/result.dml"
"$run_dir/provenance_handoff" release-input "$run_dir/handoff-worker"
```

The request arguments are the versioned operation (`example.add-one@1` or
`example.subtract-one@1`), tree entry and DAG binding. The request commit records
all three and points back to the source snapshot. Only the bundle files cross
between roles.

The fourth command is optional worker cleanup. Use a fresh worker path when
supplying a request bundle. This example uses fixed ref names for one handoff
at a time; don't reuse or retarget those refs while that handoff is active.
Keep `request-pin` until publication succeeds and leave `result-pin` in place
to retain the worker's result, request and input snapshot.

- Run `request SOURCE NEW_REQUEST` without the operation and selector to export
  the existing `request-pin`, even if `main` has moved.
- Run `work WORKER NEW_RESULT` without the request path to resume from `incoming`
  or re-export an already committed `result-pin`.
- Run `stage-result SOURCE RESULT` to stop after staging. Run `publish SOURCE`
  without the result path to resume from the committed `returned` ref.

At any committed checkpoint, inspect either repository without rerunning the
operation or changing refs:

```sh
"$run_dir/provenance_handoff" inspect source "$run_dir/source"
"$run_dir/provenance_handoff" inspect worker "$run_dir/handoff-worker"
```

The source view reports why a staged result is blocked or whether it passes
publication checks in the current snapshot. See the
[inspection semantics](docs/spec-next/transfer.md#inspect-a-committed-checkpoint).

These are committed repository checkpoints, not arbitrary crash recovery or
idempotent retries of the entire workflow. Bundle paths are regular binary files.
Export never overwrites an existing file, but an interrupted write can leave a
partial file. Discard incomplete exports and retry to a fresh output path.

### Optional Nix development shell

On x86_64 and aarch64 Linux/macOS, `nix develop` supplies the compiler, Meson, and
Ninja. On Linux it also supplies Valgrind for manual memory checks. Use the
separate `.#quint` shell for [Quint behavior checks](#quint-behavior-checks).
Neither shell runs builds or checks automatically.

```sh
nix develop -c scripts/check.sh
```

## C editor setup

Run `scripts/setup-lsp.sh` in the build environment to generate an ignored
`compile_commands.json` for clangd from a separate build in `build/editor/`.
This optional tool uses Python 3 to assemble the database, including system-header
paths for Nix compiler wrappers. It does not compile or install anything.

## Contributing

See [AGENTS.md](AGENTS.md) for code and documentation conventions and
[the validation policy](docs/validation-policy.md) for reporting what was checked.
