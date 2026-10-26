# Integration feasibility: executable seams, not production guarantees

## Authority boundary and verdict

This report owns the integration experiments and synthesis, not the study's final
verdict or any DML specification. Agreements, tentative design directions and
proposed fixes retain the distinctions in [discussion.md](../../discussion.md).
No implementation-checkout changes, deployments outside synthetic local resources,
commits, cloud calls or Docker connections were made.

**Go for a constrained local obligation-journal prototype; no-go for unrestricted
HCL, generic immutable-artifact adoption, distributed deletion safety or an erasure
guarantee.** Ordinary history DAGs and stable IaC configuration can cooperate.
They do not supply the necessary ownership, readiness, operational-state,
publication-fencing or copy-removal guarantees by themselves.

The strongest joined counterexample is not a DAG failure: a correctly retained
artifact can still be overwritten, replaced or deleted by the materialized
manager. The local provider rejects import, then a subsequent create overwrites
execution-created bytes. Losing state recreates identities despite identical HCL.
Removing declarations bypasses `prevent_destroy` and removes destroy hooks. A
repository publishing after approval can invalidate destruction safety even if
OpenTofu's own plan/state were internally consistent.

## Independent reproduction and discrepancies

Inputs were the completed reports, summaries, code, fixtures and condensed evidence
from [history](../history/report.md), [retention](../retention/report.md),
[OpenTofu](../opentofu/report.md) and [adversarial](../adversarial/report.md).
History delivered within the bounded five-minute wait. Agent sessions were not
used as evidence.

After reviewing effects and paths, I copied the scripts **byte-for-byte** into a
fresh integration-owned layout. This relocates their `__file__`-relative outputs,
not their behavior or dependencies. The lab's HCL module and local-provider lock
remain unchanged; the adversarial suite receives its same pinned public sources
and a private metadata file pointing at the existing lab executable. No provisioning
script or global installation was run. [Reviewed checksums](reviewed-sources.json)
now cause the runner to reject changed first-wave code before execution.

From `/work/repos/micha/dml-design`:

```sh
./feasibility/integration/run-all --refresh-sources
./feasibility/integration/run-all --models-only
./feasibility/integration/run-all
```

The first full run failed, rather than silently skipping the local provider. Trace
[diagnosis](runtime/run-746l_y65/plugin-diagnosis.stderr) identifies a 124-byte
Unix socket pathname beneath the relocated `TMPDIR`: `listen unix ... bind:
invalid argument`. Short integration sandbox slots and the directory name `o`
fixed this without changing provider versions or first-wave scripts. Four
subsequent short-layout full runs passed; the final run also includes the added
source/count audit. A separate model-only run passed the models and explicitly
reported skipped lab/integration cases. All statuses, including the first failure,
remain in [run-index.json](run-index.json).

Environment: **Python 3.13.15; OpenTofu 1.13.2, linux_amd64; local provider 2.5.3**.
The executable SHA-256 is
`949061cbb3c3d4558928ca9a459a5052b8c5e5545d17656f33316d2e3bc335f2`;
the lab's `ready.json` originally describes the release ZIP's different checksum,
not the executable. [test-results.json](test-results.json) preserves exact commands,
versions, reviewed-input hashes and durable condensed observations.

| Independent result | Observed | Evidence class |
| --- | --- | --- |
| History | 24 tests; 11-scenario fixture byte-identical | Executed model, simulated adapter |
| Retention | 20 tests; 512 graph/root cases; six interleavings | Executed finite simulation |
| Retention trace | Same SHA-256 `7c37e3e70b1b467206060b5400728717d78ed6594e59bb1c602412e777bb43dd` | Exact replay |
| OpenTofu lab | Seven probes, 86 CLI invocations, including expected failures | Real local CLI/providers |
| Adversarial | Six CLI cases, one accounting/drift case, one source-assertion case | Mixed, separately labelled |
| Joined scenario | Three requests, two arithmetic attempts, one result root; six CLI invocations | Real local effects plus model seams |

Two evidence-precision corrections matter. The adversarial field
`low_entropy_hash_recovered_in_candidates: 100` describes a **100-candidate search
domain**, not 100 evaluated hashes: its generator finds candidate `0007` on the
**eighth guess**. [audit.py](audit.py) independently measures that stopping point.
The source notes' `version_id` schema citation, 270–273, is stale for their pinned
source; the actual lines are 246–249. Function-based claims still reproduce.
No other reported counts or lab actions disagreed in the successful reruns.

The runner retains at most eight fresh run directories, never prunes existing
resources, uses bounded subprocess/network calls, and offers explicit model-only
mode. It sanitizes deployment environments; all state, copied tools' metadata,
provider downloads, synthetic content and raw logs remain ignored beneath
`integration/runtime/`. A timeout can leave synthetic resources there for
inspection; it does not trigger destructive retry/cleanup of an existing stack.

## Executable joined lifecycle

[scenario.py](scenario.py) installs the unchanged lab module using actual
OpenTofu, creating a local descriptor file and a `terraform_data` binding surrogate.
It checks the exported filename, ID and digest before feeding actual outputs into
[the history model](../history/model.py)'s installation/bound-closure operation.
This is real output-to-model integration, **not provisioned compute capacity**.

Two bounded local Python arithmetic subprocesses genuinely produce `11`. Their
requests and attempts remain distinct while the result DAG deduplicates. Between
them, another request records reuse of the first attempt. Fresh execution does not
change the selected attempt. The installation description records the execution
code digest and HCL; the binding projection remains an illustrative convention,
not validated closure completeness.

The scenario then exports an explicit resource mapping into
[the retention model](../retention/model.py). It creates simulated external bucket,
cleanup identity and pending-adoption records for an execution result. Repository A
retains compute and result through an ancestor despite an empty current snapshot;
repository B independently retains both. This seam is deliberately a small,
explicit export, not an adapter pretending to infer retention from arbitrary DAGs.

Both modeled consumers authorize compute excision. After a model reservation, an
actual OpenTofu plan deletes exactly the module's file and binding surrogate;
apply confirms the descriptor absent. A new history observation records that
outcome. The scalar result remains inspectable and selected reuse remains possible,
while the modeled compute becomes unavailable. These steps demonstrate sequential
coordination only, not an atomic authorization/deployment transaction.

Dropping A's root does not release B's result. Dropping B's root still leaves the
pending adoption/cleanup obligation protecting target and cleaner. Reconciliation
registers simulated state, records one simulated disposal failure and finally
confirms simulated absence. A controlled local result copy is then actually
unlinked; the cleanup identity becomes collectible. The external-bucket stand-in
survives. Historical scalar `11` remains in the DAG: this is resource cleanup,
**not sensitive-history erasure**.

Final detailed evidence is [scenario.json](runtime/4/cross/scenario.json).
Adoption/state registration, shared-repository fences and external disposal remain
explicit simulations; only installation, arithmetic, descriptor destruction and
controlled-copy deletion are real local operations.

## Ranked synthesis and proposed remedies

The machine-readable [issue register](issues.json) separates falsified general
claims, engineering gaps, user policy choices and untested hypotheses. The
counterexamples reject tempting simplifications, not the already-qualified user
agreements.

1. **P0 — Adoption and ownership scope (I01).** An adoption obligation is not an
   import receipt; a receipt is not a bytes-preservation guarantee. The lab's
   built-in import exposes an ID with a null configured value, and declarative
   import includes an update. Provider identity must match lifecycle ownership.
   Use provider-specific admission and retained-identity plan gates; consider
   immutable unique names or narrow version-specific adapters. The tradeoff is
   less provider generality and additional metadata/source capture.
2. **P0 — Publication versus destruction (I02/I07).** Approval/revalidation has a
   check/delete race. Fences work only for cooperative in-memory publishers here.
   A durable reservation must enlist repository/export/adoption publishers and
   survive lost acknowledgements, process death and partial deletion. Unknown
   membership blocks destruction. This sacrifices availability under partitions;
   an OpenTofu state lock does not coordinate separate research publishers.
3. **P0 — Arbitrary HCL and composition (I03/I09).** State-address isolation is not
   physical-path isolation: module instances overwrite a shared `path.module`
   file. HCL also embeds executable effects absent from output manifests.
   Faithful text storage omits required files, module revisions and effective
   inputs. Restrict capabilities, bundle dependencies, provide per-instance
   workdirs and retain cleanup programs/provider aliases. Provider compatibility
   may require multiple stacks, not one universally composable shared root.
4. **P0 — Configuration versus state (I04/I05).** Stable declarations regenerate
   safely with retained state; they do not recreate backend lineage, adoption
   mappings or provider-private state. Closure readiness needs required-field
   validation and a reconciled configuration/state receipt, not merely an output
   ID. Preserve stable declaration keys independently of resolved bindings.
   Choosing equality fields and acknowledgement freshness remains a user/domain
   policy question, not a property proven by the projection tests.
5. **P0 — Retention and dependencies (I06).** Full ancestry, all heads and aliases
   matter. Distinguish provenance, operational, containment and cleanup edges.
   Compute retirement can preserve result reuse; encryption-key retirement can
   make the same cached artifact unusable. IaC destruction ordering does not
   preserve historical identities through replacement. Shared-consumer excision
   authority and permitted cascades need explicit policy.
6. **P0 — Erasure (I08).** Real CLI tests leave synthetic sensitive plaintext in
   four artifacts after current-state tombstoning: a backup, two copies and a log.
   Sensitivity labels and digests are not removal controls. Inventory copies,
   redact exported manifests/logs and distinguish retirement from erasure.
   Same-ID exceptional tombstone resolution is not disproved by an ordinary
   hash-parent rewrite, but page wiping, backup removal and global revocation are
   untested. Residual metadata and achievable assurance are user decisions.
7. **P1 — History/accounting (I10).** Ordinary DAG conventions represent the tested
   distinctions, but occurrence allocation, transactional publication and conflict
   validation need engineering. Hashes cannot count trials or certify independence.
   Explicit unknown outcomes and reported external execution IDs remain essential;
   idempotent mock submission does not prove exactly-once execution.

### AWS findings: source only

Context7 returned “Monthly quota exceeded”; no documentation CLI was installed.
Three pinned primary files were independently downloaded twice and matched the
first-wave hashes at AWS provider **v6.70.0**, commit
`5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f`. Their
[trace and official links](../adversarial/source-notes.md) preserve the sources.

`resourceObjectUpdate` routes metadata changes through upload; absent configured
body selects an empty reader. `resourceObjectDelete` with a state version calls
`deleteAllObjectVersions`, which enumerates versions and delete markers and filters
for the **exact key**, not every prefixed object. `version_id` is computed, not a
version-selection input. These are reproduced **source findings**, not cloud-tested
empty uploads or successful deletion of all versions. Permission/object-lock
failures can interrupt deletion. An unchanged imported configuration may no-op;
import itself is not shown to empty an object.

## Smallest next prototype and gates

Build a file-backed obligation journal with two local publisher processes and an
import-capable sandbox-file lifecycle adapter. Use immutable synthetic files, stable
addresses, explicit binding readiness and an independent plan gate. Kill the
driver/deleter at reservation, import, external effect, acknowledgement and journal
publication boundaries; test non-idempotent execution and partial deletion.

**Go gates:** mismatched adoption cannot overwrite bytes; lost state cannot silently
recreate retained identities; deletion-in-flight survives restart and blocks new
roots; cleanup capability outlives research-root removal; compute retirement keeps
retained results available; incomplete bindings and unknown outcomes fail closed.

**No-go gates:** unregistered effects, unrestricted destructive plans, unchecked
provider ownership scope, and claims of cloud/distributed/erasure assurance based
on these mocks. Actual DML C/LMDB integration, AWS behavior, remote backends and
secure replica/page removal require separate experiments and authorization. No
schema, implementation or policy decision is approved by this recommendation.
