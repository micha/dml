# OpenTofu laboratory: executed feasibility findings

## Verdict and authority boundary

The proposed regenerable IaC **configuration** view is feasible in a narrow,
local module-composition test. It is not evidence that operational **state** is
regenerable, adoption is universally available, or removing configuration is
sufficient for safe cleanup. Seven real-CLI probes passed their assertions in
three fresh sandboxes; each run used 86 CLI invocations, including deliberately
failing commands.

This report owns only these laboratory observations. It does not approve DML
schemas, installation semantics, modules as the composition mechanism, or
implementation changes. The underlying exploratory direction remains in
[discussion.md](../../discussion.md). The scripts never modify that document or
the DML implementation checkout.

Strongest executed counterexamples:

- `local_file` import fails; applying its declaration afterward overwrites an
  execution-created file rather than adopting it.
- Restoring configuration with intact state gives no-op plans. Restoring the same
  configuration without state plans creation, replaces a surrogate identity, and
  overwrites independently changed file content.
- An orphaned resource cannot be destroyed after its provider alias is removed.
- Deleting a resource declaration deletes its destroy provisioner too: destruction
  succeeds without running that cleanup code.

## Reproduction and versions

Run from the repository root:

```sh
python3 feasibility/opentofu/provision.py
python3 feasibility/opentofu/probe.py
```

[Provisioning](provision.py) uses official OpenTofu **1.13.2**, Linux amd64,
from the [release](https://github.com/opentofu/opentofu/releases/tag/v1.13.2).
The archive SHA-256 is
`723bebb0df8411daff1e5fc3862e28ff5581fe5634087f4c29a9aa41d78208b5`;
it was checked against the release's published checksum list, and the script
also pins that digest. This is checksum verification, not independent signature
verification. No `.nix` files or Nix lock were found in the DML checkout, so no
Nix profile or OS installation was attempted. The executable/version are
published in ignored [ready.json](../tools/ready.json).

The only downloaded provider is **registry.opentofu.org/hashicorp/local 2.5.3**.
Its executed lock is preserved as [local-provider.lock.hcl](local-provider.lock.hcl).
The final driver copies this lock and initializes with `-lockfile=readonly`.
Built-in `terraform_data` requires no downloaded provider.

[probe.py](probe.py) creates a fresh `runtime/run-*` directory for every run.
It does not recursively delete old runs. The subprocess environment excludes
inherited deployment credentials and user CLI configuration; HOME, configuration,
cache and temporary paths are sandbox-local. All generated HCL targets are
inside the new sandbox. Actual resources were destroyed after the probes;
benign provisioner markers and raw evidence remain ignored.

Exact argument vectors, return codes, provider locks and log names are in the
final [results.json](runtime/run-we5kxfah/results.json). Saved plan JSON and raw
stdout/stderr are in that same ignored directory. Portable condensed assertions
and observations are in [evidence.json](evidence.json). Representative invocations
use `tofu -chdir=<sandbox>` with:

```sh
init -input=false -no-color -lockfile=readonly
validate -no-color
plan -input=false -no-color -detailed-exitcode -out=initial.tfplan
show -json initial.tfplan
apply -input=false -no-color initial.tfplan
output -json
import -input=false -no-color terraform_data.adopted execution-42
destroy -input=false -auto-approve -no-color
```

## Executed probes

### 1. Module material, name isolation and bindings

The [stored HCL fixture](closure/main.tf) is copied unchanged into module
material. One generated root instantiates it with stable `for_each` keys `a`
and `b`, with an explicit alias mapping and one shared `terraform_data` dependency.
Initial validation succeeds and the plan has five creates: two files, two
binding surrogates and the shared surrogate. Missing the required `local.bound`
provider mapping fails validation.

Both modules use identical internal resource names without state-address
collisions. Their files have intentionally distinct paths. This demonstrates
address isolation, **not** isolation of physical names chosen by arbitrary HCL.
Before apply, binding IDs, shared IDs and checksums are unknown; filenames are
already known. After apply, the two binding IDs differ and the shared ID matches.
Repeated apply preserves all outputs. Regenerating the root with reordered keys
produces five `no-op` actions and no unintended replacements. Renaming `a` to
`renamed` instead plans two deletes and two creates, so declaration identity
cannot casually follow output identity or presentation ordering.

Evidence: [initial](runtime/run-we5kxfah/composition/initial.json),
[regenerated](runtime/run-we5kxfah/composition/regenerated.json), and
[renamed](runtime/run-we5kxfah/composition/renamed.json) plans.

### 2. Failed adoption can become destructive creation

The driver first writes `execution-created-content` to an unmanaged sandbox file.
`tofu import local_file.adopted <absolute-filename>` returns exit 1:
**Resource Import Not Implemented**. The file is unchanged by that failed import.
The subsequent plan reports `create`, not import or update. Applying it changes
content to `configuration-content`; destroy later deletes the file.

This is a provider limitation, not an OpenTofu-wide rejection of adoption. It
also disproves treating an unsupported import as harmless permission to apply
the desired declaration. The [plan](runtime/run-we5kxfah/local-adoption/after-failed-import.json)
cannot infer the intended preservation obligation from this configuration.

### 3. CLI and declarative import, using a state-only surrogate

Actual `terraform_data` import accepts the fabricated identifier `execution-42`.
Immediately afterward, `output -json` already exposes the root binding with that
ID and a **null** value. The imported resource's `input`, `output` and
`triggers_replace` are null. A reconciliation plan proposes `update`; apply
fills in `resolved-input` while preserving the imported ID.

A separate declarative import of `execution-43` produces plan JSON containing
`importing.id` **and** an `update` action; its computed output remains unknown in
the plan. Apply imports and reconciles, and a repeated plan is no-op. Adoption
is therefore not necessarily an import-only operation, and CLI import does not
necessarily leave root outputs unavailable. Output completeness needs checking.

These are real CLI/state mechanics, but `terraform_data` does not verify that an
external object exists and manages no external artifact. Its import is explicitly
a **surrogate**, not evidence that a result object or compute job can be adopted.
See the [declarative plan](runtime/run-we5kxfah/declarative-import/import.json).

### 4. Lost configuration versus lost state

With state retained, omitting both resource declarations plans two deletes;
restoring the original declarations before apply gives two no-ops. Then the
driver moves state and its backup aside within the sandbox and writes
`execution-result-do-not-overwrite` into the file. Identical regenerated HCL now
plans two creates. Apply changes the surrogate ID and overwrites the file with
`desired-by-config`. See [lost-state actions](runtime/run-we5kxfah/loss/lost-state.json).

The test intentionally changes content after losing state to expose the danger;
it does not establish that every state-loss case changes bytes. It establishes
that source restoration alone neither recovers identity nor preserves observed
external contents.

### 5. Selective removal and dependency-sensitive destruction

Removing only installation `a` plans deletion of its file and binding; `b` and
the shared resource remain no-op. Applying deletes only `a`'s file. A final destroy
plan deletes the remaining three resources. JSON apply events record completion
in dependency-reversed order: `b` file, `b` binding, shared resource.

Evidence: [selective-removal plan](runtime/run-we5kxfah/composition/remove-a.json),
[destroy plan](runtime/run-we5kxfah/composition/destroy-all.json) and
[apply events](runtime/run-we5kxfah/logs/063-apply.stdout).
The shared resource stays because it remains declared and referenced—not because
OpenTofu aggregates DML retention claims automatically.

### 6. Provider configurations are cleanup obligations

A file created through `local.cleanup` becomes an orphan when both the resource
and provider blocks are omitted. `plan -destroy` fails with **Provider
configuration not present**. Restoring only the alias configuration allows a
`delete` plan and successful cleanup. Even this provider with no endpoint or
credentials requires the alias identity to survive until destruction.

### 7. Executable HCL and disappearing cleanup hooks

A benign `local-exec` provisioner writes a sandbox marker. Plan leaves it absent;
apply creates it. Removing the whole resource block then plans deletion but skips
its destroy provisioner. Recreating the resource and changing its retained block
to `count = 0` performs deletion **with** the cleanup marker.

The HCL is locally authored, not downloaded. This proves execution at deployment
and a concrete cleanup-loss case; it does not prove arbitrary plans are safe.
Providers and other HCL features were not sandboxed by OpenTofu itself.
Generation/storage and deployment remain separate security boundaries.

## Evidence classification, gaps and next experiment

**Executed:** all seven results above, versions, checksums, actions, output timing
and destruction events. **Modelled integration:** copying an HCL fixture stands
in for DML-to-IaC materialization; no real DML persistence or journal exists here.
**Documentation:** provider inheritance/cleanup and provisioner caveats agree
with primary [module-provider docs](https://opentofu.org/docs/language/modules/develop/providers/),
[import docs](https://opentofu.org/docs/language/import/),
[provisioner docs](https://opentofu.org/docs/language/resources/provisioners/syntax/)
and pinned [local_file source docs](https://github.com/hashicorp/terraform-provider-local/blob/v2.5.3/docs/resources/file.md).
Context7 returned “Monthly quota exceeded”; primary docs/source were used instead.
**Conjecture:** extrapolations to cloud artifacts, crash recovery and multi-writer
reconciliation remain untested. No simulator substituted for the CLI.

Prioritized possible fixes, not approved decisions:

1. **Protect state and gate adoption.** Preserve backend identity, backups and
   import metadata; reject creation/replacement for pending adopted artifacts
   until compatibility is checked. This reduces accidental loss but adds
   provider-specific logic and manual recovery cases.
2. **Keep stable declaration IDs and provider cleanup configuration.** Store
   installation keys independently of resolved binding contents. Retain provider
   aliases and necessary settings until cleanup completes; consider explicit
   `moved` migrations for address changes. This increases lifecycle metadata.
3. **Represent incomplete bindings and reconcile import drift.** Check required
   output fields and plan import/update/replace actions before publishing an
   execution-ready closure. Eager publication is simpler but can expose null or
   soon-to-change bindings.
4. **Preserve executable cleanup and shared retention explicitly.** Keep blocks
   through staged removal or use durable cleanup outside provisioners. Aggregate
   DML obligations before root generation. Simpler omission is demonstrably unsafe.
5. **Restrict deployment capability.** Review/allowlist providers and executable
   features, isolate runners and require suitable approval gates. These controls
   trade expressive HCL and deployment freedom for reduced blast radius.

Limitations include no cloud APIs, Docker, remote backend, actual import-capable
external-artifact provider, concurrency, failed destruction, conflicting provider
versions or crash-in-flight testing. Next: build or select a tiny import-capable
sandbox-file provider, import a file with deliberately mismatched attributes,
then test preservation gates and recovery between import, output publication and
cleanup. That would directly exercise the adopted-artifact lifecycle the built-in
surrogate cannot establish.
