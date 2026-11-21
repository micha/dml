# Quint feasibility: DML refs and transactions

Status: direct Quint evaluation and deterministic Python generation passed for the
create-only, mixed create/update, transaction-batch, Python context-completion and explicit-ending
context profiles on Linux ARM64. No Quint adoption or general compiler.

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

## Limits

The first two profiles cover one ref, pre-existing valid commits, fresh write transactions per
action and published ref state after each transaction ends. They do not establish transaction
rollback; the transaction profile separately checks the observed ref and one new scalar datum
across multiple actions. The context profile additionally covers normal and exceptional write-context
completion; the explicit-ending context profile separately checks commit/abort inside write
contexts and subsequent supported ended-handle operations. These context profiles do not cover
read contexts, owner closure inside a context, re-entry or finalizers. None covers concurrent
readers, injected native commit failures unrelated to poisoning, invalid commit targets,
arbitrary object graphs or unrelated keys.
Agreement is evidence for these observations, not proof of arbitrary Quint translation or
performance at larger scales. There is no verification cache or change to the older SQL/pooling
spike. The maintained gate, CI and other platforms were not rerun; this experiment retains the
existing isolated validation-scope boundary.
