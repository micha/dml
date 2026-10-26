# Targeted admission follow-up: immutable apply inputs

Resume your gate session; own only the original gate directory. The user permits
candidate design evolution. Read the completed hardening-review report/checks.
Preserve initial report/code/results as historical comparison before revising.

The independent review reproduced three additional flaws through your public test
barriers: (1) plan-file substitution after final checks destroys an extra retained
resource, (2) allowed file() expressions depend on uncaptured bytes, (3) an
unexported resource is created before receipt validation rejects it.

Try narrow fixes, retaining honest limited-scope support:
1. Apply EXACTLY the approved plan bytes, not a mutable pathname reopened after
   checking. On this Linux sandbox, a sealed memfd passed to tofu through
   /proc/self/fd with pass_fds is a good concrete experiment. Read once, verify its
   digest, seal against modification, and pass that same byte object to apply.
   Fail closed if sealing unavailable; do not silently fall back. An independently
   owned immutable bundle is another option if you can demonstrate the boundary.
2. Validate resource census BEFORE effects. The supported built-in-only root must
   export every managed resource exactly once, and a candidate cannot silently
   create an unexported resource. Reject malformed/empty census where appropriate.
3. Either capture referenced file inputs explicitly or reject unsupported evaluation
   expressions before planning. Do not claim restricted JSON is safe HCL. A small
   whitelist for the exact synthetic fixture language is acceptable; preserve
   support for expected variable/resource-id expressions, fail closed on unknown
   functions/inputs, and document that full-HCL integration remains unresolved.
4. Keep raw state observation logs restricted. Do not claim synthetic-value filters
   can detect arbitrary secrets; state logging sensitivity remains a limitation.

Add focused adversarial tests demonstrating original plan swap, extra resource,
file() and sensitive() cases are rejected before unintended effects. Existing
positive cleanup, receipt and crash cases should still run. Demonstrate the sealed
plan survives a mutable-path swap at the actual final-check barrier while the
extra retained resource remains present. Explain that sealing plan bytes alone
cannot constrain arbitrary provider effects or solve provider Delete authority.

Do not attempt a universal parser, PKI, real cloud integration or replacing the
fake journal. Existing real-journal bridge is negative evidence and must remain
labelled as such. Your gate remains a candidate narrow adapter.

Update report/summary, preserve initial evidence and publish followup-done.json
atomically after report. Include exact new CLI/test counts and code checksums.
Return and exit.
