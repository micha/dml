# daggerml

A low-level Python API backed by DML's native C codecs and local LMDB repository.
It supplies explicit values/IDs, immutable snapshot/history descriptions, refs and
atomic storage transaction contexts. Typed values retain their datum kind and
collection references; `get_datum(id).value` accesses the immediate value.

See the owning [Python API contract](../../docs/spec-next/python-api.md),
[build/package instructions](../../docs/packaging-and-distribution.md) and
[runnable history example](../../examples/repository_history.py) and
[composable DAG example](../../examples/composable_dags.py). Named bindings and
non-executing sub-DAG nodes record structure; Python computes any example values.
The separately imported [local layer](../../docs/spec-next/local-execution.md)
executes explicitly bound trusted Python entry bytes with pinned named inputs and
records ordinary request/attempt/result history. See the
[local driver](../../examples/local_execution.py) and
[cooperative child](../../examples/local_add.py); this is not a sandbox or complete
environment capture.
The separately imported [transfer layer](../../docs/spec-next/transfer.md) carries
one pinned commit's complete all-parent typed object closure through bounded bundles,
using the low-level public packed insertion seam. The
[transfer story](../../examples/pinned_transfer.py) preserves recorded attempts and
bytes/IDs without running copied source or installing source refs.
The separately imported [exchange layer](../../docs/spec-next/repository-execution.md)
connects pinned transfer and the unchanged local runner for one fresh step in local B,
then validates/returns its exact history under an explicit A ref without adoption.
See the [repository execution story](../../examples/repository_execution.py).
The additive [asynchronous contract](../../docs/spec-next/asynchronous-execution.md)
and [finite application story](../../examples/asynchronous_execution.py) retain explicit
live worker ownership while saved handles support fresh-client progress observation
and independently validated immutable P/U/F reception.
The additive [caller-request contract](../../docs/spec-next/caller-requests.md) and
[finite caller-Q story](../../examples/caller_requests.py) record Q before launch under
atomic explicit refs, then register the imported exact Q and create only T in fresh B.

The separately imported [SSH layer](../../docs/spec-next/ssh-execution.md) and
[endpoint-driven story](../../examples/ssh_execution.py) synchronously stage/invoke/fetch
caller-Q jobs through a fixed installed helper, then use unchanged exact-Q receive.
[SSH progress modes](../../examples/ssh_progress.py) additionally retain a foreground live
owner while fresh saved-identity clients retrieve validated immutable P/U/F without execution.
Docker is separate local test support, never a package/runtime dependency.

## Local build

Build **from the repository root**, not this source directory:

```sh
python -m build --wheel .
python -m build --sdist .
```

The root Meson build shares the maintained C core/dependencies between the linked
extension and bundled inspection executable. Wheels install `daggerml/_bin/dml`
(`dml.exe` on Windows); the separate `daggerml-cli` package forwards its console
entry to that executable. Fault fixtures and C test programs are not installed.

Source distributions use committed VCS content; current uncommitted development
needs explicit source staging as documented in the packaging instructions.
Declared Python >=3.8 / limited API 3.8 is not evidence of tests on every runtime.
meson-python's wheel Python tag follows the build interpreter; local Python 3.13
wheels are `cp313-abi3`, not install evidence for earlier runtimes.
