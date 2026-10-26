# Integration and synthesis

Read `../WORKER.md`; write only `feasibility/integration/`. Start immediately once
all four first-wave reports and done markers exist. If history is still running,
wait in bounded short intervals for at most five minutes, then report what is
missing rather than guessing. Read the four reports, summaries, experiment code,
and safe condensed evidence. Coordinator wants integration, not repetition.

1. Independently rerun safe tests and real OpenTofu probes in fresh workstream
   sandboxes, after reviewing code for path/credential safety. First-wave scripts
   may have fixed runtime locations; use subprocess/temporary directories/env
   only if supported or document exact rerun behavior. Do not modify their files.
   Do not silently change module dependencies or skip provider failures.
2. Produce a small executable cross-workstream scenario if practical: actual
   OpenTofu installation outputs -> model bound closure -> distinct execution
   requests/attempts/result/reuse -> adopted-resource obligations (explicitly
   simulated unless real supported provider) -> retained histories across repos
   -> requested excision/GC -> disposal outcome. Avoid brittle adapters merely to
   claim integration; fixture replay is acceptable only if labelled as such.
3. Add a safe `run-all` entrypoint that reruns models and lab tests, with statuses,
   exact versions and durable condensed results. Scripts must never destroy
   existing resources or mutate the implementation checkout. Keep fresh sandbox
   paths bounded and ignored; offer model-only mode if lab tooling unavailable.
4. Synthesize a ranked issue register. Separate falsified claims, implementable
   engineering gaps, user policy decisions and untested hypotheses. Cover closure
   identity/adoption-state acknowledgement, arbitrary HCL composition/executable
   side effects, state/config regeneration, retention vs resource dependencies,
   multi-repo destructive races, provider ownership granularity, and erasure.
5. Recommend the smallest next prototype and go/no-go gates, without treating
   mock tests as proof of DML C integration, AWS behavior or distributed safety.

The OpenTofu and adversarial summaries contain particularly strong claims about
S3 update-empty-body and all-version deletion. Those are source findings only.
Do not turn them into cloud-tested findings. If a reported number/action cannot
be reproduced, flag it; do not smooth away discrepancies. Preserve sources and
report paths. Raw agent sessions are not evidence.

Deliver `report.md` (~1200–2200 words), machine-readable test/issue summaries,
reproducible integration scripts, and the normal atomic done marker. This task
owns the synthesis report; the coordinator owns the main index and final verdict.
No commits or deployment/implementation changes.
