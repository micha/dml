# DML

[![CI](https://github.com/micha/dml/actions/workflows/ci.yml/badge.svg)](https://github.com/micha/dml/actions/workflows/ci.yml)

Local-first development with lightweight workflow guidance.

## Workflow

The canonical workflow is documented here:

- `AGENTS.md` (Agent guide)

To enforce commit message body wrapping locally:

`cp scripts/commit-msg-hook.sh .git/hooks/commit-msg && chmod +x .git/hooks/commit-msg`

## Build and Test

Use `scripts/check.sh` as the standard validation entrypoint. The
[development validation policy](docs/validation-policy.md) owns proportionate check
selection, independent acceptance and CI failure/exception reporting.

- `scripts/check.sh` - build, run tests, and enforce 100% coverage
- `scripts/check.sh -v` - also run C tests, binding ownership and native CLI fault workloads under Valgrind
- `scripts/check.sh -f` - clean build artifacts before rebuilding
- `scripts/check.sh -m` - enable Mull mutation testing
- `scripts/check.sh -c` - build, run tests, and report coverage without percentage gates (used by CI)

The script enforces vendored dependency usage, runs coverage with gcov/lcov,
and writes HTML reports under:

- `build/coverage/html` (C coverage via gcov/lcov)
- `build/coverage/python-html` (Python coverage via coverage.py, when Python
  source files exist outside tests)

Python test dependencies are in `requirements-dev.txt` (pytest, pytest-xdist,
pytest-cov, psutil, Hypothesis, and coverage.py). The current parallel-coverage
profile uses pytest-cov 7 and requires a development Python of at least 3.9;
this does not change the installed library's Python requirement. Windows CI
installs the corresponding UCRT64 packages through
[MSYS2](https://www.msys2.org/docs/python/) so native extensions match its Python
build. Workflow provisioning is unchanged: the added support tests require the
new declared development dependencies, so existing MSYS2 package provisioning
needs an update before running this updated suite there. Hosted Windows/macOS
validation and non-GNU counter merging are not demonstrated.

### Optional resource-aware parallel coverage

```bash
DML_TEST_WORKERS=auto scripts/check.sh -v
```

The default remains serial (`DML_TEST_WORKERS=0`). `auto` chooses the minimum of
host physical cores (logical CPUs if physical topology is unknown), process CPU
eligibility/quota, and the memory capacity after reserving headroom. This avoids
counting SMT threads as extra full cores when physical topology is available.
It respects Linux cgroup v1/v2 CPU quotas and remaining memory at visible parent
limits, as well as host available memory and process affinity where supported.
Fractional CPU quotas below one core use one worker. Failed/unknown allocation
probes use one worker with an explicit diagnostic; known insufficient memory
fails before launching workers rather than pretending the allocation is safe.
Windows job-object/container quotas are not currently detected.

Initial conservative allowances are **1024 MiB per worker plus 1024 MiB reserve**.
Set `DML_TEST_WORKER_MB` and `DML_TEST_RESERVE_MB` to positive integer MiB values
when a measured workload needs a different profile. These are admission estimates,
not enforced OS memory limits or claims of measured maximum usage. Explicit
`DML_TEST_WORKERS=N` bypasses automatic sizing for diagnosis; it can oversubscribe
resources. Direct `python3 -m pytest -n auto --dist=loadgroup` uses the same policy;
`--maxprocesses=N` can cap automatic selection. No worker restart/retry is requested
by the check script; test/runtime deadlines and all tests remain unchanged.

pytest-cov combines worker Python coverage using the same source scope and omit
list as serial validation. Existing coverage.py report/XML/HTML stages still
apply the original threshold (100%, or informational with `-c`). No subprocess
coverage patch is enabled: this preserves the previous measurement scope rather
than silently extending coverage to application subprocesses. Shared history
fixtures are grouped by their consuming module, not only their defining file.
Worker JUnit suite properties are forwarded to the controller, preserving native
diagnostic properties that upstream xdist does not combine itself.

Parallel native counters are isolated per worker and merged with initial C-test
counters by **gcov-tool from the same GCC toolchain** before lcov reporting.
The optional profile requires this tool; missing tools and merge failures fail
the gate. Workers sample their own process-tree RSS once per second; shared pages
can be counted more than once and transient peaks can be missed. Resource choices,
sampled peaks/errors, exit status and suite properties are written under
`build/test-results/parallel` (override with `DML_TEST_REPORT_DIR`). These metrics
are tuning evidence, not an OOM guarantee. The LMDB entity diagram is unchanged:
this adds test tooling, not stored entities or execution semantics.

CI uses `scripts/check.sh -c`: coverage reports are informational, while build,
test, and report-generation failures still fail the job.

The explicit [installed local SSH/container gate](tests/ssh/README.md) is separately mandatory
for SSH acceptance; default checks/imports never start Docker or an SSH service. Its approved
host-network fixture is loopback-only and has no shared project/exchange mounts.
The explicit [installed local Floci/Batch gate](tests/floci/README.md) separately runs
current installed DML inside actual jobs through a private internal bridge/no-host-ports
fixture. Default checks never start it; host mocks/prior packet replay/CI do not replace it.

Mutation testing uses `.mull.yml`; when `-m` is passed, `scripts/check.sh`
targets `build/check/test_version` by default when present.

## C Editor Setup

Run `scripts/setup-lsp.sh` in your build environment (Meson, Ninja, a C compiler,
Python, and Python development headers are required). It configures a separate
editor build for the shared core and Python extension, then writes an ignored
`compile_commands.json` at the repository root. No compilation is required.

The database includes compiler-discovered system-header paths for environments
such as Nix, where an unwrapped clangd cannot infer them. It does not change
Neovim's global configuration or the coverage/mutation builds.

Rerun the script after changing build definitions, compilers, or Python
installations. Restart the clangd client in Neovim after the initial setup.
See [clangd project setup](https://clangd.llvm.org/installation.html#project-setup)
and [system-header discovery](https://clangd.llvm.org/guides/system-headers).

## CLI Help

- `dml --help` documents the inspection-only native CLI's global grammar.
- [CLI contract](docs/spec-next/cli.md) owns selectors, previews, JSON and errors.
- [Python API](docs/spec-next/python-api.md) constructs existing repository state.
- [Packaging](docs/packaging-and-distribution.md) explains root builds and console forwarding.

## Docs

Start with the [as-built specification](docs/spec-next/README.md) for implemented
DML behavior: datums, snapshot/history objects, transactional repository refs,
the low-level Python API, inspection CLI and explicit
[local recorded Python execution](docs/spec-next/local-execution.md) layer.
The [runnable local story](examples/local_execution.py) executes a trusted child,
records distinct attempts and durable result DAGs; capture and interruption limits
are explicit in that layer's contract.
The [pinned transfer layer](docs/spec-next/transfer.md) and
[runnable transfer story](examples/pinned_transfer.py) copy full recorded parent
history between local repositories without executing imported source or copying refs.
The [repository execution layer](docs/spec-next/repository-execution.md) and
[A → B → A story](examples/repository_execution.py) connect pinned transfer and the
unchanged local runner, validating returned selected history before atomic import
under a caller-chosen ref while leaving A's existing heads alone.
The additive [asynchronous contract](docs/spec-next/asynchronous-execution.md) and
[finite application story](examples/asynchronous_execution.py) separate a saved handle
from its live process owner and retrieve immutable initial/publication/completion packets.
The additive [caller-request contract](docs/spec-next/caller-requests.md) and
[caller-Q story](examples/caller_requests.py) explicitly record Q before launch,
then create only T in fresh B while preserving exact Q and caller submission refs.
The separate [SSH contract](docs/spec-next/ssh-execution.md) and
[endpoint-driven story](examples/ssh_execution.py) add synchronous caller-Q stage/execute/fetch
through a fixed installed helper, keeping strict host-key checks, unknown outcomes and
unchanged exact-Q explicit-ref reception. [Foreground progress modes](examples/ssh_progress.py)
separate saved SSH identity/live owner and retrieve validated immutable P/U/F through one fixed
nonexecuting observe action. Remote gates in this demonstration are controlled externally.
Docker is local acceptance support only.
The explicit [local Floci contract](docs/spec-next/floci-execution.md) and
[finite modes](examples/floci_execution.py) add caller-Q stage/one-shot Batch submit,
saved external identity and bounded fresh immutable S3 observations without a live
submitting owner. Service status never supplies DML done; existing exact-Q/offline
explicit-ref return remains authoritative. The [trusted child](examples/floci_add.py)
uses declared finite S3 gates controlled out of band, not a runtime command hook.
The [composed recorded-steps example](docs/composed-recorded-steps.md) supplies an actual
result sub-DAG plus exact selected producer witness to a second separately recorded step,
then publishes an ordinary success-only summary. Python sequences finite public-API modes;
there is no native evaluator/scheduler or new LMDB entity.
The [explicit attempt-reuse example](docs/explicit-attempt-reuse.md) records a new request
satisfied with an explicitly selected old successful attempt/result, without new T/job.
It matches exact intent/binding/full inputs including producer witness; fresh execution
remains a separate explicit action, not automatic cache discovery or fallback.
The [versioned selection/adoption example](docs/versioned-reuse-selection.md) records an ordinary
S/V choice, revalidates it from pinned repository state, delegates explicit reuse to existing Q/W,
and adopts a fresh matching attempt only when requested. Sibling branches retain different choices;
no public cache framework/native entity or automatic fresh-to-selection update is introduced.
Its [intent-defaults example](docs/intent-reuse-defaults.md) records ordinary versioned Idef/D,
resolves reuse/execute defaults with explicit request overrides, and retains why the operation's
own Q used a selected old attempt or remained pending fresh work. It never dispatches; selection/
adoption and existing execution remain separate, with branch-local defaults and no public policy
framework or new LMDB entity.
The [versioned implementation-selection example](docs/versioned-implementation-selection.md)
records two captured bindings and a branch-local default/explicit label before independently
resolving reuse/fresh policy. Each binding has its own known selection slot; equal results
never authorize cross-binding reuse, and fresh success does not adopt itself.
The [advisory supersession example](docs/implementation-supersession.md) records an ordinary
fixed-menu A→B declaration with structured reason/evidence, separate explicit default promotion,
and actual request-basis versus separately selected knowledge views. It preserves predecessor
reuse/history; no automatic invalidation, new native entity or lifecycle framework is added.
The [multi-input reuse example](docs/multi-input-reuse.md) composes a bounded explicitly named
ordinary table of exact intent/full-binding/full-input selections and a new pinned decision
reader. Several input keys coexist; explicit adoption changes only one row using a NEW immutable
selection slot, while other rows/old branches remain. Reuse creates own Q/W, not another T/job.
The [intent-scoped reuse example](docs/intent-scoped-reuse.md) separately permits same-intent/
exact-full-input reuse across requested/producing bindings, preserving own Q versus historical
producer S/Q/T/R authority. NEW ordinary table/decision roles and explicit one-key removal retain
other entries/history/branches; default miss is fresh without automatic adoption or rediscovery.
Old exact-binding APIs remain unchanged; no native entity, result ban or cache framework is added.
The [recorded argument-map prototype](docs/recorded-argument-maps.md) separately supplies logical
callables with typed MAP datums and bound datum-only getters while preserving construction/source
relationships in ordinary DAGs. Its NEW datum-keyed table/decision and own-Q/old-T satisfaction
separate requested from historical executed provenance; no general evaluator, automatic cache or
security sandbox is introduced. [Explicit installed acceptance](tests/argument_maps/README.md)
uses synchronous local attempts and SAME-history blocked nonexecuting readers.
The additive installed [internal builtin surface](docs/internal-builtins.md) supplies fixed
URI/versioned NULL bindings and argument-map NODE -> NODE calls, with nested map/list getters,
copied-value callable access and separately retained actual sources. Ordinary semantic profiles
use existing native storage; no general evaluator/native opcode is added. Its bounded one-S
example preserves own Q versus historical T/result and exact retained v1/v2 implementations.
[Installed acceptance](tests/builtins/README.md) uses two synchronous local attempts and SAME-history
blocker-FIRST readers; development GHA remains intentionally disabled.
The [composed ordinary-node-call example](docs/composed-node-calls.md) connects successful add/double
steps through existing normal-return nodes, matches downstream reuse by full argument MAP value,
and separately captures requested producer S/T/R versus OLD double's original executed chain.
[Explicit installed acceptance](tests/composed_nodes/README.md) has eight Q/six synchronous LOCAL
attempts/ten child getters and SAME-history nonexecuting readers; no generic evaluator is added.
The [closure-bound-dependency example](docs/closure-bound-dependencies.md) captures fixed internal
getter bindings and an I64 scale source at closure creation, separately from invocation arguments.
Its new capture-aware key preserves requested versus OLD executed capture; default changes never
retarget immutable closures. [Explicit installed acceptance](tests/closures/README.md) has six Q/
four synchronous LOCAL attempts/eight child getters, not nested ordinary calls or a general evaluator.
The [captured ordinary-call draft](docs/captured-ordinary-calls.md) supplies a fixed double_sum with
actual captured add/double calls through a NEW example-local in-process adapter and unchanged LOCAL
leaves. Short recording scopes/direct result nodes preserve own requests versus OLD selected chains;
convenience defaults do not retarget captures. [Gated installed acceptance](tests/captured_calls/README.md)
is opt-in and currently pending; no native entity, general evaluator or runtime dispatcher is added.
The additive [implementation-bound invocation surface](docs/implementation-bound-invocation.md)
provides explicitly imported `daggerml.calls` structural captures and a common owned node-call
facade. NEW example integration routes outer/leaf/getter calls through that facade and matches
reuse by intent plus full argument-MAP value while retaining exact requested/OLD producer authority.
Old helper keys/APIs stay unchanged. One current installed local story (13Q/10T, six direct LOCAL
children,17 getters) and blocked SAME caller/replica reader pass; final full validation, independent
acceptance and publication remain pending. This is not hosted-platform assurance; development GHA
remains disabled.
Its [glossary](docs/spec-next/glossary.md) owns the shared vocabulary. The old draft
specification below remains design context, not an implementation claim.

- `docs/documentation-guidelines.md` (How to write and maintain docs)
- `docs/packaging-and-distribution.md` (Python package layout and release plan)
- `docs/architecture.md` (Architecture overview)
- [LMDB entity map](docs/lmdb-entity-diagram.html) (Offline interactive diagram of implemented storage; open in a browser)
- `docs/core-storage.md` (Native datum codec and local repository API)
- [docs/spec-next/README.md](docs/spec-next/README.md) (As-built specification)
- [tests/coverage-exclusions.md](tests/coverage-exclusions.md) (Coverage scope and rationale)
- `docs/spec/overview.md` (Old draft specification)
- `docs/spec/object-model.md` (Packed records, hashing, keyspace)
- `docs/spec/execution.md` (Execution lifecycle, caching, adapters)
- `docs/spec/remotes.md` (Remote snapshot flow and transfer)
- `docs/spec/cli.md` (CLI contract and error codes)
- `docs/spec/python-bindings.md` (Python API proposal)
- `docs/spec/maintainability.md` (Maintainability assessment rubric)
