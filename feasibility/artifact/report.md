# Immutable-artifact provider experiment

## Verdict and authority boundary

**Actual OpenTofu adoption is feasible; automatic destruction is not yet safe.** A
241-line Linux Go provider imports execution-created synthetic files without
rewriting them, reconciles metadata without content writes, detects mismatches,
and recovers from state loss and a real process interruption. However, an explicit
backend replacement deletes a valid artifact before the adoption-only creation
handler fails. This is a demonstrated destructive counterexample, not a passing
production safety contract.

This report owns only this experiment's observations. The provider and its policy
choices are candidate designs, not approved DML semantics. No DML implementation,
cloud resources, existing research files, shared tools, or OS settings were changed.

## Reproduction and packaging

From the design repository root:

```sh
python3 -B feasibility/artifact/build.py
python3 -B feasibility/artifact/test_provider.py
```

The build uses the already installed, explicitly pinned Go **1.26.8**, Terraform
Plugin SDK **v2.38.2**, `golang.org/x/sys` **v0.40.0**, and OpenTofu **1.13.2**.
Python is **3.13.15**. [go.mod](go.mod) and [go.sum](go.sum) pin the dependency
closure. The build runs `go mod verify` followed by
`go build -trimpath -o tools/terraform-provider-immutable_v0.1.0`, with module,
build, temporary and home directories scoped to ignored `runtime/` paths.
No compiler installation or Python surrogate was needed.

The provider source is `dml.invalid/feasibility/immutable`, version **0.1.0**.
[build.py](build.py) packages an unpacked filesystem mirror and an explicit CLI
configuration with no direct registry installation method. Ignored `ready.json`
contains absolute executable, compiler, mirror and CLI-config paths plus hashes.
The shared OpenTofu executable is used read-only and checked against SHA-256
`949061cbb3c3d4558928ca9a459a5052b8c5e5545d17656f33316d2e3bc335f2`.
The compiled provider hash is
`3f3f69e57054ed57d760a9765679d8caf1d072a3f34af92ea2662a5da59ff7b1`.

The harness creates new numbered sandboxes, retains at most eight without deleting
old runs, and supplies an isolated home and `TF_CLI_CONFIG_FILE`. All fixtures,
state, plans and raw logs remain ignored. Safe fixture generation and assertions
are in [test_provider.py](test_provider.py); [test-results.json](test-results.json)
is the condensed evidence index. The expanded run executed **52 real CLI
invocations**, including the killed apply; expected failures count as observations,
not unexpected harness failures.

Context7 returned **“Monthly quota exceeded”**. No replacement documentation CLI
was installed. API details were checked against the pinned official
[SDK resource source](https://github.com/hashicorp/terraform-plugin-sdk/blob/v2.38.2/helper/schema/resource.go),
[importer source](https://github.com/hashicorp/terraform-plugin-sdk/blob/v2.38.2/helper/schema/resource_importer.go),
and current official OpenTofu
[mirror configuration](https://opentofu.org/docs/cli/config/config-file/)
and [CLI import documentation](https://opentofu.org/docs/cli/commands/import/).
Downloaded source and documentation are retained under ignored `runtime/docs/`.
An initial bounded build failed because Go traversed its nested module cache;
a separate ignored `runtime/go.mod` excluded that cache, after which build and
module verification succeeded.

## Candidate resource contract

[main.go](main.go) implements a real `immutable_artifact` resource, not
`terraform_data`. Required configuration records a relative `path`, expected
`sha256`, logical `resource_id`, and `owner`. Computed state records file and
sandbox-root physical identities as `device:inode`. A CLI import ID is a JSON
receipt containing all six fields; import verifies the receipt against existing
bytes and identities before registering state. No Create operation creates or
uploads anything: it returns an adoption-only error.

Every root and relative parent component is opened through directory descriptors
with `O_NOFOLLOW`; targets must be regular files with one link. Absolute locators,
noncanonical paths, escapes, symlink targets/parents and hardlinks are refused.
The provider never opens content for writing. Read verifies rather than accepting
changed bytes; immutable configuration changes fail during planning and are also
checked during Update. Only the string `metadata` can change, in state alone.

Delete verifies the root, physical file identity and digest, rechecks immediately
before descriptor-relative unlink, and treats absence as safe. A mismatch produces
an explicit error while leaving the observed file in place. The provider trusts
the configured root and caller-supplied ownership receipt: the harness establishes
freshness, but the provider does not authenticate ownership or independently prove
that a root is an authorized sandbox.

## Executed evidence

All rows below are **executed actual provider/CLI evidence**, not simulation.
Detailed command arguments, return codes and logs are linked through the condensed
[test results](test-results.json) and each run's ignored `commands.json`.

| Probe | Observed result |
|---|---|
| CLI import, apply and repeated no-op | Import registers existing bytes; subsequent plan exits 0 and apply reports no changes. Initial apply materializes output values. |
| Metadata change | Plan exits 2; apply reports one changed resource. SHA-256, inode and modification time remain identical. |
| Configured path, digest, owner or logical ID change | All four plans fail with immutable-field diagnostics. |
| External byte tampering | Refresh fails. `destroy -refresh=false` independently checks content and fails without removing tampered bytes. |
| Lost state | With state and backup moved aside, plan proposes creation; apply fails adoption-only without changing bytes. Re-import from the execution receipt restores management and a no-op plan. |
| Retirement and missing import | Matching destruction unlinks the file. Re-import of the absent file fails without recreating it. |
| Stale saved destroy plan | After same-byte replacement by a different inode, applying the saved plan fails. A separately replaced sandbox root also causes failure, preserving both old and new files. |
| Invalid import locators | Escape, absolute path, target symlink, parent symlink, hardlink, absent file, wrong digest and symlink-configured root all fail; synthetic outside-root sentinels remain unchanged. |
| Declarative import | Saved import plan includes import identity and metadata reconciliation. Apply preserves digest/inode/mtime; the next plan exits 0. |
| Real interruption | A bounded test-only pause after unlink lets the harness kill the CLI/plugin process group with SIGKILL. The file is absent but old state still records the resource. Retrying unrefreshed destruction succeeds safely and removes the stale state entry. |

The exported manifest contains exactly locator, digest, logical ownership/identity
and physical/root identity, not synthetic content. An additional inspection found
no synthetic content string in the expanded run's 13 state/backup files. This
shows the fixture's content is not copied into manager state, not that arbitrary
metadata or digests are non-sensitive.

For contrast, the original
[local_file adoption experiment](../opentofu/report.md#2-failed-adoption-can-become-destructive-creation)
failed import and then overwrote execution-produced bytes on apply. That baseline
was referenced, not duplicated or retroactively changed.

## Strongest counterexample and prioritized gaps

**P0 — forced replacement bypasses immutable-field protection.** After successful
import, the harness executes:

```sh
tofu apply -auto-approve -input=false -no-color \
  -replace=immutable_artifact.result
```

OpenTofu plans destroy/create, invokes the valid Delete, and only afterward reaches
the failing Create handler. Apply exits 1, but the file is already gone. Therefore
“creation is forbidden” does not mean “replacement cannot destroy retained
artifacts.” The evidence is retained in the run's `replace/` fixture and final
apply log. SDK source also documents that custom diff is skipped for tainted
resources and destruction; that related taint behavior was not separately tested.

Candidate fixes include an apply-time retirement authorization checked inside
Delete, or separate non-destructive adoption and explicitly destructive retirement
capabilities. A backend-neutral gate could reject replacement and require a
journal reservation, but arbitrary gate bypass would remain unsafe. A provider
Delete token would make bypass harder while adding durable token lifecycle,
retry and crash-recovery requirements. These are proposals, not implemented fixes.

**P1 — physical checks are not an atomic conditional unlink.** An external actor
can replace a pathname after the final check, modify an open inode while hashing,
add links, or rename an opened parent outside the configured root. Directory
handles prevent symlink redirection but do not solve hostile directory relocation.
Device/inode numbers can also be reused. These are code/syscall limitations, not
race outcomes established by this finite test. Stronger guarantees require
cooperative exclusive namespace ownership, fencing, or a storage backend exposing
conditional deletion of immutable object identities.

**P1 — ownership and receipts need a durable authority.** State labels do not
provide exclusive ownership, cross-repository retention, withdrawal authorization,
or duplicate-import exclusion. OpenTofu's import documentation explicitly warns
against managing one physical object at multiple addresses. The harness writes an
execution receipt before import, but does not prove atomic file creation plus
receipt publication or integrate the journal workstream. Integrating those gates
is the next experiment, especially around re-import and forced replacement.

**P2 — retirement is not erasure or production recovery.** SIGKILL exercises one
specific acknowledgement gap, not power-loss persistence or remote backend
recovery. No filesystem/directory fsync guarantee, digest privacy guarantee,
backup purge, inode generation identity, bounded file-size policy or cancellation
of long hashing is implemented. External tampering is detected, not prevented.
Unlink provides no content-erasure guarantee. The prototype is Linux-only and
should remain confined to synthetic sandboxes until the P0 admission gap is fixed.
