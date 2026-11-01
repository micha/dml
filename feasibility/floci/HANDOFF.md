# Floci feasibility assignment

## Authorization and ownership

The user asked the existing window-2 agent to establish Floci feasibility so the coordinator
can preserve its context window. This is a separate bounded feasibility study, **not Iteration11
GO**, DML implementation/specification work, or permission to restart completed Iteration10.

Existing worker `%215` in `dml-design:2` has a verified empty new Pi session. Coordinator `%197`.
No additional agents. Worker owns this study's report/reproducible probes under
`feasibility/floci/`; preserve coordinator's uncommitted Iteration10 design notes. Implementation
`../dml` is read-only, clean at published099d156. Do not use/wipe its shared builds.
No worker/design commit or push, release/package publication, cloud/second-host/remote Docker,
global installation/service/firewall changes or unrelated resource operations.

## Required reading

Read machine instruction index first and follow it; verify `/work`. Read design AGENTS/README,
current discussion/resume/glossary, feasibility index/ITERATION-RESULTS/final audit for historical
limits (do not execute old coordinator/done-marker protocols). Read implemented SSH/asynchronous/
caller-request/transfer/local contracts and Iteration10 RESULTS/REVIEW as needed for DML boundaries.
Use Context7 skill for current library/API documentation; consult pinned primary Floci docs and
source, not marketing/README alone. Current docs indexed as `/floci-io/floci` advertise Batch
immediate and real Docker runner modes; establish which released version actually contains them.

## Question

Could a **Batch-style execution adapter tested locally against Floci** let one bounded invocation
submit a real job, exit, and later fresh invocations poll the same job and retrieve DML history,
without requiring the caller to retain a foreground SSH connection or inventing a DML supervisor?

The adapter owns submission/polling/retrieval/cleanup. Floci would provide external job execution
mechanics. This is a candidate direction, not an architectural/API agreement. Floci's default
`immediate` success simulation must never count as actual computational execution evidence.

## Work order

1. Pin primary source/release/image identities. Audit Batch Docker mode's actual submission,
   job lifecycle, real command execution, DescribeJobs, attempts/retries, timeouts, cancellation,
   failure/logs, persistence/restart and container/resource ownership. Determine support/version
   gaps explicitly. Read actual implementation enough to distinguish documented vs operational.
2. Inspect only explicit local Docker socket/context/cache/tools/prerequisites. Use cached tools/
   images and isolated project sandboxes. If realization needs image pulls/downloads/installations,
   report exact minimal pinned prerequisites/provenance/size/placement and request scoped approval
   **before** doing them; do not silently inherit completed Iteration9/10 provisioning permission.
3. Where prerequisites permit, run bounded local real-Docker probes in owned named/labelled fixture
   resources. Floci API must be loopback-only; no AWS endpoints/real credentials, use synthetic local
   credentials and explicit endpoint on every SDK/API request. Docker socket access is substantial
   authority: explain fixture trust, ensure local daemon only, no project/A/sensitive/shared runtime
   mounts, no privileged/global changes or broad exposed listener. Agree a narrowed profile or
   report blocker rather than bypassing isolation. No existing container/image retag/prune/deletion.
4. Minimum actual evidence: submit a gated real container, prove SubmitJob returns while work is
   still gated, submitting client exits, fresh client polls same job ID, out-of-band gate advances
   work, result bytes are really computed, nonzero-after-result failure and job/attempt identity
   are preserved. Polls must not launch another computation. If useful use installed current DML
   wheels read-only in an isolated job to publish/return history; no production adapter/integration.
5. Evaluate smallest input/progress/output exchange (candidate S3 vs another explicitly bounded
   mechanism). Assess pinned full-history bundles/exact caller Q/unchanged-head receive feasibility,
   not only service-status polling. Service SUCCEEDED/FAILED is **not** automatically DML done or
   its computational/cleanup outcome. Include launch/acknowledgement-loss ambiguity, duplicate
   submission/idempotency limits and Floci retry implications for DML attempt occurrences.
6. Distinguish API simulations/mock faults from actual Docker process tests. Only safe before-spawn/
   after-reap loss barriers; never kill/disconnect a computational child for convenience. Finite
   cooperative gates released in finally, prove owned-writer/container disposition before fixture
   retirement. Retain owned fixture/B/evidence as blocker if disposition cannot be proved. Do not
   follow serialized historical paths as cleanup authority. Restart/host-loss claims only if tested;
   not required to promise durable remote lifetime or AWS equivalence.
7. Produce concise decision-ready REPORT.md plus minimal reproducible safe probes where worthwhile.
   Include exact source/release/image/commands/exits/evidence, functional gaps, security/ownership,
   simulation vs real execution, restart limits, costs/prerequisites, and smallest bounded Iteration11
   recommendation. Verdict: viable / viable with constraints / blocked / unsuitable, with falsifiable
   criteria. Missing runtime evidence is blocked/unverified, not passing feasibility. End with a
   short synthesis (roughly one screen) so coordinator need not ingest all raw docs/logs.

## Scoped image-pull approval

After worker primary-source/release audit, user approved via questionnaire **only**:

```sh
docker --host unix:///var/run/docker.sock pull --platform linux/amd64 \
  docker.io/floci/floci@sha256:09b72c45f333019adecb302e79c6b746e290135f528016c8514618bc7ab02344
```

Floci2.3.0 released tag SHA `ee15f502bfc017861b67b076b82e1ccd032c7129`; worker reports
86,782,013 compressed layer bytes (~83MiB), unpacked unknown. Pull into existing `/work/docker`;
retain image, no retag/prune/install/build/cloud. Postpull source/image correspondence must be
verified before running (prepull config metadata read failed HTTP400). Report actual provenance/
size and finish socket-authority/network/loopback/no-sensitive-mount safety audit; submit precise
fixture run/network profile for coordinator review **before launch**. Do not inherit SSH fixture
host networking: worker source audit finds embedded DNS binds0.0.0.0:53 in container detection,
so host-network Floci would broaden exposure. Narrow private internal bridge/loopback-only HTTP
publication or private-bridge clients remains candidate, not authorized workaround.

## Accepted narrowed fixture profile

After approved pull, worker verifies Floci2.3.0 OCI revision matches released source and Docker
reported Size345463540 bytes (~329.5MiB), not exact disk allocation. Coordinator accepts precise
`runtime/profile-proposal.txt`: new owned labelled **internal private bridge, no host networking,
no published ports/public listeners**. Namespace-private HTTP/DNS is accepted instead of literal
127 within Floci; this is no public exposure, not inherited SSH host-network permission.

Trusted pinned Floci has local rw Docker socket authority (daemon-root-equivalent, not sandbox),
new private labelled volume, constrained nonroot/cap-drop/no-new-privileges service container.
Cached immutable Node clients/jobs run on same private bridge without mounts/socket; attempts1,
synthetic explicit local API/S3 endpoints, finite gates/natural reap, restart only after reaping.
Batch child lack CPU/PID limits is qualified; trusted finite workload only. Verify effective
network/internal/noPortBindings/socketGID/OCI/user/security/resource/env/service controls before
submission. Capture exact IDs and correlate service-created children with owned job IDs; no
broad prefix-only destructive cleanup. Uncertain disposition retains fixture/evidence as blocker.
No downloads/global service/firewall/profile weakening/production DML integration authorized.
Proceed bounded real execution/fresh polling/exchange evidence under this exact profile.

## Narrow synthetic DML replay authorization

Worker reports real private-profile Node jobs/success/nonzero23/S3/polling/reaped restart pass,
owned resources archived/retired. Coordinator approves optional replay of **known synthetic
Iteration10 P/U/F packets/current reviewed wheels** only: source artifacts/implementation read-only,
new study sandbox, cached Python/local wheels, no downloads/build/shared-build/CI/spec integration.
Recreate fixture only under exact accepted pinned private profile with new owned IDs/retirement
checks. Verify selected data provenance/no credentials/sensitive research; S3 transfer of complete
packet files with exact original bytes, public read_observation/explicit-ref receive into new A,
independent typed-byte/all-parent/ref preservation oracles and bounded wrong-Q/phase rejection.
Never execute captured source/dispatch DML/follow historical paths as authority. Report this as
**transport/validation replay of prior DML execution**, not DML running in a Floci Batch child or
an end-to-end production adapter pass. Node real-job evidence remains separate. Finish concise
report with tested/composed/untested capabilities; no Iteration11 GO or expanded profile.

## Post-run harness audit and bounded correction

Worker discovers initial service-key regex missed EC2's enabled field after comments. Initial
Node/S3 evidence therefore includes additionally enabled **private EC2/9169 IMDS**, no EC2
calls/children/public ports; archived/retired, not proof of exact four-service profile. Coordinator
approves focused harness correction/rerun only: robustly enumerate all released enable keys,
explicit EC2=false, assert effective enabled-service set exactly batch/s3/cloudwatchlogs/iam
**before submission**, verify actual private9169 absence if disabling EC2 prevents it, abort on
profile mismatch without widening exposure. Natural completion/reap/archive/exact-owned retirement
unchanged; preserve deviation rather than rewriting initial evidence.

Initial packet validator's wrong-matching-Q rejection raised native NotFoundError rather than
its too-narrow expected ExchangeError; correct private oracle/fresh sandbox, no runtime changes.
Keep association-specific rejection distinct from missing-base/foreign-Q typed rejection and
preserve failed harness evidence. Report final corrected-profile evidence separately.

## Communication and stop

Send compact progress/blockers/questions to coordinator `%197` via tmux. Coordinator expects an
initial source/prerequisite verdict promptly, then full evidence-backed recommendation. Keep
raw logs/artifacts/keys/runtime ignored; never commit sensitive data. No new agent/session/window,
production code/spec/diagram edits, full DML builds/CI, commit/push, provisioning/resource subsystem,
cloud execution or later feature work. Stop after report and owned resource disposition, pending
coordinator/user review. No historical completion-marker protocol.
