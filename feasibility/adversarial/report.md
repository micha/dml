# Adversarial feasibility review

## Verdict and authority boundary

**Conditionally feasible as a journal plus constrained, regenerable IaC view;
not established for arbitrary HCL or generic immutable-artifact adoption.** The
strongest counterexample is AWS `s3_object`: imported bytes are not recovered into
configuration, and a later metadata change takes the upload path, whose body is
empty when no source/content is configured. Versioned destruction can delete
**all versions of that key**, not just the version recorded by an attempt.
These are pinned-source conclusions; no cloud behavior was executed.

This is research, not approved DML design or specification change. Existing draft
schemas are not authority for the emerging occurrence/resource model. No changes
were made to the implementation checkout or other workers' directories.

## Executed evidence and reproduction

```bash
python3 feasibility/adversarial/fetch_evidence.py \
  --aws-commit 5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f --aws-release v6.70.0
python3 feasibility/adversarial/experiments.py
```

Executed with Python **3.13.15**, OpenTofu **1.13.2**, built-in `terraform_data` only.
The full suite passed after correcting an invalid multiline module fixture.
Six cases executed OpenTofu; one simulated research accounting plus local drift;
one asserted provider-source properties without executing the provider.
[Results](runtime/results.json), [scripts](experiments.py), and
[primary-source trace](source-notes.md) give exact commands, hashes, observations,
and limitations. Context7 was quota-blocked; official sources were fetched directly.
All state, copied synthetic values, and raw logs are ignored under `runtime/`.

## Ranked findings

### 1. Critical: adoption is not bytes-preserving management

**Documentation/source, cloud unexecuted.** AWS provider v6.70.0 requires bucket
and key, but not source/content. Import reads HEAD attributes, not body bytes.
`resourceObjectUpdate` calls upload for metadata/cache-control/content-type changes;
without body configuration the upload selects zero bytes. A matching unchanged
import may no-op, so this is not a claim that import itself always destroys data.

**Possible fix:** separate immutable-object retention/deletion from ordinary
mutable-object management, using a purpose-built adapter or provider with
validated narrow operations. Alternatively retain and verify source bytes and
explicitly accept update semantics. `ignore_changes` can suppress selected diffs
but does not prevent empty recreation after disappearance or address replacement.
**User judgment:** how much provider-specific admission policy is acceptable?

### 2. Critical: provider identity and destruction exceed artifact identity

**Source/documentation, cloud unexecuted.** `version_id` is computed, not an input;
import identifies bucket/key and refresh reads the current version. When state
has a version ID, destruction calls `deleteAllObjectVersions`, including matching
delete markers. Two attempts using different versions of one key therefore do
not obtain independent lifecycle ownership. Slash normalization also collapses
some distinct URI keys. Object locks/permissions can cause partial failure.

**Possible fix:** unique, canonical keys per artifact plus recorded digest/version;
or a version-specific lifecycle adapter. Reject conflicting ownership and retain
retryable deletion obligations. **User judgment:** manage whole keys or versions?

### 3. Critical: tombstones and sensitivity do not establish physical erasure

**Executed OpenTofu/local hashing.** A synthetic sensitive output appeared in
state and `tofu output -json`. After replacing it with a tombstone, current state
was clean, but plaintext survived in a state backup, two copies, and a raw log.
A retained SHA-256 digest of the low-entropy synthetic value was recovered from
100 candidate guesses. Rewriting a hash-addressed child changed its parent's hash.

**Possible fix:** explicit same-ID exceptional tombstone resolution, non-sensitive
metadata, output allowlists, deletion tracking for copies/backends/logs, and
revocation boundaries. Encryption reduces exposure but introduces key/copy
management. The existing draft has same-ID tombstones; neither that draft nor this
test proves storage-page wiping or distributed erasure. **User judgment:** retained
metadata, lawful scope, permitted replicas, and achievable assurance levels.

### 4. High: regenerable configuration is not regenerated operational state

**Executed OpenTofu.** Identical HCL reapplied after deleting sandbox state created
a new `terraform_data` ID. The old successful observation remained unchanged.
This tests identity loss, not remote import recovery. Source storage alone does
not retain backend lineage, address-to-object adoption, provider bindings, or
pending actions.

**Possible fix:** DML remains obligation authority; preserve desired HCL plus
inputs, stable declaration identities, import locators and adoption/disposal
receipts. Back up operational state or deliberately rebuild it with verified
imports. Deployment remains user/agent-selected. **User judgment:** durable journal
fields versus state-backup/recovery responsibilities.

### 5. High: exact HCL storage is not dependency capture

**Executed plus documentation.** Copying identical HCL containing
`file("${path.module}/payload.txt")` without the payload changed a successful apply
into a plan error. OpenTofu's lock file captures provider dependencies, not remote
module selections. Mutable Git module refs, external files, tfvars/environment
inputs, and tool dependencies can change behavior without changing stored HCL.

**Possible fix:** bundle module trees/files; pin remote revisions; retain lock and
engine versions and non-secret effective inputs; explicitly document unresolved
external inputs. This belongs largely to project closure assertions, not a DML
claim of complete capture. **User judgment:** replay availability versus storage cost.

### 6. High: shared-root composition can alter installed closures

**Executed plus documentation.** Two local module instances wrote the same
`path.module` path; the second replaced `alpha` with `beta`. Provider aliases need
explicit mapping, provider configurations must survive until dependent deletion,
and one provider source version must satisfy all modules in a root. Independently
pinned incompatible closures cannot simply coexist in that root.

**Possible fix:** read-only module sources, per-instance work directories, stable
namespaces, explicit provider contracts, and root partitioning on incompatible
versions. **User judgment:** one shared manager versus multiple isolated stacks.

### 7. High: arbitrary HCL contains effects absent from retention accounting

**Executed OpenTofu.** A creation provisioner wrote a sandbox compute marker;
removing its entire resource declaration destroyed its state but did not execute
the removed destroy-time provisioner. The file survived. Arbitrary shell effects
cannot be inferred from HCL resource outputs, so resource-manifest completeness
is an assertion, not a language guarantee.

**Possible fix:** prohibit or explicitly register provisioner-owned effects;
retain cleanup programs/provider configurations until obligations finish; use
adapter cleanup receipts. This trades expressiveness for inspectable lifecycle
coverage. **User judgment:** accept a constrained authoring contract or opaque effects.

### 8. High: dependency-safe replacement is not historical identity retention

**Executed plus source.** `prevent_destroy` blocked explicit destruction while its
declaration existed; removing that declaration produced a valid plan to destroy
one object. AWS bucket/key inputs are replacement-triggering. Configuration
namespacing/address changes can therefore silently convert retained objects into
old instances scheduled for destruction. `create_before_destroy` only changes
ordering, not the obligation to retain the original.

**Possible fix:** stable addresses/move records and an independent plan gate
checking retained physical identities against deletes/replacements. **User
judgment:** retention overrides and explicit authorization for migrations.

### 9. Medium: successful recorded outputs are observations, not current truth

**Executed local drift; architecture inference.** Overwriting a synthetic file
left its URI unchanged and invalidated the recorded digest. An independently
applied stack can similarly change live bindings without rewriting historical
DML success. Even a freshly checked digest does not guarantee continued retention.

**Possible fix:** separately identify configuration revision, backend/lineage,
applied state and observation time/version/digest. Add new drift/remediation
observations instead of changing old outcomes. **User judgment:** when execution or
reuse requires revalidation, without restricting deployment-tool freedom.

### 10. Medium: occurrence counts do not establish empirical independence

**Simulation.** Three requests, including intentional reuse, referenced two
attempts with one content-identical result. Counting requests or unique result
hashes gave the wrong execution count. Two fresh attempts can still share model
state, seed, retrieval cache, or hidden dependencies. Publication gaps also leave
unknown attempts; a submission retry is not proof of one external execution.

**Possible fix:** record request/attempt/action distinctly, preserve reused attempt
identity and independence rationale, and represent unknown outcomes. **User
judgment:** methodology and acceptable independence claims remain research policy,
not guarantees certified by DML.

## Worked lifecycle A: non-deterministic agent comparison

1. Installation description records agent implementation, adapter, HCL, pinned
   dependencies and non-secret configuration. Install provisions compute; an
   observed binding produces closure C1. Partial deployment does not imply readiness.
2. Request Q1 binds C1 and inputs; attempt A1 is recorded before submission. The
   agent publishes progress and result R. Recovery after a crash checks the job
   ID; it can still report unknown, rather than silently retrying as A1.
3. Q2 intentionally reuses A1 for inexpensive downstream analysis. It contributes
   no new empirical trial. Q3 freshly executes A2; identical R does not merge A2
   into A1. An independent-model comparison avoids substituting A1 and records
   shared retrieval/environment limitations.
4. Result artifacts are registered for narrow adoption, not uploaded as empty
   `s3_object` placeholders. Excising compute retires that operational binding;
   C1 remains historical, but is unavailable for fresh runs. A replacement install
   creates a newly bound closure, not an assertion that the old compute still exists.

## Worked lifecycle B: dataset and derived artifacts

1. An externally managed bucket remains external. Research reads dataset version
   V1/digest H1 and installs a transform closure with separately managed compute.
2. An attempt creates derived artifact at unique key K1, recording version/digest,
   publication status and pending adoption. A crash between creation and publication
   can still leak an unknown object: the journal is not proven strict write-ahead.
3. Adoption registers K1 without taking ownership of the bucket or unrelated
   versions. A second analysis may intentionally reuse K1; a validation attempt
   actually re-runs from V1 rather than treating reuse as another measurement.
4. Retirement removes compute while keeping V1 references, K1 and methodology.
   If V1 is withdrawn, authoritative excision overrides retention and evaluates
   derived K1, copied state, logs and other consumers. A tombstone is withdrawal
   evidence; externally owned V1 deletion and replica/backups remain separate
   obligations. No compliance guarantee follows from a successful IaC destroy.

## Limitations and next experiment

No cloud execution, actual DML integration, remote backend recovery, concurrent
deployments or adversarial replica tests were performed. Prioritize a separately
authorized disposable S3 test: import nonempty/versioned objects, no-op apply,
metadata drift, deletion/replacement, and version-scoped retention checks. Without
cloud authorization, next test a fake provider exposing HEAD versus body behavior
and a plan-policy gate against retained identity deletion. These alternatives are
proposals for falsification, not approved implementation.
