# Design-history archive before instance decommissioning

This branch preserves the complete `dml-design` Git history and its accumulated notes in the
existing **micha/dml** remote under **archive/dml-design**. It is the separate design repository's
tree/history, not a merge into DML source or a runtime release. Original local checkpoint:
`bb8bdcf093ed1bad79fa7c48eaea90d94ba169f3`.

The user authorized this preservation branch and a separate stopped implementation snapshot:

- [spike/per-exercise-reuse](https://github.com/micha/dml/tree/spike/per-exercise-reuse): accepted
  isolated relational prototype, checkpoint `62b4104dfade52fb574cdc80f933eb02a81994d5`.
- [wip/iteration25-stopped](https://github.com/micha/dml/tree/wip/iteration25-stopped): unfinished
  implementation, explicitly unaccepted/unmerged. Worker stopped by user; no restart or new tests.

Earlier instructions describe their historical gate/ownership state. The worker is now stopped;
archiving records does not complete its pending implementation or validation. Future-gate delegation
for the per-exercise prototype expired at its completion, not extended by this archive operation.

Native stores, build outputs, logs, prefixes and ignored raw evidence remain outside Git. In
particular approximately5.2GiB of relational spike evidence on the original instance is **not**
preserved by these branch pushes. Durable artifact/instance-volume backup remains a separate task;
no cloud/global service or shutdown operation is authorized by this source preservation checkpoint.

The archive is pushed directly to the existing remote URL; no new GitHub repository/design remote,
merge, tag, release, force push, CI enablement or native/runtime investigation is implied. Native19
remains paused, VP001 remains OPEN/UNKNOWN; preserve raw failed evidence and uncertainty.
