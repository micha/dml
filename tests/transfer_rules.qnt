module transfer_rules {
  type Row = { key: str, packed: str }
  type Edge = { parent: str, child: str }
  type Change = { kind: str, key: str, before: str, after: str }
  type DatumRead = { stage: str, parent: str, id: str, kind: int, i64: int }
  type Lineage = {
    parent: str, inputDatum: str, outputDatum: str, implementationDatum: str,
    inputValue: int, outputValue: int, implementation: str
  }
  type Publication = { expected: str, actual: str, update: str }
  type Integrity = {
    refs: int, brokenRefs: int, invalidEntries: int, invalidObjects: int, reachable: int,
    brokenReachableEdges: int, brokenUnreachableEdges: int, intactUnreachable: int,
    brokenUnreachable: int, unreachable: List[str]
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
    otherChanges: List[Change],
    value: DatumRead,
    lineage: Lineage,
    publication: Publication,
    integrity: Integrity
  }
  type Commit = { id: str, packed: str }
  type Parent = { id: str, datum: str }
  type Fixture = {
    root: Commit, initialHead: Commit, sourceHead: Commit, rootKey: str,
    datum: str, parent: Parent, rows: List[Row], edges: List[Edge],
    destinationCount: int, sourceDetached: List[str]
  }
  type Observation = { fixture: Fixture, attempts: List[Attempt] }
  type Expected = {
    present: bool, importedExport: bool, staged: bool, published: bool, canonical: str,
    selected: bool, result: str, outputDatum: str, implementationDatum: str, resultRows: List[Row],
    captured: bool, returnExported: bool, returned: bool, inspected: bool,
    staleRejected: bool, returnPublished: bool
  }

  pure val sentinel = "a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5"
  pure val mainKey = "726566732f68656164732f6d61696e" // refs/heads/main
  pure val stagedKey = "726566732f68656164732f696e636f6d696e67" // refs/heads/incoming
  pure val resultKey = "726566732f68656164732f726573756c742d70696e" // refs/heads/result-pin
  pure val initial: Expected = {
    present: false, importedExport: false, staged: false, published: false, canonical: "",
    selected: false, result: "", outputDatum: "", implementationDatum: "", resultRows: List(),
    captured: false, returnExported: false, returned: false, inspected: false,
    staleRejected: false, returnPublished: false
  }
  pure val publicationSequence = List("export", "import_exported", "read_main", "read_value",
    "read_staged", "stage_imported", "read_staged", "read_staged_value", "read_staged_parent_value",
    "read_main", "publish_imported", "read_main", "read_value", "read_parent_value")
  pure val lineageSequence = List("export", "import_exported", "stage_imported", "read_staged_value",
    "record_add_one", "read_lineage", "record_add_two", "read_lineage", "read_main", "read_staged")
  pure val returnSequence = lineageSequence.concat(List("capture_source_main", "export_return", "import_return",
    "repeat_return", "read_source_main", "inspect_return", "reject_stale_return", "read_source_main",
    "publish_return", "read_returned_main", "read_source_pin", "read_main", "read_staged", "read_lineage"))
  // Both publication attempts report the ref-get status here; their update and completion are separate.
  pure val returnOkStatuses = Set("capture_source_main", "export_return", "import_return", "repeat_return",
    "read_source_main", "inspect_return", "reject_stale_return", "publish_return", "read_returned_main")
  pure val releaseSequence = returnSequence.concat(List("reject_stale_release", "read_staged", "abort_release",
    "read_staged", "release_staged", "read_staged", "reject_missing_release", "read_lineage", "read_returned_main"))
  pure val releases = Set("reject_stale_release", "abort_release", "release_staged", "reject_missing_release")
  pure val checkSequence = List("import_exported", "check_unpinned", "stage_imported", "check_staged",
    "record_add_one", "publish_return", "release_staged", "check_released", "check_published_source")
  pure val checks = Set("check_unpinned", "check_staged", "check_released", "check_published_source")
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
      and evidence.foldl(false, (covered, row) => covered or
        (coversSequence(row.attempts, releaseSequence) and coversSequence(row.attempts, checkSequence)))
  }

  pure def expectedStatus(command: str, state: Expected): str =
    if (command == "read_value") (if (state.published) "ok" else "not_found")
    else if (command == "read_staged") (if (state.staged) "ok" else "not_found")
    else if (command == "read_source_pin" or command == "reject_missing_release") "not_found"
    else if (command == "reject_stale_release") "invalid_state"
    else if (releases.contains(command) or checks.contains(command)) "ok"
    else if (goodExports.contains(command) or goodImports.contains(command) or returnOkStatuses.contains(command)
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

  pure def returnExportVerdict(attempt: Attempt, fixture: Fixture, state: Expected): str = {
    val rows = state.resultRows
    if (attempt.shape != "buffer" or attempt.result != state.result) "return_export_root"
    else if (rows.length() != 7 or not(exactRows(attempt.rows, fixture.rows.concat(rows)))) "return_export_rows"
    else {
      // Candidate rows are declared in output datum/node, identity datum/node, DAG, tree, commit order.
      val edges = List({ parent: rows[1].key, child: rows[0].key },
        { parent: rows[3].key, child: rows[2].key }, { parent: rows[4].key, child: rows[1].key },
        { parent: rows[4].key, child: rows[3].key }, { parent: rows[5].key, child: rows[4].key },
        { parent: rows[6].key, child: rows[5].key }, { parent: rows[6].key, child: fixture.rootKey })
      if (dependencyOrder(attempt.rows, fixture.edges.concat(edges))) "pass" else "return_export_order"
    }
  }

  pure def mainMoved(fixture: Fixture): Change = {
    kind: "modified", key: mainKey, before: fixture.initialHead.id, after: fixture.root.id
  }

  pure def sourceMainMoved(fixture: Fixture, state: Expected): Change = {
    kind: "modified", key: mainKey, before: fixture.sourceHead.id, after: state.result
  }

  pure def stagedAdded(fixture: Fixture): Change = {
    kind: "added", key: stagedKey, before: "", after: fixture.root.id
  }

  pure def stagedRemoved(fixture: Fixture): Change = {
    kind: "removed", key: stagedKey, before: fixture.root.id, after: ""
  }

  pure def resultAdded(commit: str): Change = {
    kind: "added", key: resultKey, before: "", after: commit
  }

  pure def expectedChanges(attempt: Attempt, fixture: Fixture, state: Expected): Set[Change] = {
    val command = attempt.command
    if (goodImports.contains(command) and not(state.present)) additions(fixture.rows)
    else if (command == "stage_imported") Set(stagedAdded(fixture))
    else if (command == "release_staged") Set(stagedRemoved(fixture))
    else if (command == "publish_imported") Set(mainMoved(fixture))
    else if (command == "publish_return") Set(sourceMainMoved(fixture, state))
    // A already contains the whole input closure; only the result snapshot and commit are new.
    else if (command == "import_return") additions(state.resultRows)
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

  pure def returnInOrder(command: str, state: Expected): bool =
    if (command == "capture_source_main") state.result != "" and not(state.captured)
    else if (command == "export_return") state.captured and not(state.returnExported)
    else if (command == "import_return") state.returnExported and not(state.returned)
    else if (command == "repeat_return" or command == "read_source_main") state.returned and not(state.returnPublished)
    else if (command == "inspect_return") state.returned and not(state.inspected)
    else if (command == "reject_stale_return") state.inspected and not(state.staleRejected)
    else if (command == "publish_return") state.staleRejected and not(state.returnPublished)
    else if (command == "read_returned_main" or command == "read_source_pin") state.returnPublished
    else true

  pure def returnPublicationVerdict(attempt: Attempt, fixture: Fixture, state: Expected): str = {
    val stale = attempt.command == "reject_stale_return"
    val compared = attempt.publication
    if (compared.expected != (if (stale) fixture.root.id else fixture.sourceHead.id)) "return_expected_tip"
    else if (compared.actual != fixture.sourceHead.id) "return_actual_tip"
    else if (compared.update != (if (stale) "none" else "ok")) "return_update"
    else if (attempt.result != state.result) "return_target"
    else "pass"
  }

  pure def integrityVerdict(attempt: Attempt, fixture: Fixture, state: Expected): str = {
    val command = attempt.command
    val unpinned = command == "check_unpinned"
    val staged = command == "check_staged"
    val source = command == "check_published_source"
    val graphSize = fixture.rows.length()
    val resultSize = state.resultRows.length()
    val kept = fixture.destinationCount
    val reachable = if (unpinned) kept else if (staged) graphSize + kept
                    else if (source) graphSize + resultSize else graphSize + resultSize + kept
    val detached = if (unpinned) fixture.rows.foldl(List(), (out, row) => out.append(row.key))
                   else if (source) fixture.sourceDetached else List()
    val report = attempt.integrity
    if ((unpinned and (not(state.importedExport) or state.staged or state.result != ""))
        or (staged and (not(state.staged) or state.result != ""))
        or (not(unpinned or staged) and (state.staged or not(state.returnPublished)))) "integrity_order"
    else if (report.refs != (if (unpinned) 1 else 2) or report.reachable != reachable) "integrity_roots"
    else if (report.brokenRefs != 0 or report.invalidEntries != 0 or report.invalidObjects != 0
             or report.brokenReachableEdges != 0 or report.brokenUnreachableEdges != 0
             or report.brokenUnreachable != 0) "integrity_damage"
    else if (report.intactUnreachable != detached.length() or report.unreachable.length() != detached.length()
             or report.unreachable.foldl(Set(), (out, key) => out.union(Set(key)))
                != detached.foldl(Set(), (out, key) => out.union(Set(key)))) "integrity_unreachable"
    else "pass"
  }

  pure def verdict(attempt: Attempt, fixture: Fixture, state: Expected): str = {
    val command = attempt.command
    val status = expectedStatus(command, state)
    val completion = if (command == "record_add_two" or command == "reject_stale_release"
                         or command == "reject_missing_release") "invalid_state"
      else if (command == "reject_stale_return" or command == "abort_release") "aborted"
      else if (busy.contains(command) or refWrites.contains(command) or command == "record_add_one"
                or command == "read_main" or (command == "read_staged" and state.staged)
                or command == "capture_source_main" or command == "read_source_main"
                or command == "publish_return" or command == "release_staged") "ok"
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
    else if (not(returnInOrder(command, state))) "return_order"
    else if (releases.contains(command) and
             (not(state.returnPublished) or state.staged == (command == "reject_missing_release"))) "release_order"
    else if (attempt.otherChanges.length() != 0) "other_inventory"
    else if (changes != expectedChanges(attempt, fixture, state)) "inventory"
    else if (checks.contains(command)) integrityVerdict(attempt, fixture, state)
    else if (lineageWrites.contains(command)) lineageWriteVerdict(attempt, fixture)
    else if (command == "read_lineage" or command == "inspect_return" or command == "read_returned_main")
      lineageReadVerdict(attempt, fixture, state)
    else if (command == "export_return") returnExportVerdict(attempt, fixture, state)
    else if (command == "import_return" or command == "repeat_return")
      (if (attempt.result == state.result) "pass" else "return_import_root")
    else if (command == "capture_source_main" or command == "read_source_main") readVerdict(attempt, fixture.sourceHead)
    else if (command == "read_source_pin") readVerdict(attempt, { id: sentinel, packed: "" })
    else if (command == "reject_stale_return" or command == "publish_return")
      returnPublicationVerdict(attempt, fixture, state)
    else if (releases.contains(command))
      (if (attempt.result == (if (command == "reject_stale_release") state.result else fixture.root.id))
        "pass" else "release_expected_tip")
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
        staged: attempt.command != "release_staged" and (state.expected.staged or attempt.command == "stage_imported"),
        published: state.expected.published or attempt.command == "publish_imported",
        canonical: if (state.expected.canonical == "" and goodExports.contains(attempt.command))
                     attempt.binary else state.expected.canonical,
        selected: state.expected.selected or attempt.command == "read_staged_value",
        result: if (attempt.command == "record_add_one") attempt.result else state.expected.result,
        outputDatum: if (attempt.command == "record_add_one") attempt.lineage.outputDatum
                     else state.expected.outputDatum,
        implementationDatum: if (attempt.command == "record_add_one") attempt.lineage.implementationDatum
                             else state.expected.implementationDatum,
        resultRows: if (attempt.command == "record_add_one") attempt.rows else state.expected.resultRows,
        captured: state.expected.captured or attempt.command == "capture_source_main",
        returnExported: state.expected.returnExported or attempt.command == "export_return",
        returned: state.expected.returned or attempt.command == "import_return",
        inspected: state.expected.inspected or attempt.command == "inspect_return",
        staleRejected: state.expected.staleRejected or attempt.command == "reject_stale_return",
        returnPublished: state.expected.returnPublished or attempt.command == "publish_return"
      },
      verdicts: state.verdicts.append(verdict(attempt, observed.fixture, state.expected))
    }).verdicts

  // The oracle must reject a successful partial export, failure with a leaked row,
  // and failure that changes the caller's output ID even if the LMDB state is unchanged.
  pure val leaf = { key: "aa", packed: "bb" }
  pure val root = { key: "cc", packed: "dd" }
  pure val fixture = {
    root: { id: "cc", packed: "dd" }, initialHead: { id: "ee", packed: "11" },
    sourceHead: { id: "44", packed: "22" }, rootKey: "cc", datum: "aa", parent: { id: "55", datum: "77" },
    rows: List(leaf, root), edges: List({ parent: "cc", child: "aa" }),
    destinationCount: 1, sourceDetached: List("33")
  }
  pure val noValue: DatumRead = { stage: "", parent: "", id: "", kind: 0, i64: 0 }
  pure val noLineage: Lineage = {
    parent: "", inputDatum: "", outputDatum: "", implementationDatum: "",
    inputValue: 0, outputValue: 0, implementation: ""
  }
  pure val noPublication: Publication = { expected: "", actual: "", update: "" }
  pure val noIntegrity: Integrity = {
    refs: 0, brokenRefs: 0, invalidEntries: 0, invalidObjects: 0, reachable: 0, brokenReachableEdges: 0,
    brokenUnreachableEdges: 0, intactUnreachable: 0, brokenUnreachable: 0, unreachable: List()
  }
  pure val emptyAttempt: Attempt = {
    command: "", status: "ok", completion: "none", shape: "", result: "", binary: "", rows: List(),
    changes: List(), otherChanges: List(), value: noValue, lineage: noLineage, publication: noPublication,
    integrity: noIntegrity
  }
  pure val exported = {
    ...emptyAttempt, command: "export", shape: "buffer", result: "cc", binary: "ff", rows: List(leaf, root)
  }
  pure val rejected = { ...emptyAttempt, command: "extra", status: "invalid_payload", result: sentinel }
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
  pure val capturedState = { ...pinnedState, captured: true, resultRows: newCandidateRows }
  pure val exportedReturnState = { ...capturedState, returnExported: true }
  pure val importedReturnState = { ...exportedReturnState, returned: true }
  pure val inspectedReturnState = { ...importedReturnState, inspected: true }
  pure val rejectedStaleState = { ...inspectedReturnState, staleRejected: true }
  pure val publishedReturnState = { ...rejectedStaleState, returnPublished: true }
  pure val returnExport = {
    ...exported, command: "export_return", result: "99", rows: fixture.rows.concat(newCandidateRows)
  }
  pure val returnImport = {
    ...emptyAttempt, command: "import_return", result: "99",
    changes: newCandidateRows.foldl(List(), (out, row) =>
      out.append({ kind: "added", key: row.key, before: "", after: row.packed }))
  }
  pure val originalSourceMain = { ...readback, command: "read_source_main", result: "44", binary: "22" }
  pure val inspectedReturn = { ...lineageRead, command: "inspect_return" }
  pure val staleReturn = {
    ...emptyAttempt, command: "reject_stale_return", completion: "aborted", result: "99",
    publication: { expected: "cc", actual: "44", update: "none" }
  }
  pure val publishedReturn = {
    ...staleReturn, command: "publish_return", completion: "ok",
    publication: { expected: "44", actual: "44", update: "ok" },
    changes: List(sourceMainMoved(fixture, rejectedStaleState))
  }
  pure val reopenedReturn = { ...lineageRead, command: "read_returned_main" }
  pure val missingSourcePin = { ...unstagedReadback, command: "read_source_pin" }
  pure val released = {
    ...emptyAttempt, command: "release_staged", completion: "ok", result: "cc",
    changes: List(stagedRemoved(fixture))
  }
  pure val staleRelease = {
    ...emptyAttempt, command: "reject_stale_release", status: "invalid_state", completion: "invalid_state", result: "99"
  }
  pure val checkUnpinned = {
    ...emptyAttempt, command: "check_unpinned",
    integrity: { ...noIntegrity, refs: 1, reachable: 1, intactUnreachable: 2, unreachable: List("aa", "cc") }
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
    verdict(returnExport, fixture, capturedState) == "pass",
    verdict({ ...returnExport, result: "cc" }, fixture, capturedState) == "return_export_root",
    verdict({ ...returnExport, rows: newCandidateRows }, fixture, capturedState) == "return_export_rows",
    verdict({ ...returnExport, rows: newCandidateRows.concat(fixture.rows) },
      fixture, capturedState) == "return_export_order",
    verdict(returnImport, fixture, exportedReturnState) == "pass",
    verdict({ ...returnImport, result: "cc" }, fixture, exportedReturnState) == "return_import_root",
    verdict({ ...returnImport, changes: List() }, fixture, exportedReturnState) == "inventory",
    verdict({ ...returnImport, changes: returnImport.changes.append(resultAdded("99")) },
      fixture, exportedReturnState) == "inventory",
    verdict({ ...returnImport, otherChanges: List(stagedAdded(fixture)) },
      fixture, exportedReturnState) == "other_inventory",
    verdict(originalSourceMain, fixture, importedReturnState) == "pass",
    verdict({ ...originalSourceMain, result: "99" }, fixture, importedReturnState) == "read_target",
    verdict({ ...originalSourceMain, binary: "11" }, fixture, importedReturnState) == "read_commit",
    verdict(inspectedReturn, fixture, importedReturnState) == "pass",
    verdict({ ...inspectedReturn, result: "cc" }, fixture, importedReturnState) == "lineage_tip",
    verdict({ ...inspectedReturn, lineage: { ...inspectedReturn.lineage, inputValue: 44 } },
      fixture, importedReturnState) == "lineage_input",
    verdict(staleReturn, fixture, inspectedReturnState) == "pass",
    verdict({ ...staleReturn, completion: "ok" }, fixture, inspectedReturnState) == "completion",
    verdict({ ...staleReturn, publication: { ...staleReturn.publication, update: "ok" } },
      fixture, inspectedReturnState) == "return_update",
    verdict({ ...staleReturn, changes: publishedReturn.changes }, fixture, inspectedReturnState) == "inventory",
    verdict(publishedReturn, fixture, rejectedStaleState) == "pass",
    verdict(publishedReturn, fixture, importedReturnState) == "return_order",
    verdict({ ...publishedReturn, changes: List() }, fixture, rejectedStaleState) == "inventory",
    verdict({ ...publishedReturn, publication: { ...publishedReturn.publication, expected: "cc" } },
      fixture, rejectedStaleState) == "return_expected_tip",
    verdict({ ...publishedReturn, publication: { ...publishedReturn.publication, actual: "cc" } },
      fixture, rejectedStaleState) == "return_actual_tip",
    verdict({ ...publishedReturn, result: "cc" }, fixture, rejectedStaleState) == "return_target",
    verdict(reopenedReturn, fixture, publishedReturnState) == "pass",
    verdict({ ...reopenedReturn, result: "44" }, fixture, publishedReturnState) == "lineage_tip",
    verdict(missingSourcePin, fixture, publishedReturnState) == "pass",
    verdict({ ...missingSourcePin, status: "ok" }, fixture, publishedReturnState) == "status",
    verdict(checkUnpinned, fixture, importedState) == "pass",
    verdict(checkUnpinned, fixture, stagedState) == "integrity_order",
    verdict({ ...checkUnpinned, integrity: { ...checkUnpinned.integrity, reachable: 3 } },
      fixture, importedState) == "integrity_roots",
    verdict({ ...checkUnpinned, integrity: { ...checkUnpinned.integrity, brokenReachableEdges: 1 } },
      fixture, importedState) == "integrity_damage",
    verdict({ ...checkUnpinned, integrity: { ...checkUnpinned.integrity, unreachable: List("aa", "aa") } },
      fixture, importedState) == "integrity_unreachable",
    verdict(released, fixture, publishedReturnState) == "pass",
    verdict(released, fixture, pinnedState) == "release_order",
    verdict({ ...released, changes: released.changes.append({ kind: "removed", key: "cc", before: "dd", after: "" }) },
      fixture, publishedReturnState) == "inventory",
    verdict(staleRelease, fixture, publishedReturnState) == "pass",
    verdict({ ...staleRelease, completion: "ok" }, fixture, publishedReturnState) == "completion",
    verdict({ ...staleRelease, result: "cc" }, fixture, publishedReturnState) == "release_expected_tip",
    coversPublication(beforeStaging.concat(List(stagedReadback, stagedValue, stagedParent)).concat(afterStaging)),
    not(coversPublication(beforeStaging.concat(List(stagedReadback, stagedValue)).concat(afterStaging))),
    not(coversPublication(beforeStaging.concat(List(stagedReadback, stagedValue, stagedParent))
      .concat(List(published, readback, valueRead, parentRead))))
  }
}
