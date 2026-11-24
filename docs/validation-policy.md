# Development validation policy

## Authority boundary

This document owns validation selection and reporting for the C consolidation
branch. [Build and validation](../README.md#build-and-validation) owns commands;
[the as-built specification](spec-next/README.md) owns technical contracts.

## Current gate

Run `scripts/check.sh --quint` on the final relevant sources. CI runs this gate
on Linux, macOS, and Windows and retains Meson logs. It covers ref creation,
atomic snapshot publication and rollback, caller-side conditional publication,
binary commit transfer and the staged result round trip, read-only integrity and
reachability checks, and explicit transactional garbage collection. It also runs
focused interpreter and Python binding tests, native integrity and collection
fault checks, native transfer boundary and fault tests, and Quint's separate
provenance handoff workflow checks against the C example.

Without `--quint`, the command only compiles the C core; that does not validate
runtime behavior. See [Quint behavior checks](../README.md#quint-behavior-checks)
for tooling. The CI gate does not measure coverage or build the Python wheel.

The suites and coverage reports described at
[`feasibility-complete`](https://github.com/micha/dml/tree/feasibility-complete)
are historical evidence, not a passing gate for current code.

## Choose evidence before running

- Map behavior changes or fixes to focused positive and negative checks against
  the current core. Cover relevant failure paths. Mocks do not substitute for real
  runtime checks of a changed mechanism.
- Use an installed consumer or equivalent boundary check when changing native
  build or installation behavior. For handoff changes, also run the
  [process integration against the installed C library](../tests/README.md#process-integration).
  For Python binding or packaging changes, run the focused binding tests and
  [ref replay against the installed wheel](../tests/README.md#replay-refs-against-the-installed-wheel).
  Use Valgrind when touching memory-critical paths.
- Prefer Quint for behavior that can be checked against live observations. Keep
  core API replay separate from application-level workflow suites. Keep model
  rules independent of observed implementation outcomes, and check that
  important success and rejection scenarios are exercised. Use focused native
  tests for fault injection and other low-level behavior better checked directly.
- Coverage is optional diagnostic evidence, not a percentage target or gate.
  Use it to investigate specific testing gaps rather than to drive test selection.
- Review the changed surface independently according to risk. Freeze the source
  identity and avoid concurrent changes to shared build directories during review.

## Report actual results

State what ran, what passed or failed, and what remains untested. Never count an
empty suite, skip, archived result, or unavailable platform as passing. Report CI
against its actual commit and job outcomes; missing jobs or logs are not evidence of
success. Investigate attributable or unknown failures. An inherited failure needs
evidence and an explicit, scoped acceptance exception with an owner and a follow-up;
do not relabel it as passing.
