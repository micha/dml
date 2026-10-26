# Candidate-design iteration results

## Verdict

**The central design is concretely feasible under a cooperative, local contract.**
We now have an actual bytes-preserving OpenTofu artifact provider, a durable journal
with immutable observations, and a demonstrated same-file adoption/retirement
handoff. However, these are not production-ready or a general safe-resource-manager
implementation. The final audit found another input-capture bypass; effect-side
Delete authority and distributed publication coordination remain open.

These are candidate approaches for morning review, not approved DML schemas or
policy. The first [feasibility results](RESULTS.md) and original counterexamples
remain preserved. No DML implementation/spec changes or cloud-resource operations
were performed.

## What changed after the first study

### Durable facts plus operational projections

[Journal v2](journal/report.md) adds append-only, content-addressed whole-projection
snapshots in the same transactions as logical changes. Prior heads, creation,
adoption and ticket states remain inspectable after reopen; chain/projection
validation and mutation guards are tested. Mutable tables are coordination
projections, not permission to rewrite research history.

A durable creation intent now precedes file creation. Real process death after
intent, after file persistence and before receipt no longer leaves an invisible
orphan. Matching present files can be reconciled without rewriting them; unsafe
or changed outcomes remain quarantined with cleanup prerequisites protected.

The **35-test suite includes 12 abrupt OS exits**. This is a real local SQLite
experiment, not a proposed replacement for LMDB. Full snapshots are deliberately
unscalable; complete registered membership/dependencies and cooperative namespace
writers remain assumptions. A same-byte replacement before the first physical
receipt remains ambiguous. Initial v1 reports/code are retained separately.

### An actual artifact-aware OpenTofu provider

The [Go provider](artifact/report.md) imports execution-created files, verifies
locator/digest/physical identity, and updates metadata without writing content.
Lost-state re-import and mismatch/escape rejection are actual provider behavior,
not a `terraform_data` surrogate. The harness ran **52 CLI invocations**, including
real SIGKILL recovery after unlink and before state acknowledgement.

This validates OpenTofu as a plausible first backend when the provider's lifecycle
semantics match the artifact. It does not rehabilitate unsafe generic S3 semantics.
The provider still permits an important bypass: raw forced replacement deletes a
valid file before adoption-only Create fails. Durable retirement authority inside
the effect receiver is not implemented.

### Apply checked bytes, not a checked pathname

The [gate follow-up](gate/report.md) applies the exact approved plan through a
Linux sealed memfd. The same captured byte object is used for inspection, checks
and apply. Actual write/grow/shrink/seal mutations fail with EPERM; swapping the
original pathname at the final barrier cannot substitute the destructive plan.

Pre-effect resource census and an explicit synthetic-fixture expression whitelist
also reject unexported resources and unsupported `file()`/`sensitive()` inputs.
Current logs omit stdout/stderr bodies and restrict permissions; raw manager state
can still contain sensitive values. This whitelist is an experiment boundary,
**not a proposed replacement for full HCL**.

The combined delivery reports **28 regression groups, 22 new groups and four
historical replays, using 285 CLI invocations**. Counts are different units, not
an additive unit-test total. The standalone gate still uses a fake research policy
journal; its real-journal bridge honestly rejects unrelated UUID/file mappings.

## Actual joined handoff and independent verification

The [initial hardening review](hardening-review/report.md) joined an actual
journal-created file with the actual provider via an explicitly narrow FileGate.
Head-derived ancestry and a second consumer block disposal; trusted experimental
excision permits it. SIGKILL after provider unlink leaves durable intent and stale
manager state. Checked retry converges, and journal acknowledgement observes actual
absence rather than trusting a zero apply exit.

The [fresh final audit](final-review/report.md) independently executed **seven
focused cases and 73 CLI calls**. It verified sealed-plan substitution resistance,
pre-effect rejections, a positive fixture and a sealed same-file bridge. The
approved victim was deleted while an extra retained UUID survived. Journal history
and absence acknowledgement validated after actual provider disposal. This second
bridge did not repeat SIGKILL; the earlier kill evidence is explicitly inspected,
not counted again.

The bridge uses provider-specific physical mapping and private journal verification;
it is not the generic gate secretly becoming provider-independent. Manager receipts
and bundles remain sidecars rather than complete versioned DML observations.
Neither bridge integrates the existing C core, cloud providers or remote backends.

## A new flaw remains: the entire input directory is the boundary

The final auditor added `main.tofu.json` with the same exported resource census but
a different literal input. OpenTofu prefers this source, while the gate's material
enumeration omitted it. Adding and changing the file left the material digest
unchanged; check/apply accepted the untracked literal embedded in the saved plan.

This is **not a memfd seal bypass** and did not delete an extra retained resource.
It falsifies complete source capture even for a small literal fixture. A minimal
fix is to reject unexpected OpenTofu extensions. A more principled next experiment
is a retained immutable input directory/bundle with explicit file, module, provider
and variable boundaries. We did not silently patch and declare that broader
problem solved.

## Approaches and choices to review

1. **Keep the facts/authority separation.** Retention, pending obligations and
   observation history belong in durable versioned records. Deployment technology
   remains user-selected; strong safety requires a generic cooperative admission
   contract and authority checked by the actual destructive receiver.
2. **Keep the provider-aware seam.** A manager UUID is not an artifact identity.
   Provider-specific registration, preservation and absence rules are necessary.
   Compare the familiar OpenTofu provider route with a simpler direct artifact
   adapter; neither eliminates filesystem/external-effect races.
3. **Do not mistake a volatile sealed plan for a durable execution bundle.** Seals
   protect bytes during this apply, not provider code, state, arbitrary effects or
   crash-time plan retention. Record exact permitted manager observations as
   immutable facts, without exporting raw sensitive state indiscriminately.
4. **Review availability and historical inspection.** The coarse global fence is
   demonstrated but can block unrelated work indefinitely. Per-resource fences need
   dependency/membership coverage. Reacquiring old operational heads after excision
   is rejected by this candidate; historical-inspection copying may deserve a
   distinct meaning rather than blanket rejection.
5. **Composition remains a real design question.** Stable declaration slots must
   precede resolved closure identities. Retaining historical HCL must not mean
   reapplying every historical configuration; define active desired contributions,
   shared-resource conflicts and provider-version compatibility before generalizing
   one shared root.
6. **Excision authority and erasure assurance remain project decisions.** Shared
   consumers, cleanup custody, incomplete census and sensitive copies require
   explicit scope. Unlink/tombstones are not universal legal erasure guarantees.

The smallest next experiment combines an immutable deployment bundle, versioned
manager receipts and identity-scoped provider Delete authority, then attacks forced
replacement and effect-before-receipt crashes. This is a recommendation, not another
unapproved production build mandate.

## Study integrity and operational notes

The first resumed hardening follow-up hit two model-provider server errors and is
not credited as completed review. An alternate model was unavailable because the
account lacked its use-case registration; no account settings were changed. A
fresh-context audit on the working model completed successfully. Thus this is
independent-context review, not claimed cross-model agreement.

A coordinator harness error also occurred: editing a Bash launcher while earlier
instances were blocked in Pi left two missing post-report exit records. The
hardening wrapper's Bash parsing failure (status 2) was observed; the earlier gate
wrapper's final status was not recaptured before its window closed. Delivered
experiments were independently rerun, but neither wrapper is reported as a zero
exit. Later launchers were frozen unique copies; final successful markers and
process statuses were checked. Diagnoses remain in ignored runtime logs.

All worker windows were closed after preserving results; the original user window
remains. Sources/reports are persistent under this repository, generated tools and
runtime evidence are ignored, and changes are left uncommitted for morning review.
