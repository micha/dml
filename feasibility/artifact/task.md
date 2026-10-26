# Import-capable immutable-artifact provider experiment

Read `../WORKER.md` and `../ITERATION.md`; own only `feasibility/artifact/` including
its ignored tools/runtime. Start now. This task has the explicit additional scoped
Go-toolchain/module-download allowance in ITERATION.md. Do not modify shared tools
or globally install anything. Use primary current SDK docs/source, pin dependencies
and retain go.mod/go.sum; Context7 is likely quota blocked, use direct official
sources and report that fact. No cloud credentials/APIs/providers.

Try building a tiny actual Terraform/OpenTofu Go provider for adoption-only,
immutable synthetic files. OpenTofu is the only resource-manager backend in this
experiment; this is not just a state-only terraform_data surrogate.

Provider requirements (candidate contract):
- All operations confined to a provider-configured fresh sandbox root. Reject path
  escapes and symlink targets/parents; never delete arbitrary paths. No file creation
  fallback for a missing import. Fail safely rather than overwrite existing bytes.
- Actual CLI import registers an execution-created file, with locator and expected
  content digest; resource identity, ownership and configured checksum are explicit.
- Read/metadata-only updates never upload or rewrite content. Changed expected
  content/path is rejected or clearly treated as separately authorized replacement,
  never silently accepted as an in-place immutable artifact mutation.
- Delete checks physical identity/content against recorded expectation before
  unlinking. Already-absent resource is safe; mismatched/replaced content yields
  explicit failure/unknown outcome rather than deleting an unrelated artifact.
- Preserve enough state/receipt to reconcile after interruption; manifest exports
  contain no synthetic secret bytes, just allowed identity/digest data.

Use a minimal official SDK/framework version compatible with a scoped pinned Go
compiler. Package the compiled provider with a local filesystem mirror and a
private placeholder provider source name; no registry service needed. Publish an
ignored `ready.json` with tofu/compiler/provider executable paths and version/
checksums so later integration can use them. Source files/HCL fixtures/tests should
be safe to keep in Git; binaries/modules/cache stay ignored.

Tests should actually execute tofu import or declarative import, plan/apply no-op,
metadata change, deliberate content mismatch, lost-state recovery by re-import and
retirement/deletion. Include original local_file adoption/overwrite as contrast by
reference, not duplication. Distinguish what provider immutability protects from
external file tampering and unavoidable path/unlink races. No erasure guarantee.

Keep scope tight. If compiler/SDK/provider build is blocked after bounded effort,
produce an explicit blocker and an executable pure-Python resource-adapter fallback,
clearly labelled non-OpenTofu. Do not pretend a surrogate proves real provider
adoption. Prefer roughly 150–300 lines of provider code and a small harness over a
production plugin framework. Finish report/summary/normal done.
