# Explicit installed closure-bound-dependency acceptance

Opt-in controller, **NOT** a default fixture. [Owning example](../../docs/closure-bound-dependencies.md),
[builtins](../../docs/internal-builtins.md), [handoff](../../../dml-design/iterations/23-closure-bound-dependencies/HANDOFF.md)
and [validation policy](../../docs/validation-policy.md) own scope. No Docker/SSH/Batch/image/service,
native lifecycle fix, nested ordinary worker or generic evaluator.

## Readiness and sole launch

Fresh isolated cached current-source install; measure installed modules/native/CLI/interpreter
against maintained/actually compiled bytes. No old prefix reuse/download/global tooling.
Copy SEVEN measured files to NEW owned `launch-source` next to absent story root:
`installed_story.py`, `offline_read.py`, `closure_calls.py`, `closure_runtime.py`, `closure_funcs.py`,
`reuse_selection.py`, `explicit_reuse.py`. Helpers remain example-local, not installed library APIs.
Parent and child import only isolated installed DML. Unset PYTHONPATH/PYTHONHOME; parent `-I` alone
does not sanitize plain-child inherited environment. Coordinator readiness review precedes run.

```sh
# Actual fresh prefix and owned directory are turn-specific:
env -u PYTHONPATH -u PYTHONHOME /fresh/venv/bin/python -I /owned/launch-source/installed_story.py metadata-controls
env -u PYTHONPATH -u PYTHONHOME /fresh/venv/bin/python -I /owned/launch-source/offline_read.py controls /owned/story /owned/launch-source
# Once ONLY after readiness approval:
env -u PYTHONPATH -u PYTHONHOME /fresh/venv/bin/python -I /owned/launch-source/installed_story.py run /owned/story
# After known wait/reaped/absent direct children and safe original retirement:
env -u PYTHONPATH -u PYTHONHOME /fresh/venv/bin/python -I /owned/story/captured-source.unavailable/offline_read.py controls /owned/story /owned/story/captured-source.unavailable
env -u PYTHONPATH -u PYTHONHOME /fresh/venv/bin/python -I /owned/story/captured-source.unavailable/offline_read.py read /owned/story /owned/story/captured-source.unavailable
```

Metadata controls reject spawn/connect/urllib transport before Q/T. Reader activates blockers BEFORE
DML/helpers import and independently rejects spawn/http/urllib transport/connect; exact pure stdlib
URI parsing remains allowed. Cooperative restrictions are evidence, not a security sandbox.

## Six own Q, four synchronous local attempts

One fixed `(13+29)*scale` func: Q1 capturedv1/originA/scale2 fresh84/adoptS1;
Q2 SAME capture reuseOLD84 after defaultsv2/scale3; Q3 SAME capture fresh84/v1;
Q4 NEW capturedv2/originB/scale2 reuseOLD84; Q5 NEW capture fresh84/v2;
Q6 capturedv2/scale3 valid-mismatch/pending then fresh126/no adoption.
Exactly FOUR actual direct children, TWO map-get positions each; zero list/construction/support/
compatibility/nested calls. Metadata and hits never dispatch. Bootstrap is authoring, not invocation.

Controller captures actual importing helpers/runtime/entry bytes BEFORE Q/T, then incremental
Q/D/C/E/K/intended dispatch/PID/native pre-dispatch/actual wait return/outcome/cleanup receipts BEFORE
assertions. Only four explicit execute boundaries permit one expected exact child each. Direct wait/
reap is proved BEFORE completion observation/import/public S; poll flags alone are insufficient.
Failure or uncertain custody means STOP/scoped triage, not relaunch/deadline increase.

After all four children are known wait-exit0/reaped and owned PIDs absent, rename ONLY owned source/
workspace/packet/expected originals unavailable and retain inert evidence; copy SAME complete typed
history to replica. Historical strings are not cleanup authority. No external fixture is created.

## SAME-history nonexecuting readers

Fresh reader checks original/current copied helper/controller/runtime/interpreter source identities,
forbids target storage writes/recording/dispatch/logical arithmetic and permits public validation
scratch. Validates actual6Q4T8positions, strict capture/key/source/wrapper/getter profiles, original
versus requested capture on both hits, actual D/Cq/fullQ/W/successfulS/orderedF spines, three atomic
B/C publications, exact summary links/values/no adoption/custody and unchanged caller/replica bytes.
Inspector fixed semantic recomputation is not another invocation. Correct reader-only errors on SAME
stopped evidence, preserve original failures/bytes; never repeat computation to obtain a pass.

[Finite mutations](mutations.py) use measured private candidate/plugins and focused HOST tests.
Native rollback/substitution/host coverage differ from actual installed children/platform assurance.
[Results](../../../dml-design/iterations/23-closure-bound-dependencies/RESULTS.md) retain commands/source
qualifications/raw failures/custody/independent disposition. GHA remains disabled/NOTRUN/notpass;
native19 PAUSED/VP001 OPEN UNKNOWN, no historical diagnosis/standing waiver/fresh platform green.
