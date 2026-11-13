# Per-exercise reuse — candidate design

**Final bounded status:** COMPLETE/ACCEPTED/STOPPED; [results](PER-EXERCISE-RESULTS.md) own as-built
behavior/raw failures/source qualifications. Candidate/GO/preparation below historical, no restart.

**Subsequent implementation GO:** user “implementation is GO” approves this bounded plan,
retaining concrete pre-edit/readiness gates. [Pre-edit review](PER-EXERCISE-PRE-EDIT.md) awaits
acceptance BEFORE coding/activation; [coordination](PER-EXERCISE-COORDINATION.md) owns current state.
Historical preparation wording below is superseded only within that approved scope; not as-built.

Status: **PREPARED FOR REVIEW; no implementation GO**. After the recommendation to move reuse
from whole batches to individual exercises, the user said “proceed”. The immediately preceding
offer was dependency/key design and a bounded acceptance plan, with implementation after approval.
This authorizes local design preparation only. [Example](PER-EXERCISE-EXAMPLE.md),
[conditional handoff](PER-EXERCISE-HANDOFF.md). All engineering choices below are assistant candidates.

## Goal and deliberately small family

Prove that changing one exercise's explicit inputs causes only that exercise and its downstream
projection/check to execute again, while other cases retain their actual OLD producing attempts.
Keep whole-candidate-build invalidation conservative. Random sampled refresh remains DEFERRED.

Recommend THREE deterministic cases from the already exercised `shared_index` map/get family:
positive-a(value42,faultFalse), negative-b(value42,faultTrue), positive-c(value43,faultFalse).
Change negative-b's value42→44 in the story. Both negative versions must identify the deliberately
wrong operation value; the expected rejection is not a tool error. This is a generated semantic
family, NOT three additional maintained-test conversions. The original16 assertion integration
remains intact; generic scenario dispatch and full-suite migration are deferred.

Recommend additive `per_exercise/` spike modules after a separate GO. Reuse existing canonical
E/P/C identity/artifact/Store authority unchanged and retain every older adapter/role/evidence.
No new native entity, low-level Repository API, installed-Python runtime change or general evaluator.

## Three independently selected stages per case

Each case has E/P/C requests, attempts and known selectors, using existing stage names. Granularity
comes from the case envelope, not new native request kinds. A batch is a recorded grouping of these
requests/results, not an additional computation attempt that falsely represents fresh execution.

| Stage | Dependencies in candidate key |
| --- | --- |
| E | Controller namespace; whole candidate build/native/runtime manifest; exercised helper/harness bytes; stable scenario ID; exact I64 value and bool fault; evidence contract and unchanged limits |
| P | Namespace; selected E key AND immutable artifact digest; producer publication root; decoder/extractor/schema/normalizer/materialization dependencies; case boundary and limits |
| C | Namespace; selected P key AND artifact digest; exact case authority/roots/membership/query scope; checker/SQL/transitive views/assertion contract/runtime dependencies and limits |

Keep the existing required E/P/C dependency field sets; composite manifests fit those fields.
Put scenario/parameter/profile/root context in the existing envelope context. No mask/facet/new
identity implementation is assumed. Controller namespace pins admission/recording/dispatch; replaceable
stage variants belong to their explicit stage manifests. Common-wrapper changes may invalidate
all stages conservatively; an isolated checker payload change must not change E/P identities.

A stable scenario ID identifies the logical exercise (positive-a/negative-b/positive-c); it is NOT
an occurrence ID. Actual controller run/Q/T occurrences, current batch publication, filesystem
paths and other cases' parameters are not computational inputs to this case key. They remain in
request/grouping/provenance records outside the key. The three scenarios remain distinct even if
values coincide; arbitrary label renaming/equivalence/discovery is not introduced.

Expectations/assertion policy are separately pinned and compared after SQL, never supplied as
accept/reject answers to predicates. Scope/position/source constraints used by SQL are actual
checker inputs and belong in its key. Captures/roots cannot be replaced merely because values match.

## Shared native storage without shared fixture contamination

ONE owned candidate evidence repository across the finite story, serialized access only. Fresh E
processes open that store and use short write scopes; no per-case database/lock copying. Each fresh
E constructs an isolated fixture from THIS case's value only using the existing fixed helpers,
not a fixture whose inputs are the union of this batch's values. Otherwise changing negative-b
would change the fixture identity for positive-a/c and defeat genuine selective reuse.

A fresh E produces the familiar ONE-case producer publication: parentless empty P0, then P1 with
parents=(P0,CN), description/context/observations and producer run. CN retains both checkpoint tips.
Use additive adapter code over unchanged `fixture`/`make_case`/role helpers, not calling the old
whole-directory `exercise()` which creates a new repository. Export THIS P1's portable closure to
its immutable E artifact. Producer occurrence comes from the actual E attempt, never the next batch.

ONE owned decoder repository similarly receives public imports for fresh P, with extraction from
THIS E publication only. Other physically present objects do not expand case authority. No import
or extraction on a P reuse hit. Keep existing typed extraction/case profile validation, all-parent
retention and public transfer limits. Extraction work within fresh P remains whole-case, not delta
native-object memoization; that optimization is deferred.

## New immutable index: requested versus produced

The old catalog requires every case occurrence to belong to its current run. It cannot accept OLD
producer descriptors in a NEW run by relabeling them. Recommend a NEW batch index/entry/run profile;
leave old `shared_index.catalog` and `shared_existing` profiles unchanged.

Each NEW generation starts its own parentless empty publication P0 and appends three entries:
`PN.parents = (PN-1, selected CN)`. Existing entries never change within that generation. A later
input configuration creates a separate generation, not a replacement inside an old index.

Each entry records:
- stable scenario ID/current requested parameters and current E request occurrence/record identity;
- exact selected OLD-or-NEW E terminal attempt/outcome, E key and artifact manifest identity;
- a native SubDAG link to the ORIGINAL producer description and producer run, preserving context,
  observations and occurrence; selected CN/roots remain the original producer's actual IDs;
- explicit fresh-versus-reused relation verified against the controller's satisfaction/attempt.

Native description/run links retain those DAGs; second-parent CN retains the case's actual fixture
and checkpoint history. Parent reachability alone never grants availability to another case.
Controller Q/T/outcome IDs in this evidence store are BYTES references to a SEPARATE repository,
not native links or proof by themselves. The controller's batch/grouping record links actual Q/T/O
DAGs there and records this batch publication plus its bundle/manifest identity. Admission checks
cross-check both sides. Missing controller evidence fails closed; exporting a native batch bundle
alone does not export the separate controller history or all historical producer P0/P1 publications.
Those producer publications remain in their selected E artifact bundles.

The new catalog validates current requested computational context against the selected producer
context/key and verifies all explicit roots/occurrence markers, rather than requiring the OLD
producer occurrence to equal the NEW generation occurrence. No inferred global datum origin,
rewritten OLD observations or fake new E attempt. Generation context is not silently inserted
into P/C computational keys. Aggregate publication assembly is trusted recording work on reuse,
not candidate execution.

## Per-case facts, one pooled materialization, per-case checks

Fresh P returns one immutable case fact capsule: canonical sorted typed rows, complete validated
case context/membership/roots, decoder/source receipts and manifest. Reused P returns the OLD exact
capsule. Do not include this NEW generation's label/run/publication in an unchanged capsule.

A trusted fixed materializer merges the three selected capsules into ONE closed pooled DuckDB
file for a selected generation. Verify each capsule manifest, key/upstream authority, schema and
row owner/uniqueness; identical typed-object rows may be shared, conflicting same-ID rows fail.
Pool roots are not globally merged by checkpoint number: roots/positions stay case-local and are
created as TEMP data by each C query; pooled roots remain empty. Bound the union by the existing
10000-object limit, not three times that cap. No unchecked pickle/database copying/imported verdicts.

Materialization identity includes ordered scenario IDs/P keys/P artifact digests, schema,
materializer bytes and declared DuckDB/runtime. Known identical inputs reuse the verified closed
pool; changed P selection creates a new pool. This is deterministic fixed artifact assembly with
an explicit receipt/grouping record, not a fourth generic stage or a hidden native computation.
Pool-build work, process ownership and failures are reported separately, including on reuse rounds.

C's key includes its OWN P key/artifact and scoped inputs, NOT the merged pool's file digest or
unrelated capsules. This narrower dependency is safe only if all reads are confined to THIS case:
READ_ONLY connection, TEMP availability set derived from CN, all views filtered by typed membership,
case-local roots/positions, explicit source/binding scope, no unscoped global count/join. Pool admission
is mandatory even for cached checks in a new generation. Freeze/review this confinement proof before
activation; no dependency narrowing based solely on timing or identical verdicts.

A C reuse hit loads the OLD verdict/attempt, executes no SQL, and records NEW request satisfaction.
A fresh C checks ONE case and requires exact expected acceptance or the owning map_get_value
counterexample at THIS bad-operation subject; unexpected violations/errors fail. All three
per-case agreements must hold for the outer batch assertion to pass. A selected verdict is
historical assurance, not current-platform execution or current coverage.

## Adoption, bounds and risks

Existing known-slot lookup only; unknown/failed attempts cannot satisfy a request. A found corrupt
selection/artifact errors, never triggers automatic fresh fallback. Fresh completion does not adopt.
The worked example keeps at most FIFTEEN selectors per branch under the existing16 cap: later
normalizer/candidate variants are demonstrated WITHOUT adoption, and sibling adoption replaces one
existing E slot. Do not raise the cap to accommodate a longer demonstration.

All existing native64/builtin16arguments/16positions, transfer32MiB/controller-artifact32MiB,
extract10000 and profile case16 bounds remain; actual batch size3. No new wall-clock cutoff,
semantic deadline, threshold/coverage/skip change. Process separation is not a sandbox; one serialized
owner and declared local deterministic inputs only. Cross-store artifact/commit publication is not
crash-atomic; validate before publishing grouping and never declare partially assembled batches passed.

Principal risks to review: shared fixture accidentally binding other inputs; new index rewriting
OLD producer provenance; cross-store references treated as native edges; per-case query leaking
pooled rows; conflicting shared object descriptions; whole-pool digest leaking into case keys;
controller-code pin leaking checker variants into E; selector cap exhaustion; materializer failures
being mislabeled expected semantic rejection. Meaningful controls must cover these, not omit them.

Planning is complete; review all three documents and give separate implementation GO. No fresh
native reads of retained stores, test/story/preparation/build/install, source change, commit/push,
main integration or extra worker authorized by this candidate. GHA disabled/native19 PAUSED/VP001
OPEN UNKNOWN/no standing waiver remain; main/Iteration25/shared-build ownership unchanged.
