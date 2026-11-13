# Implementation-bound node invocation

Status: **installed local capability validated by focused tests, one recorded story and a blocked
SAME-history reader; final full validation, independent acceptance and publication pending**.
Development GHA remains disabled; no hosted-platform assurance or earlier-failure diagnosis is claimed.

## Authority boundary

This page owns the explicitly imported [`daggerml.calls`](../python/daggerml/daggerml/calls.py)
structural capture/facade contract and informative NEW fixed
[example integration](../examples/implementation_calls.py).
[Internal builtins](internal-builtins.md) owns unchanged primitive dispatch/node semantics;
[Python storage](spec-next/python-api.md), [caller Q](spec-next/caller-requests.md),
[LOCAL](spec-next/local-execution.md), [exchange](spec-next/repository-execution.md),
[successful leaf S](versioned-reuse-selection.md) and [transfer](spec-next/transfer.md)
retain their separate authority. [Validation policy](validation-policy.md) owns assurance.
Old20–24 helper roles, capture keys and APIs are not reinterpreted by this new slice.

## Intent contract and implementation captures

Intent defines the computational contract. Implementation closure pins dependencies at creation;
semantic variability belongs in invocation argument values or a different intent, not hidden
captures that change the promised result. There is no intent environment or computational K here.
Same-intent membership declares equivalent result semantics; it does not certify correctness,
purity, complete environmental capture or scientific validity.

All conventions use native Literal/SubDAG/DAG records, not new native entities or opcodes:

| Profile | Exact fields/root |
| --- | --- |
| E `implementation-environment-v1` | role STRING root, zero–sixteen named capture DAG links |
| Capture `implementation-capture-v1` | role STRING root, kind STRING `builtin`/`ordinary`, intent URI, target DAG |
| C `implementation-closure-v1` | role STRING root, intent URI, binding B DAG, environment E DAG |
| In-process B `implementation-inprocess-binding-v1` | role STRING root, adapter URI, source BYTES, interpreter/timeout-ms NULL, environment E DAG |

Leaf B retains exact existing LOCAL shape/types/bounds. E-before-B-before-C construction embeds no
future C/F ID. Native links retain captured dependencies; strings inside source are not edges.
Capture names follow native ASCII rules and cannot be `role`. Ordinary capture edges have structural
depth at most8; adding an environment charges the NEW edge, so constructors cannot return an
over-depth E that readers reject. Cycles, duplicates, wrong kinds/root/types reject.

**Structural work safety (IC-003).** ONE reader/constructor operation owns successful native C/E/B/
capture proofs plus full ordinary-edge subtree height. Sixteen different names may share one child;
all named positions/intent-kind-target associations remain checked, but the child structure/source
is not exponentially re-expanded. Each visited edge checks actual owner/thread/ended state and
`entry depth + full height <=8`; no active/depth reset/caller-supplied memo/persistent cache. B proof
retains actual INPROCESS environment; EVERY requesting C independently matches its own E.

Public raw record lengths guard native DAG materialization/accessors first: C148/capture140,
LOCAL-or-builtin B178/INPROCESS B209/E<=2432 bytes derive native fixed fields/names, not new caps.
The typed charged view also intercepts eager SubDAG helper reads. Unique rooted DAG/node/scalar-datum
records obey unchanged transfer membership/record/packed-byte limits, not full history traversal;
wrong composites reject and do not become structural leaves. Stored URI comes from native validated
URI datum identity, not repeated host text canonicalization. Warm state checks ignore an actual
public ref target, not mutable navigation authority. Native raw reads can allocate/perform direct
validation BEFORE Python checks; no stronger native bounded-read/RSS/sandbox guarantee is supplied.

Constructors share ONE validation walk across ALL existing capture entries and admit conservative
future metadata records/bytes BEFORE any put. E needs at most147 new records/C7, derived from owning
record layouts; actual native dedup may use less. Native mutation poison/abort remains unchanged.
They return public IDs; no full post-put readback/accounting is claimed. Fixed adapters additionally
reject unsupported exact shallow sets BEFORE generic structure/retained-history traversal. This is
correctness-level work boundedness, not a global validation cache or resumed suite optimization.

`put_environment`/`put_closure` and `inspect_environment`/`inspect_closure` describe structure, NOT
executable-source wiring or producer success. Unsupported builtin source URI versions may be stored
structurally; fixed execution integration rejects unsupported exact func/source pairs, with no latest
fallback. In-process B's E link must match C. LOCAL source/E reconstruction is an additional trusted
backend check, not inferred from structural C reading. There is no arbitrary URI import/fetch registry.

## Trusted Context, bound logical interfaces

`Context(backend)` belongs ONLY to trusted recording integration. All load/bind/describe/literal/
arguments/operations/invoke methods require an entered, owner-thread, unended, unpoisoned Context.
Rejected pre-entry/repeated/closed use and caught callback/verifier/state errors poison success.
Wrong-thread use may mark copied poison state; Context performs no native cleanup from that thread.
Cleanup stays with the owning integration/Recorder thread. Node `.value` remains copied Datum after
scope closure, but further authoring/consumption rejects.

Logical code receives bound `Calls.invoke(target, argument_node)` and `Nodes.literal/arguments/
map_get/list_get`. Opaque Target/Node ownership uses exact object identity. Fabricated/foreign/value-
laundered handles reject. No Context/raw-ID loader/backend/success receipt is supplied to logical code.
Copied canonical equality includes native NaN equality; collection values remain canonical child datum
IDs. This cooperative Python boundary is NOT a security sandbox or complete-capture guarantee.

The integration protocol is explicit: `bind(Bound)`, `read(dag)`, `literal(value)`,
`arguments(entries)`, `perform(Bound, Description)`, `verify(Bound, Description, receipt)`.
There is one supplied integration, not backend registration/discovery. Read and verify MUST derive
native authority, not trust callback flags/Datum/ID/old same-context handles. Verify checks THIS exact
requested target/input and native own Q/phase/completion or precisely pinned OLD S. Context additionally
re-reads the derived native source before issuing any Node and rejects caught poisoned-state callbacks.
A valid historical result with equal value is not this invocation's association.

ALL outer entries, nested ordinary leaves and getter conveniences in the fixed example actually
traverse `Context.invoke`. Builtin integration delegates to existing exact `Recorder.call`, records
primitive operations and creates no primitive Q/T. Getter conveniences eagerly prepare their own
argument-map nodes, then use the SAME facade. Ordinary integration keeps its own request/attempt/
adapter/history authority. The facade does not erase differences between adapters.

## Informative fixed A/B composition

The NEW source files are [`implementation_calls.py`](../examples/implementation_calls.py),
[session](../examples/implementation_call_session.py),
[adapter/outer entry](../examples/implementation_call_adapter.py),
[leaf wrapper](../examples/implementation_call_leaf.py),
[outer logical source](../examples/implementation_call_funcs.py) and
[leaf logical source](../examples/implementation_leaf_funcs.py).

A/B add(a,b) and double(x) implementations capture actual map-get-v1/v2 respectively plus list-get-v1.
Outer A/B pin corresponding add/double C and getter version. Fixed source checks exact I64 names/kinds
and arithmetic range. Actual composition is two outer getters, captured add with ORIGINAL argument
Node, then captured double with a map whose source is the exact validated returned add Node. No host
precomputed42, equal literal replacement, source projection or moving-default lookup supplies it.

The finite application uses a synchronous in-process outer adapter and unchanged synchronous public
LOCAL/exchange leaves. Each fresh leaf is its direct child in a separate owned repository. No outer
worker/descendant/RPC/thread executor/general recursive evaluator or arbitrary in-process timeout is
supplied. A leaf may hold ONE Recorder writer across fixed internal builtin work only. No writer/native
handle spans ordinary dispatch, public-S validation scratch, import or waiting.

## New reuse key, two independent authorities

Matching is canonical **intent URI + full verified argument-MAP datum identity**. Binding/environment/
source/input DAG/producer/commit do NOT partition this key. Swapped named operands differ despite equal
sum. Actual requested C/B/E/source associations and OLD actual producer C/B/E/Q/T/R/F remain retained
and independently checked. There is no table/discovery index/mask/equivalence framework.

Three known selection slots choose outer/add/double results. ALL present selections validate and
contribute their full ORIGINAL semantic sets even on explicit fresh or key mismatch. Requested builtin
bindings also count on reuse. Poison is an error, not a cache miss. An outer require-selected miss
rejects before outer T. An inner require-selected miss rejects before THAT leaf T/dispatch; outer
initial T/getters or earlier successful inner work may already exist. Inner input matching is not
assumed known before the outer starts. Try-selected absence/mismatch permits separately chosen fresh
work. No automatic adoption.

NEW outer D/Q/T/phase/return/completion/S/W roles use `example-implementation-call-` prefix and own
`iq-`/`ia-` occurrence roots. D/Q commits have exact successive only-addition parents in one metadata
batch/create-only refs. Initial T precedes work. Ordered phases retain actual getter preparation/calls;
fresh leaf joins have `(previous outer phase, exact leaf F)` parents without copying leaf tree state.
Final T preserves occurrence/initial field nodes and links completion rooted in existing history,
never a future-F/self-ID cycle or fabricated LOCAL exit/cleanup.

Leaf own Q is unchanged public LOCAL Q; NEW decision/phase validation independently checks actual
preparation parent/dimensions/reservations before fresh dispatch or satisfaction. Fresh authority
composes public S with exact semantic returned node/trace/captures and ORIGINAL outer prefix.
Successful first leaf does not require later outer success. Leaf W links own NEW Q/THIS D/pinned S/
OLD T/R; outer W similarly links own Q/D/S/OLD finalT/R. Each publication has exact delta/parents.
Q may remain pending after W failure; files/native commits/external effects are separate boundaries.

Known interface/recorded leaf failure stops later calls and poisons success. Native/persistence/import/
public validation/wait uncertainty leaves durable partial history and UNKNOWN, not fabricated terminal
failure/success or automatic retry. Earlier completed inner work remains independently inspectable.
A caught facade `CallError` that resurfaces through guarded `finish`/copied-node validation is
conservatively UNKNOWN: no terminal outcome is invented merely because the facade exception class
is a ValueError subclass. Session-native receipt/position/Q/result verifier mismatches raise validation
ValueError and also remain UNKNOWN. An unclassified facade CallError reaching `Session.fail`, including
a direct pre-backend error, conservatively marks UNKNOWN rather than publishing known failure. Explicit
cooperative SessionError and fixed logical ValueError/OverflowError reached outside a failed backend
can record known failure; native/backend verification errors are not blanket-promoted to that class.

## Bounds and validation status

ONE aggregate semantic-ID set spans requested and ALL consumed ORIGINAL histories/backend/Recorder
scopes. It includes every literal/source/argument/entry/ledger/getter-preparation/operation/trace/normal
return profile and used/requested builtin binding. Capture metadata has separate exact structural/
complete native-transfer validation, not a way to hide semantic nodes. Existing64 reached DAGs,
16arguments/16positions, ORIGINAL-authority depth8 and transfer limits stay unchanged. Reservations
precede their owning puts/fresh child dispatch; request/T admission checks the actual known sets.
The add return reservation occurs after its own leaf Q, so a later quota error can leave that Q
pending. Sharing counts native IDs once but never merges call positions.

[Focused facade tests](../tests/python/test_calls.py),
[native/HOST integration tests](../tests/python/test_implementation_calls.py) and
[new-row atomicity](../tests/python/test_implementation_call_atomicity.py) distinguish real native
metadata/proof/rollback from HOST-substituted publication, with ZERO OS computational children in
those HOST tests. Separately, one current isolated installed story recorded13Q/10T with six direct
synchronous LOCAL children and17 getter positions. All six children were waited0, native-F verified,
reaped and absent before original workspaces/source retirement. A fresh blocker-first nonexecuting
reader verified both SAME caller and replica native histories, including requested B versus OLD A
producer authority, with unchanged database bytes. Current story semantic sets34/42/48/37/58 are
measured for this fixed application, not a general admission or future-OLD-union guarantee.

Twenty-five current focused checks pass; nine precisely reviewed no-value raise exclusions retain
all conditions and meaningful state guards (including mutable trusted backend expectations).
Original failed probes/API/bootstrap errors, source/AST/hash qualifications and unknown historical
platform causes remain in the evidence records. Final unchanged full validation and independent
acceptance/publication remain pending; no automatic story replay or platform-green claim follows.
See [current activation](../../dml-design/iterations/25-implementation-bound-invocation/ACTIVATION-V52.md),
[blocked reader](../../dml-design/iterations/25-implementation-bound-invocation/READER-V52.md) and
[Iteration25 results](../../dml-design/iterations/25-implementation-bound-invocation/RESULTS.md).

Diagram review: C/E/capture/call roles use existing native DAG/node/tree/commit/ref relationships,
not new LMDB entities/key families/hash/layouts; displayed storage model remains unchanged.
Development GHA disabled/NOT RUN/not pass; native19 PAUSED/VP-001 OPEN UNKNOWN/no standing waiver.
