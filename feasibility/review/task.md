# Independent feasibility review

Read `../WORKER.md`; own only `feasibility/review/`. Start now reviewing first-wave
artifacts; integration is still running. Later wait in bounded intervals for at
most 15 minutes for integration/report.md and its done marker. Do not alter other
workers' files or conclusions to make review pass.

Be an independent skeptic. Read the agreed exploratory design, all four specialist
reports and relevant code/evidence, then the integration report. Verify:
- test/probe counts, evidence labels and whether tests really establish the claims;
- scripts confine mutations to newly created sandboxes and never access credentials,
  cloud resources, existing artifacts or the production DML checkout;
- key assertions about OpenTofu import, lost state, provisioner removal, address
  stability, output sensitivity and S3 versions/metadata against actual results or
  primary pinned source. Do not execute any cloud operations;
- model safety assumptions (global fences, root census, lifecycle decisions), race
  enumeration completeness and whether integration is actual or replay/simulation;
- gaps not yet caught: head/export aliases, queued stale plans, replacement identity,
  output-vs-state race, HCL external effects, adoption after resource excision,
  artifact identity versus resource names and legal erasure guarantees.

Rerun model tests and selected actual CLI probes yourself in fresh safe sandboxes
where feasible; avoid raw agent logs as evidence. Separate independently reproduced
claims from inspected-only claims. If source files absent, you may fetch public
primary source under your own ignored runtime, with documented revision/checksum.

Produce `report.md`, `summary.json`, and atomic done marker with a clear verdict
(ready for narrow next prototype / needs corrections / blocked), ranked defects
in the study itself, any reproducer and recommended corrections. Include at least
one concrete adversarial check beyond parroting the first reports if possible.
Findings requiring new design choices are not necessarily bugs. No user policy
is approved by this review. The coordinator will resolve or disclose substantive
study defects before finishing.
