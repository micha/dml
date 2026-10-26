# Independent feasibility review

## Authority boundary and verdict

**Verdict: needs corrections; the evidence supports a narrow next prototype, not
an operational resource manager.** This review owns its experiments and assessment
only. The [design discussion](../../discussion.md) remains exploratory; no user
policy, schema, implementation, or legal-erasure guarantee is approved.

The four specialist reports are substantially honest about simulation versus real
execution. I reproduced their numerical results and the important local CLI
counterexamples. The original copied lab layout exposed a path-length failure,
now fixed and disclosed by integration. Retention invariants still omit identity
and post-withdrawal publication cases, and an independently executed saved-plan
counterexample extends the destruction race beyond three modeled atomic operations.

The completed [integration report](../integration/report.md) and marker arrived
within the bounded wait (about three minutes). Its four successful short-layout
full runs and retained initial failure are inspectable in
[the run index](../integration/run-index.json). Its evidence classes and corrected
source/count audit agree with my checks. The joined scenario is genuine local
output-to-model glue, not fixture replay, but adoption, root exports and fencing
remain manually supplied simulations. My verdict concerns the remaining coverage
and admission-policy gaps, not a claim that its corrected runner is still failing.

## Reproduction and evidence accounting

Run from `/work/repos/micha/dml-design`:

```sh
python3 -B feasibility/review/rerun.py
python3 -B feasibility/review/adversarial_checks.py
python3 -B feasibility/review/verify_sources.py
python3 -B feasibility/review/rerun_integration.py
```

Versions independently checked: Python **3.13.15**, OpenTofu **1.13.2**,
Linux amd64, local provider **2.5.3** with the first-wave readonly lock.
The shared executable SHA-256 is
`949061cbb3c3d4558928ca9a459a5052b8c5e5545d17656f33316d2e3bc335f2`;
its release ZIP matches the recorded
`723bebb0df8411daff1e5fc3862e28ff5581fe5634087f4c29a9aa41d78208b5`.
I did not install or modify shared tools.

| Evidence | Independent result | What it establishes |
| --- | --- | --- |
| History suite | 24 tests, including its 11-scenario fixture | Executed Python model; no DML primitive/API compatibility proof. |
| Retention suite | 20 tests; matching deterministic trace checksum | Executed simulation, six operation permutations and 512 graph/root combinations. |
| Local lab | Seven probes, 86 CLI commands, passing after disclosed temporary-path adaptation | Actual import/output/state/address/provider/provisioner mechanics. |
| Adversarial suite | Eight cases: six CLI, one accounting/drift sketch, one source assertion | Not eight cloud/provider tests. |
| Additional review checks | Five cases; three model checks and two CLI interleavings, 12 CLI calls | New counterexamples below, not concurrency stress tests. |
| Integration scenario | Three requests, two actual arithmetic subprocesses, one result root; six CLI calls | Actual local glue plus explicitly simulated adoption and retention. |
| AWS provider source | Three independently downloaded, checksum-matched files | Pinned-source verification only; zero cloud operations. |

The three original lab result files also each contain seven probes and 86 commands;
that claim is **inspected**, not an independent rerun of all three historical runs.
The retention trace reproduced SHA-256
`7c37e3e70b1b467206060b5400728717d78ed6594e59bb1c602412e777bb43dd`.
Reports, not raw agent sessions, were the entry points.

Detailed evidence is in ignored [runtime/](runtime/), indexed by
[latest rerun](runtime/latest-rerun.json),
[additional checks](runtime/latest-adversarial.json),
[source verification](runtime/latest-sources.json), and
[integration reproduction](runtime/latest-integration.json).
The reproducible scripts preserve exact argv, input checksums, return codes and
observations. No evidence is inferred from agent completion markers alone.

## Ranked defects and independent counterexamples

### 1. High: a queued plan outlives a retention/configuration decision

**Actual CLI.** I created a `terraform_data` resource whose sandbox-only
provisioners create/delete a synthetic compute marker, saved `plan -destroy`, then
changed its HCL input and added `prevent_destroy = true`. Applying the already
saved plan returned zero, removed the marker, and left state with zero resources.
No intervening state write occurred. This does not say OpenTofu accepts every
state-stale plan; it establishes that newer **unapplied configuration or research
retention** is not a state-serial change.

The study's publication/reservation/destruction model therefore cannot substitute
for admission control at the actual apply boundary. A candidate correction binds
approved plan digest, configuration revision, root/membership revision, physical
victim identities and a live fencing token. Every deployment mechanism must
participate, or the guarantee is explicitly limited to cooperative deployments.
That is additional coordination and may sacrifice deployment availability.

### 2. High: copied laboratory execution is path-sensitive

**Reproduced failure and corrected review harness.** Two untouched copied lab
runs failed during provider schema negotiation. Trace output identified
`listen unix .../tmp/plugin1147945797: bind: invalid argument`, not a provider
version or dependency mismatch. The nested temporary path exceeded the Unix socket
address limit. Passing shorter parent environment variables cannot fix it because
`probe.py` overwrites `TMPDIR` itself.

My runner discloses exactly one adaptation in its **review-owned copy**:
`TMPDIR=str(RUN / 'tmp')` becomes `TMPDIR=str(HERE / 't')`. HCL, provider lock,
version and assertions are unchanged; all 86 commands then pass. The original
failure is preserved in [plugin diagnosis](runtime/plugin-diagnosis.log).
A possible correction is a bounded, validated sandbox-temp override or a shorter
runtime layout, accompanied by a clean full-suite rerun. Integration has implemented
the latter in its own files and retained the original failure; I inspected its
passing reruns. Standalone lab copies still need path-aware handling.

### 3. Medium: withdrawal followed by new adoption/reference publication

**Executed simulation.** In the retention model, excise unreferenced `compute`,
then add `new-result` with `deps={'compute'}` and publish it before disposal.
Publication succeeds, withdrawn compute re-enters `retained()`, ordinary GC no
longer selects it, the result is unavailable, and `assert_safety()` still passes.
The pre-excision dependency check does not govern later dependencies.

This is a missing lifecycle-policy case, not necessarily an approved-design bug.
Possible policies reject new operational dependencies on withdrawn identities,
allow provenance-only references, or require explicit cancellation/replacement of
the retirement. Test publication before deletion, during partial deletion, and
after confirmed absence separately.

### 4. Medium: identity validation can erase ownership boundaries

**Executed simulation.** Calling `Manager.add('bucket', 'external')` and then
`add('bucket', 'provisioned')` overwrites the resource descriptor. GC subsequently
deletes that identity and the current invariants pass. This uses a public fixture
API, not direct dictionary tampering. It does not demonstrate deletion of a real
external bucket: both files are review-created synthetic objects.

Before treating invariants as admission-policy evidence, reject duplicate physical
identities, ownership changes, and alias rebinding, and give replacement a distinct
identity. Resource names/addresses cannot establish artifact-version identity.
The history allocator likewise assumes unique issuers; content hashing does not
validate occurrence uniqueness across otherwise different records.

### 5. Medium: root export and observation coupling remain manual

**Actual CLI interleaving.** Read output for binding A, replace the resource, then
pull state B. Lineage remains identical, serial advances from 1 to 2, and the
identities differ. Independently fetching outputs and state cannot establish one
atomic deployment observation. Extract manifest plus lineage/serial from one state
snapshot, or reject mismatched receipts; provider-side drift still remains possible.

**Inspected integration limitation.** The integration scenario explicitly exports
synthetic retention roots into another model. It later drops those model heads
while the history model's real head remains rooted and its result remains
reachable. Thus its successful disposal checks demonstrate the supplied export
policy, not extraction/completeness of full-history resource roots. Require a
validated root-export mapping before making an end-to-end GC claim.

## Claims that survived scrutiny

The actual lab reproduces unsupported `local_file` import followed by destructive
creation, null imported surrogate outputs, declarative import plus update, no-op
configuration restoration with state versus creation without state, stable
addresses under key reordering versus delete/create on renaming, required provider
alias retention, and disappearance of removed destroy provisioners. Built-in
`terraform_data` import remains a state-only surrogate, not external-object adoption.

Sensitive output values appear in state and `output -json`; changing the output to
a tombstone leaves the synthetic plaintext in backups/copies/logs. Dictionary
recovery of a low-entropy hash works: independently counted **eight guesses** within
a 100-candidate domain, agreeing with integration's correction. These establish
disclosure/erasure failures,
not compliance assurance, disk-page wiping, or global replica erasure.

Context7 returned **Monthly quota exceeded**. I used primary source instead,
independently verifying AWS provider **v6.70.0**, commit
`5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f`, against the
[recorded manifest](../adversarial/sources.json). In `object.go`,
`resourceObjectRead` uses HEAD without version selection and does not recover body
bytes; `resourceObjectUpdate` dispatches metadata changes through upload; absent
source/content/base64 selects an empty reader. Computed-only `version_id`,
bucket/key import, slash cleaning, and `resourceObjectDelete`'s all-version branch
are present. `deleteAllObjectVersions` filters exact key equality and deletes its
versions and markers—not every key sharing the prefix. These are strong
**source-backed conditional hazards**, not executed S3 outcomes. Some numeric line
anchors in the source notes are stale; use function/schema names.

## Safety, completeness and next experiment

My reruns allocate fresh review-owned roots, copy reviewed inputs, disable Python
bytecode writes outside them, strip credential/user CLI environments, and use only
local/built-in providers. An initial extra-check run failed because Python's default
PATH excluded Nix's `rm`; its log remains, and the successful runner carries only
allowlisted inherited PATH rather than the deployment environment. No DML checkout
mutations, credentials, cloud APIs,
Docker connections, or existing external artifacts were used. Source downloads
are bounded public GitHub reads.

The original adversarial script recursively removes an existing fixed
`runtime/sandbox/<case>` directory, and retention tests reuse fixed runtime paths.
They contain only synthetic fixtures in observed runs, but do not intrinsically
guarantee **fresh-only** mutation. Copying them into a new root makes my/integration
reruns safe; converting their standalone entrypoints to fresh allocation would
preserve evidence and tighten the stated safety contract.

The six race permutations exhaust only three modeled atomic operations, including
invalid destroy-before-reserve schedules. The 512 cases cover eight fixed-order
three-node graphs and two repositories' root subsets, not distributed membership,
crashes, stale queued applies, leases, partial effects, or hostile publishers.
Head/export aliases retain correctly in my additional check. Global census
completeness, declared dependency completeness, trusted lifecycle writers and
cooperative fences remain assumptions; the reports generally acknowledge them.

The smallest useful next prototype is a file-backed journal with two publisher
processes and one deleter, crash injection around reservation/apply/unlink/receipt,
plus saved-plan admission tests and validated identity/root exports. Keep it local;
use an import-capable sandbox-file adapter before extrapolating adoption. Advance
only when partial deletion, stale plans, duplicate identities, unknown outcomes,
and withdrawn-resource publication are either rejected or explicitly quarantined.
Legal erasure, shared-consumer override authority and closure identity projections
still require user decisions, not automatic conclusions from passing tests.
