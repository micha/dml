# Iteration 8 worked example: record Q, then attempt it in B

Status: approved bounded acceptance plan, **not executed**. The user approved the design/
example/handoff and requested a local design checkpoint. No implementation/delegation/
publication GO. [DESIGN.md](DESIGN.md) owns planned semantics; [HANDOFF.md](HANDOFF.md)
owns assurance. API spellings below remain illustrative, not as-built contracts.

## 1. Record the request while no worker exists

Create fresh owned A with pinned C under main: captured trusted addition source, named
inputs `left=4`, `right=7`, a retained composite-valued keep DAG, and an unrelated sentinel
branch/ref. The source uses the existing public child context/publication helpers. Use
finite cooperative caller-owned gates around calculation/publication as in Iteration 7;
gate paths are declared named inputs, not installed runtime fault hooks.

Save complete independent typed object closure/every packed byte for C/sentinel and refs.
Explicitly record Q:

```text
recorded = record_exchange_request(
    A, commit=C, binding_name="binding", inputs_name="inputs",
    intent_uri="urn:example:add-i64", ref="submission-1")
# recorded: base C, commit Cq, request Q, request_id qid, owned selection
```

Before any workspace/worker exists, fresh Python/CLI inspection verifies:

- Q is the existing ordinary request role, rooted in qid with exact intent/binding/inputs.
- Cq parents exactly `(C,)`; Cq tree equals C's tree plus `request-<qid> -> Q`.
- Explicit submission-1 and A-local request reservation both target Cq.
- Main/sentinel and all earlier bytes remain unchanged.
- No T, attempt ref, scratch allocation, computation, publication, outcome or cleanup.

Request existence is durable research history, not proof of dispatch. Do not attach a
fake failed/done status just because no worker starts. Importing Cq into an ordinary fresh
repository must preserve Q while creating no operational reservation/attempt or process.

## 2. Prepare pinned Q and retain the independent expectation

```text
spec = prepare_exchange(
    A, commit=Cq, request=Q, binding_name="binding", inputs_name="inputs",
    intent_uri="urn:example:add-i64", worker_ref="work", workspace=W)
handle = ExchangeHandle(W, spec)
save_exchange_handle(saved_handle, handle)
```

Preparation validates exact submission history/Q/selection and exports Cq's all-parent
closure, with no A write. Save expected Cq/Q/token separately from incoming packets.
A's main can advance independently to Cnew; neither preparation/start nor return adopts
Cq into it. Submission-1/request reservation stay at Cq, not a mutable latest execution.

An early bounded observation returns working/bootstrap without a selected T or packet.
Q is already inspectable in A/independent expectation; bootstrap is not "no request exists".

## 3. Explicit owner starts B; only T is new

A finite application supervisor starts/retains/reaps the installed fixed worker. Fresh
initiating/observing clients can exit; the sole process owner cannot be discarded.

```text
launch = start_exchange(handle)
```

Rename A offline for worker execution. The protocol supplies only W, not A's path.
B imports Cq under work, validates Q and publishes readiness. Public run_request then
atomically registers B-local Q reservation and fresh T, commits P and closes handles
before the existing executor launches captured source. No replacement Q is constructed.

Hold the computational child at its first cooperative gate. Fresh observation selects P:

- P parents `(Cq,)`, tree exactly Cq tree plus only `attempt-<aid> -> T`.
- Q ID, occurrence and all packed Q-related bytes exactly match A's recorded Q.
- T references Q, has its own fresh occurrence, and no final fields.
- Work/attempt publication refs point at P; B request reservation points at Cq.
- Lifecycle working, phase initial; no statement that recording P proves actual dispatch.

Repeat fresh observation into a different packet directory; same Q/T, no additional trial.
Receive P explicitly under trial-1-initial. A's existing Q reservation remains Cq; distinguish
it from B's refs, which were not copied. All earlier A refs/bytes stay unchanged.

## 4. Publication and completion retain the same request

Release arithmetic. Child calculates result DAG R rooted in 11, publishes U and waits at
its second gate. Observe/receive U under trial-1-publication:

- U parents `(P,)`, tree exactly P plus the associated publication.
- Q/T unchanged, T still has no final outcome; working/publication.
- R is provisional evidence, not final success or another request.

Release normal child exit; runner reaps, attempts cleanup, records F. Observe F:

- Ordered parents `(P,U)`; Q exact and unchanged; final description still identifies T.
- Done/completion only after successful full retrieval/validation.
- Success has zero exit/R; cleanup separate. Outer worker may still be exporting its
  synchronous output; process owner separately reaps it.

Remove original completion receipt after known worker reaping; observing recorded F still
works, with no finalization/retry. Copy only selected packet files, rename B offline, pass
independent expected to a fresh receiver and receive F under trial-1-final. Main remains
Cnew; submission-1 and A's request reservation remain Cq; earlier P/U refs remain unchanged.
Attempted reception of F under the existing P ref conflicts, not an automatic ref advance.

Independent breadth-first public typed-byte oracles compare C/Cq/P/U/F at A, B and packets,
including composite-only descendants/all parent history. Existing CLI agrees on Q/T/result,
parents and selected snapshots; CLI prefixes are not the completeness oracle.

## 5. Two distinct submissions and wrong-request rejection

Record Q2 for the **same pinned C/binding/inputs/intent**, under submission-2. Q2 differs in
occurrence/content ID; Cq2 differs. New W2/B2 creates fresh T2; result R can be identical.
Neither request is a cache hit or another observation of the other attempt. Preserve Q1/T1
history and refs exactly.

Negative story: take a complete, structurally valid P/U/F packet from Q2's matching job.
Copy Q1 job descriptor and rewrite receipt token/base claims to Q1 expected while keeping
Q2's valid history/bundle root and its own correct associations. Receive against Q1 expected
must reject **before A writes**. Validate the rejected candidate independently as a real
Q2 packet first, so this is not merely malformed JSON or missing dependencies. Also test
wrong Q with original receipt token, wrong Q-content under same occurrence spelling,
T referencing Q2 while tree exposes Q1, replaced Q tree binding, and missing Q.

Same-selection token checks remain, but exact pinned request/history checks provide the
new guarantee. Tokens are correlation, not authentication or protection against trusted
writers intentionally forging internally consistent expected history.

## 6. Never-started, launch failure and unknown attempts

Record Q3 under submission-3 and **never start it**. Fresh readers retain Q3/Cq3/ref and no
T/outcome. A failed later prepare (file/profile error) also leaves already-recorded Q intact.

Distinguish two launch failures:

- Outer worker spawn/setup failure after launch marker but before P: Q exists in A;
  no T invented; observation is bootstrap/working; same workspace cannot relaunch.
- Computational child spawn failure after committed P: T exists; local runner can record
  failure/cleanup F, and selected validated retrieval reports done with failure.

Use private finite worker barriers before computational spawn or after real child reaping:

- Loss after P before spawn preserves unknown T linked to caller Q; no retry.
- Child publishes/exits, worker lost after reaping before F: U remains working evidence.
- Loss after F/reaping before original receipt: explicitly retrieve F, same Q/T.
- Client exits normally after one observation while finite owner remains; next client
  observes from saved state without starting another computational process.

Run nonzero-after-U and cleanup-failure cases: failure evidence versus successful result,
separate cleanup and caller Q preserved. Do not kill a worker while its real child lives
for convenience; release cooperative gates before finally-owned worker reaping.

## 7. Atomic recording/registration and response-loss stories

- A request recording: conflicting/dangling/malformed explicit refs; occurrence collision
  retry/exhaustion; late consuming-commit/map-full after genuinely new Q/Cq puts. Fresh
  readers see entire old state and no new batch/ref after abort. Main stays unchanged.
- Actual recording process loss before A commit after new puts versus after successful
  commit before response: inspect submission ref/history, never automatically record Q again.
  Existing-ref repeat rejects without committing another occurrence.
- B run_request: wrong head/Cq/Q, absent/wrong selected tree entry, existing same/different/
  malformed reservation, attempt collision/ref/write/commit failure. No computational spawn
  before committed P; failed registration leaves imported Q/Cq and no partial T/ref batch.
- Pure transfer import creates no reservation or dispatch. Calling existing retry_step on
  an ordinary imported Q without reservation must retain its rejection behavior.
- Receive late new-A-put/ref/real map-full/consuming-commit and actual pre/postcommit loss:
  full-state batch absence versus complete publication, never a new computational attempt.
- Completed F exceeding real transfer limits remains recorded in B; no successful done
  packet response or fabricated request failure. Earlier real overflow regression remains.

Whole data-file equality preserves raw malformed refs; independently fresh typed readers
check every old/new object and relevant refs. Exclude validation-store/preexisting puts
from new-A-put evidence. Record substituted faults versus real processes/profile/storage.
No global single-dispatch proof, arbitrary owner-loss cleanup, security or power-loss claim.
