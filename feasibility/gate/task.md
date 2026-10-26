# Deployment-neutral plan admission and coherent receipts

Read `../WORKER.md`, `../ITERATION.md`; own only `feasibility/gate/`. Start now.
Preserve first-wave evidence; develop a candidate policy/gate, not an approved API.
Use the verified shared OpenTofu binary, actual local/built-in providers, and fresh
ignored sandboxes only. Do not install new tools or invoke cloud providers.

Build a narrow generic admission wrapper that can be invoked from local CLI or any
CI driver; DML knows no GitHub-specific deployment mechanics. Demonstrate raw
OpenTofu saved-plan hazard, then show candidate wrapper rejection. Also test
resource replacement and mismatched observation receipts.

Bind approval/admission to exact plan bytes, configuration material digest, victim
resource identities, observed manager state lineage/serial, authoritative research
membership/root revision and live durable reservation. Prefer integration with the
journal worker's public contract; read `../journal/contract.md` when available.
You can first design/test independently, but label a fake journal. Once the contract
exists, attempt a real adapter without modifying journal files. If five-minute
bounded wait expires, deliver the independently tested gate and explicit handoff.

Test actual CLI scenarios:
- Saved destruction plan followed by new unapplied config/retention: unguarded apply
  can destroy; generic gate rejects stale config/root admission before apply.
- Current retained actual identity rejects update/replace/destroy unless explicit
  disposition authorizes it; address equality is not identity equality.
- Positive admitted cleanup in sandbox, with a durable unknown/outcome record if
  apply is interrupted. Do not claim a subprocess check makes apply atomic.
- Manifest and manager lineage/serial from one state snapshot versus separate
  output/state calls producing mixed receipts. Decode only a deliberately non-
  secret manifest; never export whole provider state to research blindly.
- Input/config change between plan and check, stale tickets after membership change,
  and a cooperating new publisher between validation and side effect.

Explain unavoidable cooperative deployment contract: arbitrary direct CLI can
bypass a gate, and state locking only covers manager operations. Evaluate whether
holding a gate lease/transaction across apply works locally, its failure recovery,
and implications for user/agent-selected deployment freedom. Fail closed on
unknown state, malformed identity mappings or missing receipt; no universal HCL
semantic parser required. Explicitly list unsupported plan/resource types.

Deliver reproducible tests, small gate code, report with alternatives and limitations,
summary and normal done marker. No changes to first-wave scripts or shared tools.
