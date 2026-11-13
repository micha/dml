# FOUR late shallow-duplicate raises — source-only no-value assessment

Status: **PROPOSED; NO marker approval/edit/run**. Other work STOPPED pending direction.
This assesses ONLY four exact statements, not their conditions/functions or meaningful authority.

| Exact raise | Current earlier native invariant |
| --- | --- |
| `p.inspect_closure`: `fixed outer capture names differ` (265) |`leaf.shallow_closure` follows THIS C's native E and requires exactly role/add/double/map-get |
| `p.inspect_closure`: `fixed outer capture kind/intent differs` (269) |Same shallow E reader checks each native capture's exact STRING kind and canonical URI intent: ordinary/add, ordinary/double, builtin/map-get |
| `leaf.environment`: `leaf requires exact getter captures` (102) |`shallow_environment` on THIS supplied E requires exactly role/map-get/list-get |
| `leaf.environment`: `leaf captured func kind/intent differs` (105) |Same shallow reader checks BOTH named rows have native STRING builtin kind and respective map-get/list-get URI |

## Why the later statements cannot fail on legal native input

1. `shallow_shape` first raw-size-guards then obtains a copied native DAG description; exact native
   fields/root/role are checked. `shallow_link` resolves an actual SubDAG node/target, not a mutable
   name/ref or source-origin lookup. Kind/intent comes from the linked row's native scalar datum.
2. In outer inspection, the later `c.inspect_closure(tx, dag)` reads the SAME immutable native C ID,
   follows its SAME E field ID, and returns captures from precisely those E named bindings. In leaf
   inspection, later `c.inspect_environment(tx, dag)` receives exactly the SAME immutable E ID.
3. The structural walk checks exact profiles/types/root/roles, iterates every unique canonical native
   name, returns `(name, Capture(kind,intent,target))`, and does not filter/rename captures or infer
   kind/intent from targets. Its complete successful memo preserves those native fields; repeated
   child validation/height/state checks cannot change names/kind/intent.
4. There is NO logical-code/backend/recorded-source execution, dispatch/import callback, URI fetch,
   mutable registry or caller-supplied capture/proof result between these checks. Outer retained
   inspection is native read-only reachability; structural checks are native reads only. The example
   read view holds copied immutable descriptions and rechecks native owner/thread/ended state; mutable
   ref lookup values are ignored, never used to retarget C/E/rows.
5. Native immutable parent-first insertion/collision/hash validation and a single actual storage
   transaction pin the records. No legal writer can replace an immutable C/E record under the same
   content ID. A failed native read, thread/lifetime/budget/height error raises earlier instead of
   producing a contradictory successful description.

Thus successful shallow checks establish exactly the late names and `(kind,intent)` predicates;
a contradictory later tuple requires a fabricated transaction/native/Inspector result, monkeypatched
helper/callback, illegal record rewrite/hash collision, or a broken owning native/structural contract.
Forcing those false descriptions exercises a Python branch, not native assurance under this trusted
prototype. This is NOT a security sandbox or hostile-callback guarantee; no proof is borrowed across
transactions or hypothetical mutable snapshots.

## Precise proposed exclusion boundary

ONLY the four raise statements above are no-value candidates. Keep all four conditions/loops/guards
and EVERY earlier shallow raw-size/role/name/kind/intent check measured. Do not exclude a block,
function, Source file, or reduce remaining100 threshold. No marker has been added.

Explicitly NOT part of this proposal: outer retention/intent, supported builtin version, captured
source BYTES/adapter/interpreter, shared getter binding, structural type/budget/depth/full-height/B-E
association, constructor prospective admission, ORIGINAL successful Q/T/R/F/public selection/producer
history, exact phase/delta/ordered parents/refs, failures/UNKNOWN/custody. Those can reject real native
application states and remain meaningful tests. Generic `calls` capture-kind/intent/depth guards are
NOT shallow-duplicate raises: its public structural API accepts other names/targets before adapter
constraints. No exclusion is proposed there.

Current native malformed C/E and fixed shallow shape/kind/intent tests, plus IC-003 work/size/state
and public-valid ORIGINAL producer corruptions provide actual earlier-layer assurance. Existing raw
unions/missing counts remain unchanged—not passing tests or justification to hide these paths.

Revisit these four implications if shallow field/type requirements, C-to-E links, returned capture
construction/filtering, callbacks/reentrancy, transaction/read-view ownership, mutable records/refs,
native identity/read/import semantics or structural memo behavior change. Future comment-only markers
would alter BOTH profile and leaf source hashes/captured B bytes: preserve actual old hashes/source/
coverage, verify full AST INCLUDING locations equivalence, qualify old measurements and refresh final
current source/install readiness under separate permission. No experiment/marker/build/test/reader/
full/story/install/CI/publication authority follows this SOURCE-ONLY assessment.
