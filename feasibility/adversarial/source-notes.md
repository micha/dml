# Primary-source evidence and reproduction

## Authority boundary

Informative feasibility evidence only. These notes do not approve DML APIs,
provider policy, erasure claims, or specification changes. Fetched content was
read as evidence, not followed as instructions.

## Commands and versions

From `/work/repos/micha/dml-design`:

```bash
ctx7 library 'Terraform AWS provider' 'aws_s3_object import content source version_id metadata changes preserving imported object bytes'
python3 feasibility/adversarial/fetch_evidence.py
python3 feasibility/adversarial/experiments.py
feasibility/tools/tofu version
sha256sum feasibility/tools/tofu feasibility/tools/tofu_1.13.2_linux_amd64.zip
```

Context7 returned `Monthly quota exceeded`; no documentation tool was installed.
The fetch script resolved the public latest release to AWS provider **v6.70.0**, commit
`5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f`. For subsequent pinned reproduction:

```bash
python3 feasibility/adversarial/fetch_evidence.py \
  --aws-commit 5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f --aws-release v6.70.0
python3 feasibility/adversarial/experiments.py
```

Python **3.13.15**; OpenTofu **1.13.2**, linux_amd64. The shared lab's
`ready.json.sha256` identifies the release ZIP, not the extracted executable:

- ZIP: `723bebb0df8411daff1e5fc3862e28ff5581fe5634087f4c29a9aa41d78208b5`;
  matches the lab's downloaded official `SHA256SUMS` entry.
- Executable: `949061cbb3c3d4558928ca9a459a5052b8c5e5545d17656f33316d2e3bc335f2`.

The tests use only built-in `terraform_data`, outputs, local modules, and bounded
shell provisioners. Subprocess environments contain no AWS variables and no AWS
provider is initialized. No AWS API, Docker, model, or real dataset is used.
Initial module fixture syntax was invalid (a multi-argument block started on its
opening line); corrected to multiline HCL, then the complete suite passed.

Detailed machine observations are in [results](runtime/results.json),
[raw run output](runtime/latest-run.log), and per-command logs under
[runtime/sandbox](runtime/sandbox/). These ignored paths are recreated by
[experiments.py](experiments.py). Public source copies and their SHA-256 manifest
are under [runtime/sources](runtime/sources/); their URLs and hashes are preserved
in the tracked [sources.json](sources.json). Live OpenTofu/AWS documentation is
not revision-pinned; the provider source is pinned.

## AWS provider: direct source trace (cloud unexecuted)

Pinned primary sources:

- [Object documentation](https://github.com/hashicorp/terraform-provider-aws/blob/5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f/website/docs/r/s3_object.html.markdown).
- [Object implementation](https://github.com/hashicorp/terraform-provider-aws/blob/5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f/internal/service/s3/object.go).
- [Deletion helpers](https://github.com/hashicorp/terraform-provider-aws/blob/5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f/internal/service/s3/delete.go).

Source anchors in `object.go`:

| Lines / function | Observation | Consequence (inference, not cloud test) |
| --- | --- | --- |
| 89–95, 180–186 schema | Bucket and key required, `ForceNew` | Renaming the storage locator is replacement, not immutable-artifact migration. |
| 132–141, 249–258 schema | Content/base64/source optional, mutually conflicting | Import configuration need not contain artifact bytes. |
| 270–273 schema | `version_id` computed only | This resource does not let HCL pin a particular version. |
| `objectImportID.Parse` | Splits bucket/key; no separate version field | Adoption targets the key, not a version-qualified artifact. Appending a query is not documented version import syntax. |
| `resourceObjectRead`, `findObjectByBucketAndKey` | Uses `HeadObject`; no version selector; flattens metadata/ETag/version | Import/refresh does not recover source files or content. `source_hash` is state-only. |
| `resourceObjectUpdate`, `hasObjectContentChanges` | Metadata, cache control, content type, encryption, etc. trigger upload | Metadata edits are not safely metadata-only edits to imported artifacts. |
| `resourceObjectUpload` | Absent source/content/base64 selects empty reader | A content-triggering edit can upload zero bytes over the current key. |
| `resourceObjectDelete` | If state has version ID, calls `deleteAllObjectVersions` | Deletion scope is wider than the last version observed by DML. |
| `sdkv1CompatibleCleanKey` | Drops leading slash/`./`, collapses repeated slashes | Distinct DML URIs may map to one provider-managed key. |

`deleteAllObjectVersions` (delete.go 328 onward) lists versions with the key as
prefix, filters for exact key equality, then deletes matching versions and delete
markers. It is not a prefix-wide deletion. Permission/object-lock failures can
interrupt deletion. `force_destroy` can remove legal holds and bypass governance
retention; it is not a universal ability to delete compliance-locked data.

The [AWS DeleteObject API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObject.html)
explains that a version-unspecified delete usually creates a delete marker in a
versioning-enabled bucket, while deleting a particular version permanently
removes it. Do not substitute that single-request behavior for the provider's
all-version loop. The [CopyObject API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CopyObject.html)
illustrates an alternative bytes-preserving metadata-copy mechanism; this pinned
resource's content-changing update branch instead uploads configured bytes.

Unchanged, carefully matched imported configuration can plausibly no-op. The
counterexample does **not** say every import empties an object. It says adoption
alone does not preserve bytes through all later applies. Generated import HCL,
OpenTofu/provider compatibility, metadata diffs after import, IAM permissions,
object lock, multipart/KMS checksums, and actual cloud behavior remain untested.
Provider docs' Terraform 1.12 `identity` examples are not evidence of identical
OpenTofu syntax support; bucket/key ID import is the conservative case examined.

## HCL and deployment sources

- [file](https://opentofu.org/docs/language/functions/file/): files must exist at
  run start; file functions are not nodes in the resource dependency graph.
- [References](https://opentofu.org/docs/language/expressions/references/): local
  module calls share source paths; `path.module` writes can overwrite/race.
- [Dependency lock](https://opentofu.org/docs/language/files/dependency-lock/):
  locks providers, not remote module selections.
- [Module sources](https://opentofu.org/docs/language/modules/sources/): source
  retrieval is distinct from retaining dependency bytes; Git refs may be pinned.
- [Providers in modules](https://opentofu.org/docs/language/modules/develop/providers/):
  one compatible provider version per source address in a configuration, explicit
  alias mappings, provider configurations retained until dependent destruction.
- [Provisioners](https://opentofu.org/docs/language/resources/provisioners/syntax/):
  arbitrary effects are opaque to planning; removed destroy-time provisioners do
  not execute, and tainted instances introduce additional cleanup limitations.
- [Lifecycle](https://opentofu.org/docs/language/meta-arguments/lifecycle/):
  replacement ordering does not promise historical artifact identity preservation.
- [Outputs](https://opentofu.org/docs/language/values/outputs/): sensitivity
  suppresses normal UI output but values remain in state. Newer ephemeral
  facilities are restricted contexts, not a general persistent root-manifest fix.

## Prototype/core boundary

Selectively inspected DML checkout commit
`638cc4267d7aca2e34e58c60ba7a54e25f0a20eb`, without editing or running it:

- `docs/spec/execution.md` Sections 1–4 still discuss deterministic call IDs,
  pinned executions, `pending`, and no canonical record while pending. Those
  draft semantics do not establish the exploratory occurrence model's behavior.
- `docs/spec/object-model.md` Sections 7.10 and 9.3 describe same-ID tombstones;
  `src/repo.c` `lookup_datum` rejects tombstones before normal datum hash checking.
  This is a plausible exceptional-resolution seam, not evidence of global
  revocation, secure LMDB page wiping, replica erasure, or provider cleanup.

The synthetic SHA-256 parent experiment shows that rewriting ordinary
content-addressed child bytes requires changed parent identities. It does not
falsify an explicit same-ID tombstone exception, and it is not a DML integration
test. Prototype resource journals/manifests and deployment coordination can stay
outside the C core while occurrence and excision semantics are still explored.
