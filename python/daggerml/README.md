# daggerml

A low-level Python API backed by DML's native C codecs and local LMDB repository.
It supplies explicit values/IDs, immutable snapshot/history descriptions, refs and
atomic storage transaction contexts. Typed values retain their datum kind and
collection references; `get_datum(id).value` accesses the immediate value.

See the owning [Python API contract](../../docs/spec-next/python-api.md),
[build/package instructions](../../docs/packaging-and-distribution.md) and
[runnable history example](../../examples/repository_history.py).

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
