# DML design decisions

This document records agreed direction that is not yet implemented. It does not
specify current behavior or approve an API or release. See the [as-built
specification](spec-next/README.md) for current contracts and the [design discussion
archive](https://github.com/micha/dml/blob/archive/dml-design/discussion.md) for
historical context.

## Python plumbing and porcelain

**Status: Agreed direction; not implemented.**

- **C core:** Owns repository semantics. A supported operation that creates a
  DML commit and moves a ref atomically belongs in the core, including its
  preconditions, stale-ref handling and rollback. Keep the individual primitives
  available too. This does not make every application workflow a core operation.
- **Python plumbing:** Provide a public, thin binding that exposes core operations
  directly. The current `_dml_core` is a private test bridge, not a public contract.
- **Python porcelain:** Add Python idioms such as transaction context managers,
  not new repository workflows. A context manager can manage transaction lifetime
  and abort on exception. It does not choose a ref or implement commit-and-ref
  publication in Python.
- **Validation:** Once the public plumbing ships, use the installed binding for
  Quint core replay. Use focused Python tests for Python-specific presentation and
  lifetime behavior. See the [validation policy](validation-policy.md) for current
  testing practice.

The public API, handle and buffer ownership, error mapping, compatibility,
and packaging remain open. The atomic publication example illustrates where
semantics belong; it is not a promise of a new core function or signature.
