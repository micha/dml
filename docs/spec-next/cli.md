# Inspection CLI

Status: implemented native `dml` over the existing local repository.

## Authority boundary

This document owns command grammar, selectors, traversal, presentation and
exit/diagnostic conventions. [Repository](repository.md) owns storage validation,
[objects](objects.md) owns fields/names, and [records](records.md) owns datum
encoding. [Packaging](../packaging-and-distribution.md) owns the bundled executable
and Python console forwarding. Terminology follows the [glossary](glossary.md).

## Grammar

```sh
dml --version                     # also -V
dml --help
dml [--json] --repo PATH ref get NAME
dml [--json] --repo PATH show datum|node|dag|tree|commit ID
dml [--json] --repo PATH lookup DAG_ID NAME
dml [--json] --repo PATH walk DAG_ID [--limit N]
dml [--json] --repo PATH snapshot (--ref NAME | --commit ID) [--limit N]
dml [--json] --repo PATH log (--ref NAME | --commit ID) [--limit N]
```

Global options precede the command; `--repo` and `--json` can appear in either
order. `--repo` is required for repository commands. Snapshot/log require exactly
one explicit selector, avoiding confusion between hex-shaped ref names and IDs.
IDs use the C lowercase 32-hex rule. Limit is a positive decimal integer, default
100, representable as size_t; a leading `+`, whitespace or negative sign is rejected.
Duplicate selectors/limits, unknown commands/options and no command are errors.
Help is global, not per-command. No current-directory repository or default ref
is inferred. Version/help require no repository.

Each repository command opens without creation and resolves/traverses using one
read storage transaction. It neither writes objects/refs nor repairs/initializes
state. Ordinary LMDB open can access lock files; this is **not** a physically
read-only-mount guarantee.

## Commands and traversal

- `ref get`: resolve the ref's validated commit target.
- `show`: inspect the expected object type, full immediate fields and references.
  Datum collections are ID edges, never recursively loaded values.
- `lookup`: return the node ID bound to the name in the exact supplied DAG. Invalid
  names are usage errors; absent names are runtime `not_found`. No implicit descent,
  global fallback or value conversion.
- `walk`: iterative depth-first preorder of DAG/node structure: emit the starting
  DAG, visit its root then binding targets in canonical order; sub-DAG nodes visit
  their DAG target. Literal nodes include datum IDs/bounded previews without
  expanding composite datum children. Tracking uses object type and ID; shared
  objects emit once while root/binding/target edges remain in the fields. Active
  state is checked before visited suppression, rejecting traversed cycles.
- `snapshot`: inspect the selected commit, parents and tree, with entries in
  canonical name order. For displayed entries, read the DAG and root node. Literal
  roots include a datum ID and bounded preview; sub-DAG roots show their target DAG
  without descending or pretending that it is a scalar.
- `log`: iterative depth-first preorder of **all** parents in stored parent order,
  showing shared ancestors once. It is not timestamp order or first-parent history.
  Active-stack cycle detection fails on a traversed cycle. A bounded prefix is not
  a validity proof for unvisited history.

Snapshot limits displayed entries; log limits distinct displayed commits; walk
limits distinct emitted DAG/node records (not datums, edges or scope paths).
Snapshot truncation compares displayed and total entry counts. Log/walk truncation
is true only
when an unvisited work item remains after the limit, not merely because the limit
was exactly reached. Multiple parents are inspected without implementing merge.
Missing/corrupt visited objects fail the command, not produce invented history.

These bounds limit presentation/traversal, not C record allocation/read size,
binding arrays, buffered output bytes or native direct-reference validation.
Indexed binding/tree scans and visited-ID
comparisons remain simple linear scans; large histories are not benchmarked.

## Human presentation and previews

Human output is a command-specific title (`Ref`, `Object`, `Snapshot`, `History`,
`Lookup` or `DAG structure`)
followed by indented structured fields/entries, one per line. Field names match
JSON so human inspections and machine inspections have the same evidence basis.
Human datum `show` and snapshot previews bound values:

| Kind | Preview limit |
| --- | --- |
| STRING/URI | 80 Unicode code points |
| BYTES | 32 bytes, lowercase hex |
| LIST/SET/MAP | 8 IDs/pairs, no child expansion |

Previews include `truncated` and, for strings/bytes/collections, `total_count`.
ASCII controls/DEL, quotes/backslashes and Unicode C1 controls are escaped, including
U+0085/U+009B; no raw terminal escapes are emitted from datum previews. Tree entries
and parents in human `show` are complete. `--json show` gives complete datum values,
not bounded previews, and can be large.

## JSON contract

Success emits one deterministic UTF-8 JSON document plus newline. IDs and I64
values are strings, not JSON numbers. F64 is a string: finite values use
locale-independent round-trippable decimal, canonical zero is `"0"`, and nonfinite
values are `"nan"`, `"inf"`, `"-inf"`. No JSON NaN/Infinity tokens are emitted.

```json
{"command":"ref-get","name":"main","target":"<commit-id>"}
```

`show` has `command: "show"`, `type`, `id`, and these fields:

| Type | Fields |
| --- | --- |
| Datum | `datum: {kind, value}`; bytes add `encoding: "hex"` |
| Node | `kind: "literal"`, `datum: <id>` or `kind: "subdag"`, `dag: <id>` |
| DAG | `root: <id>`, `bindings: [{name, node}, ...]` in canonical order |
| Tree | `entries: [{name, dag}, ...]` in canonical order |
| Commit | `tree: <id>`, `parents: [<id>, ...]` in stored order |

Datum `kind` is lowercase null/bool/i64/f64/bytes/string/uri/list/set/map. Values
are JSON null/bool, I64/F64 strings, bytes hex strings, string/URI strings,
LIST/SET ID arrays, or MAP arrays of `{key, value}` ID pairs.

Snapshot fields: `command: "snapshot"`, `commit`, `tree`, `parents`, `entry_count`,
`entries`, `truncated`. Each entry has `name`, `dag`, `root`, and `root_node`:
`{kind: "literal", datum: <id>}` or `{kind: "subdag", dag: <id>}`. Literal entries
also have `datum` and `preview`; sub-DAG entries omit those fields.
Preview fields: `kind`, `value`, `truncated`, optional
`total_count` and `encoding`, following the same datum value rules with bounds.

Log fields: `command: "log"`, `start`, `commits` and `truncated`. Each commit is
`{id, tree, parents}`. Key/order formatting is deterministic; clients should parse
fields, not depend on exact spacing.

Lookup fields: `command: "lookup"`, `dag`, `name`, `node`. Walk fields:
`command: "walk"`, `start`, `records`, `truncated`. Each record has `type: "dag"`
or `"node"`, `id` and the immediate fields from the show table above. Literal
nodes additionally have `preview`. Deterministic structure order is not execution
or chronological order. A truncated prefix is not a validity proof for unseen content.

## Exit status and diagnostics

- **0:** success, including deliberately truncated output.
- **2:** usage/parser error, including malformed ID/limit arguments.
- **1:** repository, schema, integrity, allocation or output-write failure.

Successful results go only to stdout. Runtime/parser errors go to stderr. JSON
mode emits `{error: {code, native_code, detail}}`; parser native codes are null,
other native codes are integers. Human usage errors suggest global help. Results
are buffered before emission so late storage/validation failures leave stdout
empty. A write failure can leave partial emitted bytes; it reports failure rather
than success. SIGPIPE is ignored where available so a closed output pipe can
report a write failure. Diagnostic allocation failure uses a fixed JSON fallback.

## Evidence

[Native CLI](../../src/cli.c), [inspection tests](../../tests/python/test_inspection_cli.py),
[private fault sweeps](../../tests/python/test_cli_failures.py),
[fresh-process public acceptance](../../tests/python/test_public_acceptance.py) and
[CLI memory workload](../../tests/python/cli_memory.py) exercise the implementation.
Actual local/platform validation is recorded in
[Iteration 2 results](../../../dml-design/iterations/02-repository-usability/RESULTS.md)
and [Iteration 3 results](../../../dml-design/iterations/03-composable-dags/RESULTS.md).
