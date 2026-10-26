# OpenTofu laboratory

Read `../WORKER.md`; you exclusively own `feasibility/opentofu/` and shared ignored
`feasibility/tools/`. Start immediately.

Test the design against real OpenTofu CLI behavior with local-only resources.
Provision a pinned OpenTofu development executable without changing the OS. Prefer
Nix pinned to the existing DML dev environment nixpkgs revision (inspect its lock),
or an official release with verified checksum. Limit provisioning troubleshooting;
report a blocker rather than silently substituting a simulator for actual CLI.
Publish `feasibility/tools/ready.json` with executable path/version if available.

Build a small reproducible Python/shell test driver that runs init, validate, plan,
apply, output, import and destroy as needed under a new ignored sandbox. Actual
local_file resources may write/delete only inside that sandbox. Built-in
terraform_data is useful for dependency/import mechanics but must be explicitly
labelled a surrogate, not proof of managing external artifacts.

Priority probes:
1. Store closure HCL source as module material and generate a root with two
   installations. Validate name isolation, provider requirements and stable
   addresses. Regenerate without state destruction; assert no unintended replaces.
2. Installation outputs as resolved bindings: compare repeated apply vs distinct
   installation occurrences, unknown-before-apply values, and how outputs become
   available after CLI import versus declarative import.
3. Adoption: can local_file adopt a pre-existing execution-created file? If not,
   demonstrate and label provider limitation. Use an import-capable local/built-in
   type to test state-only import and declarative imports without cloud mutations.
4. Lost configuration vs lost state: regeneration cannot casually recreate
   operational state; show concrete consequences with safe local probes.
5. Removal of one module instance, dependency-sensitive destruction and shared
   resources. Capture plan JSON actions, not just exit code. Probe destroy-time
   provider configuration requirements and whether omitted config can block cleanup.
6. Full HCL includes provisioners/external execution: demonstrate only benign
   sandbox code if needed and document why generation/deployment are security
   boundaries. Never execute downloaded HCL or cloud providers.

Do not overbuild. Four to eight focused CLI probes with exact results are better
than a broad mock. Network provider installation is permitted only for non-cloud
providers needed here; record version locks and failures. Ensure repeat runs do
not delete anything outside your sandbox. Preserve safe scripts/fixtures and
condensed machine-readable results. Retain raw logs under your ignored runtime.
Report changes that would accidentally modify an adopted artifact.
