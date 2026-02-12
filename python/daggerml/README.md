# daggerml

`daggerml` provides the Python bindings and native extension for DaggerML.

## Local build

From this directory:

```bash
python3 -m build
```

This produces a platform wheel and an sdist in `dist/`.

The native module is a packaging scaffold and currently returns a placeholder
version string while the static core linkage is finalized.
