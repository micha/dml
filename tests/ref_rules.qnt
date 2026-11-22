module ref_rules {
  type Change = { kind: str, key: str, before: str, after: str }
  type Tip = { tip: str, tree: str, parents: List[str] }
  type Readback = { tip: str, tree: str, parents: List[str], statuses: List[str] }
  type Row = { key: str, packed: str }
  type Attempt = {
    op: str, key: str, tip: str, tree: str, parent: str, extraKey: str, finish: str,
    rows: List[Row], statuses: List[str], changes: List[Change], readback: Readback
  }
  type Fixture = { a: str, emptyTree: str }
  type Observation = { fixture: Fixture, attempts: List[Attempt] }

  pure val required = Set("created", "duplicate", "published", "aborted", "poisoned")
  pure def verdictAccepted(verdict: str): bool = required.contains(verdict)

  pure def coveragePass(_evidence: List[Observation], verdicts: List[List[str]]): bool = {
    val seen = verdicts.foldl(Set(), (allSeen, row) =>
      row.foldl(allSeen, (seen, verdict) => seen.union(Set(verdict))))
    required.subseteq(seen)
  }

  pure def addition(key: str, value: str): Change =
    { kind: "added", key: key, before: "", after: value }

  pure def createVerdict(occupied: bool, attempt: Attempt): str =
    if (occupied) {
      if (attempt.statuses != List("invalid_state", "invalid_state")) "duplicate_status"
      else if (attempt.changes != List()) "duplicate_inventory"
      else "duplicate"
    } else {
      if (attempt.statuses != List("ok", "ok")) "create_status"
      else if (attempt.changes != List(addition(attempt.key, attempt.tip))) "create_inventory"
      else "created"
    }

  pure def newTip(attempt: Attempt): Tip =
    { tip: attempt.tip, tree: attempt.tree, parents: List(attempt.parent) }

  pure def fixtureTip(id: str, fixture: Fixture): Tip =
    { tip: id, tree: fixture.emptyTree, parents: if (id == fixture.a) List() else List(fixture.a) }

  pure def snapshotChanges(attempt: Attempt, previous: Tip): Set[Change] = {
    val move = { kind: "modified", key: attempt.key, before: previous.tip, after: attempt.tip }
    attempt.rows.foldl(Set(move), (changes, row) => changes.union(Set(addition(row.key, row.packed))))
  }

  pure def publicationVerdict(attempt: Attempt, previous: Tip): str = {
    val abort = attempt.finish == "abort"
    val extra = attempt.extraKey != ""
    val commit = not(abort) and not(extra)
    val result = if (abort) "aborted" else if (extra) "poisoned" else "published"
    val finish = if (abort) "aborted" else if (extra) "invalid_state" else "ok"
    val statuses = List("ok", "ok", "ok", if (extra) "not_found" else "none", finish)
    val changes = attempt.changes.foldl(Set(), (seen, change) => seen.union(Set(change)))
    val expected = if (commit) snapshotChanges(attempt, previous) else Set()
    val after = if (commit) newTip(attempt) else previous
    val read = attempt.readback
    if (attempt.statuses != statuses) "publication_status"
    else if (changes != expected or attempt.changes.length() != expected.size()) "publication_inventory"
    else if (read.statuses != List("ok", "ok", "ok") or read.tip != after.tip
             or read.tree != after.tree or read.parents != after.parents) "publication_readback"
    else result
  }

  // The model advances based on the requests, not on the observed statuses.
  pure def historyVerdicts(observed: Observation): List[str] =
    observed.attempts.foldl({ refs: Map(), verdicts: List() }, (state, attempt) => {
      val refs = state.refs
      val occupied = refs.keys().contains(attempt.key)
      val step =
        if (attempt.op == "create") {
          val updated = if (occupied) refs else refs.put(attempt.key, fixtureTip(attempt.tip, observed.fixture))
          { refs: updated, verdict: createVerdict(occupied, attempt) }
        } else if (attempt.op != "publish" or not(occupied) or refs.keys().contains(attempt.extraKey)) {
          // This publication operation stages a new snapshot and optionally updates an absent ref.
          { refs: refs, verdict: "publication_request" }
        } else {
          val commit = attempt.finish == "commit" and attempt.extraKey == ""
          val updated = if (commit) refs.put(attempt.key, newTip(attempt)) else refs
          { refs: updated, verdict: publicationVerdict(attempt, refs.get(attempt.key)) }
        }
      { refs: step.refs, verdicts: state.verdicts.append(step.verdict) }
    }).verdicts

  pure val refKey = "726566732f68656164732f6d61696e"
  pure val targetA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  pure val targetB = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  pure val treeId = "cccccccccccccccccccccccccccccccc"
  pure val newId = "dddddddddddddddddddddddddddddddd"
  pure val fixture = { a: targetA, emptyTree: treeId }
  pure val previous = fixtureTip(targetB, fixture)
  pure val create = {
    op: "create", key: refKey, tip: targetA, tree: "", parent: "", extraKey: "", finish: "commit",
    rows: List(), statuses: List("ok", "ok"), changes: List(addition(refKey, targetA)),
    readback: { tip: "", tree: "", parents: List(), statuses: List() }
  }
  pure val rewrite = { kind: "modified", key: refKey, before: targetB, after: newId }
  pure val staged = {
    ...create, op: "publish", tip: newId, tree: treeId, parent: targetB,
    statuses: List("ok", "ok", "ok", "none", "ok"), changes: List(rewrite),
    rows: List({ key: "aa", packed: "bb" }, { key: "cc", packed: "dd" }),
    readback: { tip: newId, tree: treeId, parents: List(targetB), statuses: List("ok", "ok", "ok") }
  }
  pure val poisoned = {
    ...staged, extraKey: "6d697373696e67", statuses: List("ok", "ok", "ok", "not_found", "invalid_state"),
    changes: List(), readback: {
      tip: previous.tip, tree: previous.tree, parents: previous.parents, statuses: List("ok", "ok", "ok")
    }
  }
  pure val controlsPass = all {
    createVerdict(true, {
      ...create, statuses: List("invalid_state", "invalid_state"), changes: List(rewrite)
    }) == "duplicate_inventory",
    createVerdict(false, {
      ...create, changes: List(addition(refKey, targetA), addition("756e72656c61746564", "00"))
    }) == "create_inventory",
    publicationVerdict(staged, previous) == "publication_inventory",
    publicationVerdict({ ...poisoned, changes: List(rewrite) }, previous) == "publication_inventory",
    publicationVerdict({ ...poisoned, readback: staged.readback }, previous)
      == "publication_readback"
  }
}
