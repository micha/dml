module transfer_rules {
  type Row = { key: str, packed: str }
  type Edge = { parent: str, child: str }
  type Change = { kind: str, key: str, before: str, after: str }
  type DatumRead = { stage: str, parent: str, id: str, kind: int, i64: int }
  type Lineage = {
    parent: str, inputDatum: str, outputDatum: str, implementationDatum: str,
    inputValue: int, outputValue: int, implementation: str
  }
  type Attempt = {
    command: str,
    status: str,
    completion: str,
    shape: str,
    result: str,
    binary: str,
    rows: List[Row],
    changes: List[Change],
    value: DatumRead,
    lineage: Lineage
  }
  type Commit = { id: str, packed: str }
  type Parent = { id: str, datum: str }
  type Fixture = {
    root: Commit, initialHead: Commit, datum: str, parent: Parent, rows: List[Row], edges: List[Edge]
  }
  type Observation = { fixture: Fixture, attempts: List[Attempt] }
  type Expected = {
    present: bool, importedExport: bool, staged: bool, published: bool, canonical: str,
    selected: bool, result: str, outputDatum: str, implementationDatum: str
  }

  pure val sentinel = "a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5"
  pure val mainKey = "726566732f68656164732f6d61696e" // refs/heads/main
  pure val stagedKey = "726566732f68656164732f696e636f6d696e67" // refs/heads/incoming
  pure val resultKey = "726566732f68656164732f726573756c742d70696e" // refs/heads/result-pin
  pure val initial: Expected = {
    present: false, importedExport: false, staged: false, published: false, canonical: "",
    selected: false, result: "", outputDatum: "", implementationDatum: ""
  }
  pure val publicationSequence = List("export", "import_exported", "read_main", "read_value",
    "read_staged", "stage_imported", "read_staged", "read_staged_value", "read_staged_parent_value",
    "read_main", "publish_imported", "read_main", "read_value", "read_parent_value")
  pure val lineageSequence = List("export", "import_exported", "stage_imported", "read_staged_value",
    "record_add_one", "read_lineage", "record_add_two", "read_lineage", "read_main", "read_staged")
  pure val refWrites = Set("stage_imported", "publish_imported")
  pure val lineageWrites = Set("record_add_one", "record_add_two")
  pure val stagedValues = Set("read_staged_value", "read_staged_parent_value")
  pure val parentValues = Set("read_parent_value", "read_staged_parent_value")
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

  pure def coversSequence(attempts: List[Attempt], sequence: List[str]): bool = {
    val sequenceSize = sequence.length()
    attempts.foldl(0, (matched, attempt) =>
      if (matched == sequenceSize) matched
      else if (sequence[matched] == attempt.command) matched + 1
      else matched) == sequenceSize
  }

  pure def coversPublication(attempts: List[Attempt]): bool = coversSequence(attempts, publicationSequence)

  pure def coveragePass(evidence: List[Observation], _verdicts: List[List[str]]): bool = {
    val seen = evidence.foldl(Set(), (allSeen, row) =>
      row.attempts.foldl(allSeen, (seen, attempt) => seen.union(Set(attempt.command))))
    requiredCases.subseteq(seen)
      and evidence.foldl(false, (covered, row) => covered or coversPublication(row.attempts))
      and evidence.foldl(false, (covered, row) => covered or coversSequence(row.attempts, lineageSequence))
  }

  pure def expectedStatus(command: str, state: Expected): str =
    if (command == "read_value") (if (state.published) "ok" else "not_found")
    else if (command == "read_staged") (if (state.staged) "ok" else "not_found")
    else if (goodExports.contains(command) or goodImports.contains(command)
        or command == "read_main" or command == "read_parent_value" or command == "record_add_one"
        or command == "read_lineage" or stagedValues.contains(command) or refWrites.contains(command)) "ok"
    else if (busy.contains(command) or command == "record_add_two") "invalid_state"
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

  pure def stagedAdded(fixture: Fixture): Change = {
    kind: "added", key: stagedKey, before: "", after: fixture.root.id
  }

  pure def resultAdded(commit: str): Change = {
    kind: "added", key: resultKey, before: "", after: commit
  }

  pure def expectedChanges(attempt: Attempt, fixture: Fixture, state: Expected): Set[Change] = {
    val command = attempt.command
    if (goodImports.contains(command) and not(state.present)) additions(fixture.rows)
    else if (command == "stage_imported") Set(stagedAdded(fixture))
    else if (command == "publish_imported") Set(mainMoved(fixture))
    // For lineage writes, rows were packed independently, using reported IDs only as links/keys.
    else if (command == "record_add_one") additions(attempt.rows).union(Set(resultAdded(attempt.result)))
    else Set()
  }

  pure def readVerdict(attempt: Attempt, target: Commit): str =
    if (attempt.result != target.id) "read_target"
    else if (attempt.binary != target.packed) "read_commit"
    else "pass"

  pure def valueVerdict(attempt: Attempt, fixture: Fixture, atImportedRoot: bool): str = {
    val expectedTip = if (atImportedRoot) fixture.root.id else fixture.initialHead.id
    // The initial tree lacks `all`. The imported tip yields I64(45) through the same path
    // and its first parent yields I64(41), by construction rather than decoding observed bytes.
    val expected: DatumRead =
      if (parentValues.contains(attempt.command))
        { stage: "datum_decode", parent: fixture.parent.id, id: fixture.parent.datum, kind: 3, i64: 41 }
      else if (atImportedRoot) { stage: "datum_decode", parent: "", id: fixture.datum, kind: 3, i64: 45 }
      else { stage: "tree_entry", parent: "", id: sentinel, kind: 0, i64: 0 }
    if (attempt.result != expectedTip) "read_target"
    else if (attempt.value.stage != expected.stage) "read_value_stage"
    else if (attempt.value.parent != expected.parent) "read_parent"
    else if (attempt.value.id != expected.id) "read_datum"
    else if (attempt.value.kind != expected.kind or attempt.value.i64 != expected.i64) "read_value"
    else "pass"
  }

  pure def lineageWriteVerdict(attempt: Attempt, fixture: Fixture): str = {
    val candidateKeys = attempt.rows.foldl(Set(), (out, row) => out.union(Set(row.key)))
    if (candidateKeys.size() != 7 or attempt.rows.length() != 7 or attempt.shape != "new_keys")
      "lineage_candidate"
    else if (attempt.lineage.parent != fixture.root.id) "lineage_input"
    else "pass"
  }

  pure def lineageReadVerdict(attempt: Attempt, fixture: Fixture, state: Expected): str = {
    val read = attempt.lineage
    if (attempt.result != state.result) "lineage_tip"
    else if (read.parent != fixture.root.id or read.inputDatum != fixture.datum or read.inputValue != 45)
      "lineage_input"
    else if (read.outputDatum != state.outputDatum or read.outputValue != 46) "lineage_output"
    else if (read.implementationDatum != state.implementationDatum
             or read.implementation != "6578616d706c652e6164642d6f6e654031") // example.add-one@1
      "lineage_implementation"
    else "pass"
  }

  pure def verdict(attempt: Attempt, fixture: Fixture, state: Expected): str = {
    val command = attempt.command
    val status = expectedStatus(command, state)
    val completion = if (command == "record_add_two") "invalid_state"
      else if (busy.contains(command) or refWrites.contains(command) or command == "record_add_one"
                or command == "read_main" or (command == "read_staged" and state.staged)) "ok"
      else "none"
    val changes = attempt.changes.foldl(Set(), (seen, change) => seen.union(Set(change)))
    if (status == "unknown_command") "unknown_command"
    else if (attempt.status != status) "status"
    else if (attempt.completion != completion) "completion"
    else if ((command == "stage_imported" and (not(state.importedExport) or state.staged or state.published))
             or (stagedValues.contains(command) and (not(state.staged) or state.published))) "staging_order"
    else if ((command == "publish_imported" and (not(state.importedExport) or state.published))
             or (command == "read_parent_value" and not(state.published))) "publication_order"
    else if (lineageWrites.contains(command) and
             (not(state.staged) or not(state.selected) or state.published
              or (command == "record_add_one") != (state.result == ""))) "lineage_order"
    else if (command == "read_lineage" and state.result == "") "lineage_order"
    else if (changes != expectedChanges(attempt, fixture, state)) "inventory"
    else if (lineageWrites.contains(command)) lineageWriteVerdict(attempt, fixture)
    else if (command == "read_lineage") lineageReadVerdict(attempt, fixture, state)
    else if (goodExports.contains(command)) exportVerdict(attempt, fixture, state.canonical)
    else if (goodImports.contains(command) and attempt.result != fixture.root.id) "import_root"
    else if (command == "stage_imported" and attempt.result != fixture.root.id) "stage_target"
    else if (command == "publish_imported" and attempt.result != fixture.root.id) "publish_target"
    else if (command == "read_main")
      readVerdict(attempt, if (state.published) fixture.root else fixture.initialHead)
    else if (command == "read_staged")
      readVerdict(attempt, if (state.staged) fixture.root else { id: sentinel, packed: "" })
    else if (stagedValues.contains(command)) valueVerdict(attempt, fixture, true)
    else if (command == "read_value" or command == "read_parent_value")
      valueVerdict(attempt, fixture, state.published)
    else if (emptyExports.contains(command) and attempt.shape != "empty") "export_not_empty"
    else if (command == "dirty_export" and attempt.shape != "unchanged") "export_changed_buffer"
    else if (attempt.shape == "" and status != "ok" and attempt.result != sentinel)
      "import_changed_root"
    else "pass"
  }

  // Expected state follows requested imports, staging and publication, not observed C outcomes.
  pure def historyVerdicts(observed: Observation): List[str] =
    observed.attempts.foldl({ expected: initial, verdicts: List() }, (state, attempt) => {
      expected: {
        present: state.expected.present or goodImports.contains(attempt.command),
        importedExport: state.expected.importedExport or attempt.command == "import_exported",
        staged: state.expected.staged or attempt.command == "stage_imported",
        published: state.expected.published or attempt.command == "publish_imported",
        canonical: if (state.expected.canonical == "" and goodExports.contains(attempt.command))
                     attempt.binary else state.expected.canonical,
        selected: state.expected.selected or attempt.command == "read_staged_value",
        result: if (attempt.command == "record_add_one") attempt.result else state.expected.result,
        outputDatum: if (attempt.command == "record_add_one") attempt.lineage.outputDatum
                     else state.expected.outputDatum,
        implementationDatum: if (attempt.command == "record_add_one") attempt.lineage.implementationDatum
                             else state.expected.implementationDatum
      },
      verdicts: state.verdicts.append(verdict(attempt, observed.fixture, state.expected))
    }).verdicts

  // The oracle must reject a successful partial export, failure with a leaked row,
  // and failure that changes the caller's output ID even if the LMDB state is unchanged.
  pure val leaf = { key: "aa", packed: "bb" }
  pure val root = { key: "cc", packed: "dd" }
  pure val fixture = {
    root: { id: "cc", packed: "dd" }, initialHead: { id: "ee", packed: "11" }, datum: "aa",
    parent: { id: "55", datum: "77" },
    rows: List(leaf, root), edges: List({ parent: "cc", child: "aa" })
  }
  pure val noValue: DatumRead = { stage: "", parent: "", id: "", kind: 0, i64: 0 }
  pure val noLineage: Lineage = {
    parent: "", inputDatum: "", outputDatum: "", implementationDatum: "",
    inputValue: 0, outputValue: 0, implementation: ""
  }
  pure val exported = {
    command: "export", status: "ok", completion: "none", shape: "buffer", result: "cc",
    binary: "ff", rows: List(leaf, root), changes: List(), value: noValue, lineage: noLineage
  }
  pure val rejected = {
    command: "extra", status: "invalid_payload", completion: "none", shape: "", result: sentinel,
    binary: "", rows: List(), changes: List(), value: noValue, lineage: noLineage
  }
  pure val earlyPublication = {
    ...rejected, command: "import_exported", status: "ok", result: "cc", changes: List(
      { kind: "added", key: "aa", before: "", after: "bb" },
      { kind: "added", key: "cc", before: "", after: "dd" }, mainMoved(fixture))
  }
  pure val published = {
    ...earlyPublication, command: "publish_imported", completion: "ok", changes: List(mainMoved(fixture))
  }
  pure val readback = {
    ...published, command: "read_main", binary: "dd", changes: List()
  }
  pure val valueRead = {
    ...readback, command: "read_value", completion: "none", binary: "",
    value: { stage: "datum_decode", parent: "", id: "aa", kind: 3, i64: 45 }
  }
  pure val valueMiss = {
    ...valueRead, status: "not_found", result: "ee",
    value: { stage: "tree_entry", parent: "", id: sentinel, kind: 0, i64: 0 }
  }
  pure val parentRead = {
    ...valueRead, command: "read_parent_value",
    value: { stage: "datum_decode", parent: "55", id: "77", kind: 3, i64: 41 }
  }
  pure val imported = { ...earlyPublication, changes: List(
    { kind: "added", key: "aa", before: "", after: "bb" },
    { kind: "added", key: "cc", before: "", after: "dd" }) }
  pure val importedState = { ...initial, present: true, importedExport: true }
  pure val stagedState = { ...importedState, staged: true }
  pure val publishedState = { ...stagedState, published: true }
  pure val staged = { ...published, command: "stage_imported", changes: List(stagedAdded(fixture)) }
  pure val stagedReadback = { ...readback, command: "read_staged" }
  pure val unstagedReadback = {
    ...stagedReadback, status: "not_found", completion: "none", result: sentinel, binary: ""
  }
  pure val stagedValue = { ...valueRead, command: "read_staged_value" }
  pure val stagedParent = { ...parentRead, command: "read_staged_parent_value" }
  pure val beforeStaging = List(exported, imported, readback, valueMiss, unstagedReadback, staged)
  pure val afterStaging = List(readback, published, readback, valueRead, parentRead)

  pure val pinnedState = {
    ...stagedState, selected: true, result: "99", outputDatum: "66", implementationDatum: "88"
  }
  pure val lineageRead = {
    ...readback, command: "read_lineage", completion: "none", binary: "", result: "99",
    lineage: { parent: "cc", inputDatum: "aa", outputDatum: "66", implementationDatum: "88",
               inputValue: 45, outputValue: 46, implementation: "6578616d706c652e6164642d6f6e654031" }
  }
  pure val newCandidateRows = List("a1", "a2", "a3", "a4", "a5", "a6", "a7")
    .foldl(List(), (out, key) => out.append({ key: key, packed: "bb" }))
  pure val duplicateLineage = {
    ...rejected, command: "record_add_two", status: "invalid_state", completion: "invalid_state",
    shape: "new_keys", result: "a7", rows: newCandidateRows,
    lineage: { ...noLineage, parent: "cc", outputDatum: "a1", implementationDatum: "a3" }
  }
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
    verdict(parentRead, fixture, publishedState) == "pass",
    verdict(parentRead, fixture, importedState) == "publication_order",
    verdict({ ...parentRead, value: { ...parentRead.value, parent: "cc" } },
      fixture, publishedState) == "read_parent",
    verdict({ ...parentRead, value: { ...valueRead.value, parent: "55" } },
      fixture, publishedState) == "read_datum",
    verdict({ ...parentRead, value: { ...parentRead.value, i64: 45 } },
      fixture, publishedState) == "read_value",
    verdict(staged, fixture, importedState) == "pass",
    verdict(staged, fixture, initial) == "staging_order",
    verdict({ ...staged, changes: List(stagedAdded(fixture), mainMoved(fixture)) },
      fixture, importedState) == "inventory",
    verdict(stagedReadback, fixture, importedState) == "status",
    verdict(stagedReadback, fixture, stagedState) == "pass",
    verdict(stagedParent, fixture, importedState) == "staging_order",
    verdict(stagedParent, fixture, stagedState) == "pass",
    verdict(readback, fixture, stagedState) == "read_target",
    verdict(lineageRead, fixture, pinnedState) == "pass",
    verdict({ ...lineageRead, lineage: { ...lineageRead.lineage, parent: "ee" } },
      fixture, pinnedState) == "lineage_input",
    verdict({ ...lineageRead, lineage: { ...lineageRead.lineage, outputValue: 47 } },
      fixture, pinnedState) == "lineage_output",
    verdict({ ...lineageRead, lineage: { ...lineageRead.lineage, implementation: "00" } },
      fixture, pinnedState) == "lineage_implementation",
    verdict(duplicateLineage, fixture, pinnedState) == "pass",
    verdict({ ...duplicateLineage, completion: "ok" }, fixture, pinnedState) == "completion",
    verdict({ ...duplicateLineage, shape: "existing_keys" }, fixture, pinnedState) == "lineage_candidate",
    verdict({ ...duplicateLineage, changes: List({ kind: "added", key: "a1", before: "", after: "bb" }) },
      fixture, pinnedState) == "inventory",
    coversPublication(beforeStaging.concat(List(stagedReadback, stagedValue, stagedParent)).concat(afterStaging)),
    not(coversPublication(beforeStaging.concat(List(stagedReadback, stagedValue)).concat(afterStaging))),
    not(coversPublication(beforeStaging.concat(List(stagedReadback, stagedValue, stagedParent))
      .concat(List(published, readback, valueRead, parentRead))))
  }
}
