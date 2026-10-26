# DML glossary

Status: working vocabulary, evolving with the design spiral.

## Authority boundary

This document owns the meanings of terms used in the current design discussion
and maintained documentation. It does not define object layouts, APIs or execution
protocols. Implemented behavior is specified in the
[technical documents](README.md); design agreements and open questions are recorded
in [the design discussion](../../../dml-design/discussion.md).

An entry here does **not** mean the concept is implemented. **Provisional** marks
an unsettled term or distinction, not merely an unimplemented feature. Examples are
informative.

## Using the vocabulary

- Maintained documentation uses these terms consistently. Define a new technical
  term here or explicitly qualify a document-local term; do not silently use an
  established term with a different meaning.
- Design conversation follows the glossary on a best-effort basis. Informal wording
  and exploratory names are fine; clarify consequential ambiguities and update the
  glossary when the meaning changes.
- Prefer the terms below over unexplained synonyms. Exact API identifiers, quotations
  and historical documents may use different words; explain the mapping when useful
  rather than rewriting historical evidence.
- Changing a definition is a visible design change, not an opportunity to turn an
  open question into a decision. Fix mismatches in maintained documents as part of
  the relevant change; do not sweep archived reports or frozen fixtures.

## Repository structure

### Datum

A recorded value, such as a number, string, bytes, URI or collection. A datum is not
itself a computational node. A URI datum records a reference; it does not necessarily
capture the referenced external contents.

### Node

An element of a computational DAG. In the explored recursive model, a node describes
a sub-DAG or a primitive operation. A literal node connects a datum to the graph.
Exact node representation and executable behavior remain iteration-specific.

### DAG

A directed acyclic graph of nodes and their relationships. It can have a root and
named bindings. Its structure is not limited to its named nodes.

### Sub-DAG

A DAG viewed as part of a larger computation. It is not a separate fundamental kind
of graph. Execution produces a result sub-DAG; the amount of detail represented
inside it is researcher-controlled.

### Root

The designated entry/result node of a DAG. The root is a node reference, not
necessarily a name spelled `root`. Exact root-selection behavior belongs to the
implemented contract.

### Named binding

An association from a name to a node within an explicitly scoped DAG. A name provides
access to an already-bound node; it is not a global node identifier or a late version
selection. Binding structure and duplicate-name rules remain representation questions.

### Named node and anonymous node

A **named node** is exposed through a named binding in the DAG under consideration.
An **anonymous node** has no such binding there and is reached through graph structure.
These describe naming in a scope, not necessarily distinct node types.

### Lookup

Obtaining a node by name from an explicitly supplied DAG. This explicit scope is
provisionally agreed. Lookup is not execution of the node or conversion to a Python
value. Exact name syntax and missing-name behavior remain open.

### Tree

A named collection of DAG references in a repository snapshot. A tree is distinct
from the computational structure inside each DAG.

### Snapshot

The recorded repository state at a particular commit. It does not mean a capture
of the whole external environment, nor that every referenced resource is preserved.

### Commit

An immutable history object recording a snapshot and its parent commit references.
Prefer **DML commit** when Git commits or storage transactions are also in view.
A containing commit does not automatically contribute to every computation's reuse
identity.

### Commit graph

The graph of commits linked by parent references. It records repository history,
not the computational data flow represented inside DAGs.

### Ref

A mutable, repository-scoped named pointer to a commit. Moving a ref does not mutate
the target commit. A branch head or an execution publication ref is a use of a ref;
exact ref categories and namespaces remain open.

### Repository

A DML object store with its repository state and navigation references. Prefer
**DML repository** when distinguishing it from an experiment or IaC Git repository.
A local storage foundation need not yet implement the complete commit/ref model.

### Remote

A repository exchange location through which parties synchronize DML objects and
refs. Prefer **repository remote** where other remote services are also discussed.
A remote can be local, such as a filesystem location; remote exchange does not
necessarily imply a network or cloud execution.

### Record

A stored encoding of an object or other repository state. Distinguish a record's
content identity from the occurrence identifier of an event described by that record.
Not every stored record is immutable: refs are mutable navigation state.

### Storage transaction

An atomic batch of local storage operations. **Committing a storage transaction**
is not the same operation as creating a DML commit. One is a persistence boundary;
the other creates a repository-history object.

## Computation and execution

### Intent

The identity of a computational purpose, with a stable intent URI and versioned
**intent definitions**. An intent definition can capture dependency nodes. The stable
URI is not the complete executable binding or automatically a reuse identity.

### Implementation

The code or other executable mechanism selected to realize an intent. Multiple
implementations of one intent can be available side by side. A recorded reference
to implementation code does not by itself prove complete environmental capture.

### Execution adapter

The mechanism responsible for execution mechanics, including interacting with an
external process/service and its recovery or cleanup. It can use DML to wrap a
non-DML program's output in a result sub-DAG. It is not the same role as repository IO.

### Repository IO adapter

The mechanism that transports repository objects and refs through a remote's IO
interface. It is distinct from an execution adapter, even if one tool performs both
roles. Exact interfaces remain open in the new direction.

### Closure — provisional

A resolved executable binding for an intent, including its selected implementation,
execution adapter and relevant configuration/dependencies/resource bindings. We
currently lean toward installation producing a **bound closure**. Exact dimensions
and construction are open; do not confuse this with a Python language closure.

### Argument

An input node explicitly supplied by a caller for a computation. Named argument
bindings are being explored as the execution environment's access mechanism.

### Dependency

A node on which a computation depends. A **captured dependency** is bound when an
intent definition or closure is constructed, rather than selected from a moving ref
at execution time. Closure-level capture is still being explored. Dependencies are
not limited to Python package dependencies.

### Execution description — provisional

The recorded computational dimensions selected for execution, including the closure
and argument bindings. This is a discussion label, not an approved core node kind.
Its separation from request data and exact dimension set remain open. Earlier
“execution node” wording should be qualified when this is what is meant.

### Request

A distinct recorded occurrence of asking for a computation with a selected binding.
A request may reuse a historical attempt or have fresh attempts, including multiple
attempts after interruption. A reuse hit is still a new request.

### Attempt

A distinct occurrence created for fresh execution. Recording an attempt does not
prove the external executor started. Many observations may concern the same attempt;
new observations or cleanup do not automatically create another attempt.

### Execution

The activity of carrying out a computation and producing a result sub-DAG. When
counting events, use **request** or **attempt** rather than an ambiguous “execution”.
Repository history need not capture every external action in that activity.

### Result sub-DAG

The DAG produced by execution. It may contain a minimal wrapped value or detailed
intermediate computation. Identical result content does not merge distinct attempts.
Prefer this over “bare return value” when describing the recorded DML result.

### Observation

A recorded fact or report about an occurrence, such as progress, an external job
identifier or an outcome. The record preserves what was reported; it does not
certify external truth or scientific validity. **Fresh empirical observation** refers
to new execution evidence, not merely another polling response or reuse hit.

### Outcome

A recorded computational result or failure. A missing final outcome is **unknown**,
not automatically failure. Computational outcome and cleanup outcome are separate.
The agreed adapter lifecycle labels are `working` and `done`; they are not synonyms
for computational success and failure.

## Identity and reuse

### Identity facet

A purpose-specific identity derived from a node's recorded description. Two nodes
can match under one facet and differ under another. Facet equality permits only
the operation for which that facet is defined, not universal substitution.

### Record facet

The facet accounting for the full recorded description, including its masks.
**Record identity** or **content identity** may describe the corresponding immutable
object identity. Exact facet names, encodings and extension to other objects remain
open; do not assume every object already has multiple implemented facets.

### Reuse facet

The facet identifying computations eligible to share a selected historical attempt,
with dimensions excluded according to a mask. Its derived identity is also called
the **reuse key** or, when discussing caching, the **cache key**. It is not necessarily
the record identity of the execution description.

### Mask

A rule selecting which dimensions contribute to an identity facet. Excluded dimensions
are replaced with a canonical sentinel, illustratively NULL, before hashing. Actual
bindings remain recorded. Excluded means deliberately ignored, not missing or unknown.
Mask representation, ownership and defaults remain open.

### Occurrence identifier

An identifier distinguishing a request or attempt from otherwise-identical occurrences.
It identifies the event across later records about it, rather than a particular version
of those records. Its generation and format remain open.

### Reuse

Satisfying a request using a recorded historical attempt rather than starting a fresh
attempt. It is not another independent execution or empirical trial. Prefer **reuse**
for this behavior; **cache** is useful when referring specifically to key/lookup machinery.

### Reuse selection

Versioned, branch/commit-scoped state choosing the historical attempt to reuse for a
reuse key. Different snapshots can select different attempts without altering history.

### Adoption

In computational reuse, recording a fresh attempt as the selected reusable attempt.
In resource management, registering an existing external resource with a manager.
Qualify as **reuse adoption** or **resource adoption** when both meanings are in view.
Neither operation necessarily starts a new computation or creates a physical resource.

## Supporting design terms

### Installation — provisional

The workflow realizing an installation description into a bound closure, potentially
provisioning resources. Distinguish the description, each installation attempt and
its resulting closure. Exact installation semantics remain open.

### Resource

Data, code, dependencies, execution machinery or infrastructure referenced outside
DML's local value storage. A **resource datum** records its description/reference and
management associations; it is not the external resource itself. Ownership determines
management authority, not merely containment.

### Materialized resource-management view — provisional

A regenerable IaC configuration derived from recorded DML resource obligations,
currently explored as an ordinary OpenTofu Git repository. Generating the configuration,
registering resources in manager state and applying physical changes are distinct.

### Garbage collection (GC)

Optional collection of unrooted repository history/objects and eligible project-owned
resources. Retention follows full history rooted at refs, not just current snapshots.
External cleanup custody must survive until cleanup can complete or be retried.
Exact roots and implementation are open.

### Excision

Authorized withdrawal of content or resources despite retained references, distinct
from GC of unreachable history. A **tombstone** can preserve permissible evidence
of withdrawal; it is not proof of physical deletion or universal erasure.

### Sidecar observer

An ordinary external consumer that reads recorded computation for inspection or
visualization. It is not a DML subsystem or mandatory producer integration.

### Design spiral

Incremental development through minimal prototypes and review, alternating broad
and deep iterations as useful. An **iteration** is one turn with a concrete learning
or capability goal, not a requirement to finalize a subsystem. DML development
state remains ephemeral until `v1.0.0`; no per-turn migrations or version bumps are
required.
