# Iteration 5 worked example: carry recorded history to another repository

Status: informative acceptance story for the user-approved bounded plan, not executed
during preparation. Implementation remains unauthorized. [DESIGN.md](DESIGN.md)
owns planned semantics; [HANDOFF.md](HANDOFF.md) owns implementation/evidence work.
Illustrative APIs and provisional engineering details are not as-built contracts.

## 1. Produce two attempts in A

Use a fresh test-owned repository A and the current installed Iteration 4 runtime.
The source story is equivalent to two additions in
[the existing local example](../../../dml/examples/local_execution.py), but the
acceptance fixture needs only two launches for its main transfer:

- Named I64 inputs `left = 4`, `right = 7`.
- Captured trusted [addition source](../../../dml/examples/local_add.py), explicitly
  selected interpreter and finite timeout.
- Two `run_step` invocations with the same binding/inputs and intent URI.
- Distinct request and attempt occurrences, identical result sub-DAG content rooted
  in 11, final success and separate cleanup disposition.

Save the second completion commit as **C2**. Save the first completion, both
pre-dispatch commits, both publication commits and the result DAG IDs. Through
public reads, save exact record bytes for the entire typed object closure of C2.
Also add an unrelated source branch/object not reachable from C2, so a later check
can prove that transfer is not copying all of A's storage or refs.

The closure includes both ordered parents of each completion commit, historical
initial/final attempt descriptions and all required code/input/outcome/result datums.
Two same-result occurrences remain two occurrences; shared result bytes are one
immutable record in their typed keyspace.

## 2. Export exactly C2

Illustrative proposed API:

```python
from daggerml.transfer import export_commit, import_commit

bundle = export_commit(source_path, commit=second.final_commit)
```

The exporter receives the immutable ID, not `main`. It performs no execution or
source-ref mutation. Persist returned bytes as a bounded caller-owned local file
for a fresh importer process. The example owns its file/scratch operations; no
filesystem archive extraction or remote configuration is involved.

Move A's `main` to a later existing/new commit through ordinary repository operations.
Export C2 again; the bytes must match the original bundle. The saved record bytes
also remain unchanged. A separate export of the later commit may differ normally.
Changing a mutable ref does not change what the earlier bundle means.

## 3. Import into initialized B

Initialize a separate fresh B before importing, using the existing repository API.
Give B an unrelated object and ref `keep`; save its target and bytes. All source
handles must be closed; a file-mediated fresh process imports the bundle without
needing A, its Python source checkout, or live source refs.

```python
# Candidate surface, not an implemented call today:
received = import_commit(destination_path, bundle, ref="received")
assert received.commit == second.final_commit
```

Fresh low-level Python inspection in B verifies:

1. `received` points to C2, without creating a replacement DML commit.
2. Every reached record's typed ID and exact bytes equal A's saved oracle.
3. Completion parent lists preserve pre-dispatch and publication parents in order.
4. Both requests and both attempts retain their occurrence literals and associations.
5. The two outcomes reference the same result DAG; its named/root value is 11.
6. `keep` and its immutable contents remain unchanged.
7. A's unrelated branch-only object/history is absent unless independently shared
   with C2; the fixture must choose genuinely distinct sentinel content.
8. No source `main`, request-reservation or attempt-publication ref was created in B.
   Stored ref-name/path strings in transferred DAGs remain data, not navigation state.

Inspection uses pinned IDs and ordinary edges, not convenience return values alone.
Attempt/publication **history** is present through commit parents; source publication
**refs** are deliberately not transferred. Nothing here establishes runnable recovery
state, a fresh trial, historical-path availability or complete external capture.

## 4. Reimport and ref conflict

Reimport the same bundle into B with `ref="received"`; the existing same-target ref
and all original record bytes remain unchanged. Import without `ref` also succeeds
without adding an implicit head. Export C2 from B and compare its deterministic bytes
with A's bundle.

Create another destination ref pointing to different content. Import requesting that
ref: expect conflict, never overwrite/merge it. Use a separate bundle with at least
one genuinely new object so the test can independently prove rollback of earlier
insertions in the failed batch, not just absence of ref movement.

## 5. Ordinary CLI inspection

No new transfer/execution CLI command is proposed. With the installed existing CLI:

```sh
dml --json --repo destination.dml ref get received
dml --json --repo destination.dml snapshot --ref received
dml --json --repo destination.dml snapshot --commit <pre-dispatch-commit>
dml --json --repo destination.dml walk <final-attempt-dag> --limit 100
dml --json --repo destination.dml show dag <result-dag>
dml --json --repo destination.dml log --ref received
```

Compare full ordered parents with Python reads. Bounded `walk`/`log` prefixes are not
complete closure evidence; the fresh-reader oracle enumerates the complete fixture.
Inspection must not launch transferred source or dereference URI targets.

## 6. Negative and interruption fixtures

Use separate deterministic tests, not destructive changes to the acceptance repos:

- A missing/corrupt reached parent, node or composite-datum child makes export fail.
- Malformed JSON/base64/packed bytes, wrong kind/ID/format, truncation, duplicate or
  extra rows, a wrong root and an omitted dependency are rejected atomically.
- Omit a dependency that already exists in B: still reject the thin bundle.
- A late bad row, different/malformed ref, native map-full or injected storage-commit
  error leaves earlier new objects and refs unpublished; B's sentinel remains intact.
- Deterministically stop an importer after several puts but **before commit**. A fresh
  reader sees no batch/ref. Reimport the full original bundle explicitly and succeed.
- Deterministically stop after successful storage commit but before the return response.
  A fresh reader may see the complete batch/ref; no acknowledgement is not failure.
  Same-target reimport succeeds without manufacturing another execution occurrence.

Private barriers live in fixtures or private method substitutions, not installed
callbacks/fault flags. Every process has finite harness deadlines and test-owned
cleanup. Actual portable versus signal/native-abort evidence must be qualified.
The source history's `done`, failures or unknowns are copied unchanged; importing
an unknown attempt does not finalize or retry it.
