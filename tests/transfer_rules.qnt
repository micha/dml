module transfer_rules {
  type Row = { key: str, packed: str }
  type Edge = { parent: str, child: str }
  type Change = { kind: str, key: str, before: str, after: str }
  type DatumRead = { stage: str, id: str, kind: int, i64: int }
  type Attempt = {
    command: str,
    status: str,
    completion: str,
    shape: str,
    result: str,
    binary: str,
    rows: List[Row],
    changes: List[Change],
    value: DatumRead
  }
  type Commit = { id: str, packed: str }
  type Fixture = { root: Commit, initialHead: Commit, datum: str, rows: List[Row], edges: List[Edge] }
  type Observation = { fixture: Fixture, attempts: List[Attempt] }
  type Expected = { present: bool, importedExport: bool, published: bool, canonical: str }

  pure val sentinel = "a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5"
  pure val mainKey = "726566732f68656164732f6d61696e" // refs/heads/main
  pure val initial: Expected = {
    present: false, importedExport: false, published: false, canonical: ""
  }
  pure val publicationSequence = List("export", "import_exported", "read_main", "read_value",
                                      "publish_imported", "read_main", "read_value")
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

  pure def coversPublication(attempts: List[Attempt]): bool = {
    val sequenceSize = publicationSequence.length()
    attempts.foldl(0, (matched, attempt) =>
      if (matched == sequenceSize) matched
      else if (publicationSequence[matched] == attempt.command) matched + 1
      else matched) == sequenceSize
  }

  pure def coveragePass(evidence: List[Observation], _verdicts: List[List[str]]): bool = {
    val seen = evidence.foldl(Set(), (allSeen, row) =>
      row.attempts.foldl(allSeen, (seen, attempt) => seen.union(Set(attempt.command))))
    requiredCases.subseteq(seen) and evidence.foldl(false, (covered, row) =>
      covered or coversPublication(row.attempts))
  }

  pure def expectedStatus(command: str, published: bool): str =
    if (command == "read_value") (if (published) "ok" else "not_found")
    else if (goodExports.contains(command) or goodImports.contains(command)
        or command == "read_main" or command == "publish_imported") "ok"
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
    if (attempt.shape != "buffer" or attempt.result != fixture.root.id) "export_output"
    else if (not(exactRows(attempt.rows, fixture.rows))) "export_rows"
    else if (not(dependencyOrder(attempt.rows, fixture.edges))) "export_order"
    else if (canonical != "" and canonical != attempt.binary) "export_unstable"
    else "pass"

  pure def mainMoved(fixture: Fixture): Change = {
    kind: "modified", key: mainKey, before: fixture.initialHead.id, after: fixture.root.id
  }

  pure def expectedChanges(command: str, fixture: Fixture, state: Expected): Set[Change] =
    if (goodImports.contains(command) and not(state.present)) additions(fixture.rows)
    else if (command == "publish_imported") Set(mainMoved(fixture))
    else Set()

  pure def readVerdict(attempt: Attempt, target: Commit): str =
    if (attempt.result != target.id) "read_target"
    else if (attempt.binary != target.packed) "read_commit"
    else "pass"

  pure def valueVerdict(attempt: Attempt, fixture: Fixture, published: bool): str = {
    val expectedTip = if (published) fixture.root.id else fixture.initialHead.id
    // The old tree lacks `all`. The new tree binds `all` / `z-bound` to I64(45)
    // by construction, not by decoding the source fixture's observed bytes.
    val expected: DatumRead =
      if (published) { stage: "datum_decode", id: fixture.datum, kind: 3, i64: 45 }
      else { stage: "tree_entry", id: sentinel, kind: 0, i64: 0 }
    if (attempt.result != expectedTip) "read_target"
    else if (attempt.value.stage != expected.stage) "read_value_stage"
    else if (attempt.value.id != expected.id) "read_datum"
    else if (attempt.value.kind != expected.kind or attempt.value.i64 != expected.i64) "read_value"
    else "pass"
  }

  pure def verdict(attempt: Attempt, fixture: Fixture, state: Expected): str = {
    val command = attempt.command
    val status = expectedStatus(command, state.published)
    val completion = if (busy.contains(command) or command == "publish_imported"
                         or command == "read_main") "ok" else "none"
    val changes = attempt.changes.foldl(Set(), (seen, change) => seen.union(Set(change)))
    if (status == "unknown_command") "unknown_command"
    else if (attempt.status != status) "status"
    else if (attempt.completion != completion) "completion"
    else if (command == "publish_imported" and (not(state.importedExport) or state.published))
      "publication_order"
    else if (changes != expectedChanges(command, fixture, state)) "inventory"
    else if (goodExports.contains(command)) exportVerdict(attempt, fixture, state.canonical)
    else if (goodImports.contains(command) and attempt.result != fixture.root.id) "import_root"
    else if (command == "publish_imported" and attempt.result != fixture.root.id) "publish_target"
    else if (command == "read_main")
      readVerdict(attempt, if (state.published) fixture.root else fixture.initialHead)
    else if (command == "read_value") valueVerdict(attempt, fixture, state.published)
    else if (emptyExports.contains(command) and attempt.shape != "empty") "export_not_empty"
    else if (command == "dirty_export" and attempt.shape != "unchanged") "export_changed_buffer"
    else if (attempt.shape == "" and status != "ok" and attempt.result != sentinel)
      "import_changed_root"
    else "pass"
  }

  // Expected state follows requested imports and publication, not observed C statuses or IDs.
  pure def historyVerdicts(observed: Observation): List[str] =
    observed.attempts.foldl({ expected: initial, verdicts: List() }, (state, attempt) => {
      expected: {
        present: state.expected.present or goodImports.contains(attempt.command),
        importedExport: state.expected.importedExport or attempt.command == "import_exported",
        published: state.expected.published or attempt.command == "publish_imported",
        canonical: if (state.expected.canonical == "" and goodExports.contains(attempt.command))
                     attempt.binary else state.expected.canonical
      },
      verdicts: state.verdicts.append(verdict(attempt, observed.fixture, state.expected))
    }).verdicts

  // The oracle must reject a successful partial export, failure with a leaked row,
  // and failure that changes the caller's output ID even if the LMDB state is unchanged.
  pure val leaf = { key: "aa", packed: "bb" }
  pure val root = { key: "cc", packed: "dd" }
  pure val fixture = {
    root: { id: "cc", packed: "dd" }, initialHead: { id: "ee", packed: "11" }, datum: "aa",
    rows: List(leaf, root), edges: List({ parent: "cc", child: "aa" })
  }
  pure val noValue: DatumRead = { stage: "", id: "", kind: 0, i64: 0 }
  pure val exported = {
    command: "export", status: "ok", completion: "none", shape: "buffer", result: "cc",
    binary: "ff", rows: List(leaf, root), changes: List(), value: noValue
  }
  pure val rejected = {
    command: "extra", status: "invalid_payload", completion: "none", shape: "", result: sentinel,
    binary: "", rows: List(), changes: List(), value: noValue
  }
  pure val earlyPublication = {
    command: "import_exported", status: "ok", completion: "none", shape: "", result: "cc",
    binary: "", rows: List(), value: noValue, changes: List(
      { kind: "added", key: "aa", before: "", after: "bb" },
      { kind: "added", key: "cc", before: "", after: "dd" }, mainMoved(fixture))
  }
  pure val published = {
    command: "publish_imported", status: "ok", completion: "ok", shape: "", result: "cc",
    binary: "", rows: List(), changes: List(mainMoved(fixture)), value: noValue
  }
  pure val readback = {
    command: "read_main", status: "ok", completion: "ok", shape: "", result: "cc",
    binary: "dd", rows: List(), changes: List(), value: noValue
  }
  pure val valueRead = {
    command: "read_value", status: "ok", completion: "none", shape: "", result: "cc",
    binary: "", rows: List(), changes: List(),
    value: { stage: "datum_decode", id: "aa", kind: 3, i64: 45 }
  }
  pure val valueMiss = {
    ...valueRead, status: "not_found", result: "ee",
    value: { stage: "tree_entry", id: sentinel, kind: 0, i64: 0 }
  }
  pure val imported = { ...earlyPublication, changes: List(
    { kind: "added", key: "aa", before: "", after: "bb" },
    { kind: "added", key: "cc", before: "", after: "dd" }) }
  pure val importedState = { ...initial, present: true, importedExport: true }
  pure val publishedState = { ...importedState, published: true }
  pure val controlsPass = all {
    verdict({ ...exported, rows: List(root) }, fixture, initial) == "export_rows",
    verdict({ ...exported, rows: List(root, leaf) }, fixture, initial) == "export_order",
    verdict({ ...exported, changes: List({kind: "added", key: "aa", before: "", after: "bb"}) },
      fixture, initial) == "inventory",
    verdict({ ...rejected, changes: List({kind: "added", key: "aa", before: "", after: "bb"}) },
      fixture, initial) == "inventory",
    verdict({ ...rejected, result: "cc" }, fixture, initial) == "import_changed_root",
    verdict(earlyPublication, fixture, initial) == "inventory",
    verdict(published, fixture, { ...initial, present: true }) == "publication_order",
    verdict({ ...published, changes: List() }, fixture, importedState) == "inventory",
    verdict({ ...published, completion: "invalid_state" }, fixture, importedState) == "completion",
    verdict({ ...published, result: "ee" }, fixture, importedState) == "publish_target",
    verdict(readback, fixture, importedState) == "read_target",
    verdict({ ...readback, result: "ee", binary: "11" }, fixture, publishedState) == "read_target",
    verdict({ ...readback, binary: "11" }, fixture, publishedState) == "read_commit",
    verdict(valueMiss, fixture, importedState) == "pass",
    verdict({ ...valueMiss, value: { ...valueMiss.value, stage: "tree" } },
      fixture, importedState) == "read_value_stage",
    verdict(valueRead, fixture, publishedState) == "pass",
    verdict({ ...valueRead, value: { ...valueRead.value, id: "bb" } },
      fixture, publishedState) == "read_datum",
    verdict({ ...valueRead, value: { ...valueRead.value, kind: 4 } },
      fixture, publishedState) == "read_value",
    verdict({ ...valueRead, value: { ...valueRead.value, i64: 44 } },
      fixture, publishedState) == "read_value",
    coversPublication(List(exported, imported, exported, readback, valueMiss,
                           published, readback, valueRead, exported)),
    not(coversPublication(List(exported, imported, valueMiss, published, readback, valueRead))),
    not(coversPublication(List(exported, imported, readback, valueMiss, published, readback)))
  }
}
