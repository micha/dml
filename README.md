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

Python test dependencies are in `requirements-dev.txt` (pytest, Hypothesis, and
coverage.py). Windows CI installs the corresponding UCRT64 packages through
[MSYS2](https://www.msys2.org/docs/python/) so native extensions match its Python
build.

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
