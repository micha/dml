# daggerml-cli

Installs the `dml` console entry for the native
[inspection CLI](../../docs/spec-next/cli.md). The forwarding function locates
`daggerml/_bin/dml` (`dml.exe` on Windows), never PATH's `dml`, and forwards
arguments/streams/exit status. Install with the matching `daggerml` distribution.

## Local build

From this directory:

```sh
python -m build
```

This produces a pure-Python wheel and source distribution in `dist/`.
Build the native `daggerml` distribution from the repository root, as described in
[packaging instructions](../../docs/packaging-and-distribution.md). No CLI mutation
commands or Python record interpreter are supplied by this console package.
