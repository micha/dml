module staged_import_rules {
  type Row = { key: str, packed: str }
  type Group = { id: str, rows: List[Row] }
  type Fixture = { keep: Group, selected: Group, result: Group, initialRows: List[Row] }
  type Attempt = {
    command: str, target: str, ref: str, variant: str, compared: str, result: str, packed: str,
    status: str, readStatus: str, update: str, completion: str, removed: int, inventory: List[Row]
  }
  type Observation = { fixture: Fixture, attempts: List[Attempt] }
  type Snapshot = { objects: Set[Row], refs: str -> str, captured: str }
  type Prediction = { state: Snapshot, expected: Attempt, covered: str }

  pure val sentinel = "a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5"
  pure val schema = { key: "6d6574612f736368656d61", packed: "444d4c310100010018000000000000000000000001000000" }
  pure val refKeys = Map(
    "main" -> "726566732f68656164732f6d61696e",
    "incoming" -> "726566732f68656164732f696e636f6d696e67",
    "returned" -> "726566732f68656164732f72657475726e6564"
  )

  pure def rowSet(rows: List[Row]): Set[Row] = rows.foldl(Set(), (out, row) => out.union(Set(row)))
  pure def group(f: Fixture, target: str): Group =
    if (target == "keep") f.keep else if (target == "selected") f.selected else f.result

  // The result extends the selected commit, which already includes its ancestors.
  pure def closure(f: Fixture, target: str): Set[Row] =
    if (target == "") Set()
    else if (target == "result") rowSet(f.selected.rows).union(rowSet(f.result.rows))
    else rowSet(group(f, target).rows)

  pure def initial(f: Fixture): Snapshot = {
    objects: closure(f, "keep"), refs: Map("main" -> "keep", "incoming" -> "", "returned" -> ""), captured: ""
  }

  pure def inventory(f: Fixture, s: Snapshot): Set[Row] =
    s.refs.keys().fold(s.objects.union(Set(schema)), (out, ref) => {
      val target = s.refs.get(ref)
      if (target == "") out else out.union(Set({ key: refKeys.get(ref), packed: group(f, target).id }))
    })

  pure def exactRows(observed: List[Row], expected: Set[Row]): bool =
    observed.length() == expected.size() and rowSet(observed) == expected

  pure val emptyAttempt: Attempt = {
    command: "", target: "", ref: "", variant: "", compared: "", result: "", packed: "", status: "none",
    readStatus: "none", update: "none", completion: "none", removed: 123456789, inventory: List()
  }

  pure def predictStage(f: Fixture, s: Snapshot, a: Attempt): Prediction = {
    val wanted = closure(f, a.target)
    val occupied = a.ref != "bad/ref" and s.refs.get(a.ref) != ""
    val newRows = wanted.exclude(s.objects)
    val status =
      if (a.ref == "bad/ref") "invalid_argument"
      else if (a.variant == "truncated") "invalid_bounds"
      else if (occupied) "invalid_state"
      else "ok"
    val covered =
      if (occupied and newRows.size() == 7 and a.target != s.refs.get(a.ref)) "duplicate_new_objects"
      else if (occupied and newRows.size() == 0 and a.target == s.refs.get(a.ref)) "duplicate_same_target"
      else if (status == "ok" and newRows.size() == 10 and a.target == "selected") "stage_fresh_closure"
      else if (status == "ok" and newRows.size() == 0) "stage_present_closure"
      else status
    {
      state: if (status != "ok") s else { ...s, objects: s.objects.union(wanted), refs: s.refs.set(a.ref, a.target) },
      expected: { ...emptyAttempt, status: status, result: if (status == "ok") group(f, a.target).id else sentinel },
      covered: covered
    }
  }

  pure def predictCollection(f: Fixture, s: Snapshot): Prediction = {
    val retained = s.refs.keys().fold(Set(), (out, ref) => out.union(closure(f, s.refs.get(ref))))
    val survivors = s.objects.intersect(retained)
    val resultKept = rowSet(f.result.rows).subseteq(survivors)
    val removed = s.objects.size() - survivors.size()
    val covered =
      if (removed == 17 and s.refs.get("main") == "keep") "collect_unpinned_closure"
      else if (s.refs.get("returned") == "result" and resultKept) "collect_preserving_stage"
      else if (s.refs.get("returned") == "" and s.refs.get("main") == "result" and resultKept) "collect_preserving_main"
      else if (removed == 7 and s.refs.get("returned") == "" and s.refs.get("main") == "selected") "collect_last_root"
      else "other"
    { state: { ...s, objects: survivors }, covered: covered,
      expected: { ...emptyAttempt, status: "ok", completion: "ok", removed: removed } }
  }

  pure def predictRead(f: Fixture, s: Snapshot, a: Attempt): Prediction = {
    val capture = a.command == "capture_main"
    val target = s.refs.get(if (capture) "main" else a.ref)
    val commit = group(f, target)
    {
      state: if (capture) { ...s, captured: target } else s,
      expected: if (target == "") { ...emptyAttempt, status: "not_found", result: sentinel }
        else { ...emptyAttempt, status: "ok", readStatus: "ok", result: commit.id,
               packed: commit.rows[commit.rows.length() - 1].packed },
      covered: if (a.ref == "returned" and target != "") "read_staged" else "other"
    }
  }

  pure def predictPublication(f: Fixture, s: Snapshot): Prediction = {
    val matches = s.captured == s.refs.get("main")
    {
      state: if (matches) { ...s, refs: s.refs.set("main", "result") } else s,
      expected: { ...emptyAttempt, status: "ok", compared: group(f, s.captured).id, target: f.result.id,
                  result: group(f, s.refs.get("main")).id, update: if (matches) "ok" else "none",
                  completion: if (matches) "ok" else "aborted" },
      covered: if (s.refs.get("returned") != "result" or s.captured == "") "invalid_order"
               else if (matches) "published" else "stale_main"
    }
  }

  pure def predict(f: Fixture, s: Snapshot, a: Attempt): Prediction =
    if (a.command == "stage") predictStage(f, s, a)
    else if (a.command == "collect") predictCollection(f, s)
    else if (a.command == "read_ref" or a.command == "capture_main") predictRead(f, s, a)
    else if (a.command == "publish_returned") predictPublication(f, s)
    else if (a.command == "import_result") {
      state: { ...s, objects: s.objects.union(closure(f, "result")) }, covered: "other",
      expected: { ...emptyAttempt, status: "ok", result: f.result.id }
    } else if (a.command == "advance_main") {
      state: { ...s, refs: s.refs.set("main", "selected") }, covered: "other",
      expected: { ...emptyAttempt, status: "ok", completion: "ok" }
    } else if (a.command == "release_returned") {
      state: { ...s, refs: s.refs.set("returned", "") },
      covered: if (s.refs.get("returned") == "result") "released" else "invalid_order",
      expected: { ...emptyAttempt, status: "ok", completion: "ok", target: f.result.id }
    } else { state: s, covered: "invalid_order", expected: emptyAttempt }

  pure def check(f: Fixture, a: Attempt, p: Prediction): str = {
    val e = p.expected
    if (p.covered == "invalid_order") "order"
    else if (a.status != e.status) "status"
    else if (a.completion != e.completion) "completion"
    else if (a.readStatus != e.readStatus or a.packed != e.packed) "readback"
    else if (a.update != e.update or a.compared != e.compared) "comparison"
    else if ((a.command == "publish_returned" or a.command == "release_returned") and a.target != e.target) "target"
    else if (a.result != e.result) "result"
    else if (a.removed != e.removed) "removed"
    else if (not(exactRows(a.inventory, inventory(f, p.state)))) "inventory"
    else "pass"
  }

  pure def runHistory(observed: Observation): { state: Snapshot, verdicts: List[str], covered: Set[str] } = {
    val f = observed.fixture
    observed.attempts.foldl({ state: initial(f), verdicts: List(), covered: Set() }, (out, attempt) => {
      val p = predict(f, out.state, attempt)
      { state: p.state, verdicts: out.verdicts.append(check(f, attempt, p)), covered: out.covered.union(Set(p.covered)) }
    })
  }

  pure def historyVerdicts(observed: Observation): List[str] = runHistory(observed).verdicts
  pure def verdictAccepted(verdict: str): bool = verdict == "pass"

  pure def coveragePass(evidence: List[Observation], _verdicts: List[List[str]]): bool = {
    val seen = evidence.foldl(Set(), (out, row) => out.union(runHistory(row).covered))
    val required = Set("stage_fresh_closure", "stage_present_closure", "duplicate_same_target", "duplicate_new_objects",
      "invalid_argument", "invalid_bounds", "collect_unpinned_closure", "collect_preserving_stage", "stale_main",
      "read_staged", "released", "collect_last_root", "published", "collect_preserving_main")
    required.subseteq(seen) and evidence.foldl(true, (ok, row) => {
      val f = row.fixture
      ok and closure(f, "result").size() == 17 and closure(f, "keep").size() == 5
         and closure(f, "result").intersect(closure(f, "keep")).size() == 0
         and exactRows(f.initialRows, inventory(f, initial(f)))
    })
  }

  pure val kept = { key: "aa", packed: "11" }
  pure val selected = { key: "bb", packed: "22" }
  pure val result = { key: "cc", packed: "33" }
  pure val fixture: Fixture = {
    keep: { id: "aa", rows: List(kept) }, selected: { id: "bb", rows: List(selected) },
    result: { id: "cc", rows: List(result) }, initialRows: List()
  }
  pure val originRows = List(schema, kept, { key: refKeys.get("main"), packed: "aa" })
  pure val pinnedRows = originRows.concat(List(selected, { key: refKeys.get("incoming"), packed: "bb" }))
  pure val staged = { ...emptyAttempt, command: "stage", target: "selected", ref: "incoming", variant: "valid",
                      result: "bb", status: "ok", inventory: pinnedRows }
  pure val beforeStage = initial(fixture)
  pure val stagePrediction = predict(fixture, beforeStage, staged)
  pure val rejected = { ...staged, target: "result", status: "invalid_state", result: sentinel }
  pure val rejectPrediction = predict(fixture, stagePrediction.state, rejected)
  pure val controlsPass = all {
    check(fixture, staged, stagePrediction) == "pass",
    check(fixture, { ...staged, inventory: originRows.append(selected) }, stagePrediction) == "inventory",
    check(fixture, { ...staged, inventory: originRows.append(pinnedRows[4]) }, stagePrediction) == "inventory",
    check(fixture, rejected, rejectPrediction) == "pass",
    check(fixture, { ...rejected, inventory: pinnedRows.append(result) }, rejectPrediction) == "inventory",
    check(fixture, { ...rejected, result: "cc" }, rejectPrediction) == "result"
  }
}
