# Feasibility study

Separate later study: [Floci report](floci/REPORT.md), [coordinator review](floci/REVIEW.md) and
[bounded handoff](floci/HANDOFF.md). **Complete/stopped, viable with constraints**: real local
Batch Docker jobs/fresh polling/S3 plus prior DML packet replay, not combined DML-in-Batch adapter
execution. Its scoped image pull/private fixture authorization does not alter the historical
study's safety rules below or authorize more runs/Iteration11 implementation.

Status: the first study and candidate-design iteration are complete. The result is
a qualified feasibility pass for narrow cooperative local mechanisms, not approval
for automatic real-resource management. The user authorized autonomous delegated
research and then explicitly allowed evolving and trying candidate designs. DML
implementation/specification changes and live cloud-resource operations were not
part of this work.

## Goal

Try to falsify the emerging design using executable local experiments and
adversarial worked examples. Find integration gaps, unsafe assumptions, and the
smallest next prototype. Distinguish current implementation capabilities from
simulations and OpenTofu behavior.

## Results

Start with [candidate iteration results and morning-review choices](ITERATION-RESULTS.md),
then [the focused final audit](final-review/report.md).
The [first study's findings](RESULTS.md) and [candidate approaches](CANDIDATES.md)
preserve how the design evolved. The [iteration ledger](ITERATION.md) records scope.
Detailed synthesis is in [integration/report.md](integration/report.md), qualified
by [the independent review](review/report.md). The review verdict is **needs
corrections before end-to-end safety claims**; passing finite models do not establish
production GC, cloud adoption, or erasure guarantees.

Reproduce from this repository's root:

```sh
python3 -B feasibility/integration/run-all --refresh-sources
# Or omit real OpenTofu/provider probes explicitly:
python3 -B feasibility/integration/run-all --models-only
```

The lab's pinned executable must already be available for a full run; see
[its report](opentofu/report.md) and `opentofu/provision.py`. Model-only or unavailable
tooling runs report skipped stages, not full success. Generated sandboxes are
retained with a bounded eight-run limit; inspect/archive old ignored runs before
repeated reruns. No existing sandbox is automatically deleted.

Candidate entrypoints, also from the repository root:

```sh
python3 -B feasibility/journal/test_followup.py
python3 -B feasibility/artifact/test_provider.py
python3 -B feasibility/gate/followup_tests.py
python3 -B feasibility/final-review/audit.py
```

These differ in evidence units and runtime. The gate's combined suite executes
285 CLI calls; the final audit is a smaller seven-case check. Consult their reports
for fresh-sandbox caps, tool prerequisites and expected negative outcomes. The
final audit intentionally reproduces an unfixed `.tofu.json` capture bypass;
passing the audit is not a claim that the gate is universally safe.

## Workstreams

1. **OpenTofu lab:** actual local CLI experiments for materialization, provisioning,
   import/adoption, outputs, dependency-sensitive destruction, and state recovery.
2. **History model:** executable ordinary-DAG model of installation, bound closures,
   distinct requests/attempts, reuse, interruption, and bounded adapters.
3. **Retention model:** executable full-history multi-repository retention, shared
   ownership, pending adoption, GC races, excision, and disposal retry experiments.
4. **Adversarial review:** HCL composition/regeneration, concrete cloud-provider
   adoption limitations from primary sources, and security/erasure failure scenarios.

The coordinator integrated findings, commissioned independent reviews, verified
markers/evidence and directed targeted candidate fixes. Eleven specialist roles
were assigned across the two phases and final audit, with resumed follow-ups.
An unavailable alternate model did not execute work; failed resumed audits are not
counted as completed review. See the final results for orchestration limitations.

## Safety and evidence

- No cloud/service mutations, real AWS operations, Docker daemon operations,
  external deployments, secret inspection, or destruction of existing resources.
- Local lifecycle experiments are limited to newly created sandbox resources.
- No OS changes, global installs, service control, remote creation, or pushes.
- DML implementation at `/work/repos/micha/dml` is read-only.
- Project-scoped tool realization/downloads are permitted; pin and report versions,
  checksums, and commands. Do not weaken or silently bypass verification.
- Generated state, logs, binaries, sessions, and runtime data are ignored. Commit
  reproducible scripts, safe fixtures, and concise reports, not raw agent sessions.
- No worker commits or delegates. The coordinator controls integration and review.

## Evidence layout

Each workstream has `task.md`, `report.md`, reproducible prototypes/tests where
useful, and an atomic `done.json` published after the report is complete. Raw
execution logs live in ignored `runtime/` directories. A done marker denotes task
completion, not necessarily passing experiments.

Workstream tasks and `WORKER.md` document completed assignments, not a directive to
restart the study. Successful deliveries and failed/blocked attempts are separately
recorded. All worker windows are closed; persistent results and Pi sessions remain.

The discussion in [../discussion.md](../discussion.md) remains exploratory.
The study did not amend conceptual agreements into an implementation specification.
