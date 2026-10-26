# Independent hardening review and actual local handoff

## Verdict and authority boundary

**Qualified success for a narrow cooperative synthetic handoff; no-go for general
retention-safe deployment.** Actual journal-created files can be adopted unchanged
by the actual OpenTofu artifact provider, protected by head-derived history, and
retired with durable intent and absence acknowledgement after real process death.
The candidate interfaces do not directly compose: this required the explicitly
restricted `FileGate` adapter in [checks.py](checks.py).

The strongest new counterexample is **saved-plan substitution after final
validation**: an apply ticket authorized deletion of one resource; replacing its
plan file at the final-check barrier destroyed another resource whose identity
remained retained. Failure to retrieve the final receipt occurred *after* both
resources were gone. SQLite fencing does not fence filesystem plan writers.

This report records experiments and recommendations, not approved DML policies.
No native DML, cloud, live service, hostile-filesystem, distributed-protocol or
physical-erasure guarantee follows. First-wave counterexamples remain intact.

## Reproduction and evidence

From `/work/repos/micha/dml-design`:

```sh
python3 -B feasibility/hardening-review/run_review.py
# Rerun only independent checks against the retained delivery snapshot:
python3 -B feasibility/hardening-review/checks.py feasibility/hardening-review/runtime/3
```

[run_review.py](run_review.py) calls [prepare.py](prepare.py), copies and verifies
candidate sources, then runs their tests without modifying workers. Source copies
are byte-identical except a disclosed provider-test `TMPDIR` relocation into the
review-owned runtime, avoiding Unix socket-length problems. Shared OpenTofu and
provider executables/mirror are read-only; hashes are checked. No tools were built
or installed. Every run allocates new ignored fixtures, caps retained runs at
eight, and never automatically removes old resources.

Delivery evidence is indexed in [evidence.json](evidence.json), with exact source
hashes in [the frozen manifest](runtime/3/source-manifest.json). These match all
corresponding current worker files at final validation. Versions: Python
**3.13.15**, SQLite **3.51.2**, OpenTofu **1.13.2**, Linux **6.18.55**, immutable
provider **0.1.0**, built by its worker with Go **1.26.8** / SDK **v2.38.2**.

| Independent execution | Observed result |
| --- | --- |
| Journal v2 combined suite | 35 passing tests: 20 baseline plus 15 focused; 12 abrupt OS exits |
| Gate suite | 28 passing result groups, including real-journal negative integration and effect/outcome interruption |
| Artifact suite | 52 real CLI invocations, including expected failures and SIGKILL |
| Review checks | 18 result groups, including actual joined provider destruction and fresh counterexamples |

Counts are different units, not an additive test total. The final joined/attack
run is [checks-2.log](runtime/3/checks-2.log); complete results are
[review-results.json](runtime/3/review-results.json). Earlier snapshots/logs remain
under `runtime/1` and `runtime/2`. The first copied artifact run failed because its
runtime parent was missing; creating that owned directory fixed the harness.
An early attack run stopped on a post-destruction receipt error; the corrected
assertion preserves and reports the already-completed destructive effect.

Reports/markers were awaited through bounded read-only polling, then all three
reports and the journal's separate v2 follow-up marker were read. Context7 returned
**Monthly quota exceeded**; no documentation CLI was installed. Official
[apply documentation](https://opentofu.org/docs/cli/commands/apply/) confirms saved
plans drive apply, and [show documentation](https://opentofu.org/docs/cli/commands/show/)
warns that JSON exposes sensitive values. Those downloaded pages supplement,
rather than substitute for, executed evidence.

## What actually joins

The adapter creates fresh journal databases and initially empty sandboxes. The
journal creates a UUID-named file and records device/inode/digest. An import receipt
uses that **same logical identity and actual physical file**, not a fabricated
`terraform_data` UUID mapping. CLI import, initial output materialization and a
no-op plan preserve digest, inode and mtime. The existing gate rejects this
provider configuration as unsupported, confirming interface friction honestly.

Repository A has an operational commit followed by an empty child; B has a
provenance commit. Actual stored heads and parent traversal retain the file.
Deletion admission rejects the empty-current-snapshot trap, rejects after dropping
A's head while B remains, and rejects an unavailable registered member. Trusted
lab excision then overrides retained availability while preserving associations.
This tests the candidate API, not authenticated multi-consumer consent.

`FileGate` captures generated configuration/lockfile, one coherent state receipt,
root revision, actual plan bytes and provider-specific identity fields. It parses
every resource change in this single-resource fixture, accepts only an exact delete,
and calls journal reservation/intent before invoking real provider apply. It is
not the existing generic gate and is not a universal parser. Its private
`_verify` use under a journal transaction is another seam to make public if pursued.

A child process executes provider Delete with its bounded post-unlink pause. The
parent observes absence and SIGKILLs the entire child/CLI/plugin group. Reopening
finds journal `intent`, undisposed metadata, a surviving fence, and old manager
state still containing the artifact. Retrying the same checked plan converges
manager state; journal `ack` then observes actual absence. Acknowledgement before
intent or with the file still present is rejected. Historical B associations
survive; an old operational head cannot be reacquired, while new provenance-only
history can publish. A second fresh fixture substitutes a different inode with
identical bytes; admission rejects it and preserves both files.

## Independent failures and surviving limitations

1. **Effect-boundary plan/config race — executed.** A `before_effect` callback uses
   the gate's existing test barrier to replace a checked targeted-delete plan with
   an all-resource delete plan. The extra retained identity is destroyed. A separate
   callback adds `prevent_destroy` after checks; destruction still executes. Neither
   requires editing candidate source. The raw saved-plan bypass also survives the
   worker rerun. Fixing ticket parsing is helpful but not effect-side fencing.
2. **Incomplete captured inputs — executed.** The allowed resource `input`
   expression `${file("input.txt")}` passes material validation. Changing that
   uncaptured file after planning passes `Gate.check`. “Restricted JSON” does not
   imply complete evaluation capture. Trusted fixture expressions are an assumption,
   not enforced language safety.
3. **Resource census validated too late — executed.** Add a second built-in resource
   without exporting it. Planning/admission succeeds; apply creates it; only the
   after-state receipt rejects the malformed mapping. Fake-journal reservation also
   accepts an empty member census. The real journal correctly requires nonempty,
   available members, but discovering *unregistered* consumers remains assumed.
4. **Sensitive raw observations — executed.** `${sensitive("SYNTHETIC-REVIEW-SENSITIVE")}`
   is accepted despite rejecting sensitive variable declarations. The projected
   receipt omits this synthetic value; raw `cli.log` contains it through state JSON.
   Provider manifests additionally expose locators, ownership, digests and physical
   identities: excluding bytes does not make all metadata public. Modules fail
   closed rather than obtaining composition support.
5. **Provider destruction authority — independently reproduced.**
   `tofu apply -replace=immutable_artifact.result` deletes an imported valid file
   before adoption-only Create fails. Import/no-op/metadata behavior, content and
   inode mismatch rejection, escape/symlink/hardlink rejection, absent-file handling,
   root replacement and provider crash recovery all pass. They do not prevent an
   authorized-looking but ungated Delete. Read/hash/recheck/unlink is still not an
   atomic conditional delete; adversarial replacement during that syscall gap is
   a source-based limitation, not a race demonstrated here.

## Immutable research state: correction recognized, not hidden

The initial journal v1 only mutated adoption, withdrawal and ticket observations.
That did not meet the user's versioned-state requirement; the frozen v1 evidence
remains. During review the worker delivered **v2** with transactional, append-only,
content-addressed whole-projection snapshots and pre-effect creation intent.
Independent combined tests verify prior heads/ticket states remain inspectable,
update/delete/replace guards, chain validation, projection/history rollback and
creation crash recovery. The joined run additionally validates immutable snapshots
containing `creation`, `adoption`, `managed`, `disposal` and all ticket states.
**It is no longer accurate to call v2 merely mutable-row history.**

This solves the narrow substrate problem, not native versioned DML research DAGs.
Exact OpenTofu receipts/config bundles in this adapter remain sidecars rather than
immutable journal observations. Full snapshots retain potentially sensitive
metadata and scale poorly. Creation still accepts an identical-byte replacement
before the first inode receipt; the independent focused test reproduces this
ambiguity while retaining the moved original. Quarantining changed/unsafe outcomes
works. These limitations replace, rather than erase, v1's invisible-orphan finding.

## Alternatives, priorities and morning recommendation

- **Coarse versus per-resource fencing:** retain the coarse reservation for the next
  local test: its durable crash behavior is demonstrated, although stuck tickets
  block unrelated work. Per-resource fences improve availability but must cover
  dependency closure, membership changes, new heads and shared consumers—not merely
  victim IDs. Neither alone protects mutable plan files.
- **Provenance versus operational acquisition:** current per-head rechecks safely
  reject reacquired withdrawn operations while permitting provenance. An explicit
  historical-inspection mode could allow copying old operational history without
  reacquiring execution capability; it needs a distinct authorization meaning.
  Do not simply disable head rechecks.
- **Provider versus direct artifact adapter:** the provider preserves familiar
  OpenTofu planning/module opportunities and achieves actual adoption. A direct
  journal effect is simpler and avoids replacement machinery, but gives up that
  resource-manager seam and still has filesystem races. Prefer reviewing the
  provider route with explicit Delete authority; keep direct cleanup as the
  comparison, not a secretly selected backend.

**P0 next experiment:** copy plan/config/provider inputs into an immutable owned
execution bundle, record exact manager receipts in versioned history, and require
Delete to verify a durable identity-scoped retirement authorization. Reproduce
plan substitution, forced replacement and effect-before-receipt death against that
contract. Reject uncaptured expressions and unexported resources *before* effects,
and keep raw state observations restricted. Excision authority and complete
membership/dependency registration need explicit project-level contracts.

In the morning, review **v2 journal + narrow provider-aware admission** as the
promising candidate, not the unchanged fake gate as a finished integration.
Deployment technology can remain user-selected; cooperative effect authority is
the unresolved safety condition. All recommendations remain tentative.
