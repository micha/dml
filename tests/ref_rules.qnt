module ref_rules {
  type Change = { kind: str, key: str, before: str, after: str }
  type Tip = { tip: str, tree: str, parents: List[str] }
  type Readback = { tip: str, tree: str, parents: List[str], statuses: List[str] }
  type Row = { key: str, packed: str }
  type Attempt = {
    op: str, key: str, tip: str, tree: str, parent: str, extraKey: str, finish: str,
    expected: str, observed: str, rows: List[Row], statuses: List[str], changes: List[Change],
    readback: Readback
  }
  type Fixture = { a: str, b: str, c: str, emptyTree: str, candidateTree: str }
  type Observation = { fixture: Fixture, attempts: List[Attempt] }

  pure val refKey = "726566732f68656164732f6d61696e" // refs/heads/main
  pure val required = Set("created", "duplicate", "published", "aborted", "poisoned", "read", "moved", "stale")
  pure def verdictAccepted(verdict: str): bool = required.contains(verdict)

  pure def coversContenders(row: Observation, bFirst: bool): bool = {
    val attempts = row.attempts
    val fixture = row.fixture
    if (attempts.length() < 5) false
    else all {
      attempts[0].op == "create" and attempts[0].key == refKey and attempts[0].tip == fixture.a,
      attempts[1].op == "read" and attempts[1].key == refKey,
      attempts[2].op == "read" and attempts[2].key == refKey,
      attempts[3].op == "publish_expected" and attempts[3].key == refKey
        and attempts[3].expected == fixture.a and attempts[3].tip == (if (bFirst) fixture.b else fixture.c),
      attempts[4].op == "publish_expected" and attempts[4].key == refKey
        and attempts[4].expected == fixture.a and attempts[4].tip == (if (bFirst) fixture.c else fixture.b)
    }
  }

  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool = {
    val seen = verdicts.foldl(Set(), (allSeen, row) =>
      row.foldl(allSeen, (seen, verdict) => seen.union(Set(verdict))))
    required.subseteq(seen)
      and evidence.foldl(false, (covered, row) => covered or coversContenders(row, true))
      and evidence.foldl(false, (covered, row) => covered or coversContenders(row, false))
  }

  pure def addition(key: str, value: str): Change =
    { kind: "added", key: key, before: "", after: value }

  pure def modification(key: str, before: str, after: str): Change =
    { kind: "modified", key: key, before: before, after: after }

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

  pure def fixtureTip(id: str, fixture: Fixture): Tip = {
    tip: id,
    tree: if (id == fixture.c) fixture.candidateTree else fixture.emptyTree,
    parents: if (id == fixture.a) List() else List(fixture.a)
  }

  pure def refReadback(tip: Tip): Readback = {
    tip: tip.tip, tree: tip.tree, parents: tip.parents, statuses: List("ok", "ok", "ok")
  }

  pure def snapshotChanges(attempt: Attempt, previous: Tip): Set[Change] = {
    val move = modification(attempt.key, previous.tip, attempt.tip)
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
    if (attempt.statuses != statuses) "publication_status"
    else if (changes != expected or attempt.changes.length() != expected.size()) "publication_inventory"
    else if (attempt.readback != refReadback(after)) "publication_readback"
    else result
  }

  pure def readVerdict(attempt: Attempt, tip: Tip): str =
    if (attempt.changes != List()) "read_inventory"
    else if (attempt.readback != refReadback(tip)) "read_readback"
    else "read"

  pure def expectedVerdict(attempt: Attempt, previous: Tip, after: Tip): str = {
    val stale = attempt.expected != previous.tip
    val statuses = if (stale) List("ok", "none", "aborted") else List("ok", "ok", "ok")
    val changes = if (previous.tip == after.tip) List()
                  else List(modification(attempt.key, previous.tip, after.tip))
    if (attempt.statuses != statuses) "expected_status"
    else if (attempt.observed != previous.tip) "expected_observed"
    else if (attempt.changes != changes) "expected_inventory"
    else if (attempt.readback != refReadback(after)) "expected_readback"
    else if (stale) "stale" else "moved"
  }

  // The model advances based on the requests, not on the observed statuses or current tip.
  pure def historyVerdicts(observed: Observation): List[str] =
    observed.attempts.foldl({ refs: Map(), verdicts: List() }, (state, attempt) => {
      val refs = state.refs
      val occupied = refs.keys().contains(attempt.key)
      val step =
        if (attempt.op == "create") {
          val updated = if (occupied) refs else refs.put(attempt.key, fixtureTip(attempt.tip, observed.fixture))
          { refs: updated, verdict: createVerdict(occupied, attempt) }
        } else if (not(occupied)) {
          { refs: refs, verdict: "missing_ref_request" }
        } else if (attempt.op == "read") {
          { refs: refs, verdict: readVerdict(attempt, refs.get(attempt.key)) }
        } else if (attempt.op == "publish_expected") {
          val previous = refs.get(attempt.key)
          val current = if (attempt.expected == previous.tip) fixtureTip(attempt.tip, observed.fixture)
                        else previous
          { refs: refs.put(attempt.key, current), verdict: expectedVerdict(attempt, previous, current) }
        } else if (attempt.op == "publish" and not(refs.keys().contains(attempt.extraKey))) {
          // This publication operation stages a new snapshot and optionally updates an absent ref.
          val commit = attempt.finish == "commit" and attempt.extraKey == ""
          val updated = if (commit) refs.put(attempt.key, newTip(attempt)) else refs
          { refs: updated, verdict: publicationVerdict(attempt, refs.get(attempt.key)) }
        } else {
          { refs: refs, verdict: "publication_request" }
        }
      { refs: step.refs, verdicts: state.verdicts.append(step.verdict) }
    }).verdicts
  pure val targetA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  pure val targetB = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  pure val targetC = "cccccccccccccccccccccccccccccccc"
  pure val newId = "dddddddddddddddddddddddddddddddd"
  pure val fixture = { a: targetA, b: targetB, c: targetC, emptyTree: "ee", candidateTree: "ff" }
  pure val original = fixtureTip(targetA, fixture)
  pure val previous = fixtureTip(targetB, fixture)
  pure val candidate = fixtureTip(targetC, fixture)
  pure val create = {
    op: "create", key: refKey, tip: targetA, tree: "", parent: "", extraKey: "", finish: "commit",
    expected: "", observed: "", rows: List(), statuses: List("ok", "ok"),
    changes: List(addition(refKey, targetA)), readback: { tip: "", tree: "", parents: List(), statuses: List() }
  }
  pure val rewrite = modification(refKey, targetB, newId)
  pure val staged = {
    ...create, op: "publish", tip: newId, tree: fixture.emptyTree, parent: targetB,
    statuses: List("ok", "ok", "ok", "none", "ok"), changes: List(rewrite),
    rows: List({ key: "aa", packed: "bb" }, { key: "cc", packed: "dd" }),
    readback: refReadback({ tip: newId, tree: fixture.emptyTree, parents: List(targetB) })
  }
  pure val poisoned = {
    ...staged, extraKey: "6d697373696e67", statuses: List("ok", "ok", "ok", "not_found", "invalid_state"),
    changes: List(), readback: refReadback(previous)
  }
  pure val readOriginal = {
    ...create, op: "read", tip: "", finish: "", statuses: List(),
    changes: List(), readback: refReadback(original)
  }
  pure val moveToB = {
    ...create, op: "publish_expected", tip: targetB, expected: targetA, observed: targetA,
    statuses: List("ok", "ok", "ok"), changes: List(modification(refKey, targetA, targetB)),
    readback: refReadback(previous)
  }
  pure val rejectC = {
    ...moveToB, tip: targetC, observed: targetB, statuses: List("ok", "none", "aborted"),
    changes: List(), readback: refReadback(previous)
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
      == "publication_readback",
    readVerdict({ ...readOriginal, changes: List(rewrite) }, original) == "read_inventory",
    readVerdict({ ...readOriginal, readback: refReadback(previous) }, original) == "read_readback",
    expectedVerdict({ ...moveToB, changes: List() }, original, previous) == "expected_inventory",
    expectedVerdict({ ...rejectC, statuses: moveToB.statuses }, previous, previous) == "expected_status",
    expectedVerdict({ ...rejectC, observed: targetA }, previous, previous) == "expected_observed",
    expectedVerdict({ ...rejectC, changes: List(modification(refKey, targetB, targetC)) }, previous, previous)
      == "expected_inventory",
    expectedVerdict({ ...rejectC, readback: refReadback(candidate) }, previous, previous) == "expected_readback"
  }
}
