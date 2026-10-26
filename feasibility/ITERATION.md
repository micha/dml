# Candidate-design iteration

Status: complete; see [iteration results](ITERATION-RESULTS.md) and
[the final audit](final-review/report.md). After the first study, the user said:
"feel free to evolve the design and try things. we can review your approaches in
the morning." This authorizes candidate designs and additional isolated prototypes;
it does not make their policy choices approved or permit live cloud operations.

Preserve the first-wave counterexamples and reports. Fixes belong in new prototype
directories so we can compare approaches rather than retroactively making the
baseline look safe.

## New workstreams

- **journal:** durable SQLite-backed synthetic ownership/retention/disposal journal,
  canonical identities, actual commit/head root export, and multiprocess crash tests.
- **gate:** backend-neutral plan/receipt admission and saved-plan stale-retention
  tests using actual local OpenTofu. No GitHub-specific integration.
- **artifact:** try an actual import-capable OpenTofu sandbox-file provider to test
  bytes-preserving artifact adoption, non-destructive updates and guarded disposal.
- **hardening review:** actual same-file handoff, independent attacks and initial
  candidate comparison.
- **final review:** a fresh-context targeted audit of sealed-plan fixes, including
  a new `.tofu.json` material-capture bypass. Two resumed hardening attempts failed
  at the model provider; an alternate model was unavailable before executing tools.
  Neither is counted as completed review.

SQLite is an experiment substrate, not a proposed replacement for DML's LMDB core.
A custom provider is an experiment in the OpenTofu seam, not a selected production
dependency. Policy choices must be reported and alternative approaches considered.

## Additional safety/tool allowance

Only the artifact worker may realize a scoped Go toolchain/download pinned Go SDK
modules for building a local provider. Keep downloads, binaries and tool realization
under ignored `artifact/runtime/` or `artifact/tools/`; do not alter global profiles,
OS declarations, services or the shared first-wave OpenTofu tool. No cloud SDK
providers or credential reads. All provider operations must target newly created
sandbox files, never arbitrary paths. Report unsupported capabilities honestly.

All other worker-contract boundaries still apply. No worker commits, pushes,
delegates, edits other worker directories, or modifies the DML implementation.
The coordinator may resume workers after initial delivery for focused integration
corrections. Original study findings remain valid until reproduced fixes explicitly
address them.
