# Iteration 2 delivery notes

Status: implemented, independently reviewed and published through `e253249`.
Its exact-SHA Actions run passes all six jobs. The final local default check also
passes (255 Python tests), with memory/exclusion qualifications preserved below.
See [REVIEW.md](REVIEW.md) and the [publication checkpoint](#publication-checkpoint)
for independent and platform evidence. No tags, releases or package publication.

## Source state and authority

This section records implementation/review before publication. The final committed,
pushed state and newer validation are in the [publication checkpoint](#publication-checkpoint).

The user authorized this fresh window-2 session, bounded local implementation and
coordinator review/fixes. `/work` is mounted. Implementation HEAD remains
`06bf66e0352eebc47fe6093fb278f6b8c07120f7`, initially clean. All delivered changes are
uncommitted. Existing ignored build outputs were preserved. Design checkout had
pre-existing AGENTS/README/discussion edits and iteration notes; those were not
reset or committed. The old implementation `docs/spec/` is untouched. No versions,
record encodings, schema numbers or C repository primitives changed.

The coordinator reserved `build/check` for the worker, then requested/released an
explicit pause for independent probes. After the final check below the worker
confirmed a second shared-build/runtime pause: no further `build/check` commands
or runtime edits while the coordinator reruns validation. Only delivery/docs and
package accounting continue.

## Documentation consultation

Context7 resolutions for CPython and meson-python were attempted but quota-blocked.
Current official [capsule](https://docs.python.org/3/c-api/capsule.html),
[stable ABI](https://docs.python.org/3/c-api/stable.html),
[Meson Python module](https://mesonbuild.com/Python-module.html),
[meson-python source distribution](https://mesonbuild.com/meson-python/how-to-guides/sdist.html)
and [limited-API](https://mesonbuild.com/meson-python/how-to-guides/limited-api.html)
documentation were retrieved directly and consulted instead. Local installed
backend source and live Mull help supplied version-specific behavior checks.

## Selected engineering choices

These are assistant-selected bounded choices, not additional user design agreements.
Owning as-built contracts are [Python API](../../../dml/docs/spec-next/python-api.md),
[CLI](../../../dml/docs/spec-next/cli.md) and
[packaging](../../../dml/docs/packaging-and-distribution.md).

- Frozen, hashable 16-byte `ObjectId`; lowercase string datum kinds; owned frozen
  `Datum`, `LiteralNode`, `DAG`, `Tree` Mapping and `Commit` descriptions. Explicit
  ID collections, no recursive auto-insertion/dereferencing. Exact scalar types;
  bool before int; signed bounds. C remains the codec/identity/storage authority.
- Native capsules, not integer pointers. Transactions retain native owners; Python
  owners retain weak transaction references. Factories reject overlapping active
  transactions, and direct public `Transaction(...)` construction is rejected.
- Creating-thread operations, GIL held, one active transaction per wrapper; no
  global path/handle registry. Failed mutations poison the Python context even
  before native put; caught failures abort and raise on normal exit/commit.
- Finalizers never commit. Foreign-thread transaction destruction queues native
  cleanup for the next creating-thread repository operation/finalizer. Unsupported
  last-owner destruction on a foreign thread with pending transactions emits
  ResourceWarning and safely abandons native resources until process exit. It is
  explicitly **not leak-free supported finalization**.
- Candidate typed CLI grammar/explicit ref or commit selectors, one read transaction,
  deterministic all-parent DFS with active/visited IDs, bounded snapshots/previews
  and fixed JSON fields. Human output is a title plus indented structured fields,
  rather than compact JSON. C0/DEL and C1 controls are escaped. Results are buffered
  before printing; write failures report failure (partial writes are possible).
- Root Meson shares the maintained core/dependencies between extension and native
  CLI. Root `pyproject.toml` replaces the independent package scaffold; runtime
  install tags package only Python sources/stub/marker, extension and `_bin/dml`.
  The console forwards to that package-relative binary, never PATH's `dml`.
- Release changes only relocate core wheel/sdist build entry paths. The attempted
  oldest-interpreter selector change was reverted at coordinator request; existing
  `cp312-*` selection/platform matrix/publication controls remain unchanged.

## Exact changed files

Paths relative to `../dml`:

- Build: `meson.build`, new `pyproject.toml`; removed
  `python/daggerml/{meson.build,pyproject.toml}`;
  `.github/workflows/release-python.yml` (only package/source build locations).
- API/binding: `python/daggerml/daggerml/{__init__.py,_core.pyi}`,
  `python/daggerml/src/_core_module.c`, `python/daggerml/README.md`.
- CLI/console: `src/cli.c`, `python/daggerml-cli/daggerml_cli/main.py`,
  `python/daggerml-cli/README.md`.
- Validation/editor integration: `scripts/{check.sh,setup-lsp.sh}`,
  `tests/python/test_setup_lsp.py`. The existing editor setup now configures the
  shared root project; this preserves its feature, not a new editor scope.
- Test fixtures: new `tests/conftest.py`, `tests/c/{cli_fault_driver.c,python_faults.h}`;
  `tests/c/{fault_injection.c,fault_injection.h}` add private realloc substitution;
  `tests/coverage-exclusions.md`, new `tests/valgrind-cpython.supp`.
- Python tests/workloads: new `tests/python/{test_python_api.py,test_binding_failures.py,
  test_lifetime_edges.py,test_inspection_cli.py,test_cli_failures.py,
  test_forwarding_native.py,test_public_acceptance.py,binding_memory.py,cli_memory.py}`;
  updated `tests/python/test_python_scaffolds.py` replaces mocked scaffold claims.
- Example: new `examples/repository_history.py`.
- Docs: `README.md`, `docs/{architecture.md,dml.1,packaging-and-distribution.md}`,
  `docs/spec-next/README.md`, new `docs/spec-next/{python-api.md,cli.md}`.

Design changes: this report and delivery/resume updates to README/discussion.
Existing design AGENTS, DESIGN and HANDOFF edits remain preserved. Generated
venvs, archives, wheels, builds, counters and logs remain ignored or session-local.
Raw environment-bearing Meson JSON logs were not copied into design notes.

## Baseline and final standard validation

Commands from `../dml`, using the existing project-local tools shell:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

| Run | Exit | Outcome |
| --- | --- | --- |
| Baseline | 0 | 7 C executables under Valgrind; 86 Python tests; C retained 990/990 lines, 78/78 functions, 835/835 outcomes |
| Informational implementation checkpoints (`-c`) | 0 where suite passed | Initially 222 tests; measured new native/Python populations, not substituted for the default gate |
| First default checkpoint | 1 | One added test mistakenly required C1 escapes for a non-C1 U+00A0 string; corrected the assertion, not runtime behavior |
| Next default checkpoint | 1 | Functional/memory tests pass; two invariant/CPython inline branch attributions remain; precisely cataloged markers added |
| Passing default checkpoint | 0 | 7 C tests; 236 Python tests; Python 399/399 statements; C retained 1555/1555 lines, 125/125 functions, 1409/1409 outcomes |
| Final `-v`, after coordinator boundary refinements | **0** | **7 C tests; 249 Python tests; Python 399/399 statements; C retained 1555/1555 lines, 125/125 functions, 1409/1409 outcomes** |

Final default also executes the real binding Valgrind workload and **60 native CLI
Valgrind processes**: allocation-cleanup sweeps plus two real large full-JSON outputs.
All 60 native CLI processes assert zero memory errors and zero allocated bytes at
exit. Seven registered C test logs also report no memory errors/leaks. Binding
runtime allocations are separately accounted for below.

Diagnostic logs: `/tmp/dml-iteration2-baseline.log`,
`/tmp/dml-iteration2-informational{,3}.log`,
`/tmp/dml-iteration2-default{1,2,3}.log`,
`/tmp/dml-iteration2-final-check{,2}.log`. These are session-local diagnostics,
not durable evidence dependencies; checked-in tests reproduce the workflows.

Meaningful additional evidence:

- Public API creates 42/C1/main, 43/C2/ref movement and 44/C3/fork. A producer process
  exits; fresh native CLI calls inspect both snapshots/history; a fresh Python
  process checks every saved first record byte. Existing C driver independently
  hashes Python-returned bytes. Earlier immutable records remain unchanged.
- Exceptional abort and caught native, conversion, codec and duplicate mutation
  failures roll back prior objects/ref movement. Read failures do not poison writes.
- All ten kinds, canonical bytes/IDs, scalar bounds, NaN/zero, explicit collection
  refs, ordered parents/names, missing/wrong types, map-full complete retry,
  contexts/factories/explicit endings and copied-description lifetimes are tested.
- Normal and faults-disabled fixture APIs explicitly verify False, empty LIST/SET/MAP
  and empty tree/commit, signed min/negative/max values and actual float values.
  Fault scalar decoding now asserts values/types, not merely datum kind.
- Native/CPython binding allocation sweeps, reference-stealing cleanup, native begin,
  get and consuming-commit failures use a private extension from the same source.
  Production extension/core have no installed fault controls.
- CLI JSON kinds/nonfinite floats/huge I64, strict grammar, explicit selectors,
  previews/non-ASCII controls, exact-limit/shared-ancestor traversal, late corruption,
  output errors/closed pipe, >4 KiB full JSON text/bytes and bounded human views pass.
  A private simulated constant hash exercises cycle rejection; it is not a real
  XXH3 collision. Core schema/fault tests remain in the standard validation.

## Review corrections

The coordinator caught direct Transaction construction bypassing the wrapper
policy, cleanup after explicit owner close, compact JSON disguised as human output,
foreign-finalizer safety, C1 escaping, stale stub/tag accounting and memory boundaries.
These were addressed with regressions and documented restrictions.

An adversarial warnings-as-errors test exposed a real destructor crash: passing
its dying capsule to `PyErr_WriteUnraisable` could re-enter destruction. The fix
uses None as the unraisable context. Disposable-process tests verify warning,
ignored warning, promoted warning, unraisable hook and no spurious normal stderr.
The failing regression and passing recheck remain in
`/tmp/dml-iteration2-lifetime-regression.log` and earlier checkpoint logs.

The coordinator reports 30 independent real-extension API/CLI probe checks passed,
including fresh processes, hex-shaped ref disambiguation, exact-limit shared
ancestors, 112-entry truncation, non-BMP preview boundaries, scalar typing, immutable
bytes, rollback and lifecycle/thread policy. The coordinator also reports public
history + packaged snapshot43 passed from an independent new `/tmp` venv. These
are coordinator-reported evidence, not worker reruns. The coordinator's fresh final
`scripts/check.sh -v` also exits **0**: 7 C executables, 249 Python tests, Python
399/399 statements, retained C 1555/1555 lines, 125/125 functions, 1409/1409 outcomes,
binding zero unsuppressed errors and 60 native CLI Valgrind processes. Log:
`/tmp/dml-iteration2-coordinator-final-check.log`. The coordinator reports both
whitespace checks pass and no outstanding functional blocker. Final documentation
reconciliation and independent evidence are recorded in [REVIEW.md](REVIEW.md).

## Coverage populations and exclusions

Final marker-free diagnostic, from the same build (after the runtime comparison):

```sh
lcov --capture --no-markers --ignore-errors unused --directory build/check \
  --exclude '/usr/*' --exclude '*/subprojects/*' --exclude '*/tests/*' \
  --exclude '*/build/check/*' \
  --output-file build/coverage/lcov.iteration2-unexcluded.info --rc branch_coverage=1
```

Exit 0. It retains GCC/CPython headers and ignores source markers. It emits one
LMDB dependency gcov consistency warning and two absent-filter warnings; no DML
consistency check is disabled. `/tmp/dml-iteration2-unexcluded-final.log` records it.

| Population | Lines | Functions | Outcomes |
| --- | --- | --- | --- |
| Final marker-free | 1584/1592 | 129/129 | 1483/1524 |
| Final default gate | 1555/1555 | 125/125 | 1409/1409 |

All exclusions remove **37 lines** (29 previously hit), **115 outcomes** (74 hit),
**4 dependency functions** (all hit). No DML function is excluded. Prior exclusions
remain 16 lines/67 outcomes. Iteration 2 additions:

| Source | Removed lines | Removed outcomes | Removed functions |
| --- | --- | --- | --- |
| CPython `object.h` dependency helpers | 20 (20 hit) | 32 (19 hit) | 4 (4 hit) |
| Binding precise invariant/refcount markers | 0 | 6 (3 hit) | 0 |
| CLI precise invariant markers | 1 (0 hit) | 10 (6 hit) | 0 |

[The owning catalog](../../../dml/tests/coverage-exclusions.md#iteration-2-binding-and-cli-exclusions)
identifies each statement and rationale. These denominator removals are not passing
tests. Datum decoding is **not** excluded as allocation-free: URI/text validation
can allocate again, and URI fault sweeps exercise failure after a successful read.
All thresholds remain unchanged.

## Binding memory accounting

`PYTHONMALLOC=malloc` and `--trace-children=yes` are essential here: without exec
tracing, Valgrind instrumented Nix's wrapper but not the CPython workload. That
initial wrapper-only exit 0 is **not** memory evidence. The traced unsuppressed run
exited 101 on CPython cached/interned Unicode reports (474,863 definite bytes,
135 possible bytes), with no DML allocation frames in those reports.

[Specific runtime call-chain suppressions](../../../dml/tests/valgrind-cpython.supp)
exclude neither DML buffers/handles nor direct binding Unicode-return chains, and
suppress no invalid access/uninitialized-value errors. The workload includes
multi-element ID/map arrays, empty collections, False, signed/floating values,
allocation failure, copied values and legal owner-thread deferred cleanup.

```sh
for mode in 1 0; do
  DML_MEMORY_BASELINE="$mode" PYTHONMALLOC=malloc valgrind \
    --trace-children=yes --error-exitcode=101 --leak-check=full \
    --show-leak-kinds=definite --errors-for-leak-kinds=definite --track-origins=yes \
    --suppressions=tests/valgrind-cpython.supp python3 tests/python/binding_memory.py
done
```

Final pair exits 0/0. Runtime-only import baseline and full workload both retain
**499,539 bytes in 8,695 blocks**: 475,103 bytes/8,635 blocks suppressed and
24,436 bytes/60 blocks reachable. Both report zero unsuppressed errors/leaks
(622 runtime contexts suppressed). Earlier pairs had different interned-string
counts as source changed; both members of each pair matched. Logs:
`/tmp/dml-iteration2-memory-final-{1,0}.log`.
Unsupported foreign-last-owner abandonment deliberately leaks native resources;
it is tested only in disposable subprocesses, **not** included in these leak-free
supported-lifetime claims.

## Bounded mutation diagnostics — not green gates

Existing LLVM 21/Mull 0.34.2 tooling was used in a separate ignored
`build/iteration2-mutation/native`, never shared `build/check`. Serial runner
(`--workers 1`), with real pytest as test program and `DML_BIN` selecting that build.
No agents/workers were delegated. The original build used repository `.mull.yml`
with its **full 12 operators**. Narrower runner files did not retroactively restrict
compiled mutation metadata; reports contain arithmetic/order/equality/logical
operators. Do not describe those first runs as two-operator tests.

For follow-up, explicitly exported compilation/runner configuration included the
same 12 operators and only CLI/binding source paths, then cleaned/recompiled the
separate build. The operator set is the repository `.mull.yml` list; output/fault
sources are test-only and excluded. Representative commands:

```sh
export MULL_CONFIG="$PWD/build/iteration2-mutation/mull-full.yml"
export LLVM_PROFILE_FILE="$PWD/build/iteration2-mutation/profiles/%p.profraw"
meson compile --clean -C build/iteration2-mutation/native
meson compile -C build/iteration2-mutation/native
export DML_BIN="$PWD/build/iteration2-mutation/native/dml"
mull-runner-21 --workers 1 --reporters IDE --report-dir build/iteration2-mutation \
  --report-name cli-final --test-program "$PY_TEST" "$DML_BIN" \
  -m pytest -q tests/python/test_inspection_cli.py tests/python/test_cli_failures.py
```

`PY_TEST` was `/nix/store/a1nqcxh6a6976bf6ivjz8x83wvgjjanp-python3-3.13.15-env/bin/python3`.
The other inputs/test populations were:

| Input / report | Tests | Killed / selected | Survivors | Reporter score / exit |
| --- | --- | --- | --- | --- |
| Native CLI, initial | inspection | 27/38 | 11 | 71% / 1 |
| Native CLI, follow-up `cli-final.txt` | inspection + CLI faults | 30/38 | 8 | 78% / 1 |
| CLI fault driver, initial | CLI faults | 14/26 | 12 | 53% / 1 |
| CLI fault driver, `cli-fault-final.txt` | CLI faults + buffer capacity/NUL arithmetic boundaries | 16/26 | 10 | 61% / 1 |
| Normal extension, initial/follow-up `binding-final.txt` | public API + lifetime | 12/13 | 1 | 92% / 1 |
| Fault extension, `binding-fault.txt` | binding faults | 46/54 | 8 | 85% / 1 |

These numbers are covered/selected mutants, not all code or allocation paths.
CLI output-detail and meaningful growth/overflow variants were killed after new
closed-pipe/buffer tests. Real >4 KiB JSON and large-output Valgrind now additionally
exercise growth without thousands of fault processes.

Survivors remain visible:

- Capacity `<`/`<=` at equality can add a redundant realloc; the 1024-minimum
  comparison returns the same capacity at equality. Escaping space as `\u0020`
  preserves JSON value semantics. Some parser-boundary variants remain equivalent
  through later null/argument checks, or are unexercised by the fault-only subset.
- The maximum-size guard edge requires an unrealizable allocation. Reversing the
  successful idle close-status check copies another success without changing output.
  These are not evidence of new functional defects or reasons to chase 100%.
- Warning `<0` to `<=0` survives even strengthened normal/unraisable assertions:
  calling the unraisable helper without a pending error adds no observed output on
  this CPython build. This is a bounded observation, not a portability guarantee.
- Fault-only URI/schema success, False/count-zero and calloc-size variants reveal
  limitations in that isolated population; not all are equivalent. Coordinator
  requested small success/value assertions for False, empty LIST/SET/MAP/tree and
  signed/floating decoding. Those now pass through both public and faults-disabled
  fixture APIs, plus memory workloads. No broad mutation rerun follows; frozen
  survivor counts above are **not** reclassified as killed.
- **`little64` `i<8` to `i<=8` is out-of-bounds/overshift UB, not equivalent.**
  Physical trailing NUL storage can make an over-read/shift escape the current
  value/addressability oracle. Valgrind does not prove logical-span or shift bounds;
  no UBSan/mutant-memory kill is claimed. Current production code retains `i<8`.

All mutation runs exit 1 on survivors; they are diagnostic evidence, **not passing
mutation gates**. No thresholds were lowered. Logs are
`/tmp/dml-iteration2-mull-{cli,cli-final,cli-fault,cli-fault-final,binding,binding-final,binding-fault}.log`;
ignored report files named above contain locations/operators. No broader mutation,
sanitizer or platform guarantee follows.

## Local packaging and installed evidence

Coordinator authorized bootstrap only in newly created ignored
`build/iteration2-packaging`, never system/global/shared tools. Using the existing
shell's Python 3.13.15:

```sh
python3 -m venv --without-pip --system-site-packages build/iteration2-packaging
# Download a PyPI pip wheel into that venv directory; run its module only there.
PYTHONPATH=build/iteration2-packaging/pip-26.2.2-py3-none-any.whl \
  build/iteration2-packaging/bin/python -m pip install pip meson-python hatchling build
build/iteration2-packaging/bin/python -m pip install ninja
```

Exact added versions: pip 26.2.2, build 1.6.1, meson-python 0.22.1, Meson 1.12.1,
Ninja 1.13.2, hatchling 1.32.4, pathspec 1.1.1, pyproject-metadata 0.12.1,
pyproject_hooks 1.3.3, tomlkit 0.15.2, trove-classifiers 2026.9.21.13. The venv
inherits existing project-shell test dependencies; no inherited package was changed.
Initial no-isolation build correctly failed on missing Ninja package metadata;
Ninja was then installed in this venv and builds passed.

```sh
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration2-packaging/dist .
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  --outdir build/iteration2-packaging/dist python/daggerml-cli
```

Both exit 0. Core wheel tag is `cp313-abi3-linux_x86_64`; console is `py3-none-any`.
Native/core/dependency code is linked into the extension and packaged executable;
installed native `ldd` shows libc/loader only, not a Python runtime/core/dependency
shared library. This local Nix-linked Linux wheel is not manylinux/other-host proof.

The regular VCS sdist command exits 0 but **does not contain current uncommitted
source**: its root pyproject/new API doc are absent. Meson explicitly warns of dirty
content omission. It does contain configured vendored subprojects. That archive
was rejected as current-source evidence, never installed/published.

For no-commit validation, an explicit staging archive copied current tracked/new
source files (excluding ignored artifacts) plus resolved xxHash 0.8.3, LMDB 0.9.35,
utf8proc 2.11.3 and uriparser 1.0.2 source/build definitions, and wheel PKG-INFO.
It introduces no second maintained native source copy. Extracted outside source
paths under ignored packaging scratch, then built with downloads disabled:

```sh
build/iteration2-packaging/bin/python build/iteration2-packaging/stage_source.py
build/iteration2-packaging/bin/python -m build --wheel --no-isolation \
  -Csetup-args=--wrap-mode=nodownload --outdir build/iteration2-packaging/source-wheel \
  build/iteration2-packaging/source/daggerml-0.1.0
```

Exit 0; self-contained staged source-to-wheel route works without fetching native
dependencies. The root and staged-source native wheels have identical SHA-256
`c831b9cb2b2645e5679da614ab7caabdc545221a34c90349d842fe52bfcc41b0`.
The console wheel is `f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983`.
Later changes are tests/delivery docs, not runtime package code. The staging
procedure/artifacts are local validation, not a dirty-tree release backend.

Installed with `--no-deps --force-reinstall` into that venv, then ran from `/tmp`
in fresh scratch with spaces, copying the example there. Separate producer process,
installed console/native version/ref/snapshot/history agreement, saved records,
43 result and caught-error rollback all pass. A fake PATH `dml` returning 99 did
not intercept forwarding. Import paths assert venv site-packages, not build/source.
Coordinator independently repeated public history/snapshot43 in another new venv.

Logs: `/tmp/dml-iteration2-{package-seam,package-seam2,installed-seam,source-wheel,
installed-final,vcs-sdist}.log`. No publication, repair/retag or remote workflow run.
Declared >=3.8/limited API 3.8 is preserved, but only CPython 3.13 Linux x86_64 is
locally demonstrated. Existing cp312 release selection does not provide wheel
coverage for every earlier declaration. Windows/macOS/ARM, earlier Python,
free-threaded Python and oldest-runtime wheel viability are **not tested here**.

## Limits, review stop and next turn

The delivered API remains low-level and the CLI inspection-only. C direct checks
are not transitive graph guarantees; multiple parents are not merge. Single-active,
thread/lifetime restrictions and safe-abandonment misuse are deliberate. Preview
limits do not bound underlying record reads/allocations; simple tree/visited scans
remain unbenchmarked. Coverage percentages and finite memory/mutation tests are
not scientific or general production-safety certification.

Worker and coordinator functional/default/memory and local package evidence is
complete for the bounded slice, with mutation/platform/source-VCS limitations
explicit. Agent implementation and final-document reconciliation are finished;
[REVIEW.md](REVIEW.md) records independent acceptance. All work is stopped for user
review; no further runtime/shared-build work is started by this completed turn.
Final whitespace, local-link and source-status checks pass: HEAD remains `06bf66e`,
both indexes are empty and old `docs/spec/` has no diff. Changes remain uncommitted.

Suggested next spiral turn, **not started or authorized here**: use the reviewed
low-level API in one small researcher-authored history/inspection workflow to learn
which separate higher-level helpers are actually useful. No execution, remote,
resource, observer or convenience framework was added in this turn.

## Publication checkpoint

The user subsequently authorized implementation commits, normal push and Actions
verification. The coordinator fetched/verified the existing remote and inspected
the complete 4,620-line staged diff. The reviewed slice is committed as
`ee0327f08f3aeb4a324c8f82958a166a85e9e323`
(`Add low-level Python repository API and inspection CLI`), 39 files. A trailing
blank line in a new test file was removed before committing; its 11 focused tests
pass. The existing local language-server commit `06bf66e` was also published by
that push. No force push, tag, release, remote creation or account change occurred.

### Actions failures and bounded fixes

- [Initial CI run 40466170875](https://github.com/micha/dml/actions/runs/40466170875)
  passes all five Unix jobs, but Windows fails during collection. A broad file
  glob picked `_core_fault.dll.a` (a linker import library), producing no Python
  import spec. Fix `d9a554c2a60c231d3a8f7c50eb2bd74cd5a09ea1` selects exact
  module names plus the interpreter's `EXTENSION_SUFFIXES`, shared by tests and
  the memory harness. Five new regressions cover Windows/Unix suffixes, decoy
  linker artifacts, preference order, absence and an actual native loader.
- [Second CI run 40466858460](https://github.com/micha/dml/actions/runs/40466858460)
  gets through Windows collection; five tests fail. Three CLI fixtures decoded
  UTF-8 output using the Windows default locale; two editor fixtures fell through
  to the real compiler because a POSIX shebang fake is not a native Windows
  executable. Fix `e253249eca70ad588d918d321a54a1413447b8a0` explicitly decodes
  native CLI text as UTF-8, adds a forced-ASCII-fallback regression, and uses an
  explicit CMD compiler fixture on Windows. No tests were disabled or thresholds
  changed; production API/core/CLI behavior is unchanged by these test-only fixes.

Both follow-up staged diffs were inspected and normal pushes returned 0. Failed
runs are retained as historical evidence, not relabeled as successful retries.

### Final local validation

After the second fix, fresh default validation:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Exit **0**: 7 C executables under Valgrind, **255 Python tests**, Python **399/399**
statements; retained C **1555/1555 lines**, **125/125 functions**, **1409/1409
outcomes**. Binding memory workload has zero unsuppressed errors; all **60 native
CLI Valgrind processes** pass. Existing exclusions and suppressions are unchanged.
Log: `/tmp/dml-iteration2-windows-fixtures-final-check.log`.

Intermediate selector implementation accounting: a first local `-v` run after
adding the helper exits 101 on a 94-byte CPython Unicode/path-stat leak report;
all 254 functional tests pass. Enumerating existing candidates before suffix
selection avoids that extra path-stat allocation, without adding a suppression.
A fresh check then passes with 254 tests. The final runtime-only/full binding
comparison both reports zero unsuppressed errors but no longer has identical
suppressed runtime populations: respectively 475,319 bytes/8,639 blocks and
475,414 bytes/8,640 blocks. The earlier identical-pair measurements above remain
historical, not silently applied to this helper. Logs:
`/tmp/dml-ci-selector-memory-{1,0}.log`,
`/tmp/dml-iteration2-ci-fix-{check,final-check}.log`.

### Exact-SHA final Actions verification

[CI run 40467554833](https://github.com/micha/dml/actions/runs/40467554833), head
`e253249eca70ad588d918d321a54a1413447b8a0`, completed **success**. Monitoring:

```sh
gh run watch 40467554833 -R micha/dml --compact --exit-status --interval 15
```

Exit 0. Final JSON status, exact head SHA, all six jobs, completed logs, the run
list for that SHA and remote `refs/heads/master` were checked again.

| Job | Result | C executables | Python results |
| --- | --- | --- | --- |
| [Linux x86_64](https://github.com/micha/dml/actions/runs/40467554833/job/122066533316) | Success | 7 | 255 passed |
| [Linux aarch64](https://github.com/micha/dml/actions/runs/40467554833/job/122066533579) | Success | 7 | 255 passed |
| [macOS x86_64](https://github.com/micha/dml/actions/runs/40467554833/job/122066533245) | Success | 7 | 251 passed, 4 skipped |
| [macOS arm64](https://github.com/micha/dml/actions/runs/40467554833/job/122066533466) | Success | 7 | 251 passed, 4 skipped |
| [Windows AMD64](https://github.com/micha/dml/actions/runs/40467554833/job/122066533458) | Success | 7 | 250 passed, 5 skipped |
| [Strict Linux check.sh](https://github.com/micha/dml/actions/runs/40467554833/job/122066533361) | Success | 7 | 255 passed |

Four skips are the existing Unix `/dev/full` device tests where that device is
absent; Windows additionally skips the Unix SIGPIPE/closed-pipe test. Portable
private output-failure sweeps remain enabled. No new fixture skip hides a failure.

The Linux validation job remains informational `scripts/check.sh -c`; its reported
retained counts are also 100%, but it does not enforce percentage thresholds or
run `-v` memory checks. The independent local default `-v` evidence remains distinct.
This CI supplies functional build/test evidence for the existing five-platform
matrix; it is not installed wheel/release validation on those platforms.

Only CI ran for the final SHA. Release Python was not triggered; no packages were
published. Implementation checkout and index are clean at the pushed SHA. Design
notes remain local/uncommitted in the separate no-remote checkout, preserving prior
notes. No more workers or subsequent feature iteration was started.
Session-local diagnostics: `/tmp/dml-iteration2-actions-{final.json,final.log,
portability-watch.log}` and the earlier failed-run logs. Raw CI/Meson environment
logs were not copied into this repository.
