module transfer_rules {
  type Row = { key: str, packed: str }
  type Edge = { parent: str, child: str }
  type Change = { kind: str, key: str, before: str, after: str }
  type Attempt = {
    command: str,
    status: str,
    completion: str,
    shape: str,
    result: str,
    binary: str,
    rows: List[Row],
    changes: List[Change]
  }
  type Fixture = { root: str, rows: List[Row], edges: List[Edge] }
  type Observation = { fixture: Fixture, attempts: List[Attempt] }

  pure val sentinel = "a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5"
  pure val goodExports = Set("export", "repeat", "reexport")
  pure val goodImports = Set("import", "alternative", "import_exported")
  pure val emptyExports = Set("missing_root", "missing_edge", "busy_export", "oversize_export")
  pure val busy = Set("busy_export", "busy_import")
  pure val badHeaders = Set("bad_magic", "bad_version", "reserved", "bad_packed")
  pure val badBounds = Set("short_header", "short_frame", "short_record", "trailing",
                           "oversize_record", "oversize_export", "oversize_count", "oversize_bundle")
  pure val badGraphs = Set("wrong_root_type", "duplicate", "extra", "thin", "forward")
  pure val badIDs = Set("wrong_id", "wrong_root", "corrupt_store")
  pure val badKinds = Set("wrong_kind", "embedded_kind")

  pure val requiredCases = goodExports.union(goodImports).union(emptyExports).union(busy)
    .union(badHeaders).union(badBounds).union(badGraphs).union(badIDs).union(badKinds)
    .union(Set("dirty_export", "map_full"))

  pure def verdictAccepted(verdict: str): bool = verdict == "pass"

  pure def coveragePass(evidence: List[Observation], _verdicts: List[List[str]]): bool = {
    val seen = evidence.foldl(Set(), (allSeen, row) =>
      row.attempts.foldl(allSeen, (seen, attempt) => seen.union(Set(attempt.command))))
    requiredCases.subseteq(seen)
  }

  pure def expectedStatus(command: str): str =
    if (goodExports.contains(command) or goodImports.contains(command)) "ok"
    else if (busy.contains(command)) "invalid_state"
    else if (badHeaders.contains(command)) "invalid_header"
    else if (badBounds.contains(command)) "invalid_bounds"
    else if (badIDs.contains(command)) "integrity_error"
    else if (badKinds.contains(command)) "invalid_kind"
    else if (badGraphs.contains(command)) "invalid_payload"
    else if (command == "missing_root" or command == "missing_edge") "not_found"
    else if (command == "dirty_export") "invalid_argument"
    else if (command == "map_full") "map_full"
    else "unknown_command"

  pure def exactRows(rows: List[Row], expected: List[Row]): bool =
    rows.length() == expected.length()
      and rows.foldl(Set(), (seen, row) => seen.union(Set(row)))
          == expected.foldl(Set(), (seen, row) => seen.union(Set(row)))

  pure def dependencyOrder(rows: List[Row], edges: List[Edge]): bool =
    rows.foldl({ ok: true, keys: Set() }, (state, row) => {
      ok: state.ok and edges.foldl(true, (ok, edge) =>
        ok and (edge.parent != row.key or state.keys.contains(edge.child))),
      keys: state.keys.union(Set(row.key))
    }).ok

  pure def additions(rows: List[Row]): Set[Change] =
    rows.foldl(Set(), (changes, row) => changes.union(Set({
      kind: "added", key: row.key, before: "", after: row.packed
    })))

  pure def exportVerdict(attempt: Attempt, fixture: Fixture, canonical: str): str =
    if (attempt.shape != "buffer" or attempt.result != fixture.root) "export_output"
    else if (not(exactRows(attempt.rows, fixture.rows))) "export_rows"
    else if (not(dependencyOrder(attempt.rows, fixture.edges))) "export_order"
    else if (canonical != "" and canonical != attempt.binary) "export_unstable"
    else "pass"

  pure def expectedChanges(attempt: Attempt, fixture: Fixture, present: bool): Set[Change] =
    if (goodImports.contains(attempt.command) and not(present)) additions(fixture.rows)
    else Set()

  pure def verdict(attempt: Attempt, fixture: Fixture, present: bool, canonical: str): str = {
    val command = attempt.command
    val status = expectedStatus(command)
    val completion = if (busy.contains(command)) "ok" else "none"
    val changes = attempt.changes.foldl(Set(), (seen, change) => seen.union(Set(change)))
    if (status == "unknown_command") "unknown_command"
    else if (attempt.status != status) "status"
    else if (attempt.completion != completion) "completion"
    else if (changes != expectedChanges(attempt, fixture, present)) "inventory"
    else if (goodExports.contains(command)) exportVerdict(attempt, fixture, canonical)
    else if (goodImports.contains(command) and attempt.result != fixture.root) "import_root"
    else if (emptyExports.contains(command) and attempt.shape != "empty") "export_not_empty"
    else if (command == "dirty_export" and attempt.shape != "unchanged") "export_changed_buffer"
    else if (attempt.shape == "" and status != "ok" and attempt.result != sentinel)
      "import_changed_root"
    else "pass"
  }

  // Expected state follows requested good imports, not observed C statuses.
  pure def historyVerdicts(observed: Observation): List[str] =
    observed.attempts.foldl({ present: false, canonical: "", verdicts: List() }, (state, attempt) => {
      present: state.present or goodImports.contains(attempt.command),
      canonical: if (state.canonical == "" and goodExports.contains(attempt.command)) attempt.binary
                 else state.canonical,
      verdicts: state.verdicts.append(verdict(attempt, observed.fixture, state.present, state.canonical))
    }).verdicts

  // The oracle must reject a successful partial export, failure with a leaked row,
  // and failure that changes the caller's output ID even if the LMDB state is unchanged.
  pure val leaf = { key: "aa", packed: "bb" }
  pure val root = { key: "cc", packed: "dd" }
  pure val fixture = { root: "cc", rows: List(leaf, root), edges: List({ parent: "cc", child: "aa" }) }
  pure val exported = {
    command: "export", status: "ok", completion: "none", shape: "buffer", result: "cc",
    binary: "ff", rows: List(leaf, root), changes: List()
  }
  pure val rejected = {
    command: "extra", status: "invalid_payload", completion: "none", shape: "", result: sentinel,
    binary: "", rows: List(), changes: List()
  }
  pure val controlsPass = all {
    verdict({ ...exported, rows: List(root) }, fixture, false, "") == "export_rows",
    verdict({ ...exported, rows: List(root, leaf) }, fixture, false, "") == "export_order",
    verdict({ ...exported, changes: List({kind: "added", key: "aa", before: "", after: "bb"}) },
      fixture, false, "") == "inventory",
    verdict({ ...rejected, changes: List({kind: "added", key: "aa", before: "", after: "bb"}) },
      fixture, false, "") == "inventory",
    verdict({ ...rejected, result: "cc" }, fixture, false, "") == "import_changed_root"
  }
}
