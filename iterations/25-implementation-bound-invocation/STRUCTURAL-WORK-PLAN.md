# Structural capture work: source-only assessment and proposed correction

Status: **PROPOSED; STOP this change before edits/probes pending explicit coordinator review**.
This is a correctness/boundedness issue in the NEW promoted structural facade, not performance work,
not an experiment/provisioning request and not a native/public-repository API expansion.

## Current source and exact problem

`calls.inspect_closure` validates B then calls `inspect_environment`; every ordinary named capture
calls `inspect_closure(target, depth+1)`. Both functions maintain only the current active path;
a completed child is not remembered. `put_environment` separately inspects every ordinary child
at depth1; `put_closure` reinspects the completed E. Depth8/captures16 bound path length/fanout,
NOT total repeated validation work. Supported prototype adapter checks come AFTER generic recursive
structural reading, so unsupported captures can consume this work before rejection.

A legal shared graph can use ONE LOCAL B, nine C/nine E levels and eight capture-row DAGs. At each
nonleaf E, sixteen distinct legal names all link the SAME capture-row DAG/ordinary child C; deepest
E has zero captures. Thus only **27 distinct DAGs** (plus typed nodes/datums) suffice. LOCAL B has no
E field, so the same structurally valid B can be used at these levels; no future IDs/cycle/forward
reference/hash forgery is needed. Same intent/shape does not authorize running that source.

For one root C at depth0 with eight ordinary-edge levels:

```text
C validations = sum(16**d, d=0..8) = 4,581,298,449
E validations = same
capture-edge validations = 4,581,298,448
leaf C/E visits = 16**8 = 4,294,967,296
```

Each repeated C validates B and its source fields; native typed reads/canonicalization/copying repeat.
A one-MiB source within existing binding profile can therefore be recopied billions of times.
Native transfer limits charge distinct objects, so this small graph remains below them. Although
mathematically finite, the current practical structural work bound is unsafe.

Constructors have the SAME issue: the final `put_environment` checks sixteen depth1 child graphs,
then `put_closure` walks that E again. Constructor validation does not require a DML commit, and
has no separate transfer/export work bound. A valid first call or unsupported adapter cannot rely
on later transfer validation to protect the structural reader. No run was used to establish this.

## Narrow proposed correction (no implementation yet)

Introduce ONE private structural-walk context per public structural reader/constructor invocation:

1. Actual supplied transaction identity, creating thread and active traversal path.
2. Successful immutable structural results per `(profile-kind, DAG ID)` plus their exact maximum
   **ordinary capture-edge height**. This is visited validation within ONE operation, not a persisted
   cache, arbitrary builtin/read wrapper, repository cache or computational reuse registry.
3. Distinct typed-record membership and raw record-byte accounting using existing PUBLIC native
   reads/IDs. Use existing transfer object/record/packed-byte limits as the authority, not a new
   numeric cap or raised semantic64/depth8/16 limit. No alternative packed codec/hash.

On EVERY entry, including a completed/visited child:

- Enforce original requested depth0..8 and active-cycle condition BEFORE visited reuse.
- Validate real owner/thread/ended state through an actual public typed DAG read, not supplied flags.
  The C/E/capture DAG descriptions are bounded small fixed-field profiles; do not reread large B source
  on each edge. Do not keep a native handle beyond its supplied short operation/scope.
- A successful visited result is usable ONLY when `entry depth + stored full height <=8`.
  A node first visited shallowly cannot bypass a later deep path. Height is computed from the complete
  validated capture structure, not a zero/reset/count flag. Active cycle guards stay intact.
- Failures/partial proofs are never reusable. No class constructor/Inspector bypass, active-set reset,
  caller-supplied memo, trust flag or cross-transaction result reuse.

Each C/E/capture row/B is fully inspected at most once in the walk; all sixteen named positions/names/
intent-kind-target relationships are STILL checked. Shared capture rows/child C do not merge positions.
Every ancestor receives the real child height. A typed structural work membership/byte check precedes
recursive processing and semantic fields/large source materialization where the existing APIs permit it.
Native record reads themselves allocate before size checks, as existing transfer authority documents;
no new native bounded-read/RSS/time guarantee is claimed.

### Constructors

`put_environment` validates ALL supplied capture entries with the SAME walk context BEFORE any row
puts, not sixteen independent contexts. The new ordinary edge is charged exactly as current depth1
construction. `put_closure` similarly uses one walk for E/B validation; no self-ID cycle or source
version relaxation. Public output C/E schemas/types/API names remain unchanged.

Reserve conservative NEW metadata records/bytes before constructor puts, within existing transfer
limits. No private codec is needed: native owning layouts supply fixed conservative reservation sizes
(records.md: datum40+payload; objects.md: node40, DAG40+sum(20+name bytes)). For N captures:

- Capture row: at most8 new records, `420 + len(CAPTURE_ROLE) + len(kind) + len(intent)` packed bytes.
- E: at most`N+3` records, `144 + len(ENVIRONMENT_ROLE) + 60*N + sum(name byte lengths)` packed bytes.
- Combined environment at most`9*N+3 <=147` new records. Sharing/dedup may use less; no optimistic
  subtraction without actual existing native identity evidence.
- C: at most7 new records, `388 + len(CLOSURE_ROLE) + len(intent)` packed bytes.

Lengths use validated ASCII native names/URI and fixed ASCII roles/kinds. Reservations are size
upper bounds for safety, not a new encoding/hash implementation. Each record also obeys existing
MAX_RECORD_BYTES. Actual inserted rows remain authored through unchanged public mutation APIs and
native transaction poison/abort. No graph/statement omitted to lower budget; no post-put application
error silently leaves a claimed successful constructor. Review these formulas against owning layout
BEFORE coding; native allocation/mutation failure behavior is not altered.

### Fixed adapter early rejection

Before calling generic recursive structural inspection, fixed example leaf/outer inspectors should
read their own shallow exact capture names and kind/intent wiring through native descriptions. Reject
unsupported sets immediately. This supplements, NEVER replaces, the generic walk/height/native checks;
all supported requested and OLD producers still receive complete structural/source/history validation.
No weaker matcher/source fallback/default lookup or recursive ordinary evaluator is introduced.

## Preliminary review refinements (SOURCE ONLY; not approval to implement/probe)

Coordinator verified constructor reservation formulas against owning20/40-byte layouts. The following
refinements are mandatory in the proposed walk; they supersede any suggestion that native DAG views
are small merely because a legal profile is small.

### Binding proof is structural, environment association is EVERY-C

A visited B result records actual native role/adapter/source/interpreter/timeout and, for INPROCESS,
its actual native `environment` DAG ID. It NEVER means “B valid for caller E”. On EVERY C, including
visited C reached at another depth, check that C's own E matches the cached native INPROCESS B.env.
LOCAL B has no E field; exact fixed source/E reconstruction remains adapter responsibility. Builtin
versus ordinary admissible B kinds are independently checked for each requesting capture/C. A shared
B under two C/E associations cannot inherit the first caller's approval. Height/association guards
stay separate from expensive B field decoding.

### Size guard BEFORE native DAG description/accessors

Use public `get_record("dag", id)` and length checks BEFORE `get_dag`/binding scans. Native owning
DAG layout is40 + sum(20 + name bytes); derived valid sizes are:

| Expected profile | Fields/name sum | Native DAG size bound |
| --- | --- | --- |
| C |4 fields /28 name bytes |148 bytes EXACT |
| Capture row |4 /20 |140 bytes EXACT |
| LOCAL/builtin B |5 /38 |178 bytes EXACT |
| INPROCESS B |6 /49 |209 bytes EXACT |
| E |role plus N<=16 names, each native ASCII<=128 |64+20N+sum(names), maximum2432 |

These are existing profile/layout consequences, NOT new numeric limits. Unknown-role B may use the
209 maximum only to safely obtain its bounded native description; afterward native role selects
exact178/209 shape. No oversized valid-native-but-malformed application DAG may be materialized
before rejection. Exact C/capture roles/fields retain their148/140 pre-view check.

A private operation-scoped **charged structural transaction view** is supplied to existing shape/
scalar/link helpers. Its `get_dag` ALWAYS obtains/charges raw bytes and enforces the expected registered
profile bound, or the conservative2432 maximum for an eager link whose target kind is not yet known.
The target receives its tighter expected bound before structural expansion. Thus `b.link`'s eager
`tx.get_dag` cannot bypass the guard. This is a typed structural safety boundary, not reinstating
rejected generic read wrappers/performance caches or changing Repository APIs.

Warm owner/thread/ended checks use an uncached public ref lookup with ignored target (NotFound only
is handled), or a DAG read ONLY AFTER its raw/profile size guard. Never use an unguarded get_dag
as a supposed cheap state probe. No mutable ref value contributes to a structural proof.

### Entire typed charge route (rooted structure ONLY)

The walk owns successful raw/descriptive typed reads for THIS actual transaction, not arbitrary
repository history. Every first reached `(kind, ObjectId)` charges actual raw record length and one
membership against existing transfer record/object/packed totals BEFORE structural processing.

- Root C/E/B/capture: raw DAG -> bound check -> native DAG description -> each role/field/root NODE.
- Every field/root node: raw NODE exact40 -> native node description. Literal -> its DATUM; SubDAG
  -> actual target DAG through the guarded `get_dag` surface. Wrong node kind rejects.
- Every scalar datum: raw DATUM charged/size-guarded -> native datum description -> exact scalar kind/
  profile value/length checks. Fixed role/kind/name/config scalars use their valid layout-derived bounds;
  BYTES source40+existing1MiB source maximum, I6448, NULL40. Canonical URI/interpreter strings retain
  existing native/record/binding limits; do not invent a new string cap.
- A composite DATUM where a scalar is required is an ERROR, not a successful proof with hidden child
  IDs ignored. Reject before following composite children or reusing its description. Successful
  structural profiles contain NO composite datums. No TREE/COMMIT/parent/history export is entered.
- Native public raw/typed reads can themselves allocate/perform direct native validation before Python
  length/kind checks. We cannot change that boundary or promise zero native scan/allocation: malformed
  composites/native raw records retain existing public-read limitations. The charged view eliminates
  repeated application expansion and huge DAG description/accessor work; any stronger pre-native
  bound needs separate public/native scope. Do not parse packed kind/payload bytes privately.

Binding raw fields/source are decoded/charged once, but EACH C compares its own native E association;
all named capture positions/kinds/intents/targets remain independently checked. Failed/partial scalar/
DAG reads never enter successful memo results. Public helpers must not receive the original transaction
instead of the charged view at any structural path.

### Constructor remaining-budget route

ALL existing target/binding/E validation uses the same charged walk BEFORE puts. Then reserve the
already reviewed conservative NEW typed records/packed bytes within the walk's REMAINING limits:
E<=147 records, C<=7, per-record source/layout limits and exact ASCII role/kind/name/URI lengths.
No dedup subtraction/reset/new caps. If exhausted, reject BEFORE the first mutation. Author via the
unchanged native public transaction; native allocation/mutation failures retain native poison policy.
Only successful constructor output receives a public native ID; no post-put Python budget error can
be silently treated as construction success. Current implementation validates existing targets and
admits conservative future records/bytes BEFORE puts, then returns public IDs. It does NOT perform
or claim full post-put readback/accounting of newly authored rows. No inferred origin/alternate codec/
hash. Native mutation failures retain native transaction poison/abort.

Additional proposed finite metadata negatives AFTER explicit approval: SAME INPROCESS B/two different
C.env must reject second association even after B visited; an oversized native DAG must reject before
native get_dag (including b.link/warm route); wrong scalar composite cannot be approved as a leaf;
constructor remaining-budget exhaustion rejects before put. No graph/run/marker/core edit has occurred.

## Proposed practical bound and proof obligations

For V distinct structurally reached profile/binding DAGs and E named capture edges, expensive validation
is O(V+E) rather than O(16**8). E <=16 times distinct environment count. Per-edge state/depth/height/name/
association checks remain; source BYTES/canonical values are decoded once per distinct binding/record
within the walk. Typed native membership/packed-byte totals stay within existing100000/4MiB/16MiB
limits. This is a bounded work/safety model, NOT a five-minute-suite/latency/RSS improvement claim.

Before any probe, review walk ownership, exact complete typed read-charge surface, constructor
reservation arithmetic, early adapter checks and native Source/C/E schema invariants. If source review
finds a missing public seam or a need for a new numeric limit, STOP and separately decide—do not silently
invent a cap, expand APIs or resume rejected read wrappers.

After explicit acceptance ONLY, finite focused native metadata tests would prove:

- A truly shared sixteen-way legal-depth8 graph is validated with counted distinct successful native
  expansions, while all positions survive; no huge unfolded run/baseline/performance benchmark.
- Constructor and reader agree on depth8/next9; diamond with SAME child shallow/deep rejects the deep
  path correctly even after shallow visited success. No reset/zero-height shortcut.
- Wrong capture type/source/late invalid child and native ended/wrong-thread state still reject;
  failures not reused. Constructor exhausted prospective membership/bytes rejects BEFORE puts.
- Unsupported fixed adapter capture set rejects without recursive child expansion. All supported
  requested/OLD full authority/semantic sets remain unchanged, scoped/nonexecuting evidence only.

This plan starts NO run, graph authoring, build, install refresh, test, story or performance experiment.
Existing separately authorized targeted closure may continue, but this specific structural change
awaits review. Any subsequent source fix changes capture/install/coverage identities: retain original
source/proofs/raw measurements, collect relevant exact-current checks and refresh readiness after
final substantive fixes. GHA disabled/native19 PAUSED/VP001 OPEN UNKNOWN/full/story/publication HOLD.
