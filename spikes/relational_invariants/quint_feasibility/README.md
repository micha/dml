# Quint feasibility: DML refs and transactions

Status: feasibility spike closed. Direct Quint evaluation and deterministic Python generation
passed for the create-only, mixed create/update, transaction-batch, Python context-completion
and explicit-ending context profiles on Linux ARM64. [Graph-backed checks](#graph-backed-transaction-verification)
reopen saved transaction evidence. [Measurements](#transaction-graph-repeatability-and-cost)
did not justify a verification cache. [Failure artifacts](#replay-a-shrunk-transaction-failure)
keep graph writes off the passing and shrinking paths. The [final experiment](#native-fault-control)
caught, shrank, and replayed a fault introduced in a disposable native build. A separate
[design-to-build follow-up](#read-context-design-to-build) refined a Python read-context rule in
Quint and regenerated the concrete test. No Quint adoption, general compiler, or maintained-gate
integration.

The [trace interpreter design](TRACE-INTERPRETER-DESIGN.md) records the proposed follow-up:
Quint supplies histories for native replay, with independent evidence of repository changes.

## Authority boundary

This note records the protocol and results of this experiment, not a DML requirement.
[Ref semantics](../../../docs/spec-next/repository.md#refs) and the
[Python API](../../../docs/spec-next/python-api.md#repository-and-transactions) own the
contract. The [maintained validation scope](../../../README.md#maintained-validation-scope)
is unchanged.

## What was checked

With a valid target commit, `Transaction.create_ref` on an existing ref must reject with
`invalid_state` and leave the published target unchanged, even when the requested target is
identical. [`ref_rules.qnt`](ref_rules.qnt) defines this rule once: `whenRefExists` selects
attempts and `expectRejectedAndPreserved` checks them. Nonmatches are `unexercised`, not passes.

- [`ref_model.qnt`](ref_model.qnt) defines the transition separately from the rule. Quint
  exhaustively enumerates the 121 histories of length 0–4 over three abstract target IDs,
  checks each attempt, and checks same-target and different-target matching witnesses. This
  is explicit finite enumeration in Quint, not a randomized simulation or a model-checker proof.
- The shared [`ref_binding.py`](ref_binding.py) creates real rooted commits in a fresh native repository
  for each history. Every requested create runs in a fresh write transaction; the harness
  aborts failed calls and observes the published ref in separate read transactions before
  and after. It passes the IDs and result to Quint, not a model-predicted post-state. The
  adapter distinguishes an absent ref from a `not_found` on its target using the current
  native `ref was not found` diagnostic; other read failures propagate.
- The [direct evaluator](exercise_ref.py) encodes observations as a typed Quint list and decodes one ITF
  state with an ordered list of verdicts. ITF success means evaluation completed, not that
  the rule passed. Hypothesis receives violations during each property invocation. This
  path runs the original Quint rule without translation.

## Run locally

From the repository root, with Node/npm available, enter `nix develop` for Python 3.12,
Hypothesis, and the native build tools. The spike-only Quint install stays under ignored
`build/`. The TypeScript evaluator needs neither a Java model checker nor the Rust backend.

```sh
base="$PWD/build/quint-feasibility"
spike=spikes/relational_invariants/quint_feasibility
mkdir -p "$base/tool" "$base/python/daggerml"
npm install --prefix "$base/tool" --cache "$base/npm-cache" --no-save \
  --no-audit --no-fund --ignore-scripts @informalsystems/quint@0.33.1
quint="$base/tool/node_modules/.bin/quint"

export NIX_LDFLAGS="${NIX_LDFLAGS#-rpath $PWD/outputs/out/lib}"
meson setup "$base/native" --wrap-mode=nodownload
ninja -C "$base/native" _core.abi3.so
cp python/daggerml/daggerml/__init__.py "$base/native/_core.abi3.so" "$base/python/daggerml/"

"$quint" typecheck "$spike/ref_model.qnt"
"$quint" test "$spike/ref_model.qnt" --backend=typescript --max-samples=1
PYTHONPATH="$base/python" python -B "$spike/exercise_ref.py" --quint "$quint"
```

## Direct-evaluation results

Base `971b630` with only isolated, unpublished spike changes. Linux ARM64, Nix Python 3.12.15,
Hypothesis 6.151.10, Node 22.23.2, Quint 0.33.1. The Quint top-level version is pinned for
this experiment; the npm dependency tree is not a repository lock.

| Check | Result |
| --- | --- |
| Quint model | Exit 0; both safety and matching-witness tests passed |
| Overwrite model control | Exit 1 as intended; both tests detected the overwrite |
| Directed real DML | Fresh create unexercised; same-target and different-target duplicates passed |
| Fabricated observations | False success and rejection with a changed target each violated the rule |
| Hypothesis | 24 histories; 48 matching attempts passed, 23 unexercised |
| Shrinking | Fabricated overwrite shrank `[2, 2, 0, 0]` to `[0, 1]` with failing IDs and result |

The concrete command exited 0 in about 16 seconds for these checks. Logs and exit codes are
local ignored artifacts under `build/quint-feasibility/`. The maintained API, test gate,
fixtures and dependencies were not changed. The full maintained gate, CI, and other platforms
were not rerun for this isolated experiment.

## Deterministic Python generation

[`generate_python.py`](generate_python.py) compiles `ref_rules.qnt` to type-checked Quint JSON
and lowers the three verdict functions and their constructors. It emits a Hypothesis driver
from a fixed template using the spec's operation, target alphabet and history bound. The
bounded model reads the same scenario. The handwritten [`ref_binding.py`](ref_binding.py)
executes the actual DML operation and assembles its observations; it has no correctness rule.
The generator does not translate the abstract transition model or invent bindings for new DML
operations. It rejects unsupported IR, schema changes and unmapped operations.

After the setup above, run these commands from the same Nix shell:

```sh
mkdir -p "$base/gen-a" "$base/gen-b" "$base/gen-offline/empty-bin"
PYTHONHASHSEED=1 python -B "$spike/generate_python.py" --quint "$quint" --out "$base/gen-a/generated_ref.py"
PYTHONHASHSEED=2 python -B "$spike/generate_python.py" --quint "$quint" --out "$base/gen-b/generated_ref.py"
cmp "$base/gen-a/generated_ref.py" "$base/gen-b/generated_ref.py"
PYTHONPATH="$base/python:$base/gen-a" \
  python -B "$spike/check_generated.py" differential --quint "$quint"

cp "$spike/ref_binding.py" "$spike/check_generated.py" "$base/gen-a/generated_ref.py" "$base/gen-offline/"
python_bin=$(command -v python)
(cd "$base/gen-offline" && env -i PATH="$PWD/empty-bin" PYTHONPATH="$base/python" \
  "$python_bin" -B check_generated.py offline)
```

| Check | Result |
| --- | --- |
| Repeat generation | Byte-identical with different hash seeds and with the Quint target set reordered |
| Baseline agreement | All 426 actual and 144 synthetic observations agreed with direct Quint |
| Changed-spec control | Different alphabet, bound and expected status took effect; all 88 verdicts agreed |
| Unsupported-spec control | `or` type-checked in Quint; the generator exited 1 and emitted no file |
| Python-only property | 32 histories: 65 matching passes, 31 unexercised; missing evidence rejected |
| Python-only shrinking | Fabricated overwrite shrank `('c', 'c', 'a', 'a')` to `('a', 'b')` |

For the changed-spec control, use an isolated rule copy, change the target set to
`Set("z", "x")`, the bound to `3`, and the expected failure to `Failed("not_found")`.
Generate from that copy with `--source`, then use the copy and `--changed-profile` in the
differential command. The actual DML adapter must still record `invalid_state`.

The 121 real histories had 306 matching passes and 120 nonmatches. The synthetic matrix
crossed absent/present before and after, each requested target, and success or two error
codes; it yielded 9 passes, 36 nonmatches and 99 violations. A first differential attempt
put all observations in one Quint input and hit the 10-second process deadline. Batching
at 32 observations kept that deadline unchanged and passed. On this host the Python-only
property and shrink control together took about 0.5 seconds. The stage had no Quint source
or generator and did not expose Quint, Node or npm on `PATH`; it is not a filesystem sandbox.
Generated Python, control sources, logs and exits are in ignored `build/quint-feasibility/`.

## Mixed create/update histories

[`mixed_ref_rules.qnt`](mixed_ref_rules.qnt) lists the operations, targets, history bound
and rule IDs. It keeps the duplicate-create rule and adds two update rules: updating an absent
ref returns `not_found` and leaves it absent; updating an existing ref succeeds and publishes
the requested commit. Neither generator nor binding filters actions by current ref state.
The binding captures native `invalid_state` and `not_found` statuses; unrelated errors propagate.

[`mixed_ref_model.qnt`](mixed_ref_model.qnt) defines transitions separately. The generated
Python driver samples operation/target pairs, checks each observation against every rule,
and fails if any rule had no match across the suite. The generator supports the two DML
operations through an explicit binding; the Python driver does not list the rule names.

After the setup above, use the same Nix shell:

```sh
mixed="$base/mixed"
mkdir -p "$mixed/gen-a" "$mixed/gen-b" "$mixed/offline/empty-bin"
"$quint" typecheck "$spike/mixed_ref_model.qnt"
"$quint" test "$spike/mixed_ref_model.qnt" --backend=typescript --max-samples=1
for run in a b; do
  python -B "$spike/generate_python.py" --quint "$quint" --source "$spike/mixed_ref_rules.qnt" \
    --out "$mixed/gen-$run/generated_mixed.py"
done
cmp "$mixed/gen-a/generated_mixed.py" "$mixed/gen-b/generated_mixed.py"
PYTHONPATH="$base/python:$mixed/gen-a" python -B "$spike/check_mixed.py" differential --quint "$quint"
cp "$spike/ref_binding.py" "$spike/check_mixed.py" "$mixed/gen-a/generated_mixed.py" "$mixed/offline/"
python_bin=$(command -v python)
(cd "$mixed/offline" && env -i PATH="$PWD/empty-bin" PYTHONPATH="$base/python" \
  "$python_bin" -B check_mixed.py offline)
```

| Check | Result |
| --- | --- |
| Bounded model | Both tests passed over 85 histories (0–3 actions with two target IDs); every rule had a witness |
| Model negative control | Allowing an update to create a missing ref failed bounded safety, as intended |
| Deterministic emission | Byte-identical across two hash seeds and after reordering all three Quint sets |
| Differential check | All 1,008 verdicts agreed across 228 real attempts and 108 synthetic observations |
| Spec-only rule control | A fourth rule for first-create success was emitted, matched and agreed with Quint without Python changes |
| Python-only property | 40 histories: 25 duplicate-create, 13 existing-update and 27 missing-update matches passed |
| Python-only negative controls | Rejected missing and mismatched evidence; create-only histories were insufficient for the update rules |
| Python-only shrinking | A fabricated failed update shrank from `create(a) → create(a) → update(b)` to `create(a) → update(b)` |

The bounded concrete run had 44 duplicate-create, 44 existing-update and 70 missing-update
matches; all passed. The synthetic matrix tested both operations, absence and each target
before and after, each requested target, and three outcomes. Real DML still executed during
the shrink control; only the observation was changed. The original create-only profile
regenerated byte-identically and passed its differential regression. Logs and control sources
are local under ignored `build/quint-feasibility/mixed/`.

## Transaction batches

The [repository transaction contract](../../../docs/spec-next/repository.md#transactions) and
[Python failure handling](../../../docs/spec-next/python-api.md#contexts-and-failure-handling)
own the requirements. This profile checks multiple ref mutations and a new scalar datum in
one write transaction, followed by explicit commit or abort. It includes a caught mutation
failure followed by an attempted commit on that same transaction, rather than automatically
aborting after the failure.

- [`transaction_rules.qnt`](transaction_rules.qnt) owns six rules: per-step create/update effects,
  observation continuity, a genuinely new staged marker, clean commit publication,
  poisoned-commit rejection/rollback, and explicit-abort rollback. Continuity links the first
  step to the initial snapshot, every subsequent before/after observation, and the terminal
  observation to staged state (or initial to staged for an empty history). It also checks
  prior-poison flags against preceding recorded failures. It does not predict hidden ref state.
- [`transaction_model.qnt`](transaction_model.qnt) defines transitions independently of those
  predicates. It exhaustively checks 510 bounded batches: three initial ref states, 85 histories
  of 0–3 operation/target pairs, and two endings. This is finite enumeration, not an unbounded
  proof or external model-checker run.
- [`transaction_binding.py`](transaction_binding.py) executes all requested operations, including
  attempts after poisoning. It captures actual before/after reads, operation outcomes and ending
  outcome. The Python wrapper refuses reads after poisoning; evidence records
  `Unreadable("invalid_state")`, not an invented preserved internal state. Published ref and
  marker state are read separately after ending the transaction, before fallback abort cleanup.
  A rejected commit that leaves the write transaction active therefore fails the fresh read
  instead of borrowing rollback from cleanup. Unrelated errors propagate.
- The marker ID is obtained through a preparatory native insertion that is aborted. A separate
  read establishes absence before the tested batch; a read inside the batch establishes presence
  before any ref attempt. This distinguishes rollback from insertion of an already-stored object.
- [`generate_transactions.py`](generate_transactions.py) reuses the original lowerer's checked-IR
  helpers without changing the earlier generators. It adds list length, boolean `or`, integer
  literals, record construction, local values and left folds with lexically scoped binary lambdas.
  The type layouts and operation
  binding remain explicit and narrow. Unsupported constructs/schema changes fail without emission.
  The generated driver receives rule IDs and scenario bounds from Quint and counts matching
  witnesses across the suite.

After the setup above, run from the same Nix shell:

```sh
work="$base/transactions/review-fixes"
mkdir -p "$work/gen-a" "$work/offline/empty-bin"
"$quint" typecheck "$spike/transaction_model.qnt"
"$quint" test "$spike/transaction_model.qnt" --backend=typescript --max-samples=1
python -B "$spike/generate_transactions.py" --quint "$quint" \
  --out "$work/gen-a/generated_transactions.py"
PYTHONPATH="$base/python:$work/gen-a" python -B "$spike/check_transaction_generation.py" \
  --quint "$quint" --out "$work/controls"
PYTHONPATH="$base/python:$work/gen-a" python -B "$spike/check_transactions.py" \
  differential --quint "$quint"
cp "$spike/transaction_binding.py" "$spike/ref_binding.py" "$spike/check_transactions.py" \
  "$work/gen-a/generated_transactions.py" "$work/offline/"
python_bin=$(command -v python)
(cd "$work/offline" && env -i PATH="$PWD/empty-bin" PYTHONPATH="$base/python" \
  "$python_bin" -B check_transactions.py offline)
```

| Check | Result |
| --- | --- |
| Bounded model | Both tests passed; 510 batches safe and every rule matched |
| Model negative controls | Poisoned publication, marker-only leakage and disconnected staged state each failed bounded safety |
| Deterministic emission | Byte-identical across hash seeds and reordering all four scenario/registry sets |
| Scenario control | Changed target alphabet and history bound took effect in generated Python |
| Spec-only backend control | Nested folds, local values and records agreed with Quint for nonmatch, pass and violation, including shadowing |
| Fail-closed controls | Type-correct unsupported list selection and changed observation schema emitted no file |
| Differential evaluation | All 8,250 verdicts agreed over 510 real and 865 synthetic batches |
| Python-only property | 80 batches; 19 clean commits, 29 poisoned commits and 32 aborts matched; 80 continuity/marker and 74 step-rule matches |
| Evidence/publication controls | Missing/misassociated/malformed evidence and eight fabricated publication failures rejected |
| Continuity regressions | Five disconnected histories passed the older five rules but violated continuity |
| Ending-consumption control | A deliberately non-consuming rejected commit failed its fresh read before fallback cleanup; the injected leak was then cleaned up |
| Generic shrinking | Fabricated partial ref publication shrank three actions to `create(a) → create(a)` followed by commit |
| Existing-ref shrinking | Value shrinking retained an existing ref, a successful update to a different target, duplicate-create rejection and rejected commit |

The bounded real run had 45 clean commits, 210 poisoned commits and 255 aborts; all passed.
The synthetic matrices cross outer ref states, endings, outcomes and marker visibility;
individual step states, targets, outcomes and prior-poison status; marker presence; and poisoned
completion evidence, plus five targeted continuity regressions. Every rule had synthetic violations.
The artificial nested-fold rule is only a compiler control, not a DML requirement.

### Review corrections and evidence boundaries

The initial transaction experiment reported 6,850 agreeing verdicts and 510 passing real batches.
A subsequent review exposed two assurance defects that those checks and the initial read-only
review missed:

- Locally valid step effects and staged/published equality did not require a continuous history.
  For example, `before=A`, successful `update(B)` with `step.after=B`, and `staged=after=A`
  passed the original checker. The new continuity rule rejects this and separate first-step,
  interior-step, empty-history and prior-poison inconsistencies. Each targeted control still
  passes every older rule, isolating the added obligation.
- The adapter aborted in `finally` before inspecting publication. That could supply rollback
  when a rejected commit failed to consume its transaction. Observation now precedes fallback
  cleanup. A test-only replacement of poisoned commit leaves it active; the real fresh-read
  guard rejects it, and only then does cleanup abort it. This checks supported API-level
  consumption/visibility, not every internal native-handle invariant.

The initial counts remain historical evidence for incomplete predicates and cleanup-dependent
observations, not acceptance of the corrected profile. Original artifacts remain under
`build/quint-feasibility/transactions/`; corrected runs are under its `review-fixes/` directory.

The separate existing-ref control generated all create/update attempts without state-based
filtering. It corrupted publication only after observing a successful update to a different
commit followed by a non-poisoned duplicate-create rejection and failed commit. Hypothesis
shrunk initial `b`, `update(a) → create(a)` to initial `a`, `update(b) → create(a)`; both ended
with rejected commit. This is value shrinking that preserves the required two-action story,
not action-count shrinking. The generic absent-ref control separately demonstrated 3→2 action
shrinking. Real observations were checked before either control corrupted only publication.

These checks used the existing Linux ARM64/Nix/Quint toolchain recorded above. Ninja checked
the native target and reported no work; the current Python wrapper and native module were
restaged before real execution. The offline stage had no Quint source/generator or Quint,
Node or npm on `PATH`; it was not a filesystem sandbox. Each shrink invocation still executed
real DML before corrupting only the evidence. Logs, generated Python, control sources and exits
are ignored local artifacts under `build/quint-feasibility/transactions/`. The reproduction
commands above use its `review-fixes/` directory for the corrected profile.

## Python write-context completion

The [Python context contract](../../../docs/spec-next/python-api.md#contexts-and-failure-handling)
owns the requirements. This profile extends the isolated experiment to actual `with tx:`
completion, not a direct call to `__exit__`:

- Normal exit publishes clean writes. After a caught mutation failure, normal exit rejects
  with `invalid_state` and rolls back both the ref and the new marker.
- Exceptional exit aborts and propagates the **same exception object**, including when an
  earlier mutation failure was caught inside the context. Matching a type or message is
  insufficient evidence of original-exception propagation.

[`context_rules.qnt`](context_rules.qnt) imports the existing transaction step, continuity
and marker predicates rather than redefining them. It adds clean/poisoned normal-exit and
exceptional-exit predicates over a nested transaction observation and exception evidence.
[`context_model.qnt`](context_model.qnt) reuses the independent ref-operation transitions,
then defines context-completion transitions separately from these predicates. Its finite
scope is again 510 batches: three initial states, 85 histories and two completion modes.

[`context_binding.py`](context_binding.py) catches mutation failures without ending the
context, then either exits normally or raises a fresh sentinel instance. Exception evidence
records identity using `is`: original, same-type replacement or suppression; unrelated body
and exit errors propagate. Only an `InvalidStateError` from normal completion after the body
finished becomes an ending outcome. Fresh publication reads precede fallback abort cleanup.
The adapter reuses transaction evidence validation before any rule matches.

[`generate_contexts.py`](generate_contexts.py) adds only the checked two-module import profile
and the context record/entry point to the existing lowerer. It does not add language operators,
generate DML bindings or support arbitrary imports. The prior three generated profiles remain
byte-identical. [`check_context_generation.py`](check_context_generation.py) checks deterministic
emission, spec changes, fail-closed boundaries and deliberately incorrect completion models;
[`check_contexts.py`](check_contexts.py) checks direct Quint agreement and Python-only execution.

After the shared setup above, use the same Nix shell:

```sh
work="$base/contexts"
mkdir -p "$work/gen-a" "$work/offline/empty-bin"
"$quint" typecheck "$spike/context_model.qnt"
"$quint" test "$spike/context_model.qnt" --backend=typescript --max-samples=1
python -B "$spike/generate_contexts.py" --quint "$quint" \
  --out "$work/gen-a/generated_contexts.py"
PYTHONPATH="$base/python:$work/gen-a" python -B "$spike/check_context_generation.py" \
  --quint "$quint" --out "$work/controls"
PYTHONPATH="$base/python:$work/gen-a" python -B "$spike/check_contexts.py" \
  differential --quint "$quint"
cp "$spike/context_binding.py" "$spike/transaction_binding.py" "$spike/ref_binding.py" \
  "$spike/check_contexts.py" "$work/gen-a/generated_contexts.py" "$work/offline/"
python_bin=$(command -v python)
(cd "$work/offline" && env -i PATH="$PWD/empty-bin" PYTHONPATH="$base/python" \
  "$python_bin" -B check_contexts.py offline)
```

### Context-completion results and review

Base `5f66258` with isolated, unpublished spike changes, using the same Linux ARM64/Nix/
Quint 0.33.1 toolchain as above. The native target reported no work; the current Python wrapper
and native module were restaged before execution.

| Check | Result |
| --- | --- |
| Bounded model | Both tests passed; 510 contexts safe and every rule matched |
| Model negative controls | Exceptional publication, marker leakage, replaced exception and poison masking the body exception each failed safety |
| Deterministic emission | Byte-identical across hash seeds and reordering all four context sets |
| Spec-only controls | Changed alphabet/bound executed; added rule and changed imported predicate agreed with Quint |
| Fail-closed controls | Extra import, changed context/imported layouts and unsupported imported list selection emitted no file |
| Differential evaluation | 12,738 agreeing verdicts over 510 real and 1,613 synthetic contexts |
| Python-only property | 100 contexts: 20 clean normal exits, 35 poisoned normal exits and 45 exceptional exits; all six rules matched |
| Evidence controls | Incomplete/misassociated/malformed evidence, 15 fabricated completion failures and five continuity regressions rejected |
| Actual exit controls | Swallowed/replaced sentinel, publication on exception, silent poisoned completion and non-consuming exit each detected |
| Error propagation | Unrelated body errors, unrelated sentinel, body `InvalidStateError` and unrelated exit error propagated unchanged |
| Shrinking | Fabricated exceptional ref leakage shrank initial `b`, `update(a)` to initial `a`, `update(b)` |
| Earlier profiles | Create-only, mixed and explicit-transaction Python regenerated byte-identically |

The exhaustive concrete run matched 45 clean normal exits, 210 poisoned normal exits and
255 exceptional exits. All 510 matched continuity/marker rules; 504 matched step effects.
These are per-rule witnesses, not an assertion of exhaustive branch coverage for arbitrary
future predicates. The shrink control executed and checked real DML first, then corrupted
only published-ref evidence. It retained the existing-ref update and original exception;
this was **value shrinking**, not action-count reduction.

Two collaborating agents split implementation and the independent differential/offline
harness, then cross-reviewed each other's source and results. The implementation agent
additionally ran the actual exit/error-propagation and continuity controls independently.
The first differential invocation failed because its observation module lacked an explicit
import of transaction constructors; imports in `context_rules` are not re-exports. The harness
was corrected, `not_found` was added to its synthetic outcomes, and the bounded differential
and Python-only checks passed. The failed log remains alongside the corrected `*-v2` evidence
under ignored `build/quint-feasibility/contexts/peer-review/`. Generation controls and independent
review logs remain under `build/quint-feasibility/contexts/`.

The profile remains isolated: no maintained library, test gate, dependencies or storage model
changed; no new coverage exclusions were added. The full maintained gate, CI and other platforms
were not rerun, following the existing isolated validation-scope boundary. Nothing was committed
or pushed for this continuation. The Python-only stage has no Quint sources/generator or Quint,
Node or npm on `PATH`; it is not a filesystem sandbox.

## Explicit endings inside Python write contexts

The [Python lifecycle contract](../../../docs/spec-next/python-api.md#contexts-and-failure-handling)
owns the requirements. The earlier context profile was checkpointed as `484ca43` before
this continuation; its preceding results are retained evidence, not freshly rerun checks.

This profile executes `commit()` or `abort()` **inside an actual `with tx:`**, catches
supported explicit-ending errors, and then either finishes normally or raises a fresh body
sentinel. A successful explicit commit stays published even if the later body raises;
context exit does not undo a completed transaction. A poisoned explicit commit rejects and
rolls back before either kind of exit. Explicit abort rolls back in both cases.

- [`explicit_context_rules.qnt`](explicit_context_rules.qnt) reuses the transaction step,
  continuity and fresh-marker predicates. Its five additional rules check clean/poisoned
  explicit commit, explicit abort, ended-handle operations and subsequent context exit.
- [`explicit_context_model.qnt`](explicit_context_model.qnt) defines transitions separately.
  It enumerates 1,020 contexts: three initial ref states, 85 histories of 0–3 create/update
  attempts and four ending/exit combinations. This is finite enumeration, not an unbounded
  proof or external model-checker run.
- [`explicit_context_binding.py`](explicit_context_binding.py) records the explicit-call
  outcome separately from the eventual context outcome. Immediately after the explicit
  ending, **inside the body and before any probes**, a fresh reader observes the ref and
  marker. Neither later probes, context exit nor fallback cleanup can supply consumption or
  rollback for that observation. A second fresh reader observes publication after exit.
- The binding attempts an ended-handle read, mutation, commit and idempotent abort. Transparent
  instance-local wrappers count public `commit`/`abort` calls only during the tested writer's
  context exit, excluding reader completion, body probes and fallback cleanup. This detects
  repeated completion even when an extra abort is otherwise harmless. These observations
  check supported Python API behavior, not every internal native-handle invariant.
- Original-exception evidence uses `is`, not matching type/message. Unrelated errors propagate;
  an `InvalidStateError` from an erroneous exit after the body finished is recorded as an exit
  failure, including when it masks the sentinel.
- [`generate_explicit_contexts.py`](generate_explicit_contexts.py) supports only the checked
  two-module import profile and explicit evidence layout. It reuses the existing expression
  lowerer; the integer exit-call field adds no arithmetic operators or integer function
  signatures. [`check_explicit_context_generation.py`](check_explicit_context_generation.py)
  and [`check_explicit_contexts.py`](check_explicit_contexts.py) own the independent controls.

After the shared setup above, use the same Nix shell:

```sh
work="$base/explicit-contexts"
mkdir -p "$work/gen-a" "$work/offline/empty-bin"
"$quint" typecheck "$spike/explicit_context_model.qnt"
"$quint" test "$spike/explicit_context_model.qnt" --backend=typescript --max-samples=1
python -B "$spike/generate_explicit_contexts.py" --quint "$quint" \
  --out "$work/gen-a/generated_explicit_contexts.py"
PYTHONPATH="$base/python:$work/gen-a" python -B "$spike/check_explicit_context_generation.py" \
  --quint "$quint" --out "$work/controls"
PYTHONPATH="$base/python:$work/gen-a" python -B "$spike/check_explicit_contexts.py" \
  differential --quint "$quint"
cp "$spike/explicit_context_binding.py" "$spike/context_binding.py" \
  "$spike/transaction_binding.py" "$spike/ref_binding.py" "$spike/check_explicit_contexts.py" \
  "$work/gen-a/generated_explicit_contexts.py" "$work/offline/"
python_bin=$(command -v python)
(cd "$work/offline" && env -i PATH="$PWD/empty-bin" PYTHONPATH="$base/python" \
  "$python_bin" -B check_explicit_contexts.py offline)
```

### Explicit-ending results and review

Base `484ca43` with isolated, unpublished spike changes, on Linux ARM64 with the same
Nix Python 3.12.15, Hypothesis 6.151.10, Node 22.23.2 and Quint 0.33.1 toolchain. Ninja
reported no work; the current wrapper and native module were restaged before real execution.

| Check | Result |
| --- | --- |
| Bounded model | Both tests passed; 1,020 contexts safe and every rule matched |
| Model negative controls | Abort/poisoned publication, post-commit rollback, replaced sentinel, readable ended handle and repeated abort each failed safety |
| Deterministic emission | Byte-identical across hash seeds and reordering all four scenario/registry sets |
| Spec-only controls | Changed alphabet/bound executed all four combinations; a ninth rule and changed imported predicate agreed with Quint |
| Fail-closed controls | Extra import, changed explicit/imported layouts and unsupported imported list selection emitted no file |
| Differential evaluation | 23,528 agreeing verdicts over 1,020 real and 1,921 synthetic explicit-ending contexts |
| Python-only property | 120 contexts; 17 clean commits, 36 poisoned commits and 67 aborts matched; all context-exit/continuity/ended-handle/marker rules matched |
| Evidence controls | Incomplete/misassociated/malformed evidence, 66 fabricated lifecycle failures and five continuity regressions rejected |
| Actual adapter controls | Wrong publication, repeated completion, suppressed/replaced sentinel, four incorrect ended operations and three non-consuming explicit endings detected |
| Error propagation | Unrelated runtime/sentinel/`InvalidStateError` body failures and unrelated exit failure propagated unchanged |
| Shrinking | Fabricated rollback after successful explicit commit shrank initial `b`, `update(a)` to initial `a`, `update(b)`, both followed by an original body exception |
| Earlier profiles | All four profiles regenerated byte-identically; focused poisoned normal/exceptional context regressions passed |

The exhaustive concrete run matched 90 clean explicit commits, 420 poisoned explicit commits
and 510 explicit aborts. All 1,020 matched context-exit, continuity, ended-handle and marker
rules; 1,008 matched step effects. Every rule had synthetic violations. The synthetic matrices
cover step observations, completion outcomes/exception identity/call counts, pre-/post-exit
publication snapshots, each ended-handle probe, marker visibility and disconnected histories.
These are bounded witnesses and differential results, not exhaustive coverage of arbitrary
future predicates. The full differential invocation passed on its first run.

The shrink control checked real DML before corrupting only final publication evidence. It
retained the successful explicit commit, changed ref target and original sentinel. This was
**value shrinking**, not action-count reduction.

Two agents split the implementation and independent harness, then cross-reviewed the other's
source. The implementation agent independently reran the complete generation-control and
Python-only harnesses. Initial offline harness runs exposed two harness defects: a helper's
positional `batch` parameter conflicted with an evidence field of the same name, and a
fabricated explicit-ending snapshot also violated the alphabetically earlier context-exit
rule. Renaming the helper parameter and keeping final publication consistent isolated the
intended rule. Both failed logs remain under `build/quint-feasibility/explicit-contexts/peer-review/`
alongside the passing `offline-v3` results; these were harness corrections, not DML changes.

This continuation was checkpointed locally after independent review of the sources and retained
evidence. No maintained library, gate, dependencies, storage model or coverage exclusions changed.
The full maintained gate, CI and other platforms were not rerun under the existing isolated
validation-scope boundary. Raw logs, generated Python,
control sources, exit codes and reviewed-source hashes remain ignored local artifacts under
`build/quint-feasibility/explicit-contexts/`. The Python-only stage has no Quint sources/generators
or Quint, Node or npm on `PATH`; it is not a filesystem sandbox.

## Graph-backed transaction verification

This isolated continuation exercises one existing transaction-batch case: start at `a`,
update to `b`, attempt a duplicate create at `a`, then attempt commit on the poisoned
transaction. The unchanged [binding](transaction_binding.py) runs the real DML operations
and captures publication before fallback cleanup. The graph stores those observations after
the exercise; it neither computes expected state nor re-executes the transaction on replay.

[`transaction_graph.py`](transaction_graph.py) stores a versioned native datum map under
ref `transaction-evidence` → commit → tree → DAG → literal. Requests and steps use ordered
datum lists, and snapshots and outcomes use tagged lists. The graph has no JSON payload.
The evidence repository is separate from the exercised repository. Observed target IDs are
strings, not links to the original target objects, which this check does not need.
The reader requires the caller's expected commit ID and recipe, validates the decoded batch,
and hands it to the existing generated predicates. A root ID identifies the graph; it does not
attest that the observations actually happened.

After the shared setup above, in the same Nix shell:

```sh
work="$base/transaction-graph"
mkdir -p "$work/gen" "$work/offline/empty-bin"
python -B "$spike/generate_transactions.py" --quint "$quint" \
  --out "$work/gen/generated_transactions.py"
cp "$spike/transaction_graph.py" "$spike/check_transaction_graph.py" \
  "$spike/transaction_binding.py" "$spike/ref_binding.py" \
  "$work/gen/generated_transactions.py" "$work/offline/"
python_bin=$(command -v python)
(cd "$work/offline" && env -i PATH="$PWD/empty-bin" PYTHONPATH="$base/python" \
  "$python_bin" -B check_transaction_graph.py)
```

### Graph-backed results

Both agents cross-reviewed the adapter and harness, then staged and ran the harness separately
on Linux ARM64 with Nix Python 3.12.15. Fresh Quint 0.33.1 generation was byte-identical to
that of the reviewed transaction profile. Both runs reopened root
`e096e6b8470c549025611177fcaaa6e6` and recovered the exact live batch. All six verdicts agreed,
including in a fresh Python process: four passed and two were unexercised. The staged runs
had no Quint, Node or npm on `PATH`; they were not filesystem sandboxes.

The harness independently built native graphs with incomplete publication evidence, an unknown
schema and a parented root. Each was rejected with a matching root pin. The writer rejected
incomplete evidence before creating an evidence repository. The reader also rejected mismatched
recipes and a stale pin after the ref moved. A structurally complete graph that incorrectly
published both the updated ref and the marker violated `commitPoisoned` and left all other
verdicts unchanged.

The harness removes its temporary evidence repositories. Logs, exit codes and reviewed-source
hashes are ignored local artifacts under `build/quint-feasibility/transaction-graph/`. This is
one round-trip case; the continuation below checks repeatability and cost separately.
No maintained code or gate changed, and the full gate and CI were not rerun.

## Transaction graph repeatability and cost

The [measurement harness](measure_transaction_graph.py) pairs two independent executions per
sample, each in a fresh exercised repository. The direct path checks the live batch. The graph
path saves the batch to a separate new evidence repository, reopens it with a root pin, then
checks the reopened batch. Workers run sequentially in fresh Python processes with different
hash seeds. Both paths execute real operations; there is no cache or skipped execution.

The default run measures 30 pairs per recipe in each of four workers after three warmup pairs
per worker and recipe. The harness rotates recipe order and alternates which path runs first.
Each timed check evaluates all six rules; assertions for batch equality, repeat roots, and
expected verdicts run outside the timers. The four two-action recipes cover clean commit,
poisoned commit, explicit abort, and a second clean commit with a different first update but
identical outer observations and verdicts. The clean traces produced distinct roots. An untimed fresh reader verified the pinned graphs and rejected
a mismatched recipe. Flipping only `markerAfter` in the poisoned batch changed its root, failed
reopen under the original pin, and violated only `commitPoisoned` under its own pin.

After the shared setup above, in the same Nix shell:

```sh
work="$base/transaction-graph-measurement"
mkdir -p "$work/gen" "$work/offline/empty-bin"
python -B "$spike/generate_transactions.py" --quint "$quint" \
  --out "$work/gen/generated_transactions.py"
cp "$spike/measure_transaction_graph.py" "$spike/audit_transaction_graph.py" \
  "$spike/transaction_graph.py" "$spike/transaction_binding.py" "$spike/ref_binding.py" \
  "$work/gen/generated_transactions.py" "$work/offline/"
python_bin=$(command -v python)
(cd "$work/offline" &&
  env -i PATH="$PWD/empty-bin" PYTHONPATH="$base/python" "$python_bin" -B \
    measure_transaction_graph.py --json "$work/measurement.json" &&
  env -i PATH="$PWD/empty-bin" PYTHONPATH="$base/python" PYTHONHASHSEED=123 "$python_bin" -B \
    audit_transaction_graph.py > "$work/audit-forward.json" &&
  env -i PATH="$PWD/empty-bin" PYTHONPATH="$base/python" PYTHONHASHSEED=799 "$python_bin" -B \
    audit_transaction_graph.py --reverse > "$work/audit-reverse.json" &&
  cmp "$work/audit-forward.json" "$work/audit-reverse.json")
```

### Measurement results

Two agents cross-reviewed the harnesses and ran the default measurement separately on the same
Linux ARM64 host (Nix Python 3.12.15, ext4 `/tmp`, Quint 0.33.1 generation). All three default runs
produced identical evidence receipts. The table reports ranges of per-recipe, per-run medians,
not a latency guarantee. The logs retain per-stage minima and maxima; the slowest individual
save was 161 ms.

| Timed stage | Median range |
| --- | ---: |
| Validate and check live evidence | 18–24 µs |
| Save native evidence graph | 1.65–1.93 ms |
| Reopen, decode and validate graph | 0.46–0.50 ms |
| Check reopened evidence | 16–21 µs |
| Reopen plus generated check | 0.48–0.52 ms |
| Save, reopen and check after capture | 2.16–2.46 ms |
| Execute and check live | 1.35–1.95 ms |
| Execute, save, reopen and check | 3.63–4.78 ms |

Execution includes the exercised repository's temporary lifecycle. Save includes creating,
committing, and closing the evidence repository, but not creating or cleaning up its enclosing
temporary workspace. A generated check includes observation validation and verdict accounting.
Reopen was timed immediately after save in the same process, without flushing OS caches. The
separate reader's startup and verification were not timed.

The [untimed audit](audit_transaction_graph.py) independently executed and reopened all 510
bounded recipes twice, in fresh processes with different hash seeds and opposite traversal
orders. Both passes found 510 distinct roots and identical recipe-to-root maps. Live and reopened
batches and verdict counts agreed for every recipe. There were 45 clean-commit, 210 poisoned-commit
and 255 abort witnesses, plus 510 each for continuity and marker freshness and 504 for step effects.
This is repeatability for this schema and fixed recipe set, not an estimate of Hypothesis cache
hit rates, collision resistance, or portability across platforms or versions.

**Decision:** do not build a verdict cache for this profile. If the graph is written only to
obtain a cache key, saving it here already costs far more than checking the live observations.
If the graph is required anyway and replay must still reopen and validate it, skipping only the
generated check saves tens of microseconds before lookup costs. Bypassing reopen would be a
different trust contract and was not measured. Revisit if a richer graph or more expensive
invariants make verification a material cost. A future cache would need both exact evidence
identity and checker semantics. A root alone does not attest that the observations occurred,
and a recipe-only hit would hide the marker publication change demonstrated above.

Raw samples, receipts, source hashes and exits are ignored local artifacts under
`build/quint-feasibility/transaction-graph/measure-worker/` and
`build/quint-feasibility/transaction-graph-measurement/coordinator/`. No maintained code or gate
changed; the full maintained gate and CI were not rerun.

## Replay a shrunk transaction failure

[`transaction_failure_artifact.py`](transaction_failure_artifact.py) executes and checks each
Hypothesis example live. A rule violation carries the exact checked batch as it leaves the
example. Only after Hypothesis reports a single violation does the driver save its batch as a
pinned evidence graph and raise `SavedFailure` with the rule, batch and root. It does not save
passing or intermediate shrink cases, re-execute the final recipe, or publish a failure artifact
for an adapter error or missing rule witnesses. This experiment does not select an artifact from
multiple different failures reported together.

`replay_failure` takes the evidence repository, externally supplied root and recipe, then runs the
current generated checker on the saved observations without executing the recipe. It rejects a
valid graph that no longer reproduces a violation. A root pins observations, not checker semantics
or the truth of those observations. The control first checks the actual DML batch, then flips only
`markerAfter` on a poisoned commit to test reporting and replay; it is not a DML failure.

After the shared setup above, in the same Nix shell:

```sh
work="$base/transaction-failure-artifact"
mkdir -p "$work/gen" "$work/offline/empty-bin"
python -B "$spike/generate_transactions.py" --quint "$quint" \
  --out "$work/gen/generated_transactions.py"
cp "$spike/check_transaction_failure_artifact.py" "$spike/transaction_failure_artifact.py" \
  "$spike/transaction_graph.py" "$spike/transaction_binding.py" "$spike/ref_binding.py" \
  "$work/gen/generated_transactions.py" "$work/offline/"
python_bin=$(command -v python)
(cd "$work/offline" && env -i PATH="$PWD/empty-bin" PYTHONPATH="$base/python" \
  "$python_bin" -B check_transaction_failure_artifact.py)
```

The harness removes its temporary evidence by default. Add `--out "$work/evidence"` to
retain the graph at a new path; the harness prints the root and the two-action recipe.

### Failure-artifact results

Two agents cross-reviewed the runner and harness and ran separate offline stages with fresh
native builds on Linux ARM64 (Python 3.12.15, Hypothesis 6.151.10, Quint 0.33.1 for generation).
The honest property executed 120 batches, witnessed all six rules, and never wrote evidence.
In the marker control, Hypothesis checked 22 live batches and found nine violating candidates.
It shrank `create(a) → create(a) → update(b)` to `create(a) → create(a)` with an initially
absent ref and a final commit attempt.

The harness observed a single graph write after Hypothesis reported the failure. It checked
object identity against the batch that caused the reported exception and rejected execution
outside the property. A fresh Python process reopened root `811236bf2d9d01eae623a4d61de82662`,
returned the exact batch and all six expected verdicts, and reproduced `commitPoisoned`. Its
guards prohibited live execution and native write transactions. It also rejected a wrong pin
and a mismatched recipe. Both processes ran without Quint, Node or npm on `PATH`; this was
not a filesystem sandbox.

Independent boundary checks preserved an existing destination, rejected a dangling output
symlink and refused to replay a passing graph as a failure. A simulated adapter error, missing
witnesses and a deliberately invalid baseline before control injection produced no artifact.
Three mutations in staged copies made the harness fail before graph creation: saving an equal
batch copy, re-executing after the property, and writing during shrinking. The existing offline
transaction-rules and graph round-trip harnesses also passed.

Logs, exits and source hashes are ignored local artifacts under
`build/quint-feasibility/failure-artifact/coordinator/` and
`build/quint-feasibility/transaction-failure-artifact/worker/`. No maintained code or gate
changed; the full maintained gate and CI were not rerun.

## Native fault control

The final experiment rebuilt two native extensions from copies of the same Git revision. In the
faulted copy only, `dml_txn_abort` commits the LMDB transaction if the writer is poisoned. The
unchanged Python binding still reports `invalid_state` when rejecting a failed commit. This is a
fault introduced in the test build, not a defect observed in pristine DML. An initial control
changed `dml_txn_commit` instead and produced no violation: Python aborts a failed write before
raising, so that case does not reach the native commit entry point.

After the shared setup above has populated `subprojects/packagecache/`, from the repository root
in the same Nix shell run:

```sh
bash "$spike/run_native_fault_control.sh" "$quint"
```

The [runner](run_native_fault_control.sh) archives native sources from `HEAD`, builds clean
and faulted copies without downloading wraps, and generates the checker once. Its
[offline harness](check_transaction_native_fault.py) uses the same generated checker and
unmodified observation adapter in both builds. Both properties allow all commit histories and
only empty explicit aborts: the fault can affect both endings, and this restriction gives the
single-failure artifact runner one rule to report while retaining all six clean witnesses. No
operations are filtered based on whether they are expected to fail. The runner removes the
copied sources, packages and builds on exit; it retains the patch, input hashes, build logs,
exit code, and any evidence graph in its printed `build/quint-feasibility/native-fault.*` directory.

Two agents cross-reviewed the runner and harness and independently ran the final sources on
Linux ARM64 (Python 3.12.15, Hypothesis 6.151.10, Quint 0.33.1 for generation). The clean property
checked 120 examples, matched all six rules, and wrote no graph. The faulted build checked 23
examples with 11 violations. Hypothesis shrank `create(a) → create(a) → update(b)` to
`create(a) → create(a)`, starting with no ref and finishing with a commit attempt. Both builds
reported `invalid_state`; only the faulted one published the staged ref and marker. The harness
saved the exact checked batch reported by Hypothesis at root `4e0b18e71b4e67b33a5b705634098dfd`.

A fresh pristine process recovered the exact failing batch from the supplied pin and recipe
and reported `commitPoisoned` as the only violation, without rerunning the recipe or opening a
writer during replay. Separately executing the shrunk recipe on pristine DML rolled back both
writes. Independent controls reopened the graph after removal of the disposable packages,
rejected a wrong pin and recipe, and showed that substituting a second copy of the pristine
package for the faulted one produced no saved failure. Offline stages had no Quint, Node or npm on `PATH`;
they were not filesystem sandboxes.

Final receipts are under `build/quint-feasibility/native-fault.RNubTK/` and
`build/quint-feasibility/native-fault.9nUXrq/`; the initial non-detecting run is retained at
`build/quint-feasibility/native-fault.7sssLj/`. A focused C Valgrind probe exercised poisoned abort,
publication, and handle cleanup in both builds with zero errors and no leaks. An attempted
full Python Valgrind run did not load Hypothesis through the interpreter wrapper. A narrower
instrumented Python probe reported 56 bytes definitely lost with the same CPython parser stack in
both builds. Neither Python memory check passed. Logs remain in
`build/quint-feasibility/native-fault-valgrind.LFy7Tq/` and
`build/quint-feasibility/native-fault-memory.HzMSLx/`, including the passing `native-c/` logs.
No maintained code changed; the full maintained gate and CI were not rerun.

## Read-context design to build

A read `commit()` on the [Python wrapper](../../../docs/spec-next/python-api.md#contexts-and-failure-handling)
must reject without ending the transaction. This is deliberately different from the
[native C entry point](../../../docs/spec-next/repository.md#transactions), which consumes it.
The design question was whether rejection, exit, and publication checks alone distinguish the
Python behavior from consuming the handle on rejection.

- **Design:** [`read_context_model.qnt`](read_context_model.qnt) enumerates all 78 histories of
  one to three attempts (`commit`, `create_ref` targeting an absent ref, or lookup of that absent
  ref), with normal or exceptional exit. It compares two transition models. The premature-end
  alternative still returns `invalid_state`, publishes nothing, and leaves an ended handle after
  exit. Of the 50 histories where an attempted commit prematurely ends the handle, 34 pass the
  weak rules; the refined `readStillUsable` rule detects all 50. One attempted commit suffices
  to distinguish them. In a separate model control, substituting the premature-end transition
  in the safety test made it fail. This is bounded exhaustive enumeration in Quint's TypeScript
  evaluator, not an unbounded proof or a model-checker run.
- **Build:** [`read_context_rules.qnt`](read_context_rules.qnt) defines the rules for both modes.
  The [generator](generate_read_contexts.py) lowers those predicates; the
  [adapter](read_context_binding.py) reads the seeded ref before the context and uses the **same
  handle** to read it after every attempt. The adapter also records what is observable after exit,
  before any fallback cleanup. It does not compute the expected target or outcome. The generator
  rejects disagreement between the declared rule IDs and verdict branches; the property rejects
  missing observations and requires concrete witnesses for all rules.

In the Nix shell from the repository root, set `spike` and install Quint as shown in
[Run locally](#run-locally). The runner builds its own native extension; skip the earlier
native build steps.

```sh
bash "$spike/run_read_context_control.sh" "$quint"
```

The two original Linux ARM64 runs independently built and tested the profile. All four model
checks passed. The generated source was byte-identical across hash seeds.
The pristine binding passed all 78 concrete histories and the 78 examples in the finite
Hypothesis run, witnessing all four rules. A disposable copy of the Python binding was changed to
abort the read handle before rejecting `commit()`. The native extension, adapter, generator,
and checker were unchanged. The fault still returned `invalid_state`; the subsequent read on
that handle returned `invalid_state` instead of the seeded target. The first failing example
was already one operation, and no other rule failed on it. The harness saved the observations
reported by the property in a JSON receipt without rerunning the case. A pristine process
replayed the receipt without DML operations; a separate execution of the same recipe on pristine
DML passed.
Offline stages had no Quint, Node or npm on `PATH` and were not filesystem sandboxes. The JSON
receipt is diagnostic evidence, not a pinned DML graph or a verdict cache.

Direct Quint evaluation and generated Python agreed on 344 verdicts across 78 pristine,
7 synthetic, and one faulted observation. The synthetic cases checked wrong target before a
later successful read, wrong rejection, swallowed exception, live handle after exit, both
publication observations, and classification of an empty body. An incomplete concrete record
was rejected before checking.

The runner does not perform the model substitution or the separate generation controls. In those
controls, removing `readStillUsable` from just the registry or just the verdict dispatch produced no
checker. Removing it from both compiled the weaker contract, which accepted the **same saved
observations** that the refined contract rejected, with no change to the adapter or implementation.
Unbound fields and an unsupported action also failed generation. The original logs for these
controls are in `read-context-model-control.P5786Z/` and `read-context-generation.IhhVN6/` under the
ignored `build/quint-feasibility/` directory.

The runner prints a `build/quint-feasibility/read-context.*` receipt directory and removes its
temporary builds and packages on exit. The original receipts are `read-context.eAdaUp` and
`read-context.QHx8CT`. The checkpoint run, `read-context.vGBSPV`, reproduced their clean, fault,
replay and differential JSON byte for byte. The maintained Python tests already check a rejected
read commit followed by a successful read; the new evidence is the design counterexample and its
transfer to concrete tests without a second handwritten property predicate. This was not a pristine
DML regression. No maintained code or gate changed, and the full maintained gate and CI were not
rerun.

## Limits

The first two profiles cover one ref, pre-existing valid commits, fresh write transactions per
action and published ref state after each transaction ends. They do not establish transaction
rollback; the transaction profile separately checks the observed ref and one new scalar datum
across multiple actions. The context profile additionally covers normal and exceptional write-context
completion; the explicit-ending context profile separately checks commit/abort inside write
contexts and subsequent supported ended-handle operations. The read-context follow-up covers
rejected operations on one read handle and both exit modes. None covers owner closure inside a
context, re-entry, finalizers, concurrent readers, injected native commit failures unrelated to
poisoning, invalid commit targets, arbitrary object graphs or unrelated keys.
Agreement is evidence for these observations, not proof of arbitrary Quint translation or
performance at larger scales. There is no verification cache or change to the older SQL/pooling
spike. The maintained gate, CI and other platforms were not rerun; this experiment retains the
existing isolated validation-scope boundary.
