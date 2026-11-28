# DML design decisions

This document records agreed direction. It does not specify current behavior or
approve a future API or release. See the [as-built
specification](spec-next/README.md) for current contracts and the [design discussion
archive](https://github.com/micha/dml/blob/archive/dml-design/discussion.md) for
historical context.

## Python plumbing and porcelain

**Status:** Initial public plumbing implemented. See the
[Python core binding contract](spec-next/python.md). Broader plumbing and
porcelain remain open.

- **C core:** Owns repository semantics. A supported operation that creates a
  DML commit and moves a ref atomically belongs in the core, including its
  preconditions, stale-ref handling and rollback. Keep the individual primitives
  available too. This does not make every application workflow a core operation.
- **Python plumbing:** Keep the public binding thin and expose core operations
  directly. Private replay instrumentation does not define the public API.
- **Python porcelain:** Add Python idioms such as transaction context managers,
  not new repository workflows. A context manager can manage transaction lifetime
  and abort on exception. It does not choose a ref or implement commit-and-ref
  publication in Python.
- **Validation:** As the public binding grows, use it for Quint core replay.
  Use focused Python tests for Python-specific presentation and lifetime
  behavior. See the [validation policy](validation-policy.md) for current
  testing practice.

The atomic publication example illustrates where semantics belong; it is not
a promise of a new core function or signature.

## Remote push and fetch

**Status:** Epic started; design open. See the
[remote push and fetch epic](epics/remote-push-fetch.md) for the proposed scope
and first validation milestone.
