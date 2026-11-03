# Iteration 21 candidate design: internal versioned built-ins

Status: **bounded plan reviewed; implementation/delegation/publication GO pending**.
The user subsequently stated “reviewed”; this records review of DESIGN/EXAMPLE/HANDOFF, not
implementation permission or as-built behavior. Exact engineering spellings remain refinable.
Earlier preparation provenance follows:
The user requested “prep the iteration” after agreeing the direction below. This authorizes
preparation only. Exact module/API/role/URI/limit/story mechanics are assistant recommendations,
not as-built behavior or additional user decisions. Read [EXAMPLE](EXAMPLE.md) and [HANDOFF](HANDOFF.md).

## 1. Authority and agreed direction

Vocabulary follows the [glossary](../../../dml/docs/spec-next/glossary.md). **Func** means the DML
logical callable/intent, not merely a Python function. The agreed graph-level calling convention is:

```text
func(argument-map node) -> result node
```

Argument preparation is analogous to placing evaluated arguments on a C stack: form a node whose
value is a MAP datum, while retaining the actual source-node relationships in the graph. MAP pairs
contain datum IDs, not provenance/node IDs. Built-ins may return primitive operation nodes directly;
other funcs return nodes representing their result sub-DAGs. Value access does not implicitly expose
provenance. Reuse remains func plus full argument-map VALUE, not the source node's record identity.
This is not a literal mutable stack, a security sandbox, purity proof or full-capture guarantee.

User-proposed binding convention, retained here:

```text
dml://builtin/map/get
  implementation choice
    binding DAG
      adapter:     NULL
      source:      dml://source/builtin/map/get/v1  (URI datum)
      interpreter: NULL
      timeout-ms:  NULL
```

NULL adapter deliberately selects internal DML execution. Source URI identifies an exact shipped
implementation; it is neither fetched code nor a capture of code bytes. New releases can retain old
handlers/bindings. Unsupported versions fail explicitly, never silently substitute “latest”.
Implementation updates and adapter-contract updates need not track package release numbers.
Executable compatibility and historical result validity/reuse selection remain separate.

## 2. Source findings and narrow prerequisite

Current implementation is clean published `7e9bf133d5d175a492fb1e9d651e91a476358604`; Iteration20 is
reviewed/complete-stopped. [Its owner](../../../dml/docs/recorded-argument-maps.md) describes example-
local STRING-opcode operations and a top-level bound Datum facade, not real built-in func dispatch.

Relevant authorities and findings:

- [Native URI rules](../../../dml/docs/spec-next/records.md#text-numbers-and-uris) and
  [uri.c](../../../dml/src/uri.c) currently reject the ENTIRE `dml` scheme, case-insensitively.
  Ordinary `Datum.uri(...)`, canonicalization, packed validation/import cannot yet carry the proposed
  identifiers. This is a real prerequisite, not just a Python registry change.
- [Native nodes](../../../dml/docs/spec-next/objects.md) are LiteralNode/SubDAGNode only. Neither
  supplies a callable-facing `.value` or executes its target. A proposed semantic node interface is
  distinct from these storage descriptions; no new native node kind is assumed in this first slice.
- [Python API](../../../dml/docs/spec-next/python-api.md) provides canonical datum IDs, copied values,
  ordinary DAG authoring and explicit write lifetimes. Collections contain child datum IDs.
- [Local execution](../../../dml/docs/spec-next/local-execution.md) and
  [local.py](../../../dml/python/daggerml/daggerml/local.py) accept only their fixed Python binding
  role, adapter URI, source BYTES/interpreter/timeout fields. Do not insert NULL built-in bindings
  into that old driver or relax its validator.
- [Public Q](../../../dml/docs/spec-next/caller-requests.md),
  [exchange](../../../dml/docs/spec-next/repository-execution.md),
  [transfer](../../../dml/docs/spec-next/transfer.md) and
  [successful S](../../../dml/docs/versioned-reuse-selection.md) can retain ordinary new profiles
  without changing attempt/publication/transport protocols. Old20 input/trace inspectors cannot
  decode a new URI-call profile unchanged.
- Installed module inventory is explicit in [meson.build](../../../dml/meson.build). New runtime
  code needs actual packaging plus a fresh isolated install AFTER GO; the cached20 runtime will
  not prove new built-in or new native URI behavior.

Recommend permitting `dml:` REFERENCES through the native canonical URI pipeline, with existing
ASCII/absolute/grammar/NUL/canonical-form rules unchanged. Remove only the scheme-wide rejection
and any now-unused helper; preserve encoding, hash inputs, storage schema, allocation/error rules.
Reservation means DML owns executable definitions, NOT that users cannot store references. Unknown
well-formed `dml:` URIs may be stored/inspected; they are not executable merely because of the scheme.
Dispatch reservation is not an authentication guarantee against raw trusted repository writes.
Recommend a narrow execution-namespace guard in the existing local/exchange request validators:
`dml:` intents are reserved for the built-in invoker, not executable through a user Python binding.
Otherwise removing the native URI ban would newly permit an external binding to claim a built-in
intent. Store references freely; reject such supported external invocation BEFORE Q/dispatch. No
previous valid dml:-intent requests existed under the old native ban. Preserve all other local/Q/
exchange validation, roles and lifecycle behavior; do not make NULL bindings pass old validators.
Add native/Python/packed/transfer/CLI reference coverage and owning URI/local/exchange authority
updates only during authorized implementation. Old draft specification remains historical.
No LMDB/open/async/native-lifetime investigation is included.

## 3. Small installed built-in surface (candidate)

Recommend an additive, explicitly imported installed Python module, illustratively `daggerml.builtin`:
fixed shipped handlers plus typed ordinary-node recording through the public C-backed repository API.
This is internal DML logic, not an example-only callback table, dynamically registered user handler,
source downloader, subprocess adapter or arbitrary DAG evaluator. Python implementation is the
recommended first slice; moving handlers into C later is not part of this turn. C work is restricted
to the URI-reference prerequisite, relevant tests and owning docs. This first installed execution
surface is Python; native CLI inspection/URI storage remain usable, but a native C/CLI func-invocation
API is deferred rather than claimed as already supplied. Fixed semantics/recording should permit
later C execution without changing the graph-level calling convention.

Recommended exact initial func/source identities and arguments:

| Func URI suffix under `dml://builtin/` | Exact argument names | Result | Shipped source suffix under `dml://source/builtin/` |
| --- | --- | --- | --- |
| `map/empty` | none | empty MAP | `map/empty/v1` |
| `map/insert` | `map`, `key`, `value` | new MAP, prior unchanged | `map/insert/v1` |
| `map/get` | `map`, `key` | selected datum | `map/get/v1`, `map/get/v2` |
| `list/get` | `list`, `index` | selected datum | `list/get/v1` |

Exact spellings are refinable. Recommend STRING map keys for these first operations; the native
MAP format still permits any datum key. Other native argument values/composite closure remain
available. Insert rejects duplicate canonical keys, including NFC-equivalent strings; replacement
is deferred. Get rejects missing keys. List index is I64, nonnegative, strictly below length; BOOL,
F64, negative/out-of-range indices and wrong container kinds reject, not Python coercion/negative
index behavior. No implicit Python container conversion or nested materialization.

Recommend two REAL map-get handlers with the same semantic contract: v1 validated linear lookup,
v2 validated key-ID lookup. Preserve separate version entrypoints and routing; v2 is not an alias
that makes old records execute new code. Both must obey identical native key/type/missing semantics.
This provides a concrete compatibility witness, not a claimed bug fix, performance result or actual
previous-release compatibility proof. All four functions must execute via URI + exact binding +
argument-map node, including empty/insert; renaming old20 helper calls is insufficient.

Binding profile: ordinary role, exactly `role`, `adapter`, `source`, `interpreter`, `timeout-ms`,
role-rooted. Recommend NEW `builtin-binding-v1` role, the three NULLs and canonical URI source.
The known source table fixes the compatible func URI and argument contract. Validate field types,
shape, role, func/source pairing and supported version BEFORE calling a handler or recording success.
No URI substring matching, import-by-URI, alias fallback, mutable global registration or latest-ref
lookup. A read-only structural binding inspector can describe an unsupported source without claiming
it can execute; the invoker rejects it explicitly. A generic NULL Python binding does not qualify.

Recommend one bounded example-local versioned implementation choice for map/get: immutable v1/v2
binding links and an explicit default label. Default promotion changes ONLY that choice in a new
snapshot; old choice/bindings remain. Use exact explicit override for historical calls. Other built-ins
can use explicit v1 bindings. No generic registry/menu/default framework or automatic migration.

## 4. Standard argument preparation and value-oriented nodes (candidate)

Recommend a recorder-owned semantic node handle, illustratively `ValueNode`, with copied Datum
value access and only bound operation conveniences. It represents an actual recorded source or
operation, not merely a Datum plus a claimed source ID. The recorder owns native IDs/context;
logical code is not supplied public graph/ref/path/commit/provenance properties or arbitrary-ID
navigation. No live native transaction/repository is itself a callable argument. This remains a
cooperative interface: trusted Python introspection/globals/imports can bypass it.

Node association must be per recorder/invocation and exact handle/record, NEVER a global lookup by
equal datum ID. Reject foreign-session, forged, stale/ended and fabricated handles. Revalidate
native sources/value derivation; dataclass fields and owner flags alone are not persisted authority.
Different nodes with equal values remain distinct sources, including two equal collections read
from different keys in the same invocation. Returned getter node identifies THIS consumed map/list
source, not an arbitrary equal container. Native object content can deduplicate without merging
trace positions or inventing primitive occurrence IDs.

Source descriptor/root/argument/value reads retain no native pointers in public node handles.
Copied `.value` data may remain inspectable after closure; executing/authoring through an ended
recorder rejects, and a new recorder reloads exact recorded nodes rather than reusing old handles.
Primitive calls here are immediate internal calls, not a new top-level Q/T execution driver. The
common call contract is implemented for this fixed builtin surface and the selected normal local
wrapper; generalized dispatch of arbitrary non-builtin funcs is not part of the slice.

Recommended supported source/value forms:

- Explicit literal node selected in a pinned named source DAG, retained through a strict source
  descriptor containing DAG/name/node/value association. A freshly authored literal inside a trusted
  recorder has an explicit literal profile; no claimed computation is inferred from its value.
- Actual recorded built-in result node whose exact func/binding/argument graph/result recomputes.
- A non-built-in result node ONLY under the new explicit return profile. Structural node-value
  validation does not certify attempt success; when used as historical execution evidence, public
  S/Q/T/R/F validation is a separate required workflow boundary. Acceptance inputs deliberately use
  literal/built-in construction sources, not a new computed-producer adoption subsystem.

One `arguments(...)` preparation routine accepts named source nodes, derives their actual datum
values, builds canonical STRING-key MAP pairs and records every source association. That resulting
node—not a bare map datum—is supplied to BOTH built-ins and normal funcs. Preparation is bootstrap
calling-convention machinery, not recursively invoking map/insert to construct map/insert's own
arguments. Eager values only; no lazy evaluation of a source graph or automatic dependency jobs.

For a public outer local call, the exact argument preparation DAG can be Q's full `inputs` DAG;
Q's existing native inputs link is its argument node. Extra declared binding/configuration, if
needed, lives in the captured normal binding or explicit non-value profile fields, not secretly
inside the MAP or a moving ref. Every nested builtin gets its OWN standard argument-map node.
Conveniences like `ops.map_get(container, key)` merely author key/source nodes, prepare
`{map: container, key: key_node}`, and delegate to the exact bound URI invoker. They must not contain
a second unrecorded computation path. No special top-level-only accessor or path syntax is needed.

Recommended application bounds:16 named arguments,16 successful built-in call positions per scope,
64 reached semantic profile records. Count prospective argument/source/result/trace records before
publication and define deduplication precisely. Native complete closure bounds remain unchanged;
these limits are not byte/RSS quotas. Arbitrary nested traversal/general store access is not added;
only recorded map/list getters on owned value nodes follow explicitly reached datum children.

## 5. Ordinary storage, result contract and publication (candidate)

Use native Literal/SubDAG nodes and strict NEW ordinary DAG roles. Illustrative record contents:

| Semantic record | Essential retained facts |
| --- | --- |
| literal source | exact source DAG/name/node and derived datum |
| arguments | MAP value literal plus bounded entries linking canonical keys to ACTUAL source nodes |
| built-in operation | func URI, exact binding link, argument node, result datum literal |
| normal result sub-DAG | explicit returned node, matching returned datum, ordered builtin trace, owning Q/full inputs |
| choice | func URI, immutable supported binding choices and default label |

Exact roots/field sets/role spellings need implementation refinement and review. An argument value
map never contains node IDs; computational edges are ordinary node bindings/links outside the datum.
For this first slice, a built-in's semantic primitive operation node may be stored as a SubDAGNode
link to its operation-record DAG. This is a STORAGE carrier, not an extra user-func result wrapper or
an assertion a native primitive-node enum now exists. A normal func returns a node representing its
result sub-DAG. Do not fake this interface by returning bare Datum or a native storage description
with a host “value” flag. Native schema remains unchanged.

A logical Python implementation takes the argument node and bound node operations, returns an owned
node; the trusted wrapper constructs its normal result sub-DAG with that designated node/value and
actual ordered trace. Arithmetic can stay ordinary Python over `.value`; creating a literal result
node is explicit. All successful child-local source/arguments/primitive nodes/trace/R and existing
`local.publish_result` persist in ONE child storage transaction. Exceptions before publication
produce old local failure behavior, not false success. Durable failure traces are deferred. Do not
catch meaningful errors and continue a partially recorded scope to successful publication. Recommend
a failed recording scope becomes unusable for successful completion, even if logical Python catches
the authoring/invocation error;
new scope or failure handling is explicit, with no new durable failed-call trace assumed.

Recorder implementation may stage recipes before opening that final write, or use one wrapper-owned
write while performing only native reads/fixed handlers; it must not reopen another native wrapper
or public S projection while a target transaction is live. Copied public node handles must not retain
native pointers. Inspectors finish on the creating thread; explicit closure/export reads finish
before authoring. Private failure poisoning/lifetime policy must be explicit and tested, not an
implicit new low-level transaction promise.

Caller-side construction/choice/compatibility publishes exact intended tree delta, one parent,
create-only explicit ref, response precommit. These batches, Dd/Q/W, files and external local child
execution remain separate boundaries. Inspection/revalidation recomputes fixed semantics without
invoking historical source, creating operation records or calling the recording dispatcher. Complete
all-parent typed/composite closure remains mandatory. No arbitrary sub-DAG root extraction.

## 6. Small workflow bridge, not cache-framework expansion

Recommend NEW example-local node-profile request/reuse/reader helpers, using public installed node
inspection, Q/exchange and successful S. Do not reinterpret old20 Md/Dd/trace roles, weaken old
helpers, import private `_projection` codecs or require the library to import example modules.

For this story, ONE explicitly named successful sum-pair S is sufficient; no new multi-row table or
adoption/removal/default-cache feature is needed. If the explicit slot is present, publicly validate
it EVEN when its value will not match. Require canonical sum-pair intent/new original full input/
new result profile; then compare full argument MAP datum. Exact requested/producing bindings stay
separate. Invalid S/profile/unknown/failure is error, not miss. Valid value mismatch leaves pending
fresh Q; no automatic adoption or history discovery. Force fresh and require-selected controls can
remain bounded. Existing old table helpers keep their prior behavior.

Recommend ordinary new decision Dn pinning actual basis/requested binding/full argument-node inputs/
map value/control/action/reason/consumed S. Separate owning public Q precedes ordinary W to OLD T/R.
Before W verify actual Cq parent is THIS authored Dn, exact public non-None Q/ref/reservation/tree,
not returned description claims. Reader separates requested argument sources/builtin choice from
historical executed sources/bindings/trace. Cached request has no fresh primitive trace/completion.
This bridge is concrete acceptance scaffolding, not a generic library evaluator or policy framework.

## 7. Evidence goal and exclusions

[EXAMPLE](EXAMPLE.md) recommends THREE Q/TWO synchronous LOCAL attempts for nested sum-pair:
[13,29] ->42; source-distinct equal map/new requested get-v2 binding ->reuse old42; [13,30] ->fresh43.
Actual fresh calls use four nested getters each. Three source constructions use empty+insert each;
two final direct internal compatibility calls execute get-v1/get-v2 on identical arguments after
promotion. Exactly16 successful builtin call positions, zero extra Q/T for primitives or controls.

A fresh isolated install is necessary: changed native URI behavior AND new shipped module must run
outside checkout runtime PYTHONPATH. No image rebuild/Docker/SSH/Batch/service needed. Preserve
prelaunch controller/source/native-installed identities; after two direct children are known reaped,
retire only owned originals, transfer SAME history, independently read nonexecutingly with active
spawn/transport blockers. Test fixtures/host substitutions are distinct from acceptance occurrences.

Follow [validation policy](../../../dml/docs/validation-policy.md): focused primary checks, sole
worker final unchanged full-v, risk-based independent SAME-history checks, no duplicate story/full.
[GHA disable decision](../19-intent-scoped-reuse/GHA-DISABLED.md) supersedes CI-launch wording.
[VP-001](../../maintenance/validation-policy/EXCEPTION-VP-001.md) planning revisit remains OPEN
UNKNOWN; builtin/URI validation does not diagnose old async/LMDB failures. Related source need or
recurrence requires fresh scope. No cloud/resources/scheduler/general evaluator/new native entity/
ABI/masks/purity/discovery/release/package publication, global tooling or later feature turn.
No code/spec/glossary/diagram edit or experiment follows preparation; review then separate GO.
