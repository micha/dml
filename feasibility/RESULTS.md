# Feasibility results

## Verdict and authority boundary

**The design is promising enough for a narrow local prototype, but not yet safe
for automatic management or destruction of real research resources.** Six Pi
specialists investigated the design, integrated experiments, and independently
challenged both the conclusions and their evidence. The coordinator reran the full
integrated suite successfully after review.

This report summarizes feasibility evidence, not an approved specification. Fixes,
policy alternatives, and the next prototype below are recommendations. DML's
implementation checkout and its draft specifications remain unchanged.

## What was actually tested

| Work | Result | Evidence boundary |
|---|---|---|
| Computational history | 24 tests; 11 reproducible scenarios | Python ordinary-DAG model, not native DML |
| Retention and disposal | 20 tests; 512 bounded graph/root cases; six interleavings | Finite simulation, not distributed correctness |
| OpenTofu lab | Seven probes, 86 CLI invocations per complete run | Actual local/built-in providers, expected failures included |
| Adversarial experiments | Six CLI cases, one accounting sketch, one source check | Mixed evidence, explicitly separated |
| Joined lifecycle | Three requests, two real arithmetic executions, one deduplicated result; six CLI invocations | Real local installation/execution/destruction; adoption and root export simulated |
| Independent review | Five additional checks: three model checks and two CLI interleavings | New counterexamples, not production guarantees |
| AWS provider behavior | Three independently downloaded, checksum-verified source files | Source inspection only; no S3 operations |

Versions: Python **3.13.15**, OpenTofu **1.13.2**, local provider **2.5.3**.
AWS source is **v6.70.0**, commit
`5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f`.
See [integration](integration/report.md) and [independent review](review/report.md)
for commands, hashes, observations, and limitations.

The coordinator's final command, from the design repository, was:

```sh
python3 -B feasibility/integration/run-all --refresh-sources
```

All eight reported stages passed. Condensed evidence is in
[integration/test-results.json](integration/test-results.json); that coordinator
run is retained at `integration/runtime/5/`. Earlier failures remain recorded in
[integration/run-index.json](integration/run-index.json). Raw runtime evidence and
development binaries are ignored, not intended for Git publication.

## Ideas that survived these tests

- Ordinary immutable DAG data can represent requests, attempts, installation
  results, reuse, and lifecycle observations. Explicit occurrence IDs avoid
  collapsing independent attempts with identical results.
- Installation can produce resource bindings used to construct a bound closure.
  Distinct attempts can still produce the same result identity.
- Stored HCL can be composed into a shared root using stable module-instance
  addresses and explicit provider mappings. Regeneration with preserved state
  produced no-op plans; reordering keys did not change identities.
- A bounded adapter and an independently driven lifecycle are coherent. Recorded
  computational outcomes, cleanup failures, and later remediation can remain
  distinct.
- Full-history retention, pending management obligations, GC, and authorized
  excision can coexist in a finite model. Compute retirement can preserve result
  inspection and reuse without claiming that the old closure is executable.

These are feasibility results under explicit assumptions, not proof that the
existing C core already implements the model or that provenance is complete.

## Strongest gaps and flaws

### 1. Resource management is not generic bytes-preserving adoption

Actual `local_file` import failed because the provider does not implement it. A
subsequent apply created the configured file over the execution-produced content.
Import-capable built-in surrogates also showed incomplete output bindings and
import-plus-update plans.

Pinned AWS source indicates that some `s3_object` metadata updates go through an
upload path with an empty body when no source/content is configured. Destruction
of a versioned object can enumerate all versions and delete markers of the exact
key. These are conditional source findings, **not executed S3 results**; an
unchanged import is not shown to erase data.

**Implication:** provider identity and lifecycle scope must match what research
actually owns. A single immutable object version cannot casually be represented
by a resource that manages every version of its key. Adoption needs provider-
specific preservation checks, not just a generic import acknowledgement.

### 2. Deployment freedom does not eliminate apply-time coordination

The independent reviewer saved a destruction plan, then changed configuration and
added `prevent_destroy` without applying that change. Applying the saved plan
still destroyed the sandbox resource. A new research reference also need not
change OpenTofu state, so its state lock cannot detect that retention changed.

**Implication:** keeping DML ignorant of GitHub Actions is compatible with a
backend-neutral admission protocol, but arbitrary deployment bypass cannot carry
a strong retention-safety guarantee. A real design must choose cooperative plan
admission/fencing or explicitly weaker guarantees. Approval at generation time is
not sufficient.

### 3. A regenerable configuration is not regenerable operational state

Identical HCL after state loss planned creation and yielded different binding
identities. Stable declaration addresses matter: renaming an installation key
planned delete/create. Orphan cleanup failed when the required provider alias was
removed. Removing a declaration also omitted its destroy-time provisioner.

**Implication:** persist manager state/mappings and cleanup capabilities separately
from the materialized view. Recover before applying, reject unintended replacement,
and do not rely on deletion of HCL text to execute arbitrary cleanup hooks.

### 4. Full HCL has effects beyond the exported resource manifest

Two instances wrote the same `path.module` file despite separate state addresses.
Stored source without its referenced files failed to evaluate. Provisioners can
create unmanaged effects, while outputs marked sensitive still expose plaintext
in JSON/state.

**Implication:** full-language support needs an explicit trust/capability and
capture contract. Language restriction is one option, not an approved decision;
faithful source storage alone cannot promise complete ownership discovery or safe
composition. Resolved provider/module versions, input values and dependencies also
need capture where reproducibility requires them.

### 5. Safe retention requires more than reachability

Destruction needs a complete repository/export census, durable cleanup identity
handoff, dependency knowledge, and coordination with new references. The reviewer
also demonstrated that the prototype permits both ownership rebinding of one
identity and new dependencies on an already withdrawn resource while its safety
assertions pass.

The joined scenario manually supplies a retention-root export; its history and
retention heads are not automatically coupled. Consequently, it does **not** prove
end-to-end DML-root extraction or safe cross-repository GC.

**Implication:** identity registration, dependency publication after excision,
root-export validation, and destructive admission are missing gates. They are
next-prototype requirements, not solved by the current in-memory fence.

### 6. Tombstones do not themselves deliver sensitive-data erasure

After current-state tombstoning, synthetic plaintext remained in backups, copies
and logs. Low-entropy digests also allowed dictionary recovery. Resource retirement
and content erasure need different assurance and copy-management semantics.

**Implication:** define what can actually be erased and what metadata may survive.
The study establishes no physical page wiping, replica revocation, backup purge,
or legal-compliance guarantee.

### 7. Closure identity and observation receipts remain design choices

Incidental outputs can unnecessarily split cache identities; mutable URI-only
bindings can hide changed artifacts. Reading outputs and then state across a
replacement produced a mixed observation. Hidden executor retries can also make
one recorded attempt contain multiple real executions.

**Implication:** choose identity projections and validate complete, correlated
binding receipts. Record uncertainty and actual execution identifiers rather than
inferring empirical independence from hashes or request counts.

## Corrections to the study and remaining limitations

The independent review verdict is **needs corrections before end-to-end safety
claims**, not unconditional approval. This summary adopts that qualification.
The issue registers are [integration/issues.json](integration/issues.json) and
[review/findings.json](review/findings.json).

A relocated provider lab initially failed because its Unix socket path was too
long. Shorter integration-owned paths fixed it without changing dependencies or
first-wave scripts; the failure was preserved. Integration also corrected a
100-candidate search-domain label to eight actual guesses and a stale source-line
citation. The final coordinator rerun passed.

Remaining study defects are disclosed, not silently repaired into apparent design
proof: standalone scripts can reuse synthetic fixture paths; copied lab layouts
remain path-sensitive; root exports are manually supplied; identity/withdrawal
admission cases are missing. Prefer the fresh-sandbox integrated entrypoint over
standalone fixture runners. The runner retains at most eight sandboxes, never
prunes them automatically, and refuses changed first-wave inputs. Further repeated
runs may require inspecting and archiving old ignored sandboxes first.

There was no native DML/LMDB integration, real external-artifact provider adoption,
cloud-resource experiment, remote backend deployment, crash-safe distributed
coordination, or global erasure test. No live infrastructure, existing research
data, system configuration or DML implementation files were changed. Worker tmux
windows were closed after their results and persistent Pi sessions were saved.

## Recommended next prototype

Build a **durable local obligation journal with two publisher processes and one
reconciler/deleter**, using an import-capable synthetic-file adapter. Keep the
OpenTofu materialization seam, but do not start with AWS deployment.

Test actual process death and restart around registration, reservation, import,
external effects, saved-plan admission, acknowledgement and receipt publication.
Require canonical resource identity, validated root exports and explicit withdrawal
policy. Verify that adoption preserves bytes, state loss cannot silently recreate
retained identities, stale plans cannot delete newly retained resources, pending
cleanup survives discarded history, and result reuse survives compute retirement.

This experiment would address the sharpest unresolved boundaries before investing
in production schemas or implementing them in the C core.
