# Packaging and distribution

Status: implemented native/Python build layout; remote release workflows are not
new validation evidence for uncommitted source.

## Authority boundary

This document owns build/package layout, native linking and distribution entry
paths. [Python API](spec-next/python-api.md) owns values and lifetime;
[inspection CLI](spec-next/cli.md) owns commands/output. Adapter packages remain
separate; their metadata lives under [python/adapters](../python/adapters/).

## One core, one CLI

The root [Meson build](../meson.build) maintains the C source/dependency list and
builds both the native CLI and CPython extension from it. Both link the same static
core and vendored xxHash, LMDB, utf8proc and uriparser dependencies. A native CLI
can run without importing Python; Python scripts call the extension, not a CLI or
test driver. Python/development headers are needed to build this root project.

The root [pyproject.toml](../pyproject.toml) owns the `daggerml` distribution.
The former independent `python/daggerml` build skeleton is removed; do not build
from that subdirectory. Maintained Python/native binding sources still live there.

The `python-runtime` Meson install tag selects only:

- `daggerml/__init__.py`, `local.py`, `transfer.py`, `exchange.py`, `exchange_worker.py`,
  `ssh.py`, `ssh_worker.py`, `floci.py`, `floci_http.py`, `floci_worker.py`,
  `_core.pyi`, `py.typed`;
- the linked `_core` extension;
- the native `daggerml/_bin/dml` (`dml.exe` on Windows).

Wheel installation excludes the static archive, C headers, test-only extensions,
fault controls and dependency installs. Native core/dependency code is statically
linked into the extension/executable, not copied into another maintained source
implementation. Root Meson installation also offers the C archive/headers; the
CLI executable's install location is the package directory stated above.

`daggerml-cli` remains a pure-Python distribution in
[python/daggerml-cli](../python/daggerml-cli/), with a dependency on `daggerml` and
console entry `dml`. Its one forwarding implementation locates the executable
relative to installed `daggerml.__file__`, passes arguments/streams through and
preserves status (signal termination maps to 128+signal). It **never** searches
PATH for `dml`. Missing/invalid bundled executables report a stderr error/status 1.
`python -m daggerml_cli.main` uses the same function.

## Local build/install

Informative commands, from the repository root, inside a project-local venv with
compiler, Meson/Ninja, build and backend dependencies:

```sh
python -m build --wheel .
python -m build --wheel python/daggerml-cli
python -m pip install dist/daggerml-*.whl python/daggerml-cli/dist/*.whl
cd /a/fresh/scratch/directory
python -c 'import daggerml; print(daggerml.version())'
dml --help
```

[The runnable example](../examples/repository_history.py) creates repository state
using the public API. Run it against a new path whose parent already exists, then
inspect `main` with `dml --json --repo PATH snapshot --ref main`.
Use the [composable DAG example](../examples/composable_dags.py) to produce named,
nested snapshots and inspect them with `lookup`/`walk`; it uses the same packaged
API/executable seam, without DML execution.
The [local execution example](../examples/local_execution.py) and its
[trusted child](../examples/local_add.py) require current installed parent and
child runtimes. The packaged [local layer](spec-next/local-execution.md) uses the
public API and does not install dependencies or bootstrap child imports.
The [pinned transfer example](../examples/pinned_transfer.py) uses the installed
[transfer layer](spec-next/transfer.md) to carry recorded history to a second
repository with fresh-process import/inspection, without executing copied source.
The [repository execution story](../examples/repository_execution.py) connects
those layers through explicit prepare/execute/receive stages, using fresh installed
worker/receiver processes and the same unchanged local child contract. Its
[exchange contract](spec-next/repository-execution.md) owns retained files, pinned
selection and validated explicit-ref return without adoption.
The [asynchronous story](../examples/asynchronous_execution.py) retains/reaps the fixed
installed worker while short-lived clients observe immutable P/U/F packets. The
[asynchronous contract](spec-next/asynchronous-execution.md) owns its process/packet
boundary; the example child is captured source, not an installed runtime/fault hook. The [caller-Q story](../examples/caller_requests.py) uses the
same installed modules/worker with explicit prelaunch request recording and exact-Q
first attempt; its [owning contract](spec-next/caller-requests.md) defines that delta.
The [SSH story](../examples/ssh_execution.py) uses installed explicit endpoint-driven
stage/execute/fetch and unchanged exact-Q receive; its [SSH contract](spec-next/ssh-execution.md)
owns transport/client ownership. The [SSH progress modes](../examples/ssh_progress.py) use
separate saved identity/foreground owner and bounded immutable observation/offline receive.
Docker/Nix/key/image/private-loss fixture support under
[tests/ssh](../tests/ssh/README.md) is never packaged or imported by normal runtime/default tests.
The [Floci modes](../examples/floci_execution.py) use the installed explicitly imported
[local Floci layer](spec-next/floci-execution.md) for prepare/one-shot submit/fresh bounded
observe/offline receive. Its [trusted captured source](../examples/floci_add.py) consumes
explicit local endpoint/bucket/key inputs and finite S3 gates; gate release/provisioning
remain external application policy. `tests/floci/` fixture/controllers/private ENTRYPOINT/
response-loss support are never packaged or default-started, and do not add a Docker/SDK
runtime dependency. Normal installed execution is separate from private fixture evidence.
Use [scripts/check.sh](../scripts/check.sh) for integration tests against the fresh
root extension, not a stale installed package. `-v` adds binding and CLI memory
workloads to the C tests; [coverage/memory accounting](../tests/coverage-exclusions.md)
identifies exclusions/suppressions.

## Source distributions

`python -m build --sdist .` uses meson-python/Meson VCS distribution. It includes
configured dependency subprojects (`--include-subprojects`) so a source archive
contains the maintained native sources and resolved vendored build definitions.
It does not rely on a sibling implementation checkout for native code.

Meson archives the committed VCS content: uncommitted modifications and new
untracked sources are **not** automatically included. For a no-commit development
turn, an explicit current-source staging archive can validate the source-to-wheel
route; it is not evidence that a normal dirty-tree `build --sdist` captured edits.
The exact staged archive contents and checks for this turn belong in
[Iteration 2 results](../../dml-design/iterations/02-repository-usability/RESULTS.md).
Do not publish a dirty-tree archive as a reviewed release.

## Runtime declarations and wheel tags

`daggerml` declares Python >=3.8 and compiles for limited API 3.8; `daggerml-cli`
declares Python >=3.9. meson-python marks a limited-API wheel `abi3`, but its Python
tag is the **build interpreter's** version, not the `limited_api` minimum. A local
Python 3.13 build therefore produces `cp313-abi3`, not install evidence for 3.8–3.12.
See [meson-python limited API guidance](https://mesonbuild.com/meson-python/how-to-guides/limited-api.html).
No tag is manually rewritten to imply untested compatibility.

The existing release workflow still selects CPython 3.12 (`cp312-*`) across its
Linux x86_64/aarch64, macOS x86_64/arm64 and Windows AMD64 runners. Only its core
package build directory/sdist output location is adjusted to the root build.
That matrix does not itself provide wheels for every earlier declared runtime.
Oldest-interpreter wheel coverage and macOS arm64 viability remain release-review
questions, not silently changed selectors or local cross-platform claims.

## Release controls

[release-python.yml](../.github/workflows/release-python.yml) retains tag/manual
build, smoke-install and existing publication controls. Tags `v*` can publish;
manual publication requires the existing `publish` input. Nothing here authorizes
running it, publishing packages, creating tags or changing account/system state.
Adapter implementations and publication mechanisms are unchanged by this turn.
Actual commands/platforms tested are in the iteration results, not inferred from
a declared matrix or an unexecuted workflow.
