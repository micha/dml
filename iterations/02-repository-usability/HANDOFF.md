# Iteration 2 handoff: repository usability

Status: the user reviewed the design and authorized implementation in the existing
agent's fresh Pi session in window 2, with coordinator monitoring, review and fixes.
Code changes in `/work/repos/micha/dml` for this bounded iteration are authorized.
No commit, push or package publication is authorized by this request.

**Delivery:** implementation and coordinator review are complete; see
[RESULTS.md](RESULTS.md) and [REVIEW.md](REVIEW.md). The handoff below preserves the
bounded implementation plan and authorization, not an instruction to restart work.

## 1. Authority and purpose

The [design](DESIGN.md) distinguishes user-agreed scope from proposed concrete
choices. It owns the candidate API/CLI/architecture details; this handoff owns the
work sequence, acceptance evidence, delivery requirements and stop line. Neither
is an implemented specification. The user has now authorized implementation and
coordinator-led review/fixes, within this handoff's scope.

Goal:

> Let agents construct existing local DML repository state through a supported
> low-level Python API, and let humans and agents inspect it through `dml`.

Higher-level experiment helpers can compose this API later. Do not fold a workflow
framework into the low-level binding. CLI inspection-only scope intentionally
qualifies capability parity without changing the shared repository semantics.

When the user authorizes implementation, work in the existing implementation
checkout, maintain delivery notes here, and stop after this turn for review. That
authorization does not automatically authorize commits, pushes, package publication,
new workers, environment changes or later feature work.

## 2. Required reading and preflight

Follow the machine-wide instruction index and confirm `/work` is mounted. Read:

1. [Design repository instructions](../../AGENTS.md),
   [README](../../README.md) and [resume point](../../discussion.md#resume-point).
2. [Iteration 2 design](DESIGN.md), completely.
3. [Implementation agent guide](../../../dml/AGENTS.md),
   [documentation guidelines](../../../dml/docs/documentation-guidelines.md),
   [as-built spec instructions](../../../dml/docs/spec-next/AGENTS.md),
   [orientation](../../../dml/docs/spec-next/README.md) and
   [glossary](../../../dml/docs/spec-next/glossary.md).
4. Implemented [record contracts](../../../dml/docs/spec-next/records.md),
   [object contracts](../../../dml/docs/spec-next/objects.md) and
   [repository contracts](../../../dml/docs/spec-next/repository.md).
5. [Iteration 1 delivery](../01-minimum-viable-repository/RESULTS.md), especially
   the follow-up/publication sections, and the
   [coverage catalog](../../../dml/tests/coverage-exclusions.md).
6. Source, packaging and validation files listed in Section 4.

Preparation inspected `dml` at clean `06bf66e`. The previous `6ee9329` publication
is the Iteration 1 follow-up; subsequent `06bf66e` commits the separate language-server
setup. Historical notes about unstaged LSP work are not a claim of current status.
Design checkout has existing uncommitted Iteration 1 notes plus this planning work.
Reinspect both checkouts rather than reset them or assume these observations persist.

No tests or builds were run during handoff preparation. Once authorized:

- Inspect tracked/untracked changes and relevant ignored build outputs.
- Identify the available project-local build environment and dependencies.
- Coordinate against concurrent use of `build/check`; standard validation wipes
  that build directory during Meson reconfiguration, even without `-f`.
- Run/record the relevant baseline, including the default gate when available.
- Use only fresh test-owned repositories and controlled local build/install scratch.
- Do not install globally, modify the OS or delete unrelated data to make tests pass.

Until `v1.0.0`, repositories/development state are ephemeral. No version bump,
repository migration or backwards-compatibility layer is required for this turn.
That does not relax immutable-history behavior or permit unrelated deletion.

## 3. Scope and acceptance boundary

### In scope

| Area | Capability |
| --- | --- |
| Python values | Immutable IDs, explicit datum kinds, owned object descriptions |
| Python repository | Open/create, schema, close; real C handles and ownership |
| Python transactions | Read/write contexts, explicit commit/abort, safe failure handling |
| Python objects | Construct/read existing datums, literal nodes, DAGs, trees, commits |
| Python refs | Explicit create/get/update with existing C validation |
| Exact bytes | Typed immutable-record read for independent inspection |
| Native CLI | Version/help, ref resolution, typed object display, snapshot and history inspection |
| Presentation | Deterministic human output, JSON and bounded previews/traversal |
| Distribution | Real extension/core linking, one native CLI, local installed smoke workflow |
| Delivery | Tests, standard validation integration, as-built docs and results |

### Out of scope

- CLI mutation, including initialization and ref create/update.
- Ref listing/deletion, checkout, merge/rebase, new ancestry/concurrency policies.
- New node kinds, named-node lookup/bindings, execution or sub-DAG evaluation.
- Intents, closures, occurrence records, reuse facets/masks or adoption.
- Remotes, cloud operations, resource managers, GC/excision and later observer work.
- Recursive Python-value auto-insertion, transparent dereferencing or a snapshot
  convenience framework.
- Production corruption/fault-injection APIs, a parallel Python storage backend,
  automatic map growth, persistent schema changes or a generic plugin framework.
- Package publication, release automation redesign and unrelated adapter changes.

Keep C behavior authoritative. Existing direct checks are not transitive validation;
parent lists do not implement merge; tree names do not implement DAG named bindings.

## 4. Implementation evidence to inspect

Paths below are relative to `/work/repos/micha/dml`:

| Area | Files |
| --- | --- |
| Public API | `include/dml/{dml,error,record,object,repo}.h` |
| Core | `src/{dml,error,record,object,object_id,repo,text,uri}.c` and encoding helpers |
| Native CLI | `src/cli.c` |
| Root build | `meson.build`, dependency subprojects |
| Binding scaffold | `python/daggerml/src/_core_module.c`, `daggerml/__init__.py`, `_core.pyi`, `py.typed` |
| Binding packaging | `python/daggerml/{meson.build,pyproject.toml,README.md}` |
| Console scaffold | `python/daggerml-cli/daggerml_cli/main.py`, its `pyproject.toml` and README |
| Test bridge | `tests/c/{core_driver,history_driver}.c` |
| Python tests | `tests/python/test_{records,objects,repository,cli}_hypothesis.py`, `test_history.py`, `test_python_scaffolds.py` |
| Failure assurance | `tests/c/test_faults.c`, private fault fixtures, `tests/coverage-exclusions.md` |
| Validation | `scripts/check.sh`, `requirements-dev.txt`, `.github/workflows/ci.yml`, existing Python release workflow |

Do not assume the current extension links C merely because it is native code: it
currently supplies only a hard-coded version function. Do not mistake tests that
monkeypatch `daggerml._core` for native binding integration tests.

During implementation, consult current CPython/Meson/meson-python documentation
for the chosen APIs and build integration. Preserve declared supported versions
and platforms unless the user accepts a bounded change; do not infer compatibility
from one successful local import.

## 5. Recommended implementation sequence

### A. Record the implementation sketch

Create `RESULTS.md` here when implementation begins. Before substantial code changes,
record source state, baseline outcomes and selected answers to the
[design checkpoints](DESIGN.md#9-design-checkpoints-and-stop-line):

- Public ID, Datum/kind and object-description types; scalar conversion rules.
- Transaction contexts, failed-mutation rollback, ownership and thread policy.
- Native inspection command grammar, limits and JSON field shapes.
- Shared native build, extension linking, bundled CLI and self-contained package route.

These are proposed bounded choices, not already approved exact APIs. If a replacement
is small and preserves agreed scope, explain it in the sketch and final report. Ask
before introducing a new core primitive or materially expanding the turn.

### B. Prove the native/distribution seam early

Before building a large Python surface:

1. Link the extension to the actual core and report its version from C.
2. Build/import it from the root validation build without a stale installed module.
3. Verify that an opaque repository handle can open/close test-owned state safely.
4. Resolve how wheel/sdist builds include the same maintained core and dependencies.
5. Establish the package-relative native executable location and forwarding path.

Keep one CLI implementation. The recommended console entry forwards to the bundled
native executable, never searches PATH for `dml`, and does not interpret repository
records independently. Root native CLI remains directly usable without Python.

If packaging requires a large restructuring, report the exact blocker early and
request a bounded decision. Do not spend the whole iteration building a release
system or quietly call a source-tree-only binding a usable installed API.

### C. Implement values and codecs

Build the explicit value/ID boundary and owned descriptions in
[design Section 3](DESIGN.md#3-python-values-and-object-identity).
Call C codecs for canonical encoding. Decode/copy while borrowed views are valid;
free C buffers on every conversion failure. Do not let returned descriptions retain
native pointers or mutable caller-owned containers.

Add real tests for all datum kinds, especially collection ID references, URI versus
STRING, bool before int, overflow, NaN/zero and duplicate inputs. Cross-check bytes
and IDs against existing C driver/oracles.

### D. Implement repository transactions

Add typed reads/writes and refs through actual C handles. Establish normal/exceptional
context exits before using automatic commit in acceptance scripts. Test native poison
and failures before native put (conversion/encoding); a caught failed mutation must
not permit earlier writes/ref movement to commit.

Document the proposed wrapper restrictions separately from C's capabilities. Do not
add a global handle registry or automatic concurrency protocol. Review finalizers,
owner retention and creating-thread checks as memory-critical code.

### E. Implement inspection presentation

Extend native `src/cli.c`, preserving version flags. Follow
[design Section 6](DESIGN.md#6-inspection-cli), or record a bounded replacement.
Use explicit expected types and ref/commit selectors. Resolve/traverse in one read
transaction. Keep deterministic parent/name order, shared-ancestor deduplication,
limits, escaped previews and structured errors.

The CLI should not initialize, repair or write repository objects/refs. Filesystem
lock activity from existing LMDB opening is not a research-state write; do not
promise physically read-only mounts work without implementing/testing that feature.

Use private presentation/traversal helpers as needed, not a new core query subsystem.
Test JSON through a parser and human output through stable semantic assertions plus
small golden examples. Avoid locale-dependent float formatting or raw terminal controls.

### F. Acceptance and local install

Use the public Python API, not a test driver, to construct the Section 6 fixtures.
Inspect through fresh native CLI processes and the installed Python console entry.
Run a local installed example outside the checkout to prove the extension/binary are
packaged rather than accidentally imported from build paths.

Update scaffold tests only for intentionally replaced behavior. Retain test drivers
for independent encoding and corruption tests. Neither a mocked `_core` nor CLI
stdout alone proves native API ownership and cleanup.

### G. Validation, as-built docs and review

Integrate new code into the standard check, run the required checks, document actual
contracts and report limitations. Finish with a current discussion resume point and
stop. Do not progress to execution to make the example more impressive.

## 6. Concrete acceptance workflow

In fresh test-owned scratch, using the supported Python API:

1. Create a repository. In one write transaction insert 42, its literal node, rooted
   DAG, tree entry `example`, C1 with no parents and `main -> C1`.
2. After successful context exit, save each ID and its exact record bytes.
3. In a second write transaction insert the analogous 43 snapshot, C2 with parent
   C1, and update `main -> C2` atomically.
4. Create C3 with parent C1 and another ref, demonstrating a fork without merge.
5. Close the repository and end the producing process.
6. Fresh native CLI calls resolve `main`, inspect C2's snapshot and root datum 43,
   inspect C1 by commit ID and root datum 42, and display C2/C3 histories.
7. Fresh Python reads verify saved records and IDs remain unchanged. No earlier
   record is rewritten by ref movement.
8. Repeat a snapshot/ref update but raise an exception before transaction exit:
   no new object or ref target becomes visible.
9. Repeat with a caught mutation error after prior puts/ref update: auto-exit fails
   and the entire batch remains rolled back. Exercise a native failure and a
   Python-side conversion/encoding failure separately.
10. Use a local installed `daggerml` and `daggerml-cli` outside the checkout to create
    and inspect another fresh repository through the same public interfaces.

Also construct a commit with multiple ordered parents for CLI log tests. All-parent
traversal/deduplication is an inspection operation, not a merge implementation.

## 7. Test and assurance checklist

[Design Section 8](DESIGN.md#8-validation-design) owns the detailed test matrix.
Acceptance requires evidence for each category, not merely a green count:

- [ ] Real linked extension import/version and installed import outside checkout.
- [ ] All supported value/object kinds, canonical bytes/IDs and explicit references.
- [ ] Scalar conversions, signed bounds, Unicode/URI, float and duplicate boundaries.
- [ ] Typed missing/wrong-type references and parent/name ordering.
- [ ] Object/ref atomicity, abort and caught-error rollback.
- [ ] Context exit, explicit endings, active-close, read-write rejection, owner lifetime,
      ended handles and cross-thread misuse.
- [ ] Copied descriptions and exact bytes remain usable after native cleanup.
- [ ] Map-full reports failure; reopening/larger-map full-batch retry works.
- [ ] CLI commands, JSON kinds/values, stdout/stderr/status and parser boundaries.
- [ ] Snapshot previews/escaping, deterministic log order, limits and shared ancestors.
- [ ] Corruption/missing/schema failures fail clearly without partial success output.
- [ ] Native and installed console behavior agree; forwarding has no PATH recursion.
- [ ] No CLI object/ref mutation or implicit initialization.
- [ ] Wheel build/install and source-distribution build route are accounted for.
- [ ] Native/binding and Python-source coverage populations are actually measured.
- [ ] Meaningful binding allocation/cleanup failures and memory checks are accounted for.

Use Hypothesis for public Python/CLI boundary and round-trip tests. Keep low-level
C/fault tests focused. Scratch corruption may use the existing test-only driver;
no public raw overwrite operation is needed.

### Standard checks

Use the current `scripts/check.sh` as required by the implementation guide. Adjust
its build/test integration narrowly so a normal run includes the real extension and
new CLI/binding code. Instrument native extension code and ensure its counters feed
the retained C report; subprocess/package boundaries need explicit coverage handling.
Keep default C/Python thresholds unchanged. `-c` remains informational, not a passing
default-gate substitute.

The previous environment used:

```sh
nix develop ../dml-build-tools --no-write-lock-file -c bash scripts/check.sh -v
```

Reinspect availability; this is a historical usable pattern, not a promise that the
new build needs no additional authorized tooling. Do not use `-f` casually or run
concurrent checks that wipe shared outputs. Report unavailable checks as blockers.

Apply the user's narrow no-value exclusion policy, with exact statements/regions,
rationales and tested-versus-excluded populations. Difficulty is not a rationale;
meaningful native allocation, rollback, parser and output failure paths need tests.
Reevaluate old invariants if the implementation changes them.

Use Valgrind for memory-critical binding paths as required by the implementation
guide. A Python process includes runtime/dependency allocations: distinguish them
from DML leaks and use narrowly justified suppressions if needed. Merely running
old registered C executables under Valgrind does not exercise extension ownership.
Use Mull as directed by that guide and report actual targets/results or tooling
blockers; do not claim mutation coverage from a default target unrelated to new code.

Cross-platform claims need actual builds/tests. Preserve existing CI matrix coverage
integration without publishing/running workflows unless authorized. Local Linux
results do not become Windows/macOS evidence. Check whitespace and local Markdown
links, including any new documentation-map anchors.

## 8. Documentation and delivery

Once implementation exists, add owning as-built documents for the Python API and
inspection CLI under `docs/spec-next/`. Proposed names are `python-api.md` and
`cli.md`; final names can follow actual content. Update README's document map,
Mermaid diagram and concept ownership table in the same scoped change.

- Existing records/objects/repository documents retain core semantics.
- Python documentation owns conversions, descriptions, exceptions, handle lifetime
  and contexts, including deliberate wrapper restrictions.
- CLI documentation owns grammar, selectors, limits, JSON and diagnostics.
- Packaging/build documentation owns how to build/install/run the real artifacts.
- The glossary changes only if meanings need clarification, not to host API details.
- Keep old `docs/spec/` unchanged. Do not add a missing-feature inventory or publish
  planned contracts as implemented.

Provide a small runnable acceptance example, not a framework. Clarify `.value` if
`get_datum()` returns typed descriptions rather than bare scalars.

The `RESULTS.md` report here should include:

1. Source revisions/status and exact files changed; unrelated changes preserved.
2. Selected API/binding/packaging choices and deviations from this candidate.
3. Reproducible commands, exit codes, counts and measured coverage populations.
4. Native versus packaged/fresh-process acceptance evidence.
5. Failure/cleanup/memory/mutation/platform checks actually run; blockers/skips.
6. Deliberate limits, unresolved defects and a review-oriented completion assessment.
7. One suggested next spiral turn, without starting it.

Update this design repository's README and discussion resume point to the delivered
state. Keep historical failures and prior claims visibly qualified, not rewritten.
No auto-commit/push. When requested, make focused commits and preserve unrelated work.

## 9. Stop line

End with a low-level usable Python repository API and an inspection-only CLI over
existing capabilities. Stop for user review. Do not add execution, remotes, resource
management, observer features or convenience frameworks.

The user authorized this implementation turn and use of the existing agent in a
fresh Pi session in window 2. Implement the bounded slice, respond to coordinator
review findings, and stop once reviewed. This does not authorize more workers,
commits, pushes, publication or another iteration.
