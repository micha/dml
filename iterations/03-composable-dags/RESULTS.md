# Iteration 3 implementation results

Status: implementation accepted, published as **`9b8fb71`**, and final exact-SHA
CI independently verified successful. Work is stopped. No tag, release or package
publication occurred; no later feature turn was started.

## Baseline and scope

Implementation checkout initially clean at
`e253249eca70ad588d918d321a54a1413447b8a0`. `/work` is mounted. Machine,
both repository guides and every handoff prerequisite were read completely.
Coordinator-owned design notes are preserved. Worker has exclusive `../dml/build/check`
until an explicitly agreed review pause. No additional agents or system changes.

Baseline command (from `../dml`):

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Exit 0, 255 Python tests, 7 C test executables; retained C 1555/1555 lines,
125/125 functions, 1409/1409 outcomes. Binding memory workload and 60 native CLI
Valgrind processes pass. Diagnostic: `/tmp/dml-iteration3-baseline.log`.
These are baseline checks, not evidence for the new implementation.

## Selected bounded engineering choices

Follow the approved design: root-plus-bindings reachability; literal kind 1 and
non-executing sub-DAG-reference kind 2; 40-byte base DAG record followed by canonical
ASCII name/node pairs; reject old 36-byte DAG shape without migration. Keep typed
DAG bindings distinct from tree entries. C input uses `value.dag` (root/items/count),
node uses kind/target; decoded views expose node kind plus kind-dependent reference
and DAG binding count. Add `dml_object_view_binding` and `dml_txn_lookup_node`.

Python follows `SubDAGNode(dag)`, `DAG(root, bindings)`, `put_subdag`, optional
bindings on `put_dag`, and exact-scope `lookup_node`. Descriptions copy caller
containers; insertion pair sequences preserve duplicates for C rejection.

CLI follows the approved lookup/walk grammar and fields, snapshot `root_node`,
iterative typed active/visited preorder, and distinct-record limit semantics.
No computation, causality claim, global namespace or later feature is introduced.

## Implementation checkpoints

The C codec/reference/lookup, owned Python API, native lookup/walk/snapshot,
comparison example and tests are implemented; validation/review remain in progress.
Shared named-object diagnostics now identify DAG versus tree, including encoding
name/count/allocation failures. Existing shared size/exhaustive/decode exclusions
were reassessed and cataloged; no new exclusions or weakened thresholds.

- Compile checkpoint exits 0.
- First informational `check.sh -c` exits 1: 37 legacy history-fixture failures
  exposed uninitialized union-tail fields after extending DAG input. Fixture now
  initializes the complete DAG member rather than reusing a node member's tail.
- Second informational check exits 1: one remaining legacy root-only bridge input;
  updated to explicit zero bindings. New public composition tests pass.
- Third informational check exits 1: four new corruption tests incorrectly expected
  `invalid_bounds` for a too-short envelope; corrected to actual `invalid_header`.
- First default `check.sh -v` exits 1 **only at retained branch gate**: 315 Python
  tests, Python 469/469 statements, 7 C executables and expanded memory checks pass.
  C 1680/1680 lines, 132/132 functions, 1558/1560 outcomes. Two missing native lookup
  conversion/ended-handle branches prompted real boundary tests, not exclusions.
  Binding memory: zero unsuppressed errors; 500,617 bytes/8,713 blocks at exit
  include suppressed/reachable CPython runtime populations. **141 native CLI
  Valgrind processes** pass, including new walk/lookup/sub-DAG display/snapshot
  allocation cleanup. Logs are `/tmp/dml-iteration3-{compile,checkpoint1,
  checkpoint2,checkpoint3,default1}.log`.

Coordinator read-only review identified property-strategy collisions with `root`
and `absent`; added an explicit example and a guaranteed-missing name/conditioned
root assertion. This was a potential test flake, not a runtime defect.

## Final worker validation and pause

Fresh default command is the baseline command above. Final worker run exits **0**:
**316 Python tests**, Python **469/469 statements**, **7 C executables** under
Valgrind; retained C **1681/1681 lines**, **132/132 functions**, **1562/1562 branch
outcomes**. Actual lookup argument/ended-handle tests cover the two earlier missing
branches. The private node-kind converter also rejects unsigned values above u32
rather than truncating them to an accepted kind; its boundary is tested.
Log: `/tmp/dml-iteration3-default2.log`.

Expanded binding workload exercises binding-array construction, owned copied DAG/
sub-DAG descriptions, lookup, mutation conversion/native allocation errors, and
legal owner-thread cleanup. Zero unsuppressed errors/leaks; exit heap **500,617
bytes/8,713 blocks**, of which **476,181 bytes/8,653 blocks** are narrowly suppressed
CPython runtime allocations and **24,436 bytes/60 blocks** reachable. **623 runtime
contexts suppressed**. No new suppression. This turn has no runtime-only/full
comparison pair; do not infer equal baseline heaps or allocation-free Python.
Unsupported foreign-last-owner abandonment remains outside supported leak-free
workloads, with existing disposable-process regressions and documented limits.

The native workload passes **141 Valgrind processes** (zero errors/bytes at exit),
covering old inspection plus walk/lookup, DAG bindings, sub-DAG-node display and
nonliteral snapshot roots, all allocation-failure boundaries for those commands,
and large complete datum JSON growth. C tests separately cover binding accessors,
size/name limits and both DAG encoder allocations. Fault fixtures are private;
no installed/public corruption/fault control was added.

Fresh producer/reader acceptance records both comparison commits, independently
checks returned bytes/IDs with the native bridge, descends explicitly to trial
results 5/6/7, preserves shared A and saved C1 records, and exercises a nonliteral
root. Deterministic root-first/canonical DFS suppresses repeated objects while
retaining edges; every prefix including exact exhaustion has assertions. A 1,100-
level iterative chain emits 2,202 records without C recursion. Simulated constant-
hash DAG and commit cycles are test-only fixtures, **not real XXH3 collisions**.
Late corrupted visited content fails with empty stdout; a short prefix is explicitly
not a proof for unseen structure. Read failure does not poison writes; mutation
failures/abort roll back earlier puts and ref changes under existing/new workloads.

### Coverage accounting

Marker-free diagnostic from the same completed default build:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c lcov --capture --no-markers --ignore-errors unused --directory build/check \
  --exclude '/usr/*' --exclude '*/subprojects/*' --exclude '*/tests/*' \
  --exclude '*/build/check/*' \
  --output-file build/coverage/lcov.iteration3-unexcluded.info --rc branch_coverage=1
```

Exit 0; the existing LMDB dependency consistency warning and two unused exclusion
pattern warnings remain visible (`/tmp/dml-iteration3-markerfree.log`). No DML
consistency error was ignored. No threshold/exclusion/suppression was weakened.

| Population | Lines | Functions | Outcomes |
| --- | --- | --- | --- |
| Marker-free, retaining GCC/CPython headers | 1710/1718 | 136/136 | 1636/1680 |
| Default retained gate | 1681/1681 | 132/132 | 1562/1562 |

Existing exclusions remove **37 lines** (29 hit), **118 outcomes** (74 hit), and
**4 dependency functions** (all hit). No DML function is excluded. The shared named
codec/typed traversal changes affect original line-wide branch populations; the
catalog reassesses both DAG/tree size invariants and typed traversal growth, plus
the allocation-free direct-reference decoder. Removed code is not claimed tested.

### Bounded mutation diagnostics

Mull 0.34.2/LLVM 21, independent ignored `build/iteration3-mutation/native`;
serial `--workers 1` is tool scheduling, **not an additional agent**. The exported
compile/runner configuration explicitly includes `object.c`, `repo.c`, `cli.c`
and `_core_module.c`, excludes test/dependency sources, and has **two operators**:
`cxx_eq_to_ne`, `cxx_lt_to_le`. This is deliberately bounded, not the repository's
full twelve-operator gate. Both old and new lines in those files are selected.

Build command:

```sh
nix develop ../dml-build-tools#mutation --quiet --log-format raw \
  --no-write-lock-file -c bash -c '
export MULL_CONFIG="$PWD/build/iteration3-mutation/mull.yml"
export LLVM_PROFILE_FILE="$PWD/build/iteration3-mutation/profiles/%p.profraw"
mkdir -p build/iteration3-mutation/profiles
meson setup build/iteration3-mutation/native --wrap-mode=forcefallback -Dbuildtype=debug
meson compile -C build/iteration3-mutation/native'
```

Build exits 0. Runner uses that same exported configuration, profiles and:
`mull-runner-21 --workers 1 --reporters IDE --report-dir build/iteration3-mutation
--report-name NAME INPUT`. Python-driven cases add `--test-program` pointing to
`/nix/store/a1nqcxh6a6976bf6ivjz8x83wvgjjanp-python3-3.13.15-env/bin/python3`
and `DML_BIN` selecting the mutation build.

| Input/report | Test population | Killed/selected | Survivors | Score/exit |
| --- | --- | --- | --- | --- |
| `test_faults` / `native-fault.txt` | C native fault tests | 83/97 | 14 | 85% / 1 |
| `test_object` / `objects.txt` | C object tests | 32/37 | 5 | 86% / 1 |
| `dml` / `public-composition.txt` | pytest `test_composable_dags.py -k 'comparison_example_fresh_processes or walk_late_corruption'` | 75/92 | 17 | 81% / 1 |
| `_core_fault.abi3.so` / `binding-fault.txt` | pytest `test_binding_failures.py` | 111/130 | 19 | 85% / 1 |

All runner exits are **1 on survivors**, not passing mutation gates. Logs:
`/tmp/dml-iteration3-mull-{native,objects,composition,binding}.log`; build log is
`/tmp/dml-iteration3-mutation-build.log`. Reports retain exact locations/operators.

Survivors and limits (not silently reclassified as killed):

- Minimum-name-length `<`/`<=` yields the same minimum at equality. Remaining-byte
  guards at exactly 4/16 still reject through subsequent bounds/name checks. These
  are bounded equivalent-path observations, not universal mutant equivalence claims.
- C-only object/fault diagnostic subsets do not assert all structured diagnostic
  fields; the `named_error` type selection survives there. Public malformed-DAG
  tests assert `record_type=dag`, but are not in those frozen mutation populations.
- Fault-only object decode/count/node-kind and many initialization/default-map/
  reference-validation variants reveal limited success/corruption oracles in those
  subsets; broader standard tests exist but no broad mutation rerun is claimed.
- Binding-fault lookup tests select a first matching name. The absent-name equality
  and loop-boundary mutants survive that subset; the public scope tests cover
  missing names separately. The lookup off-by-one survivor is **not equivalent**.
- The existing commit-parent validation loop off-by-one and binding `little64`
  `i<8` to `i<=8` survivors can read outside logical bounds; the latter also
  overshifts (undefined behavior), as already qualified in Iteration 2. These are
  **oracle limitations, not equivalent mutants**. No sanitizer/mutant-memory kill
  or logical-span safety guarantee is claimed. Production bounds remain strict.
- Public-composition mutation runs include core code reached by CLI/producer, not
  only CLI source; no survivor in its report is attributed to changed CLI code.
  This does not certify every CLI failure or new-code path against all operators.

### Local installed smoke

Reuse the previously authorized project-local packaging tools venv; **no package
bootstrap or global/system install** this turn. Build fresh core and console wheels,
create a new ignored `build/iteration3-packaging/installed` venv, install with no
index/dependencies, then execute from `/tmp` with fresh temporary repository scratch:

```sh
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration3-packaging/dist .
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration3-packaging/dist python/daggerml-cli
build/iteration2-packaging/bin/python -m venv --without-pip \
  build/iteration3-packaging/installed
build/iteration2-packaging/bin/python -m pip \
  --python build/iteration3-packaging/installed/bin/python install \
  --no-index --no-deps build/iteration3-packaging/dist/*.whl
cd /tmp
/work/repos/micha/dml/build/iteration3-packaging/installed/bin/python \
  /work/repos/micha/dml/build/iteration3-packaging/installed_smoke.py
```

All exit 0. A fresh installed producer and reader verify C1/C2 summaries, immutable
bytes, trial-result lookup, sub-DAG roots, exact/over-limit walk and caught-error
rollback. Console/native output agrees byte-for-byte. Module, extension and native
paths assert new venv `site-packages`, not source/build modules or PATH's binary.
Logs: `/tmp/dml-iteration3-installed-{build,smoke}.log`. Wheels are local
`cp313-abi3-linux_x86_64` and `py3-none-any`; **not** earlier-runtime, Windows/macOS/
ARM, manylinux or release evidence. The established packaging seam is unchanged;
no new sdist/staged-source route, tag, release or publication was attempted.

### Changed files and review surface

Implementation paths relative to `../dml`:

- Core/API: `include/dml/{object,repo}.h`, `src/{object,repo,cli}.c`;
  `python/daggerml/src/_core_module.c`, `python/daggerml/daggerml/{__init__.py,_core.pyi}`.
- Native fixtures: `tests/c/{core_driver,history_driver,test_object,test_repo,test_faults}.c`.
- Python tests: new `tests/python/test_composable_dags.py`;
  `tests/python/{test_objects_hypothesis,test_history,test_binding_failures,test_cli_failures}.py`.
- Memory/catalog: `tests/python/{binding_memory,cli_memory}.py`, `tests/coverage-exclusions.md`.
- Example: new `examples/composable_dags.py`.
- As-built/navigation: `docs/spec-next/{README,objects,repository,python-api,cli}.md`,
  `docs/{architecture.md,dml.1,packaging-and-distribution.md}`, `python/daggerml/README.md`.

Only this RESULTS file is worker-owned in the design checkout. Coordinator owns
REVIEW/design README/discussion/AGENTS and their authorization reconciliation.
Build/install/mutation artifacts remain ignored or session-local; no credentials,
old `docs/spec/` changes, version bumps, execution, reuse, remotes, resources,
observers, CLI mutation or packaging redesign. Original datum/literal/tree/commit
encoding regressions remain unchanged except fixtures consuming the changed DAG.

Whitespace checks pass in both checkouts. Automated local Markdown target/anchor
validation passes for all 10 worker-owned changed Markdown documents, including
this report. Implementation index is empty and old `docs/spec/` has no diff.

Worker checks completed and runtime/test edits and `build/check` use were explicitly
paused/released for coordinator validation. At that pause implementation HEAD
remained baseline `e253249` with uncommitted turn changes and empty index. The
subsequent acceptance/publication authorization below supersedes the pause and
pending-review state, not the evidence qualifications.

## Independent coordinator acceptance

The coordinator accepted implementation review after reading the source/API/CLI/
as-built changes and independently exercising the real extension and native CLI.
[REVIEW.md](REVIEW.md) owns the independent evidence and assessment. This section
records coordinator-reported results, not additional worker reruns:

- **49 independent checks**, exit 0: `/tmp/dml-iteration3-coordinator-probe.py` and
  `/tmp/dml-iteration3-coordinator-probe.log`. Includes byte oracle/canonical order,
  copied immutable descriptions, scope/root aliases, nonliteral roots, shared/exact-
  limit walk, non-BMP/control previews, historical bytes and atomic object/ref
  rollback after native/conversion/duplicate mutation failure.
- Fresh default `scripts/check.sh -v`, exit **0**:
  **316 Python tests**, **7 C executables**, Python **469/469**, retained C
  **1681/1681 lines**, **132/132 functions**, **1562/1562 outcomes**. Binding has
  zero unsuppressed memory errors/leaks with the existing narrow runtime
  suppressions; **141 CLI Valgrind processes** pass.
  Log: `/tmp/dml-iteration3-coordinator-check.log`.
- Separate `/tmp/dml-iteration3-review-install.*` venv, offline installed current
  wheels, workflow/reader from `/tmp` with PYTHONPATH unset, exit 0. Verified
  site-packages artifact paths, scoped lookup, I64 maximum, saved bytes, nested
  snapshot root and exact four-record walk. Log:
  `/tmp/dml-iteration3-coordinator-install.log`. An initial wrong interpreter
  selection failed `No module named pip`; retry used the existing packaging-tools
  interpreter, without bootstrap/global installs. This was a tooling-selection
  failure, not a product defect.
- Independent Markdown/whitespace checks pass; no outstanding functional defect
  found within the bounded scope. No coordinator mutation/sanitizer rerun or
  earlier-runtime/other-platform/manylinux/release guarantee is inferred.

User/coordinator explicitly authorized focused implementation commit(s), normal
push to existing `master`/`origin`, and monitoring/fixing all automatic exact-SHA
CI. Review findings already resolved remain recorded above; thresholds,
exclusions, mutation survivors and lifetime/platform limitations remain qualified.

## Publication checkpoint

The reviewed **31-file** implementation slice (1,004 insertions/188 deletions) was
explicitly staged and inspected; staged whitespace checks pass, with no remaining
unstaged/untracked implementation files. Commit
[`9b8fb7176e31186621dd5a4c26adadec4d76bc1e`](https://github.com/micha/dml/commit/9b8fb7176e31186621dd5a4c26adadec4d76bc1e)
(`Add composable DAGs and scoped named-node lookup`) is normally pushed to existing
`origin/master`; commit/push both exit 0. `git ls-remote origin refs/heads/master`
verifies the exact SHA. Implementation worktree/index are clean. No tag, release,
force push, new remote, agent or package publication. Design notes remain local/
uncommitted, with coordinator-owned files preserved.

[CI run 40474598485](https://github.com/micha/dml/actions/runs/40474598485), head
`9b8fb7176e31186621dd5a4c26adadec4d76bc1e`, completed **success on its first run**.
All six jobs succeed; **no CI failed run, fix commit or rerun was necessary**.
The earlier failed local implementation diagnostics remain recorded above.

Monitoring command:

```sh
gh run watch 40474598485 -R micha/dml --compact --exit-status --interval 15
```

Exit 0. Final run JSON, exact head SHA, every job, completed logs and the complete
run list for that SHA were rechecked. The only automatically triggered workflow
is this CI run. Release Python triggers only on version tags/manual dispatch, not
this branch push, and was not triggered. A macOS runner-capacity annotation was
informational, not a failed job or reduced test population.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40474598485/job/122089598300) | Success | 7 | 316 passed |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40474598485/job/122089598283) | Success | 7 | 316 passed |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40474598485/job/122089598202) | Success | 7 | 312 passed, 4 skipped |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40474598485/job/122089598408) | Success | 7 | 312 passed, 4 skipped |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40474598485/job/122089598472) | Success | 7 | 311 passed, 5 skipped |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40474598485/job/122089598048) | Success | 7 | 316 passed |

The four macOS skips are the existing absent-`/dev/full` tests; Windows additionally
skips the Unix closed-pipe/SIGPIPE case. Portable private output-failure sweeps stay
enabled; no new skip, disabled test, threshold change or suppression was introduced.
Strict Linux runs **informational `scripts/check.sh -c`**, not the local default
percentage/memory gate. Its reported retained counts also reach 1681/1681 lines,
132/132 functions and 1562/1562 outcomes, but this does not replace worker and
coordinator fresh local `-v` evidence. The five-platform CI supplies functional
build/test evidence, not installed wheel, earliest-runtime, sanitizer or release
validation on those platforms.

The coordinator independently verified HEAD/remote master, clean checkout, only
this completed automatic exact-SHA run, all six jobs and their logs, with its own
`gh run watch` exit 0. This is coordinator-reported publication verification,
separate from the worker's repeated SHA/run/job/log checks. Review acceptance and
final independent reconciliation are owned by [REVIEW.md](REVIEW.md).

Session-local diagnostics: `/tmp/dml-iteration3-actions-{watch.log,final.json,
final.log}`. Raw environment-bearing logs are not copied into design notes.
Implementation worktree/index remain clean at the pushed SHA; design notes remain
local/uncommitted, preserving coordinator-owned edits. Publication and monitoring
are complete and all work is stopped. No further code, commits, pushes, workers,
release/package publication or later feature work.


### Publication hygiene

Before staging, all top-level `test-fault-data-*` directories were inspected.
Their PID names each match `build/iteration3-mutation/profiles/<pid>.profraw`,
creation times match the worker's native fault mutation run, contents consist only
of test `repo-N/{data.mdb,lock.mdb}` or empty test directories, and no matching
process remains. The generating fixture is `tests/c/test_faults.c`'s process-ID
root/path/cleanup code. Ownership is confirmed as worker test scratch.

Only these nine exact directories were removed:
`1780539`, `1780670`, `1780877`, `1781140`, `1781271`, `1781318`, `1781395`,
`1781538`, `1782821` (each prefixed `test-fault-data-`). No wildcard deletion,
unrelated data or ignore-rule change. Remaining untracked files are only the
reviewed example and composition test. Initial implementation index is empty;
remote `refs/heads/master` still matches baseline `e253249`. Complete tracked
publication diff was inspected (1,797 lines); new example/test are also reviewed.
No build/install/mutation artifact is to be staged.
