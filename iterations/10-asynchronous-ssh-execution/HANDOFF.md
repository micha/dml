# Iteration 10 conditional handoff: asynchronous SSH execution and progress

Status: **reviewed bounded plan; local checkpoint requested**. The user reviewed
[DESIGN.md](DESIGN.md)/[EXAMPLE.md](EXAMPLE.md)/this handoff and requested checkpoint commits,
including separately authored diagram maintenance. Iteration 10 implementation/delegation/
publication GO remains pending: no worker assignment, runtime/spec edit, fixture/SSH operation,
experiment/build/provisioning or CI. Candidate/pending-review language below preserves planning
provenance; exact engineering spellings remain refinable. Iteration 9 remains complete/stopped.

## 1. Goal, recommended choices and stop line

A records/stages Q/Cq; application starts one foreground SSH execution connection without
waiting; fresh clients retrieve validated immutable P/U/F through fixed nonexecuting remote
observe; existing receive_observation atomically publishes explicit A refs with exact Q,
unchanged heads/request refs and preserved unknown/separate-cleanup boundaries.

Recommended bounded choices needing review:

- Existing stage/execute/fetch remain; asynchronous start invokes the **same fixed execute**,
  with shared local dispatch guard/remote existing guard, no remote background worker/service.
- Nonserializable live SSHLaunch retained/reaped by an application, separately saved SSH job
  identity. Wait timeout retains ownership/connection; no implicit cancellation.
- New saved directory composes existing public exchange save/load for expected plus strict
  operational SSH metadata; no duplicated spec/native codec or serialized PID/live state.
- Narrow public read-only exchange observation inspector promotes owning validation;
  host validates fetched progress without writing A. Existing receive reuses same authority.
- One new fixed helper action observe, using public observe_exchange once and helper-owned
  temporary packets, strict bootstrap/progress frame shapes, no lifecycle/success assertions.
- Duplicate remote/host/receive validation IO is accepted prototype cost; report limits.
- Local cached offline SSH-container fixture uses approved loopback-only host networking,
  no runtime project/exchange/gate/socket mounts and separately controlled remote gates.

Stop after this slice, meaningful actual installed SSH/container evidence, stable standard
checks and independent acceptance. No detached remote lifetime/service/supervisor, scheduler,
cloud/second-host/remote Docker, automatic retry/recovery/cancellation, generic command/gate/
plugin framework, new native entities/facets, provisioning/resource/GC/excision/observer UI,
version/migration, package publication or later feature. Missing primitive/material scope
change needs evidence and separate approval; no implicit C expansion.

## 2. Required reading and preflight only after separate GO

Follow machine instruction index first; verify /work mounted. Read fully:

1. Design [AGENTS](../../AGENTS.md), [README](../../README.md),
   [discussion](../../discussion.md), this design/example/handoff.
2. Implementation [AGENTS](../../../dml/AGENTS.md),
   [documentation guidelines](../../../dml/docs/documentation-guidelines.md),
   [as-built instructions](../../../dml/docs/spec-next/AGENTS.md),
   [orientation](../../../dml/docs/spec-next/README.md),
   [glossary](../../../dml/docs/spec-next/glossary.md) and linked public Python/object/record/
   repository/CLI contracts; inspect maintained sources/tests, not old plans as authority.
3. [SSH execution](../../../dml/docs/spec-next/ssh-execution.md),
   [asynchronous exchange](../../../dml/docs/spec-next/asynchronous-execution.md),
   [caller requests](../../../dml/docs/spec-next/caller-requests.md),
   [repository execution](../../../dml/docs/spec-next/repository-execution.md),
   [local execution](../../../dml/docs/spec-next/local-execution.md),
   [transfer](../../../dml/docs/spec-next/transfer.md),
   [packaging](../../../dml/docs/packaging-and-distribution.md),
   [coverage catalog](../../../dml/tests/coverage-exclusions.md),
   [SSH fixture support](../../../dml/tests/ssh/README.md), Iteration 9
   [RESULTS](../09-ssh-container-execution/RESULTS.md)/[REVIEW](../09-ssh-container-execution/REVIEW.md)
   and relevant Iteration 7/8 progress/request evidence.
4. [LMDB entity diagram](../../../dml/docs/lmdb-entity-diagram.html) and
   [maintenance guidance](../../../dml/docs/documentation-guidelines.md#as-built-visualization-maintenance).
   Review final native model/claims; do not insert candidate SSH/owner/packet boxes as LMDB entities.

Planning baseline: clean DML `29ed39be6c1c18e6d57f782dd073acd37939c71c`, design checkpoint
`f8e70b4c9371327dbaaa28d1d449aa6011c141ac`. Reinspect live index/tree/HEAD/unrelated work.
The user confirms another agent separately owns diagram changes observed during final planning
checks and will commit them in DML. Preserve that work; use its completed current baseline at
future assignment, not a forced return to the initially inspected SHA. This is not a planning
blocker and does not authorize this coordinator to edit/commit that agent's diagram work.
The subsequent checkpoint request explicitly authorizes its inclusion: diagram/test maintenance
is now locally committed as **`a94e6f51bb41ad2cfab4fad1dd2e96c97a3e728d`**, not pushed.
Six focused tests, JavaScript syntax and DOM-stub layout/navigation checks pass; no full-suite/
CI/real-browser evidence claimed. Use this clean current DML baseline unless later work moves it;
account for the existing local commit before a future authorized implementation push.
Iteration 9 fixture/private keys were retired: old ignored wheels/images/endpoint files are
not a usable live target or proof of current source provenance. No service/tool inspection
or SSH/container operation occurred in this planning turn.

After separate delegation GO only, verify actual existing worker pane/process/session,
identify coordinator/worker and start a new Pi session as directed. No extra agents or old
completion-marker protocol. Worker owns runtime/tests/as-built/example/fixture/RESULTS;
coordinator owns REVIEW/COORDINATION/design status. Exclusive **both build/check and
build/coverage** through baseline/implementation; source freeze and explicit release precede
independent coordinator use. No overlapping wipes/reconfiguration/edits.

Complete fresh standard baseline before measured source edits. After GO, inspect explicit
local Docker socket/context/cache/bare runtime/ABI/loopback port; use existing tools/caches,
no global/firewall/service change or download implied. Missing prerequisites needing pulls/
installation require scoped user decision. Rebuild current installed fixture with protected
fresh keys/no shared mounts; record image/closure/source/native/wheel bytes. Preserve approved
host-network/no-network-namespace distinction; do not silently broaden to arbitrary host networking.

## 3. Candidate source seams

Relative to implementation checkout; exact names remain refinable:

| Seam | Bounded work |
| --- | --- |
| `python/daggerml/daggerml/exchange.py` | Public read-only observation inspector inside existing parser/validator ownership; shared authoritative receive checks |
| `python/daggerml/daggerml/ssh.py` | Saved job identity, live nonwaiting launch owner/shared guard, bounded validated observation/reply framing |
| `python/daggerml/daggerml/ssh_worker.py` | Fixed observe action using public ExchangeHandle/observe_exchange and temporary packet disposal |
| `examples/ssh_progress.py` or similarly focused script | Finite explicit owner plus short-lived clients/offline receiver, declared remote gates/external controller |
| `tests/ssh/` | Current offline fixture/installed progress gate, explicit remote gate controller/safe private barriers |
| Focused Python tests | Serialization/framing/ownership/exact-Q/history/rollback/race/error/regression evidence |
| Owning as-built SSH/asynchronous documents/navigation | Describe only actual selected behavior after implementation |

No production private cross-layer exchange/local/transfer access or new native/job/role codec.
New public inspector belongs to exchange; helpers share internal SSH framing only within its
ownership. Packaging must contain runtime modules only, never tests/key/controller/fault support.
Keep original synchronous SSH and all local fresh-Q/caller-Q/asynchronous behavior intact.

## 4. Recommended work order and acceptance evidence

### A. Owning read-only inspector and saved identity

Promote strict existing packet parsing/root/phase/exact-Q/history checks without A publication.
Test read returns ref=None/nested completion ref=None, typed-valid P/U/F, cleanup before return,
wrong association/phase/history, malformed/profile/file/validation-scratch-cleanup errors and
no executor/ref/A mutation. Receive still validates before atomic actual-A import; do not weaken
field/type/outcome/evidence/cleanup/diagnostic restrictions or add a second role reader.

Saved SSH identity composes public exchange save/load in a new directory with ssh metadata last.
Exercise exact type/profile/duplicate/missing/unknown/deep/UTF8/oversize/bool counts where applicable,
partial/collision/file failures and owned descriptions. Native Windows control/credential path
normalization must not alter POSIX remote interpreter/root. Save/load with endpoint/A/input/control
unavailable must not connect/read B/signal/dispatch; file strings remain trusted operational input.
Incoming packets cannot replace expected/configuration. Test original-profile bounds as well as
small substitutions; compact IDs/diagnostics and no weakened large inputs.

### B. Live foreground SSH owner and shared one-shot boundary

Prebuild strict argv/streams/owner, create dispatch guard before Popen, return owner without
waiting for computation/auth/readiness. Spy and actual safe local-child barriers prove no
blocking wait in start. Mixed start/execute/second-start reject before another Popen; native
spawn/auth/unknown host/connection failure retains marker. No remote start_exchange/backgrounding.

Actual owner waits: acquired streams close only after known local-client disposition;
TimeoutExpired preserves Popen/streams so later wait can reap. Cover allocation/log/spawn/
postreap-output/check failures and loss before owner return with retained ownership on errors.
Any terminate/kill handling for *observation* client must never target execution connection.
Classify local SSH exit/status/stdout as transport diagnostics, never working/done/outcome.
No saved PID, hidden registry/finalizer or implicit context-manager cancellation.

### C. One fixed observe action; bootstrap/P/U/F

Remote helper reads exact owned job and uses public observation once. Bootstrap yields only
matching job bytes/no packet; malformed readiness/ref/history is an error, not masked bootstrap.
For P/U/F, fully own bounded closed bytes and dispose allocated remote scratch before successful
reply. Host owns full frame, verifies expected, uses owning public read-only inspector in host
scratch, cleans it before final new packet allocation and publishes receipt last.

Exercise original8192/transfer limits and boundary+one, duplicate/unknown/unsupported labels,
wrong fixed body counts/bools/negatives/overflow, truncation/extra/startup noise and IO failure.
Test scratch-cleanup errors on both endpoints, final packet write failure/no successful return,
partial retention, no packet for bootstrap and no A write during observation. Concurrent readers
use distinct packet directories. Malformed response/status/elapsed time never fabricates failure/done.
All host observation local clients/streams reaped or retained with explicit uncertain owner.

Prove existing coherent B read/pin semantics are preserved through SSH: ref movement between
selection and export cannot retarget the selected immutable ID. Pause meaningful races through
private finite instrumentation, compare exact bytes/parents. Do not claim a monotonic newest-
snapshot order across concurrent polls or copy source refs as authority.

### D. Actual installed gated progression and offline receive

Mandatory separate gate (never normal import/default Docker startup): actual installed fixed
helper via binary SSH, host A/prepared inputs offline, remote declared interpreter and no shared
mounts/checkout/PYTHONPATH dependence. Finite application retains execution SSHLaunch while fresh
installed clients load saved job, observe P, exit; external fixture controller releases declared
remote initial gate; fresh clients observe U while child still gated; then release publication
gate and retrieve F. Repeat observations/calls neither allocate Q/T nor change B refs/objects.

Remote gates are explicit named inputs and independently owned test resources, not host-only
paths, runtime fault imports/arbitrary-command actions or hidden observe side effects. If an
expected phase is missed, retain bounded structured selected outcome/child/worker diagnostic
and history evidence before cleanup. Do not assume gate deadline/flakiness from final phase.
Iteration 9's unchanged early caller-example CI failure remains unknown; do not alter unrelated
example/runtime just to hide it without a reproducible within-scope finding.

Independent public breadth-first **all typed objects/every packed byte/every parent** oracles
compare remote B, packet-validation store and A; include genuine prior Q/T/pub and composite-only
children. Same exact Q/only T relative to Cq, P/U/F field preservation/ordered parents and full
history; two matching submissions against same C distinct Q/T/equal result; never-started Q;
nonzero-after-U failure/evidence, launch failure and computational/cleanup separation.

Retrieve F independently without original synchronous completion/output receipt, with no
finalization/execute/ref repair. Validate before done; genuinely overflowing F still yields no
successful packet. Safe post-F/private barrier proves observation/reaping boundaries separately.
Stop endpoint after proven writer disposition before fresh installed packet-only reception of
P/U/F. Main/sentinel/submission/Q refs unchanged; B refs absent; old packets remain exact; explicit
same-target repeat nonexecuting, existing-P-ref-to-F conflict not implicit advancement.

### E. Wrong history, atomic actual-A errors and safe process loss

Independently validate real second-Q packet before first-Q swap/token/base rewrite. Test all
phases, plus typed-complete expected-Cq retaining expected Q but T-to-another-matching-Q association
with coherent U/F; rejection must not rely only on missing-base/foreign-Cq. Wrong phase/root/
parent order/fields/outcome/evidence/diagnostics/cleanup reject before A writes. Host inspector
must not report successful done from malicious transport completion assertions.

Count **successful genuinely new actual-A puts/readback** before late different/raw-ref errors,
real map-full and substituted consuming-commit failure; validation scratch/preexisting Q rows
are not new actual-A writes. Fresh independent complete typed/raw/compact physical-byte oracles
prove entire batch absence with comparable map layout. Actual pre/post-storage-commit process
barriers prove absent batch versus complete ref/history despite missing response. Retry receive
is transport/import retry, never another computation.

Actual SSH unknown/changed host key/auth/connection loss, bootstrap, unknown P/U, reaped pre-F,
post-F response loss, interrupted observations, unchanged production-profile F overflow and
cleanup error paths stay distinct. Normal installed helper evidence is mandatory; private
command substitutions are separately labelled, never installed fault hooks. Observe retry may
select newer history; it does not reproduce the lost packet or retry computation.

Execution-loss barriers only before child spawn or after actual child reaping. Do not kill/
disconnect a worker with live computational child for convenience. On errors release cooperative
gates in finally, preserve/reap application-owned local connection and prove remote owned-writer
stoppage before fixture retirement. Failure to prove disposition retains fixture/evidence as
blocker; no arbitrary PID signaling, normal unowned exit guarantee or automatic container remove.

## 5. Standard checks, documentation, freeze and publication

Reinspect standard command before use:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Measure new client/helper/inspector/example in existing source gate; preserve Python/native
thresholds, binding/141CLI memory checks and prior exclusions/runtime/finalizer qualifications.
No count assumption from prior1191 baseline. Host helper statements are not all Python branches,
installed SSH/child coverage/memory, platform/security/physical-host or remote-lifetime proof.
CI informational `-c` does not replace local `-v` or mandatory actual installed gate.

Recheck mutation tools without bootstrap; if absent, qualify the gap and exercise selected
negative oracles for wait-timeout killing connection, automatic repeat start, observation
starting/finalizing, wrong-Q/phase acceptance, trusting transported done/status, unsafe quoting/
host-key bypass, incomplete framing, premature A write and loss of selected immutable pin.
Keep exact test failure versus setup/import error distinct from a mutation-framework score.

Describe actual APIs/format/ownership/unknown/done/error choices in owning as-built docs,
linking to existing role/transfer authorities. Review diagram as-built no-native-change
rationale; do not draw proposals. Validate Markdown targets/anchors, whitespace, packaging
inventory and exact installed source/native provenance. No committed secrets/sensitive full
history, ignored fixture/scratch artifacts, vendored/unrelated changes or old-spec edits.

RESULTS records commands/exits/counts/provenance, original versus substituted fault evidence,
new actual-A put rollback, local owner/remote uncertainty, fixture gates/disposition/retirement
and profile/trust/platform/coverage/mutation limitations. Worker freezes all sources after
stable default/installed/static gates, releases **both** shared builds; coordinator independently
reviews/probes/runs fresh checks. Fix findings with regressions before acceptance. Archive
required B/evidence before retiring only stopped owned fixture/private keys, no global prune.

Before assignment: reviewed plan plus separate explicit implementation/delegation GO.
Before publication: independent acceptance and current focused commit/push/exact-SHA CI
permission; no inherited Iteration 9 authorization. No new remote/force push/release/tag/package
publication/additional worker/later turn. Stop after this bounded work for user review.
