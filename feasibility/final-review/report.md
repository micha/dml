# Focused final feasibility audit

## Verdict and authority boundary

**Qualified feasibility pass for sealed-plan admission and a cooperative same-file
handoff; no production-safety approval.** The repaired gate withstands the actual
final-barrier plan swap. A provider-aware FileGate can use the current sealing
helper without inventing UUID/file identity mappings. However, an independently
executed **`.tofu.json` material-capture bypass** remains. Provider-side destructive
authority, complete membership/dependencies and durable manager receipts remain
unresolved.

This is a fresh-context audit, not a claim that the unavailable alternate model
executed work. It records experiments and candidate approaches, not approved DML
semantics. Only this workstream was written; no dependencies, account changes,
cloud operations, commits or implementation changes were made.

## Reproduction and provenance

From the design repository root:

```sh
python3 -B feasibility/final-review/audit.py
```

[The runner](audit.py) allocates new ignored sandboxes, caps runs at four and never
prunes fixtures. It snapshots twelve inspected source/interface files and checks
their hashes both before and after execution. It imports inspected fixture builders,
not their full-suite entrypoints. [Evidence](evidence.json) includes all source
hashes, tool hashes, actual apply arguments and outcomes. Current gate/helper hashes
match the gate worker's published checksum values. Provider **0.1.0** and OpenTofu
**1.13.2** executables were reused read-only and hash-verified; OpenTofu was also
checked against its pinned archive. Host versions: Python **3.13.15**, SQLite
**3.51.2**, Linux **6.18.55**.

The successful sandbox is `runtime/run-80e3f208/`: **seven focused cases**, **55
built-in CLI calls plus 18 provider-bridge CLI calls**. These include setup and
observations, not 73 distinct tests. One earlier sandbox, `runtime/run-c031220f/`,
retains four completed cases and 40 calls before a harness assertion failed:
`terraform_data.input` in raw state wraps its string in `{value, type}`. Correcting
only the owned assertion allowed one bounded fresh rerun. No candidate checks were
weakened. Raw logs/state remain ignored; the completed 285-call gate suite and
52-call artifact suite were not rerun.

The prior hardening report and follow-up prepare/check/run/collect scripts were
inspected. The latter were **not blindly executed**, and the failed follow-up is
not counted as a completed independent audit. This run independently constructs
its own sealed bridge subclass. Context7's existing log records quota exhaustion;
native tools are unavailable here and no documentation CLI was installed. Bounded
downloads of official [OpenTofu file documentation](https://opentofu.org/docs/language/files/)
and [Linux sealing documentation](https://man7.org/linux/man-pages/man2/F_ADD_SEALS.2const.html)
are hash-indexed in [documentation.json](documentation.json).

## Independently executed findings

### 1. Checked bytes, not a reopened pathname

The swap fixture contains an approved victim and an extra retained resource. The
approved non-targeted cleanup removes only the victim declaration and exports the
survivor. At the gate's actual final-check callback, the test replaces
`cleanup.tfplan` with a valid all-resource destroy plan having a different digest.

Inspection of the live approved descriptor verifies its digest and seal mask
**15**. Write, grow, shrink and additional-seal operations each fail with **EPERM**.
The actual logged apply argv ends in `/proc/self/fd/3`, with `pass_fds=[3]`.
OpenTofu deletes the approved victim; the extra retained UUID survives unchanged.
This is actual manager/kernel evidence, not a mocked CLI. Seals freeze plan bytes,
not provider behavior, working-directory contents or destructive authority.

### 2. Pre-effect rejection and positive fixture

Separate fixtures put `file()` and `sensitive()` expressions in the declared input,
and add an unexported resource. All reject with **zero planning CLI calls**, no
saved plan and unchanged state. A positive captured string-variable update still
plans/applies successfully. Its logs omit stdout/stderr bodies and have mode 0600.

These observations support the exact JSON fixture whitelist, not arbitrary HCL,
modules, provider effects or universal confidentiality. Synthetic plaintext still
exists in manager state. Source inspection also shows argv is logged verbatim:
body-free logs do not imply value-free logs if callers supply `-var=...` arguments.
That argv exposure was not separately executed here.

### 3. New capture bypass within literal fixture semantics

`gate.material()` enumerates `.tf`, `.tf.json` and tfvars files, but not `.tofu.json`.
The adversarial fixture adds `main.tofu.json` with the **same exported resource
census and only a different literal input**. Its addition leaves the material digest
unchanged. OpenTofu plans using that untracked literal. Changing the file again
after planning also leaves the digest unchanged; both `Gate.check` and apply accept.
Actual state contains the first untracked literal embedded in the approved plan.

Official documentation corroborates OpenTofu's preferred extension behavior.
This falsifies complete source-material capture even within this small literal
scenario. It does **not** demonstrate a seal bypass or destruction of an extra
retained resource. The saved plan's whitelist still checks its own census and
expressions. Other effects through unsupported files were not attempted.

A small candidate fix is to reject unexpected OpenTofu configuration extensions
before any CLI operation, then test the exact input-directory contract. A retained
immutable execution directory is a stronger alternative but introduces provider,
backend and file-closure capture responsibilities. Neither fix was implemented.

### 4. Actual same-file sealed bridge

The original generic Gate still does not support the artifact provider. Instead,
an owned `SealedFileGate` subclass reuses the inspected FileGate's single-resource
physical mapping and the **current worker's sealed-byte helper**.

The journal creates a file; actual provider import and no-op reconciliation preserve
its digest, inode and mtime. A real head whose current child is empty still retains
the parent's operational association and blocks disposal. Trusted experimental
excision permits reservation. Before provider apply, the subclass verifies the
same logical identity, physical inode and digest, then swaps the plan pathname to
invalid synthetic bytes. Applying the inherited sealed descriptor still removes
that exact file. Journal acknowledgement verifies absence; status becomes
`acknowledged`, immutable history validates and historical association remains.

This independently proves the narrow positive helper integration, not native Gate
composition. It still uses private journal `_verify` and receipt/bundle sidecars.
No new SIGKILL was performed: prior real-kill/retry results remain **inspected prior
evidence**, not independently repeated here.

## Remaining boundaries and morning review

Source inspection of provider `remove()` confirms it checks physical/content
identity but has no journal retirement authorization. The artifact and initial
hardening reports demonstrate forced replacement deleting before Create fails;
that counterexample was not rerun. Direct CLI bypass, hostile namespace races,
pre-receipt creation ambiguity and raw-state confidentiality remain visible.
A hash chain is not privileged-writer authentication or content erasure.

Complete registered membership/dependencies remain assumptions; the generic gate's
journal is fake. Manager receipts are sidecars, not native immutable DML facts.
Full HCL, remote backends, cloud resources, native DML/LMDB and physical erasure are
untested or unsupported. Finite successful cases cannot establish those properties.

**Approaches worth reviewing in the morning:** retain v2's durable creation intent
and immutable observations; retain sealed-byte admission but tighten the entire
input-directory boundary; treat provider-aware admission as a distinct interface,
not a fabricated generic mapping. The next small experiment should combine a
retained immutable bundle with versioned manager receipts and identity-scoped
Delete authority, challenging forced replacement and death after unlink. Decide
whether coarse cooperative fencing and its availability cost are acceptable, and
whether the provider seam warrants that complexity versus direct artifact cleanup.
These are proposals for review, not new approved decisions or a broad build mandate.
