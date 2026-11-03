# Iteration 20 worked example: argument values without implicit provenance

Status: **executed, independently reviewed, delivered and STOPPED** through published
`7e9bf133d5d175a492fb1e9d651e91a476358604`. SOLE actual FIVE-Q/FOUR-local/SIX-getter story;
see [RESULTS](RESULTS.md) and [REVIEW](REVIEW.md) for actual IDs/evidence/qualifications.
This worked plan remains symbolic; no computational repeat is authorized by reading it.
GHA disabled/NOT RUN/notpass, native investigation PAUSED/VP-001 OPEN UNKNOWN. Earlier status:
**GO: reviewed bounded example authorized on2026-11-02; execution evidence pending**.
Existing window-2 agent/new Pi session with coordinator review before accepted normal publication;
see [COORDINATION](COORDINATION.md). GHA stays disabled/native investigation PAUSED/VP-001 OPEN
UNKNOWN. GO supersedes pending/no-run wording below only within this bounded scope, not as-built
claims. Earlier status: **bounded replacement plan reviewed; NOT executed; separate implementation GO pending**.
The user's “reviewed” acknowledges plan review, not run/delegation/publication permission.
Read [DESIGN](DESIGN.md) and [HANDOFF](HANDOFF.md). Symbolic IDs/API sketches are illustrative;
no commands here authorize a build, worker restart, computation or publication. The old
[projection example](../20-result-based-input-reuse/EXAMPLE.md) is deferred, not combined with this one.

## 1. Setup and value-only funcs

Use one caller repository A and fresh explicit synchronous-local execution workspaces/B stores.
Capture trusted standalone wrapper/support and func source bytes in existing local bindings;
children use installed public DML, not checkout PYTHONPATH or uninstalled example imports.
No service/Docker/SSH/Batch fixture. Existing adapter/Q/public S authorities remain unchanged.

Illustrative logical callable code (not an existing API):

```python
def add(args, values):
    left = values.map_get(args, "left")
    right = values.map_get(args, "right")
    if left.kind != "i64" or right.kind != "i64":
        raise ValueError("add requires I64")
    return Datum.i64(left.value + right.value)


def double(args, values):
    x = values.map_get(args, "x")
    if x.kind != "i64":
        raise ValueError("double requires I64")
    return Datum.i64(x.value * 2)
```

The recorder interface supplies no repository/path/context/graph/ref/source selection. It binds
map_get to the invocation's argument map, returns Datum, and records the actual map access behind
that interface. Python arithmetic is internal to the recorded func, not a new primitive.

Literal source DAGs declare I64(42), I64(13), I64(29), I64(30) and STRING names x/left/right.
Source descriptions select exact pinned literal nodes. Initialize an empty NEW datum-keyed table
for canonical double intent. Explicit captured add/double bindings; no new menu/default framework.
All metadata/source/primitive authoring creates zero Q/T.

## 2. Literal argument map and fresh double

Use the actual prototype's fixed operation authoring functions, not hand-forged result rows:

```text
E = map_empty()                       -> empty MAP datum
L = map_insert(E, source("x"), source(literal42))
                                        -> MAP { STRING("x"): I64(42) }
I_literal = full inputs(arguments=L.datum, construction=L.source)
```

One request Q1 records full I_literal. Separate explicit dispatch executes fresh T1. The trusted
wrapper calls double with only the map datum/facade; one successful map_get trace position is
recorded. Returned R84_1 has the declared return literal I64(84), plus role and trace pinned to Q1.
Complete public successful F1/S_D1 supplies Q1/T1/R84_1 authority. Explicitly insert S_D1 into
the table under the argument-map datum key. No automatic adoption while executing.

## 3. Computed42 argument map and cached double

Construct add arguments with map_empty and two map_insert operations from literal13/literal29:

```text
A42 = MAP { "left": I64(13), "right": I64(29) }
I_add42 = full inputs(arguments=A42, construction=its recorded operations)
```

Q2/new T2 executes add, with two actual map_get trace positions. Successful returned R42 has
return I64(42) and invocation/access trace; it is not the same DAG as a bare literal42 source.
Capture S_A42. Use public successful selection plus the exact returned-datum profile to obtain
the value source; do not assume arbitrary root42 means a valid return:

```text
C = map_insert(map_empty(), source("x"), returned_source(S_A42))
                                         -> MAP { "x": I64(42) }
I_computed42 = full inputs(arguments=C.datum, construction=C.source)
```

Assert with native identities:

```text
literal42 datum ID == R42's declared return datum ID
L.argument-map datum ID == C.argument-map datum ID
L.construction DAG ID != C.construction DAG ID
I_literal DAG ID != I_computed42 DAG ID
```

Q3 uses full I_computed42 and the requested double binding. Decision/table inspection validates
both actual requested construction and selected S_D1's original construction before comparing
func+argument-map datum identity. Q3 is satisfied by W3 referencing OLD T1/R84_1.

No new T, double invocation, map_get trace position, completion packet or adapter job for Q3.
The request and historical execution remain distinct:

```text
requested Q3 -> I_computed42 -> C -> S_A42 -> T2/Q2 -> literal13/literal29
satisfied W3 -> T1 -> Q1 -> I_literal -> L -> literal42
returned datum: I64(84), obtained from historical R84_1
```

A summary links Q3/W3/oldT1/R84_1 and exposes both constructions; it does not say T1 ran using
T2's result or that Q3 performed an access. Existing fresh-only composition summary is unchanged.

## 4. Different datum and explicit fresh work

Build add arguments13/30 using the same immutable primitives. Q4/T3 executes add with two access
trace positions, returning R43 whose declared return datum is I64(43). Capture S_A43 and build:

```text
C43 = map_insert(map_empty(), source("x"), returned_source(S_A43))
                                         -> MAP { "x": I64(43) }
```

C43's map datum differs from L/C. Q5 records full I_computed43; valid table miss leaves pending
fresh Q. A separate explicit dispatch executes T4/double -> returned I64(86), with one access
trace position. No automatic adoption: table still selects S_D1 at x42 and has no x43 entry.
Old snapshots/refs/source relationships remain unchanged.

## 5. Finite native census and independent readers

| Request | Logical func / arguments | New attempt | Actual result |
| --- | --- | --- | --- |
| Q1 | double / literal-source x42 | T1 | I64(84) |
| Q2 | add / left13,right29 | T2 | I64(42) |
| Q3 | double / computed-source x42 | none | reuse T1/R84_1 |
| Q4 | add / left13,right30 | T3 | I64(43) |
| Q5 | double / computed-source x43 | T4 | I64(86) |

Exactly FIVE request occurrences and FOUR attempt occurrences in retained acceptance history;
S capture/primitive authoring/table/decision/W/summary/transfer/read add no support Q/T. Fresh
funcs record SIX successful getter trace positions total (1+2+2+1). Repeated content may deduplicate
primitive DAGs; count trace positions/owning Q, not assume one unique content ID per event.
Record primitive constructions and all actual source references, not merely final map values.

After direct children are known reaped and complete outputs received, make only owned original
workspace/packet/source paths unavailable. Transfer the pinned final history to a fresh local
repository. Fresh installed nonexecuting readers, with spawn and transport blocked, verify:

- literal-versus-returned42 value equality despite different source DAGs;
- construction recomputation, every returned-source S/R/node/value association;
- canonical func/map datum key, all table rows and original S_D1 inputs/return profile;
- Q3's FULL own inputs/actual decision/Q/W ordered parent spine and exact tree deltas;
- two different provenance chains; no new Q3 getter trace or fabricated execution;
- Q5 pending-before-dispatch followed by successful86; no auto-adoption/old-row change;
- public native complete all-parent/composite closure, exact source bytes/bindings and native
  FIVE-Q/FOUR-T census. Actual process exits alone do not certify public successful history.

Coordinator should independently read SAME retained history, not repeat the computational story.
Own controller/support/callable source hashes BEFORE execution; preserve originals/failures before
oracle correction. A corrected nonexecuting reader is preferable to rerunning fresh computations.

## 6. Focused companion checks, not additional acceptance jobs

- map_empty correct empty MAP; immutable insertion retains prior map; missing and duplicate keys
  reject, including native NFC-equal STRING duplicates. Canonical key/value types and map order.
- Same structured datum from different source graphs matches; I64/F64, collection order/content,
  argument name or value change distinguishes identities as dictated by native datum semantics.
  Returned collection datum roundtrip need not claim nested callable traversal is implemented.
- Source caller-value lie, wrong literal binding, swapped returned S/R/node, unknown/failure/
  evidence-only F or arbitrary root42 profile reject; poisoned nonmatching table row rejects.
- Getter trace belongs to THIS invocation/source, even with equal map IDs elsewhere. Wrong map,
  missing key or arbitrary datum-ID navigation through facade rejects. Callable receives only
  documented Datum/map-get interface; no public graph/path/provenance properties. This is not
  adversarial Python sandbox testing or proof hidden dependencies cannot exist.
- Public full-Q input substitution with datum-only skeleton, oldQ-on-W, wrong T/R/ref/parent,
  forged getter trace and changed latest slot versus pinned record reject.
- Representative new primitive/input/table/decision/W publication rollback/loss; earlier complete
  Q may persist after W failure. Explicit one-key selection/adoption/removal preserve old/history
  and other entries, using existing validated attempts when possible rather than more real jobs.

Focused fixture occurrences, mutation drivers and host/private substitutions are reported separately.
Local story is not full platform assurance, scientific correctness, complete capture or nativefix.
GHA disabled/native investigation PAUSED/VP-001 OPEN UNKNOWN remain. Candidate starts nothing.
