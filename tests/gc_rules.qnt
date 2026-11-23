module gc_rules {
  type Row = { key: str, packed: str }
  type Change = { kind: str, key: str, before: str, after: str }
  type Group = { id: str, rows: List[Row] }
  type Fixture = { base: Group, selected: Group, result: Group, damage: Row }
  type Root = { name: str, target: str }
  type Snapshot = { objects: Set[Row], roots: Set[Root], damaged: bool }
  type Attempt = {
    command: str, order: str, edit: str, ref: str, target: str, finish: str,
    status: str, refStatus: str, completion: str, removed: int, result: str, changes: List[Change]
  }
  type Observation = { fixture: Fixture, attempts: List[Attempt] }

  pure val sentinel = 123456789
  pure val initial: Snapshot = { objects: Set(), roots: Set(), damaged: false }
  pure val refKeys = Map(
    "main" -> "726566732f68656164732f6d61696e",
    "incoming" -> "726566732f68656164732f696e636f6d696e67",
    "result-pin" -> "726566732f68656164732f726573756c742d70696e"
  )
  pure def group(fixture: Fixture, target: str): Group =
    if (target == "base") fixture.base else if (target == "selected") fixture.selected else fixture.result
  pure def rowsOf(group: Group): Set[Row] = group.rows.foldl(Set(), (rows, row) => rows.union(Set(row)))

  // A seed group has only internal edges and a parent link to its predecessor.
  // Closure comes from the fixture's construction, not observed GC/check output.
  pure def closure(fixture: Fixture, target: str): Set[Row] =
    rowsOf(fixture.base)
      .union(if (target == "base") Set() else rowsOf(fixture.selected))
      .union(if (target != "result") Set() else rowsOf(fixture.result))

  pure def rows(fixture: Fixture, snapshot: Snapshot): Set[Row] =
    snapshot.roots.fold(snapshot.objects, (out, ref) =>
      out.union(Set({ key: refKeys.get(ref.name), packed: group(fixture, ref.target).id })))

  pure def diff(before: Set[Row], after: Set[Row]): Set[Change] = {
    val removed = before.exclude(after)
    val added = after.exclude(before)
    val oldKeys = removed.fold(Set(), (out, row) => out.union(Set(row.key)))
    val changes = removed.fold(Set(), (out, row) => {
      val replacement = added.fold("", (packed, candidate) => if (candidate.key == row.key) candidate.packed else packed)
      out.union(Set({ kind: if (replacement == "") "removed" else "modified",
                      key: row.key, before: row.packed, after: replacement }))
    })
    added.fold(changes, (out, row) =>
      if (oldKeys.contains(row.key)) out
      else out.union(Set({ kind: "added", key: row.key, before: "", after: row.packed })))
  }

  pure def refEdit(fixture: Fixture, snapshot: Snapshot, attempt: Attempt): { state: Snapshot, status: str } = {
    val root: Root = { name: attempt.ref, target: attempt.target }
    val occupied = snapshot.roots.exists(ref => ref.name == root.name)
    val targetGroup = group(fixture, root.target)
    val commit = targetGroup.rows[targetGroup.rows.length() - 1]
    if (attempt.edit == "create" or attempt.edit == "update") {
      if (not(snapshot.objects.contains(commit))) { state: snapshot, status: "not_found" }
      else if (attempt.edit == "create" and occupied) { state: snapshot, status: "invalid_state" }
      else if (attempt.edit == "update" and not(occupied)) { state: snapshot, status: "not_found" }
      else {
        val otherRoots = snapshot.roots.filter(ref => ref.name != root.name)
        { state: { ...snapshot, roots: otherRoots.union(Set(root)) }, status: "ok" }
      }
    } else {
      if (not(occupied)) { state: snapshot, status: "not_found" }
      else if (not(snapshot.roots.contains(root))) { state: snapshot, status: "invalid_state" }
      else { state: { ...snapshot, roots: snapshot.roots.exclude(Set(root)) }, status: "ok" }
    }
  }

  pure def collect(fixture: Fixture, snapshot: Snapshot): { state: Snapshot, status: str, removed: int } = {
    val retained = snapshot.roots.fold(Set(), (out, ref) => out.union(closure(fixture, ref.target)))
    if (snapshot.damaged) { state: snapshot, status: "integrity_error", removed: sentinel }
    else {
      val survivors = snapshot.objects.intersect(retained)
      { state: { ...snapshot, objects: survivors }, status: "ok",
        removed: snapshot.objects.size() - survivors.size() }
    }
  }

  pure def predict(fixture: Fixture, snapshot: Snapshot, attempt: Attempt):
      { state: Snapshot, status: str, refStatus: str, completion: str, removed: int, result: str } = {
    if (attempt.command == "import_result") {
      { state: { ...snapshot, objects: snapshot.objects.union(closure(fixture, "result")) },
        status: "ok", refStatus: "none", completion: "none", removed: sentinel, result: fixture.result.id }
    } else if (attempt.command == "damage") {
      { state: { ...snapshot, damaged: true, objects: snapshot.objects.exclude(Set(fixture.damage)) },
        status: "none", refStatus: "none", completion: "none", removed: sentinel, result: "" }
    } else {
      val before = if (attempt.order == "before" or attempt.order == "only") refEdit(fixture, snapshot, attempt)
                   else { state: snapshot, status: "none" }
      val gc = if (attempt.order == "only") { state: before.state, status: "none", removed: sentinel }
               else if (before.status != "ok" and before.status != "none")
                 { state: before.state, status: "invalid_state", removed: sentinel }
               else collect(fixture, before.state)
      val after = if (attempt.order != "after") { state: gc.state, status: before.status }
                  else if (gc.status != "ok") { state: gc.state, status: "invalid_state" }
                  else refEdit(fixture, gc.state, attempt)
      val poisoned = (gc.status != "ok" and gc.status != "none")
                     or (after.status != "ok" and after.status != "none")
      val completion = if (attempt.finish == "abort") "aborted" else if (poisoned) "invalid_state" else "ok"
      { state: if (completion == "ok") after.state else snapshot,
        status: gc.status, refStatus: after.status, completion: completion, removed: gc.removed, result: "" }
    }
  }

  pure def check(fixture: Fixture, snapshot: Snapshot, attempt: Attempt): { state: Snapshot, verdict: str } = {
    val expected = predict(fixture, snapshot, attempt)
    val changes = diff(rows(fixture, snapshot), rows(fixture, expected.state))
    val actual = attempt.changes.foldl(Set(), (out, change) => out.union(Set(change)))
    val verdict = if (attempt.status != expected.status) "status"
                  else if (attempt.refStatus != expected.refStatus) "ref_status"
                  else if (attempt.completion != expected.completion) "completion"
                  else if (attempt.removed != expected.removed) "removed"
                  else if (attempt.result != expected.result) "result"
                  else if (actual != changes or attempt.changes.length() != changes.size()) "inventory"
                  else "pass"
    { state: expected.state, verdict: verdict }
  }

  pure def historyVerdicts(observed: Observation): List[str] =
    observed.attempts.foldl({ state: initial, verdicts: List() }, (out, attempt) => {
      val checked = check(observed.fixture, out.state, attempt)
      { state: checked.state, verdicts: out.verdicts.append(checked.verdict) }
    }).verdicts

  pure def verdictAccepted(verdict: str): bool = verdict == "pass"

  pure def caseName(attempt: Attempt): str = {
    if (attempt.command == "import_result") "imported_unpinned"
    else if (attempt.status == "integrity_error" and attempt.refStatus == "ok") "damage_rollback"
    else if (attempt.removed == 17 and attempt.completion == "aborted") "abort_17"
    else if (attempt.removed == 17 and attempt.completion == "invalid_state" and attempt.refStatus == "not_found")
      "poisoned_after_sweep"
    else if (attempt.removed == 17 and attempt.completion == "ok" and attempt.ref == "result-pin") "release_17"
    else if (attempt.removed == 17 and attempt.completion == "ok" and attempt.order == "none") "commit_17"
    else if (attempt.removed == 0 and attempt.edit == "delete" and attempt.ref == "incoming") "other_pin_retained"
    else if (attempt.removed == 7 and attempt.edit == "create" and attempt.ref == "incoming") "same_txn_pin"
    else if (attempt.removed == 5 and attempt.edit == "delete" and attempt.ref == "incoming")
      "shared_parent_retained"
    else if (attempt.removed == 5 and attempt.edit == "update" and attempt.ref == "incoming") "same_txn_move"
    else if (attempt.removed == 0 and attempt.order == "none") "zero"
    else "other"
  }

  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool = {
    val required = Set("imported_unpinned", "damage_rollback", "abort_17", "poisoned_after_sweep",
      "release_17", "commit_17", "other_pin_retained", "same_txn_pin", "shared_parent_retained", "same_txn_move", "zero")
    val seen = evidence.foldl(Set(), (out, observed) =>
      observed.attempts.foldl(out, (cases, attempt) => cases.union(Set(caseName(attempt)))))
    required.subseteq(seen)
      and evidence.foldl(true, (ok, row) => ok
        and closure(row.fixture, "base").size() == 5 and closure(row.fixture, "selected").size() == 10
        and closure(row.fixture, "result").size() == 17)
      and verdicts.foldl(true, (ok, row) => ok and row.foldl(true, (accepted, v) => accepted and verdictAccepted(v)))
  }

  pure val base = { key: "aa", packed: "11" }
  pure val selected = { key: "bb", packed: "22" }
  pure val result = { key: "cc", packed: "33" }
  pure val fixture: Fixture = {
    base: { id: "aa", rows: List(base) }, selected: { id: "bb", rows: List(selected) },
    result: { id: "cc", rows: List(result) }, damage: result
  }
  pure val populated: Snapshot = { ...initial, objects: Set(base, selected, result) }
  pure val sweep: Attempt = {
    command: "transact", order: "none", edit: "none", ref: "", target: "", finish: "commit",
    status: "ok", refStatus: "none", completion: "ok", removed: 3, result: "",
    changes: List({ kind: "removed", key: "aa", before: "11", after: "" },
                  { kind: "removed", key: "bb", before: "22", after: "" },
                  { kind: "removed", key: "cc", before: "33", after: "" })
  }
  pure val abort = { ...sweep, finish: "abort", completion: "aborted", changes: List() }
  pure val pin: Snapshot = { ...populated, roots: Set({ name: "result-pin", target: "result" }) }
  pure val damaged: Snapshot = { ...populated, damaged: true, objects: Set(base, selected) }
  pure val blocked = {
    ...sweep, status: "integrity_error", completion: "invalid_state", removed: sentinel, changes: List()
  }
  pure val controlsPass = all {
    diff(Set(base), Set({ ...base, packed: "44" })) ==
      Set({ kind: "modified", key: "aa", before: "11", after: "44" }),
    check(fixture, populated, sweep).verdict == "pass",
    check(fixture, populated, { ...sweep, changes: sweep.changes.slice(0, 2) }).verdict == "inventory",
    check(fixture, populated, abort).verdict == "pass",
    check(fixture, populated, { ...abort, changes: sweep.changes }).verdict == "inventory",
    check(fixture, pin, { ...sweep, removed: 0, changes: List() }).verdict == "pass",
    check(fixture, pin, { ...sweep, removed: 0 }).verdict == "inventory",
    check(fixture, damaged, blocked).verdict == "pass",
    check(fixture, damaged, { ...blocked, removed: 0 }).verdict == "removed"
  }
}
