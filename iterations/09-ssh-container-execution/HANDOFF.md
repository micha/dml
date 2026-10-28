# Iteration 9 conditional handoff: SSH execution against a local container

Status: **approved and GO**. The user authorized the existing window-2 agent in a new
Pi session to implement this bounded plan, coordinator monitoring/independent review and
fixes until satisfactory, then focused worker commit/push and exact-SHA CI/fixes. See
[COORDINATION.md](COORDINATION.md). The conditional/pending language below records the
planning checkpoint; this current authorization supersedes those permission statements,
not the scope/prerequisite/acceptance gates. Iteration 8 remains complete and stopped.

## 1. Goal and stop line

A explicitly records Q/Cq; stage through SSH into a container-side workspace with no shared
exchange mount; fixed installed worker in B creates only T for exact Q; fetch closed
completion files and use existing exact-history validation/atomic explicit-ref A receive.
Docker is an entirely local SSH-host fixture, **not a public DML execution backend**.
Begin synchronously; preserve unknown outcomes and retained B on transport loss.

Stop after this bounded Python transport/invocation slice, meaningful actual installed
SSH/container evidence and independent acceptance. No remote daemon/cloud/second-machine
experiment, Docker adapter/runtime dependency, registry/package publication, scheduler,
detached supervisor, remote async observation, arbitrary command/framework, automatic
relaunch/retry/recovery/cancellation, environment installer, native/old-spec expansion,
reuse/facets, resources/GC/excision, observer/UI, version bump/migration or later feature.
Missing primitive or material provisioning/scope change needs evidence and separate approval.

## 2. Candidate choices needing approval

- Separate SSH module/fixed installed three-action helper: stage, execute, fetch. Runtime
  contains no Docker operations or arbitrary commands. Existing public local execution,
  transfer and receive remain authoritative.
- Caller-Q-only new SSH path; original local fresh-Q/asynchronous behavior unchanged.
- Narrow public exchange job/spec reader promotes the existing strict parser; no private
  cross-layer calls, duplicate role validator or second native/packed codec.
- Explicit endpoint/identity/known-hosts/remote interpreter/root, noninteractive strict
  host-key checking, fixed quoted POSIX remote command with no PTY; no inherited arbitrary
  SSH config/proxy/forwarding options. Exact spellings remain refinable.
- Small strict length header plus bounded fixed binary bodies, no tar/remote file requests;
  transport completeness is not recorded-outcome validation.
- Separate local pre-spawn dispatch guard and remote existing one-shot marker. No global
  single-dispatch claim or marker clearing on uncertain SSH failure.
- Fetch never executes or finalizes; packet-only receive reuses public exact-Q validation.
  No transport `done`/success inference from SSH status. B's local cleanup is not fixture
  retirement; remote process lifetime after client loss remains explicitly uncertain.
- One owned local container, loopback-only SSH port, no runtime shared mounts, retained B,
  installed current compatible runtime and controlled ephemeral credentials. Cached build/
  image prerequisites are not yet verified; missing prerequisites block before new pulls.

## 3. Required reading and live preflight after separate GO

Follow machine instruction index first; verify `/work` mounted. Read fully:

1. Design [AGENTS](../../AGENTS.md), [README](../../README.md),
   [discussion](../../discussion.md), this handoff/design/example.
2. Implementation [AGENTS](../../../dml/AGENTS.md),
   [documentation guidelines](../../../dml/docs/documentation-guidelines.md),
   [as-built instructions](../../../dml/docs/spec-next/AGENTS.md),
   [orientation](../../../dml/docs/spec-next/README.md),
   [glossary](../../../dml/docs/spec-next/glossary.md), linked public Python/object/record/
   repository/CLI contracts and maintained sources/tests.
3. [Caller requests](../../../dml/docs/spec-next/caller-requests.md),
   [repository execution](../../../dml/docs/spec-next/repository-execution.md),
   [local execution](../../../dml/docs/spec-next/local-execution.md),
   [asynchronous execution](../../../dml/docs/spec-next/asynchronous-execution.md),
   [transfer](../../../dml/docs/spec-next/transfer.md),
   [packaging](../../../dml/docs/packaging-and-distribution.md),
   [coverage catalog](../../../dml/tests/coverage-exclusions.md), Iteration 8
   [RESULTS](../08-caller-recorded-requests/RESULTS.md) and
   [REVIEW](../08-caller-recorded-requests/REVIEW.md).
4. [LMDB entity diagram](../../../dml/docs/lmdb-entity-diagram.html) and its
   [maintenance guidance](../../../dml/docs/documentation-guidelines.md#as-built-visualization-maintenance).
   Review final implemented claims; do not draw candidate SSH/Docker structures as native entities.

Planning inspected clean DML **`f7113d7acb3a0fe35eed6cb0013d3074533aef51`**, local diagram
commit over published `865bb79`; design checkpoint `74a7bcd` plus preserved direction notes.
Reinspect live tree/index/HEAD. Prior green CI is not a fresh baseline; preserve unrelated
work and the unpushed diagram commit. Publication of that existing commit needs explicit
scope coordination if a later authorized push would include it.

After delegation authorization only: verify actual Pi pane/process, name implementer/
reviewer, start the existing worker in a new Pi session as directed, not another agent.
Agree exclusive ownership of **both build/check and build/coverage**. Complete fresh
standard baseline before measured source edits. Independent coordinator checks wait for
source freeze and explicit release of both builds. No concurrent wipes/reconfiguration/edits.

Live planning inspected only local service/tool metadata: Docker29.8.1 active/access via
existing docker group; OpenSSH10.5p1 clients present. It did **not** inspect images or connect.
After GO, explicitly verify local daemon/socket selection (not inherited remote context),
image/base/sshd/account/runtime/build prerequisites, architecture/ABI and loopback port
availability. Use existing tools/caches; no host service/Nix/global package changes. Missing
image/tools needing downloads requires a scoped provisioning decision. Do not pretend a
host Nix-built wheel automatically loads in a different image/libc or rewrite wheel tags.

## 4. Candidate source seams

Relative to implementation checkout:

| Seam | Bounded change |
| --- | --- |
| `python/daggerml/daggerml/exchange.py` | Narrow public strict spec/job reader; existing execute/receive semantics unchanged |
| New `python/daggerml/daggerml/ssh.py` | Owned explicit endpoint/job, bounded stage/execute/fetch client composition and local guard/client reaping |
| New `python/daggerml/daggerml/ssh_worker.py` | Installed fixed transport actions using public execute; no Docker/custom command/fault hooks |
| `meson.build`, packaging inventory | Install only new runtime modules in existing package/tag; no test/credential/image tooling packaged |
| New `examples/ssh_execution.py` | Endpoint-driven synchronous caller-Q story; no Docker requirement in application |
| Owned fixture Dockerfile/scripts and local integration entrypoint | Local-only SSH-host setup/teardown, compatible current image/runtime, ephemeral credentials, no shared execution mounts |
| Focused tests/private fault fixtures | Endpoint/framing/invocation/history/atomicity/process limits and real SSH boundary evidence |
| Owning as-built SSH contract/navigation | Describe actual behavior only after implementation; reference existing local/transfer/receive authorities |

Exact file/API names are candidate choices; record refinements. Docker image/daemon/key
management must not leak into core imports or public runtime dependencies. A container
definition is test support, not an execution closure/resource-manager schema.

## 5. Recommended work order and assurance

### A. Fix prerequisites and the acceptance fixture boundary

Establish a bounded local fixture before claiming SSH implementation evidence. Pin local
image identity and prove installed module/core/worker/console/child provenance from current
source; build compatible current wheels in a designated local fixture build if necessary.
Do not use a stale published runtime. Stage source/wheels for image build without exposing
A/checkouts at runtime. No registry publication or speculative dependency pulls.

Use an explicit owned container/name/labels, local socket, loopback-only SSH port, controlled
account and temporary credentials. Trust host key through container-owner control, strict
known-hosts thereafter. Verify mount inspection has no A, source checkout, shared exchange
or Docker-socket mount. Keep secret values out of prompts/logs/Git. Local metadata/public
image identity is fixture evidence, not proof of full computational capture.

A separate local integration entrypoint may require Docker/OpenSSH explicitly; do not make
normal import/default cross-platform tests start daemons or silently depend on them. Default
standard host tests still measure new runtime helpers; the actual local SSH/container gate
is **mandatory separately for acceptance**, not replaced by mocks or CI pass. Report missing
prerequisites as blockers, not a green skipped experiment. No workflow expansion assumed.

### B. Public spec seam and fixed helper framing

Promote the current strict reader within exchange ownership; test owned descriptions,
caller-Q-only checks and unchanged local modes. Keep job/completion/transfer codecs owned
by existing modules. New helper handles only fixed path/actions/files; never private DML
functions, dynamic modules, commands from incoming JSON or historical source/path authority.

Use strict bounded header/body/EOF checks at both endpoints. Exercise duplicate/unknown/
missing fields, malformed/deep JSON, UTF-8, bool/negative/overflow counts, exact boundary and
boundary+one, truncation/extra data/startup noise, file read/write/receipt-last failure and
partial retention. Check original-profile limits plus small substitutions, distinguishing
evidence. Framing success must not make unvalidated history `done` or import A.

Client input/output handling must avoid blocking pipe writes without a timeout, deadlock
from unread stderr and unbounded in-memory capture. File-backed streams with finite waits
are a candidate; qualify unbounded disk/spawn/dependency behavior. Close/reap acquired local
process/streams on errors; do not claim this reaps remote processes. Record exact exclusions
only under existing no-value policy, not difficult meaningful-handler exemptions.

### C. Stage and fixed command integrity

Validate explicit types, SSH option-like host/user injection, ports, credential/config paths,
remote **POSIX** absolute paths independent of host OS, NUL/newline/Unicode/NFC and shell
metacharacters. Test quotes/spaces and no injected side effects. Local argv `shell=False`
plus remote quoting both matter. Verify finite noninteractive strict host-key/auth failures;
wrong/changed host key must reject without execution or interactive acceptance.

Stage validates exact independent expected/local job before sending; exclusive remote
creation rejects readable/partial/conflicting existing directories without repair. Track
actual stage bytes and remote files. Lost acknowledgement may retain complete files, not
permission for automatic stage/execute. Q refs/old A bytes stay unchanged; stage creates
no B/reservation/T. Preserve A Q when later prepare/transport/file failure occurs.

### D. Exact-Q execution and offline return

Record Q using public Iteration8 helper; select remote interpreter explicitly. Run actual
fixed installed helper through SSH, with host A and prepared job/input files offline but
local control/log location retained. Prove no shared mount/host-source/runtime dependence.
Independent remote readers check exact Q, only fresh T, P/Cq tree and ordered P/U/F history.
Keep local pre-spawn dispatch marker and remote existing marker; second execution rejects
without launch. A new explicit workspace is not a global replay/capability guarantee.

Return recorded success and nonzero-after-publication failure/evidence/separate cleanup.
Two matching requests against the same C have distinct Q/T and equal result. Include prior
Q/T/publication history and composite-only descendants in C. Fetch is never execute; make
endpoint unavailable before fresh packet-only receive with independent expected and ordinary
CLI. Preserve main, sentinel, submission/Q refs and absent B refs. Explicit same-ref repeat
is nonexecuting; conflict is not implicit ref advance/adoption/merge.

Use independent public breadth-first **all typed objects/every packed byte/all parents**
oracles, not transfer traversal/CLI prefixes. Independently validate real Q2 packet before
wrong-Q swap/token-base rewrites. Add typed-complete expected-Cq/T-to-other-matching-Q F
retaining expected Q; association rejection must not be merely a missing-base error.
Retain unchanged final outcome/evidence/cleanup/diagnostic restrictions.

Track **successful genuinely new actual-A puts/readback** before late return-ref/raw-ref,
real map-full and substituted consuming-commit failure. Exclude validation-store/preexisting
Q rows from counts. Fresh independent full-state/raw-corruption checks prove entire batch
absence. Reuse comparable-map/compact exact-byte diagnostics so Windows does not expand a
physical padding mismatch into huge logs. Actual pre/postcommit processes prove no batch
versus complete import despite lost response. No computational retry on receive failure.

### E. Actual loss boundaries and retained history

Normal path: real installed fixed helper, binary SSH stream, independent installed receiver.
Fault tests: finite explicitly private barriers before child spawn or after actual child
reaping; label any private remote command/helper substitution as such, not normal installed
branch coverage. No installed fault imports/environment hooks. Do not kill/disconnect a
parent with a live computational child for convenience. Container-control inspection belongs
to the fixture/test oracle, not production fallback transport.

Exercise stage/client-spawn/host-key/auth/connection loss, unknown P/U, reaped pre-F loss,
F/files before SSH response loss, interrupted fetch and A storage response loss. Explicit
fetch after response loss retrieves same Q/T/F without remote execution. Missing files,
SSH255/other status, elapsed time and container liveness must not fabricate failure/done.
Real post-F unchanged production-profile overflow retains B F but no successful completion
packet. Child-launch failure after P differs from SSH failure before T. Cleanup remains
existing B scratch cleanup; fixture retirement is not folded into it.

On errors release cooperative gates and prove owned writers stopped before deleting only
fixture-owned resources. Watchdog/remote-lifetime uncertainty is a blocker/evidence gap,
not a portable cleanup claim. Retain unknown history until explicit policy; no automatic
container removal on transport error, global prune, arbitrary PID signaling or daemon.

### F. Freeze, independent review and stop

Worker records actual APIs/framing/commands/exits/counts, installed/image provenance,
real versus substituted failures, genuine new-put rollback, local versus remote reaping,
credential handling, cleanup disposition and coverage/memory/mutation/platform/trust/profile
limits in RESULTS here. Coordinator owns REVIEW/COORDINATION/design status.

After final stable standard, actual installed local SSH/container gate and static checks,
freeze runtime/tests/as-built edits and release **both shared builds**. Coordinator independently
inspects/probes/runs fresh checks; worker fixes reviewed findings with regressions. Stop at
acceptance. Commit/push/automatic exact-SHA CI require current separate authorization;
plan approval is not publication permission. No extra worker or later feature turn.

## 6. Standard assurance, documentation and publication gates

Reinspect current standard command before use:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Measure new SSH client/helper and maintained example in the existing source gate; preserve
retained native and Python thresholds, binding/141 CLI memory workloads and prior runtime
suppression/finalizer qualifications. Do not assume previous test/statement counts. Host
helper coverage is not installed-container/SSH-process coverage; informational CI `-c`
is not local default/memory `-v` or real fixture evidence.

Recheck Python mutation-tool availability without bootstrap. If unavailable, qualify the
gap and run selected negative oracles for wrong-Q acceptance, implicit repeat dispatch,
host/interpreter confusion, unsafe remote quoting, premature A publication, incomplete
framing, registration/execute on fetch, missing host-key enforcement and status-as-outcome.
Keep new pytest IDs compact, oversized boundary inputs intact and diagnostics bounded.

As-built docs must own only implemented SSH behavior and reference existing contracts.
Review `docs/lmdb-entity-diagram.html` against the final native model/identity claims; this
Python transport is expected to add **no native LMDB entity or hash-facet change**. Record
review/no-change rationale instead of inserting proposed SSH/container boxes. Keep its
focused checks current if displayed implemented claims actually change.

Validate Markdown targets/anchors, whitespace, packaged module inventory and isolated
installed provenance. No secrets, ignored scratch/image artifacts, vendored changes,
unrelated work, tags/new remote/force push or release workflow. A future authorized push
must explicitly account for the existing local diagram commit preceding this turn.

Before assignment: detailed plan approval, bounded GO, live preflight/build ownership.
Before publication: independent acceptance and current focused commit/push/CI permission.
No such assignment/publication is authorized by this planning request.
