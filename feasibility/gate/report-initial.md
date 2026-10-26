# Candidate deployment-neutral admission and receipts

## Verdict and authority boundary

**A narrow cooperative gate is feasible locally; end-to-end research-resource
admission remains incomplete.** Actual OpenTofu saved plans bypass newly added,
unapplied retention configuration. The candidate rejects those plans and other
stale receipts before applying. A durable fence and a local writer transaction
exclude a cooperating publisher across apply, at substantial availability cost.
Neither makes the external effect atomic.

This report owns this worker's experimental evidence, not DML policy or an approved
API. [gate.py](gate.py) uses a deliberately labelled **fake research journal**:
its membership and retained UUIDs are manual fixtures. The separate real-journal
probe uses the public [journal contract](../journal/contract.md), stored commits
and actual heads, but rejects an unsupported physical-identity bridge. There is
no successful joined OpenTofu/file-journal disposal claim.

## Reproduce and evidence

From the design repository:

```sh
python3 -B feasibility/gate/run_tests.py
```

The final run passed **28 named result groups**, including **130 OpenTofu CLI
invocations**, three wrapper CLI subprocesses, barrier-controlled publisher/apply
processes and two real process exits. See [test-results.json](test-results.json)
and [run_tests.py](run_tests.py). Raw manager logs, states, databases and generated
configuration are ignored under `runtime/run-58fab76a/`. Seven fresh runs are
retained, including two early development failures; the runner refuses a ninth
and never deletes an existing sandbox. Those failures exposed omitted raw-state
`sensitive=false` fields and invalid empty JSON resource blocks; the fixes did not
change first-wave evidence.

Executed versions: Python **3.13.15**, OpenTofu **1.13.2**, Linux amd64, built-in
`terraform_data` only; no downloaded provider, tool installation or cloud call.
Each CLI invocation verifies the shared official archive SHA-256
`723bebb0df8411daff1e5fc3862e28ff5581fe5634087f4c29a9aa41d78208b5` and compares the
executable to its archived bytes. This consumes, never modifies, shared tooling.

The wrapper itself was invoked successfully as separate processes:

```sh
python3 -B feasibility/gate/gate.py plan --root "$SANDBOX" \
  --journal "$DB" --ticket "$TICKET"
TOKEN=$(python3 -B feasibility/gate/gate.py reserve --root "$SANDBOX" \
  --journal "$DB" --ticket "$TICKET")
python3 -B feasibility/gate/gate.py apply --root "$SANDBOX" \
  --journal "$DB" --ticket "$TICKET" --token "$TOKEN"
```

The runner allocates these variables as fresh paths and logs exact argv. A local
CLI, scheduler or any CI driver can invoke the same protocol; nothing knows
GitHub mechanics. This is a candidate deployment contract, not a production CLI.

## Executed counterexamples and rejections

1. **Saved-plan hazard:** save `tofu plan -destroy -out=cleanup.tfplan`, then write
   `prevent_destroy=true` without applying it. Candidate apply rejects
   `stale configuration/input`. Direct `tofu apply cleanup.tfplan` still deletes
   the actual built-in UUID. The reserved ticket cannot police bypass. Independent
   root/membership-change probes also reject earlier tickets even though manager
   state did not change.
2. **Retained identity:** actual update, replacement and removal plans identify the
   prior UUID from `change.before.id`; admission rejects all three when that UUID
   is retained. Explicit disposition then admits cleanup and observes an empty
   manifest. A real unguarded replacement produces a different UUID at the same
   address; retaining the old UUID does not retain its successor. An update of
   that successor is admitted. Address equality is not physical identity equality.
3. **Mixed receipt:** read outputs, perform a real replacement, then read state.
   Combining old manifest UUID with new lineage/serial is rejected. The coherent
   extractor instead derives manifest, actual instance IDs, lineage, serial and
   snapshot digest from **one** `state pull`. Missing/publicity-invalid manifests,
   malformed mappings and unknown serial fail closed. Old observations, altered
   plan bytes, changed tfvars and omitted ticket victims are rejected separately.
4. **Interrupted driver:** real `os._exit(73)` before dispatch leaves durable
   `unknown` while the resource still exists. A second exit after successful actual
   cleanup but before outcome publication leaves `unknown` despite an empty
   manager manifest. Blind retry and new publication are rejected. These are kills
   around dispatch/acknowledgement, **not** a tested mid-provider-operation kill.
5. **Publisher between validation and effect:** the apply process pauses at a
   pipe barrier after final checks with its SQLite writer transaction held. Another
   process attempts `BEGIN IMMEDIATE` with zero timeout and observes the lock.
   Only after explicit barrier release does apply run and publication finish.
   No sleep-based ordering establishes exclusion. A durable reserved token also
   blocks publication with no transaction currently held.

## Candidate binding and receipt rules

The ticket binds exact saved-plan bytes, captured configuration/input file bytes,
manager snapshot digest plus lineage/serial, address-to-UUID victim mapping and
journal root/membership revision. Reservation persists the entire ticket and an
opaque token; apply requires that exact live record, rechecks policy and recomputes
victims from the saved plan. It checks before committing `unknown`, and again
inside the effect transaction. Update counts as a victim operation, not just delete.

Captured material is `main.tf.json` plus optional `inputs.auto.tfvars.json`.
Inherited `TF_VAR`, CLI-argument overrides and credential environment are not
passed to manager subprocesses. Source and inputs are controlled synthetic
fixtures, not a universal HCL sandbox. Unknown extra configuration is rejected.
The manifest is deliberately non-secret and exposes only built-in UUIDs. Full
state is decoded locally to validate the projection and retained only in ignored
manager logs; it is not published as research data. A state hash is not a general
confidentiality or erasure mechanism.

`terraform_data` UUIDs are manager-owned surrogates, not proof of artifact ownership.
For this limited type, observing successful apply plus the projected manager state
is adequate experimental evidence. It is not universal physical-absence evidence.

## Real journal adapter: negative integration evidence

[journal_adapter.py](journal_adapter.py) imports the unchanged public journal
source and selects **gate-owned** runtime paths through its supported constructor.
The final executed contract is `journal-v2`, source SHA-256
`fc178a5fdcf0150de37b9cbd0a70d727903926e5fc2d95793cba5a39912a7912`.
Contract/source changes during development are recorded in earlier ignored runs.

The probe creates a real journal-managed synthetic file, stores an operational
commit and publishes its head. Its derived roots reject disposal while retained;
a new member invalidates the old revision. After excision, the adapter still
rejects a mapping from the manager UUID to that file: their physical identities
are different. **The adapter's positive apply path is not executed.**

To falsify acknowledgement-by-exit-code, a deliberately mismatched independent
probe reserves the journal file with the actual manager-plan digest, persists
intent, and confirms the real journal rejects a new publisher. An actual manager
cleanup succeeds, but the file remains; journal `ack` rejects `absence not
observed`, preserving durable `intent`. The journal's own file effect and absence
ack subsequently complete. This is executed negative evidence, not joined cleanup.
A backend registration/identity/absence seam is the explicit handoff.

## Cooperative deployment and recovery tradeoffs

Arbitrary direct CLI bypasses the gate. Manager state locking coordinates manager
operations, not publication of new research references. Stronger retention safety
therefore requires every participating publisher and deployer to honor a common
admission/fencing protocol. Deployment tooling can remain user/agent-selected;
its mechanics need not enter DML, but completely uncooperative deployment freedom
implies weaker guarantees.

The local transaction works across a subprocess, but cannot atomically couple
SQLite, OpenTofu and future provider effects. A crash rolls back that transaction;
the previously committed reservation/unknown record survives and fences new work.
There is intentionally no automatic lease expiry, cancellation or blind recovery
API in the fake journal. An investigator must reconcile the exact identities and
record a trusted outcome before release. Remote leases would need fencing tokens
that the actual effect receiver honors, not merely a timer in the gate.

## Prioritized gaps, alternatives and next experiment

1. **Real identity/absence integration:** add a backend-specific managed identity
   registration and observation contract, then join the import-capable artifact
   provider to journal roots. A UUID-to-file alias is not a fix. Keep disposition
   durable until actual absence is observed.
2. **Authoritative policy:** replace the fake journal entirely. It has no actual
   commit roots, ownership registry, dependency closure or disposed-identity
   publication checks. It even permits publication after completed cleanup;
   the test reports this explicitly. Real journal policy covers more of this, but
   positive gate integration remains unproven.
3. **Concurrency/recovery:** compare coarse global fences against victim-scoped
   reservations. Global fencing is simpler but blocks unrelated research during
   long applies or unknown outcomes. Test real kills during an import-capable
   provider's operation and a second deployment process, not only driver gaps.
4. **Unsupported capabilities:** HCL text, modules, remote providers/backends,
   count/for_each/indexed/deposed instances, imports, data sources, provisioners,
   arbitrary lifecycle effects, ephemeral/external inputs and general provider
   resource types are outside this gate. Fixture expression trust is assumed;
   there is no universal semantic parser or hostile-filesystem protection.

An immutable captured deployment bundle or isolated worktree can narrow file-edit
races; this prototype's checks alone cannot prevent a noncooperating actor changing
plan/configuration after validation. Another alternative is regeneration/replanning
immediately before effects, still requiring admission against current roots.
No distributed correctness, DML/LMDB integration or real research/cloud safety was
established. These alternatives and policies remain proposals.

Documentation evidence is supplementary: Context7 reported quota exhaustion and
the rendered official site returned 403. Official repository sources for
[saved apply](https://raw.githubusercontent.com/opentofu/opentofu/main/website/docs/cli/commands/apply.mdx),
[state pull](https://raw.githubusercontent.com/opentofu/opentofu/main/website/docs/cli/commands/state/pull.mdx)
and [JSON format](https://raw.githubusercontent.com/opentofu/opentofu/main/website/docs/internals/json-format.mdx)
were downloaded into ignored runtime paths. Those are current `main`, not pinned
1.13.2 guarantees. Safety conclusions above come from executed probes; broad
provider support and remote fencing remain conjectural.
