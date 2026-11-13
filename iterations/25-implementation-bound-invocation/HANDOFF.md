# Iteration 25 conditional handoff: implementation-bound invocation

Status: **bounded plan/handoff reviewed; separate implementation GO required**.
The user approved preparation, then reviewed ALL THREE candidates; see
[review checkpoint](../../discussion.md#iteration25-plan-review). This records plan review only, not delegation,
source edits, validation runs or publication. Read ALL THREE [DESIGN](DESIGN.md), [EXAMPLE](EXAMPLE.md)
and this handoff before review. Exact names/schemas/engineering remain refinable and not as-built.

## 1. Capability and bounded scope

Deliver a narrow common Python node-call interface and implementation-only immutable captures.
All funcs consume an argument-map NODE and return a NODE. Intent + full argument-map VALUE is the new
slice's reuse key; binding/captures remain exact requested-versus-produced provenance, not key dimensions.
Semantic parameters belong in invocation arguments or a different intent, never hidden behavior-changing
captures under an unchanged contract. No intent-level environment or computational capture K.

Recommend NEW explicitly imported installed `daggerml.calls` (name illustrative): structural closure
construction/inspection, opaque bound targets/context-owned node access and unified `invoke`. Keep
actual fixed outer adapter/history/selection integration in NEW example-local files. Do not install
example imports, a generic registry/evaluator or the whole old captured-call validator. Both builtins
and ordinary calls actually traverse the facade; builtin dispatch keeps its exact existing handlers/
no-Q/T operations, ordinary calls keep request/attempt/adapters and validated producer authority.

Supported example: A/B add/double leaves with getter-v1 versus getter-v2 implementation captures;
A/B sum_then_double capturing the corresponding leaves. Synchronous in-process outer adapter, unchanged
public synchronous LOCAL/exchange leaves and SAME finite application direct-child custody. NEW intent-only
reuse helpers/roles; existing Iteration20–24 roles/keys/APIs stay unchanged. No low-level repository API,
C/storage/URI/layout/native node/entity/CLI callable change, async/RPC/descendant worker or resources.

No test-performance work, test restructuring/fixture pooling, new dependency, default-parallel/fast-slow
mode, workflow/budget/runner/release-control change. Existing resource-aware tooling may be used as-is.

## 2. Authorities and source review after future GO

Read machine/admin/work-mount guidance, both repositories' AGENTS, design README/discussion resume,
[glossary](../../../dml/docs/spec-next/glossary.md), implementation
[documentation guidance](../../../dml/docs/documentation-guidelines.md) and all25 candidates.
Owning sources/contracts:

- [builtin.py](../../../dml/python/daggerml/daggerml/builtin.py) /
  [builtin contract](../../../dml/docs/internal-builtins.md): Recorder ownership, strict semantic node
  profiles/typed values, bindings/handler versions, argument source ledgers, poison and16/16/64 limits.
- [captured session](../../../dml/examples/captured_call_session.py),
  [adapter](../../../dml/examples/captured_call_adapter.py),
  [profiles](../../../dml/examples/captured_calls.py),
  [leaf](../../../dml/examples/captured_call_leaf.py) /
  [captured-call contract](../../../dml/docs/captured-ordinary-calls.md): short scopes, exact source bridge,
  outer/leaf authority, phase joins, depth8, failures/custody; not an intent-only reusable API.
- [builtin_workflow.py](../../../dml/examples/builtin_workflow.py) and
  [intent-scoped reuse](../../../dml/docs/intent-scoped-reuse.md): prior cross-binding examples, not
  authority to reinterpret old helpers or equate arbitrary closure profiles.
- [caller Q](../../../dml/docs/spec-next/caller-requests.md),
  [LOCAL](../../../dml/docs/spec-next/local-execution.md),
  [exchange](../../../dml/docs/spec-next/repository-execution.md),
  [successful S](../../../dml/docs/versioned-reuse-selection.md),
  [transfer](../../../dml/docs/spec-next/transfer.md),
  [Python storage](../../../dml/docs/spec-next/python-api.md): unchanged public boundary authority.
- [validation policy](../../../dml/docs/validation-policy.md),
  [tools repair](../../maintenance/test-performance/TOOLS-REPAIR.md),
  [GHA disabled](../19-intent-scoped-reuse/GHA-DISABLED.md),
  [VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md).

Preparation verifies clean LOCAL HEAD `15555c01e4db19a20b4de7049f776c4d995bd5e0`, not pushed by this task.
Project-local tools repair is completed; read prototypes rejected, performance work postponed/goal5min
unmet. Recheck actual relevant source/index/tools after future GO, no automatic pre-edit full baseline.
Preserve unrelated design notes/uncommitted maintenance reports and local implementation ancestry.

Only if separately delegated, existing window2 agent in a NEW verified Pi session; no extra worker.
Coordinator explicitly transfers BOTH source/builds, worker owns until targeted HEAD/changed-surface
freeze and explicit release. No concurrent coordinator edits/builds. Preparation starts no session.

## 3. Mandatory concrete pre-edit review after GO

Before coding/build/run, provide a concise change-validation map and source-level plan addressing:

1. **Promotion boundary:** exact installed facade/token/node/closure constructors and structural readers,
   packaging/build integration and example backend responsibility. No raw-ID/unchecked callback success
   escape; no dynamic import-by-URI, mutable registry/private codec or installed imports of examples.
   Show that builtins and ordinary calls both traverse common invoke, rather than only sharing a name.
2. **Captures:** exact C/E/B schemas/root/types, supported dependency forms, E-before-B-before-C links,
   local captured source reconstruction, distinct outer adapter shape and no self-ID cycles. User's
   implementation-only rule affects new closures, not migration of old examples/specs.
3. **Nodes/state:** exact session versus Recorder ownership, copied canonical Datum access (including
   existing canonical equality rules), foreign/fabricated/ended/wrong-thread guards, poison semantics,
   rebinding/source association across short scopes and no writer/native handle held across dispatch.
4. **Reuse authority:** exact D/Q/T/S/W/completion/phase schemas, create-only refs/intended deltas/ordered
   parents and three pinned known slots. Key recomputation excludes B/E but request/producer checks do
   NOT. Own NEW Q precedes reuse; original outer/leaf producer witnesses remain independent. Present
   poison rejects even on fresh/mismatch; fresh/adoption/default changes remain separate.
5. **Execution:** fixed supported logical source actually invokes captured targets, two ordinary slots,
   synchronous in-process outer versus public LOCAL leaves, direct-child owner/cleanup, exact explicit
   return association and known failure versus partial UNKNOWN. No fabricated local outer completion.
6. **Bounds:** actual prospective graphs, future reservations and full requested+OLD semantic union
   within64/16/16/transfer/depth8; builtin preparation maps included. No reset per backend, new limit,
   source projection or same-valued literal replacement. Old34/50 is not new source evidence.
7. **Assurance:** focused positive/negative mapping, native versus HOST substitutions, finite faults,
   source/installed readiness/oracle/controller checks and sole13Q/10T/6LOCAL/17getter acceptance plan.
   Any missing installed/public seam or scope expansion requires review BEFORE edits/experiments.

Candidate mechanics can be refined within bounded scope, but do not silently substitute generic
recursion, intent captures, conservative exact-binding reuse or a host-computed composition.

## 4. Focused correctness checks

Use small real native fixtures where the asserted behavior is metadata/semantic authority. Execution
and custody checks use real owning mechanisms where needed; HOST substitutions remain labelled.

- Closure graph order/retention, unsupported capture/source version, defaults pinning, no future C ID,
  no intent capture/K; interface usage by actual logical outer and leaf getter source.
- Same-intent/full-MAP equality across distinct bindings/captures/input sources hits; changed intent,
  key names/kinds/full values miss. Swapped named operands differ; explicit scale variability is not
  accepted as a same-intent implementation change. No implementation correctness certification claim.
- Foreign/fabricated/closed/wrong-thread nodes/targets, value laundering, cross-context re-entry,
  caught errors poisoning success; builtin exact dispatch/normal no-per-primitive Q/T retained.
- Own NEW Q/W with requested B and OLD producer A; reject coherent wrong original request/attempt/
  closure/input/phase/producer links even when values equal. Validate both unselected/requested source
  framing and selected ORIGINAL success under their own actual bindings, not fake equal bindings.
- Outer hit: zero adapter/inner request/attempt/getter activity. Fresh outer+inner hit: own inner Qs,
  no fresh leaf T/dispatch. Explicit fresh: selected slots unchanged. Present malformed S errors even
  on mismatch/fresh. Missing/mismatch try-selected chooses fresh; require-selected errors before T.
- Exact short-scope source bridge, original add input, exact add result as double source, ordered call/
  getter positions, aggregate prospective/actual bounds and actual boundary ancestry depth8/next9.
- Native single-parent phase deltas, two-parent leaf join, complete ALL-parent retention, wrong refs,
  premature completion, duplicate/foreign call positions, old validators rejecting new outer roles.
- First leaf failure stops second; later failure retains first success; uncertain wait/import/native
  persistence/publication acknowledgment leaves UNKNOWN, no fabricated success/retry. Atomicity probes
  must exercise genuinely new rows, not deduplicated no-ops. No shared/private runtime fault hooks.

Choose a finite few causal private mutations for key exclusion versus provenance validation, moving
ref lookup, source substitution, fake callback success, outer-hit invocation and session poisoning.
Record measured assertions/results; failed or weak mutants are not implied successes. Narrow no-value
coverage exclusions need exact rationale/catalog; meaningful difficult paths still need checks.
Keep existing assertions, deadlines, skips, semantic limits and100 thresholds; no suite optimization.

## 5. Sole installed story and independent acceptance after GO

Prepare one fresh bounded isolated current-source DML install from available tools/cache, including the
NEW maintained module. Missing downloads/installations need separate approval. Capture module/native/
interpreter/CLI/helper/logical/controller/reader identities; sanitize checkout import paths. No silent
reuse of an older installed prefix as current implementation evidence.

Readiness review BEFORE launch: concrete accepted source/tenets/phase/union plans, blocked controls,
controller event-envelope regression and incremental custody logging. Counts are [EXAMPLE](EXAMPLE.md):
FIVE outer Q/FOUR in-process outer T/EIGHT leaf Q/SIX LOCAL leaf T, THIRTEEN Q/TEN T/SIX direct children/
SEVENTEEN map-get positions. No compatibility/support/primitive-construction jobs. Failure/uncertainty
STOP, finite triage requires its own question; no automatic second acceptance story.

Establish all SIX actual wait/reaped-absence dispositions, retire only owned operational paths, retain
SAME full inert history/data/source/logs. Fresh installed blocked caller/transferred-copy readers check
exact requested/produced chains, defaults/selections/value and no-job counts without logical execution,
recording/dispatch/transport/target writes. Public validation scratch separately allowed. Review failures
on SAME stopped data before considering a new computation. No duplicate coordinator story.

After final substantive changes run ONE unchanged `scripts/check.sh -v` in existing project tools,
record actual workers/commands/true exit/XML/coverage/memory results. No extra harness cutoff replacing
completion; no automatic second full or runtime deadline/coverage/reporting weakening. Generated test
source labels must respect existing precise reporting exclusions, not force another unapproved coverage
omit. Original failures remain raw; attribution/related native19 recurrence needs fresh scoped triage.
Freeze changed paths/HEAD/diff/source/relevant evidence and release BOTH before risk-based focused and
SAME-history NONEXECUTING independent review. Prior performance timings not acceptance for new code.

## 6. Documentation, conditional delivery and stop

After future implementation document NEW maintained interface's actual construction/invocation/ownership
contract and informative fixed backend story. Distinguish structural inspection from execution/success
proof and cross-implementation equivalence declaration from verified arithmetic. Link old authorities;
do not silently rewrite old capture keys. Review glossary consistency and
[as-built diagram guidance](../../../dml/docs/documentation-guidelines.md#as-built-visualization-maintenance):
ordinary roles use native DAG/node/tree/commit/ref, not new closure/intent/call LMDB entities. No proposed
schema/API drawn as implemented; change diagram only if actual displayed claims change.

Only after separate implementation/delegation/publication permission AND independent acceptance:
focused staged audit/worker commit/NORMAL existing push, exact accepted-current-committed-parent-clean/
live remote identities, final RESULTS and explicit STOP ALL/source-BOTH-prefixes-stopped evidence return.
No force/amend/tag/release/package/design publication. Local unpublished maintenance ancestors must be
accounted for explicitly in publication review, not silently treated as a feature-only remote delta.
Development GHA stays disabled/NOT RUN/not pass; no enable/run/workflow/settings/budget/runner change.
Read-only workflow-state verification is allowed only as part of separately authorized final delivery.

VP-001 remains OPEN/UNKNOWN, same coordinator owner/revisit conditions/no standing waiver; planning
revisit recorded in DESIGN. Native19 remains PAUSED/private incomplete-unexecuted candidate retained.
No async/LMDB/open/lifetime repair, related story restart, extra agent/cloud/global/service/image,
resource/cache/evaluator framework, later feature or push/design checkpoint commit follows preparation.
BOTH builds/source remain coordinator-owned, old workers stopped. Review these candidates, then separate GO.
