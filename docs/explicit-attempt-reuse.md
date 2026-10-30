# Explicit historical-attempt reuse

Status: informative, implemented example-local authoring over existing public APIs.

## Authority boundary

This page owns the convention of [explicit_reuse.py](../examples/explicit_reuse.py), not a
public cache API, native object kind or new execution role. [Caller requests](spec-next/caller-requests.md)
owns new Q publication; [asynchronous exchange](spec-next/asynchronous-execution.md) owns exact
historical packet inspection. [Transfer](spec-next/transfer.md) owns complete typed history/profile
validation, [Python API](spec-next/python-api.md) owns native transaction boundaries and
[local execution](spec-next/local-execution.md) owns the unchanged original T-to-Q relationship.

## Asking again versus executing again

The [two-step example](composed-recorded-steps.md) genuinely executes add13+29 -> R1(root42),
then double consumes R1 plus exact selected producer T1f and factor2 -> R2(root84). The reuse
operation deliberately asks again with a **new request Qr**, using an explicitly selected old
successful double attempt T2f/result R2. It creates no new attempt, child, B, external job,
transport token, outcome or cleanup record. Reuse is not another empirical observation.

The operation takes an immutable basis C, selected tree names/intent, old packet and an
**independently caller-owned expected Cq/Q selection**, plus explicit submission/result refs.
It calls public packet inspection itself: incoming `ReceivedObservation` or `RecordedRequest`
flags cannot supply authoring authority. That same validated successful final description
supplies exact old T2f/R2. P/U, missing/unknown/unreturnable F, malformed/wrong-Q histories and
failed F with evidence84 are not eligible. This example permits computational success with
recorded failed cleanup, preserving that historical disposition without remediation.

Before creating Qr it compares **intent URI, binding DAG ID and complete input DAG ID**.
Source, interpreter and timeout contribute through the binding; factor/type/declared fixture
inputs and producer occurrence witness contribute through inputs. Equal42/84 is not a substitute
for the selected witness. Request occurrence, containing commit, transport token and current
head are not matching dimensions. Another valid matching old successful attempt can be selected
explicitly; result equality never erases which attempt was chosen.

The selected old F must already be reachable through **any ordered parent** of C, not merely
first-parent history or an unrelated stored object. Public full-history export additionally
validates C's complete typed closure, including composite-only datum descendants, before new Q.
Existing transfer limits apply; this is not unbounded history/corrupt-store repair or performance
assurance. No private local/role/native codec is used.

## Separate Q and W publication

After prevalidation, existing public request recording creates the operation's own new Qr/Cqr
under atomic submission/request reservation refs. Its actual owned return supplies Qr fields;
the three dimensions are checked again. No arbitrary pending request description is accepted.

A **separate storage transaction** preserves Cqr's tree and adds only this ordinary DAG W:

| Binding | Node |
| --- | --- |
| `role` | literal STRING `example-explicit-reuse-v1` |
| `request` | sub-DAG reference to NEW Qr |
| `attempt` | sub-DAG reference to exact OLD final T2f |
| `result` | sub-DAG reference to actual OLD R2; also W root |

Tree entry `reuse-<new-q-occurrence>` names W. Cr has exactly `(Cqr,)` parents; the explicit
reuse-result ref is create-only. The owned response is allocated before W storage commit.
Submission/reservation refs remain at Cqr; existing heads/old records stay unchanged. Old T2f
still refers to its ORIGINAL Q2, not Qr. W is not a new local-success record or P/U/F packet.

Matching/eligibility rejection occurs before Qr. A later W ref/name/map/allocation/store-commit
failure can leave **Qr committed but pending satisfaction**, while the entire W/Cr/ref batch
rolls back. Response loss after W commit can leave complete W despite no acknowledgement.
There is no transaction spanning Q, W, files and service effects. The helper does not resume
arbitrary pending Q, automatically duplicate Q, submit fresh work, retry, repair or adopt a
new default. Existing submission/ref conflicts reject; this is not an idempotent whole-driver
or globally exclusive request-resolution/exactly-once guarantee.

## Finite offline reuse and explicit fresh control

After receiving successful old F through the unchanged public adapter, supply an independent
exchange expected file (for example the caller-owned `double-step/saved/expected.json`):

```sh
python examples/explicit_reuse.py A.dml <retained-C> \
  double-binding double-inputs urn:example:double \
  double-step/saved/expected.json copied-old-F-packet reuse-submission reused-double
```

This is one finite nonexecuting action. It imports no HTTP, Floci or Docker runtime module;
service/input/B/interpreter/source availability is unnecessary. Its printed mode is `reuse`,
not a fabricated fresh execution completion. Ordinary inspection navigates W/Qr/T2f/Q2/I2/R2:

```sh
dml --json --repo A.dml snapshot --ref reused-double
dml --json --repo A.dml walk <association-dag> --limit 200
dml --json --repo A.dml log --ref reused-double --limit 100
```

For a deliberate fresh control, separately record Qfresh on printed Cr using existing
[composition modes](composed-recorded-steps.md#finite-runnable-modes), selecting the SAME
binding/full inputs. Then explicitly stage/submit/observe/receive through the unchanged adapter.
Fresh B imports W/Qr/old T/history inertly and creates only Tfresh for Qfresh. Qr/Qfresh/Q2 and
T2/Tfresh remain distinct; Rfresh may equal R2. W stays pinned to old T2f; no default adoption
or automatic reuse/fallback occurs. Fixture-only known-stopped service resume/reset of declared
finite gate keys is test policy, not a DML recovery mechanism.

## Evidence and limits

[Native selection tests](../tests/python/test_explicit_reuse.py),
[full matching/failure gates](../tests/python/test_explicit_reuse_selection.py),
[W rollback/authoring-only response loss](../tests/python/test_explicit_reuse_atomicity.py) and
[finite offline modes](../tests/python/test_explicit_reuse_modes.py) start no Docker. The explicit
[installed three-job fixture](../tests/floci/README.md#explicit-attempt-reuse-gate) executes original
add/double, stops/archives after known writer disposition, runs fresh installed service-offline
reuse/new Q+W/no job, then explicitly resumes the proven-stopped endpoint for fresh double.
Actual persisted external job census, full native bytes/all ordered parents and available gated B
oracles are distinct from mocked submit counts or bounded CLI. Normal final B is ephemeral, not
an archived final-B promise.

The example stays in the unchanged root-source coverage gate. Host statements are not all Python
branches or installed-job/memory/platform/security assurance. Existing native/binding/CLI memory
thresholds/exclusions remain unchanged. Content IDs/history do not authenticate writers, prove
full environmental capture, scientific validity or external-resource availability. Original
Floci-specific unsigned HTTP/socket authority/job-security/cleanup/ephemeral-B/profile limits
remain in its [owning contract](spec-next/floci-execution.md). No automatic discovery/default
cache policy/facets/masks/cross-implementation equivalence/registry/scheduler/resources/cloud or
new native entity is introduced. Actual commands, failures, counts, provenance and independent
review belong to [Iteration13 RESULTS](../../dml-design/iterations/13-explicit-attempt-reuse/RESULTS.md)
and [REVIEW](../../dml-design/iterations/13-explicit-attempt-reuse/REVIEW.md).
