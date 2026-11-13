# Stopped Iteration25 — preservation snapshot

## Authority boundary

This branch preserves unfinished local work before the original instance is decommissioned.
It is **WIP, unaccepted and unmerged**, not a validated release or an approved final implementation.
The user reports the worker was stopped because it was spinning its wheels. This snapshot does
not restart that worker or its tests/builds/fixtures/readers.

- Branch: `wip/iteration25-stopped` in `micha/dml`.
- Original base: `15555c01e4db19a20b4de7049f776c4d995bd5e0`.
- Captured37 actual changed/new source and documentation files (35 porcelain status entries,
  one directory entry expands to multiple files), preserved byte-for-byte plus this notice.
- No new validation performed for this preservation commit. Earlier partial/failing evidence,
  review gates and unresolved issues are not converted into acceptance.
- Main/master is not moved; no merge, force push, tag, workflow enablement or package release.
- Design history is separately preserved at
  [archive/dml-design](https://github.com/micha/dml/tree/archive/dml-design), particularly
  `iterations/25-implementation-bound-invocation/COORDINATION.md`, `REVIEW.md` and `RESULTS.md`.
- The accepted isolated relational prototype is on
  [spike/per-exercise-reuse](https://github.com/micha/dml/tree/spike/per-exercise-reuse).

Ignored builds, native stores, logs, test output, installed prefixes and other instance-local
artifacts are **not in this Git snapshot**. Their durable backup must be handled separately before
decommissioning if they are to be retained. Native19 remains paused; VP001 remains OPEN/UNKNOWN.

Any engineering continuation requires source/evidence/ownership review and a fresh bounded scope.
Do not treat the presence of implementation docs/tests in this WIP branch as proof they passed.
