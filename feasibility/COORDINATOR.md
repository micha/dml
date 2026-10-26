# Coordinator ledger

## Authorization and baseline

The user requested autonomous feasibility research, delegated to Pi agents in new
windows of the existing `dml` tmux session. They explicitly permit closing worker
windows when no longer needed.

Baseline design repository: `0a2a136` on `main`, clean before study setup.
Baseline DML implementation: `638cc42`, clean before study setup.
No implementation/spec changes, cloud mutations, existing-resource destruction,
OS changes, remote creation or pushes are authorized by this study.

## Delegation

Four first-wave specialists ran through `run-worker.sh`, with isolated Pi
sessions and disjoint output directories. Agents inspected public primary sources;
only the OpenTofu lab provisioned a scoped development executable. Local resource
mutations were limited to newly created ignored sandboxes.

| Worker | Initial tmux window | Scope |
|---|---|---|
| opentofu | `@87` | Actual local OpenTofu behavior and composition |
| history | `@88` | Computational-history executable model |
| retention | `@89` | GC/excision and cross-repository safety executable model |
| adversarial | `@90` | Provider and architecture falsification |

Completion requires a finished report followed by an atomic marker; process exit
alone is not accepted as evidence. Raw agent/session output is not research proof.
Follow-up integration and independent review will inspect the experiments and
re-run safe tests. Reports must distinguish actual OpenTofu behavior, simulation,
source inspection, and unresolved conjecture.

## Restart and recovery

Worker sessions are named `dml-feasibility-WORKER` in Pi's standard persistent
session storage. Runtime process status and agent output are in ignored
`feasibility/runtime/`. A timed-out or failed worker can be resumed in a new tmux
window using its session ID and a focused follow-up. Do not rerun tests blindly
against existing external resources; no such resources belong to this study.

All four first-wave workers completed, followed by integration (`@91`) and
independent review (`@92`). Reports and atomic markers were verified together with
zero process exit codes. All six worker windows were closed; the original user
window was preserved.

The independent review verdict is needs corrections before end-to-end safety
claims. Integration fixed/disclosed its provider socket-path failure and evidence
count/citation discrepancies. The coordinator accepted the remaining identity,
withdrawal-publication, root-export, and deployment-admission gaps as disclosed
feasibility findings, not solved production behavior.

Final coordinator verification:

```sh
python3 -B feasibility/integration/run-all --refresh-sources
```

All eight stages passed in `integration/runtime/5/`, including 44 model tests,
actual OpenTofu probes, source audit, and local joined lifecycle. Adoption and
cross-repository retention in that joined scenario remain explicit simulations.
The DML implementation remains clean at the baseline commit. No cloud-resource
operations, system configuration changes, commits, remotes, or pushes occurred.

See [RESULTS.md](RESULTS.md) for the final verdict and next-prototype recommendation.
Artifacts remain available for user review; no new checkpoint commit was requested
for this study, so its changes are left uncommitted.

## User-authorized candidate iteration and final audit

After the first phase, the user explicitly permitted evolving the design and trying
approaches for morning review. Additional assignments were journal (`@93`), gate
(`@94`), artifact provider (`@95`), and hardening review (`@96`). Journal and gate
were resumed for focused fixes (`@97`, `@98`); initial reports/code were preserved.

- Journal v2: 35 tests, 12 abrupt OS exits; transactional immutable snapshots and
  write-ahead creation claims replace the earlier invisible-orphan limitation.
- Artifact: actual Go provider 0.1.0; 52 CLI calls; import preserves bytes but forced
  replacement remains a destructive-authority bypass.
- Gate follow-up: 28 regression/22 focused/four historical groups, 285 CLI calls;
  sealed apply bytes, pre-effect census and fixture-only evaluation rejection.
- Hardening review: real same-file provider/journal handoff, including SIGKILL
  after unlink, with honest private-interface/sidecar/cooperative limits.

Two resumed hardening audits (`@99`, `@100`) hit model-provider internal-server
errors before publishing a follow-up marker. An alternate-model attempt (`@101`)
was blocked before tool use by account use-case registration; no settings or
credentials were changed. The final fresh-context working-model audit (`@102`)
completed with exit 0: seven cases/73 CLI calls, positive sealed same-file handoff,
and a new `.tofu.json` input-capture bypass. It is not cross-model agreement.

Editing the common runner while old Bash processes were blocked caused missing
exit records for the earlier gate/hardening wrappers. Hardening's post-report parse
failure was observed as status 2; gate's final wrapper status was not recaptured.
Their experiment deliveries were independently rerun. Subsequent launchers were
frozen copies; journal/gate/final successful follow-up statuses were verified.
No absent exit record is fabricated as zero.

All 16 launched worker windows are closed, including failed attempts, and the
original user window remains. Eleven specialist roles were assigned (12 session
IDs due to the blocked alternate model and fresh fallback). Persistent reports and
sessions remain. Only project-local/synthetic effects occurred; existing Go was
reused, no OS provisioning or live infrastructure changes were made.

Final verdict and morning choices: [ITERATION-RESULTS.md](ITERATION-RESULTS.md).
Latest independent audit: [final-review/report.md](final-review/report.md).
All source/report changes remain uncommitted for review; no remote or push occurred.
