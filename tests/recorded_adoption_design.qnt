// Versioned, explicit adoption for the single-slot scale example.
module recorded_adoption_design {
  // A version ID is the path of chosen attempt IDs, oldest first; the prefix
  // and last ID stand for ordered parents (previous selection, attempt).
  // Genesis stands for (request, attempt). Ref-name literals are fixed per
  // operation and elided. All eligible attempts share a result, but not IDs.
  // Three same-request attempts, one other request, one malformed attempt;
  // two successor refs, one fixed-request plan identified by its saved main,
  // and one reuse slot per publication. Packing, aliases, faults, and transfer
  // are outside this finite model.
  type Version = List[int]
  type Reuse = { tip: int, version: Version }
  type Repo = { base: Version, left: Version, right: Version, incoming: int,
    attempts: Set[int], main: int, plan: int, reuse: Reuse, earlierReuse: Reuse }
  type Event = { op: str, before: Repo, version: Version, attempt: int, side: int, tip: int, ok: bool }

  pure val none: Version = List()
  pure val genesis: Version = List(1)
  pure val legacy: Version = List(0)
  pure val noReuse: Reuse = { tip: -1, version: none }
  pure val empty: Repo = { base: genesis, left: none, right: none, incoming: 2,
    attempts: Set(1, 2), main: 6, plan: 6, reuse: noReuse, earlierReuse: noReuse }
  pure val noEvent: Event = { op: "", before: empty, version: none, attempt: 0, side: 0, tip: 0, ok: false }
  pure def last(v: Version): int = if (v == none) 0 else v[v.length() - 1]
  pure def pin(r: Repo, side: int): Version = if (side == 0) r.base else if (side == 1) r.left else r.right
  pure def request(a: int): int = if (Set(1, 2, 3, 5).contains(a)) 10 else if (a == 4) 11 else 0
  pure def usable(a: int, q: int): bool = request(a) == q and q != 0 and a != 5
  pure def lineage(v: Version, stored: Set[int]): bool = v != none and v.indices().forall(i =>
    stored.contains(v[i]) and usable(v[i], 10) and (if (i == 0) true else v[i] != v[i - 1]))
  pure def allAttempts(v: Version): Set[int] = v.indices().map(i => v[i]).exclude(Set(0))

  var repo: Repo
  var phase: str
  var event: Event

  action init = all { repo' = empty, phase' = "fresh", event' = noEvent }
  action progress(r: Repo, p: str, e: Event): bool = all { repo' = r, phase' = p, event' = e }

  action fresh = progress({ ...repo, attempts: repo.attempts.union(Set(3)) }, "adoptSetup",
    { ...noEvent, before: repo, op: "fresh", ok: true })

  action adopt(side: int, basis: Version, a: int, dest: int, following: str): bool = {
    val allow = pin(repo, side) == basis and lineage(basis, repo.attempts) and repo.incoming == a and
      repo.attempts.contains(a) and usable(a, request(last(basis))) and a != last(basis) and pin(repo, dest) == none
    val version = basis.append(a)
    val updated = if (dest == 1) { ...repo, left: version } else { ...repo, right: version }
    progress(if (allow) updated else repo, if (allow) following else "done",
      { ...noEvent, op: "adopt", before: repo, version: basis, attempt: a, side: side, tip: dest, ok: allow })
  }

  action publish(side: int, v: Version, tip: int, following: str): bool = {
    val allow = pin(repo, side) == v and (lineage(v, repo.attempts) or v == legacy) and
      repo.plan == tip and tip == repo.main and repo.reuse == noReuse
    val updated = { ...repo, main: 7, plan: -1, reuse: { tip: tip, version: v } }
    progress(if (allow) updated else repo, if (allow) following else "done",
      { ...noEvent, op: "publish", before: repo, version: v, side: side, tip: tip, ok: allow })
  }

  action sweep = {
    // Drop genesis and all raw attempt pins. Only the named versions retain
    // attempts; the scalar result (even if main) has no edge to an occurrence.
    val live = allAttempts(repo.left).union(allAttempts(repo.right))
    progress({ ...repo, base: none, incoming: 0, attempts: live }, "publishSetup",
      { ...noEvent, op: "sweep", before: repo, ok: true })
  }

  action step = if (phase == "fresh") fresh
  else if (phase == "adoptSetup") {
    nondet scenario = Set("normal", "wrongBasisPin", "missingBasis", "wrongAttemptPin", "missingAttempt",
      "sameAttempt", "wrongRequest", "badAttempt", "legacyBasis", "badAncestor", "occupied", "unrelatedMain").oneOf()
    val ready = if (scenario == "wrongBasisPin") { ...repo, base: List(1, 3) }
      else if (scenario == "missingBasis") { ...repo, base: none }
      else if (scenario == "wrongAttemptPin") { ...repo, incoming: 3 }
      else if (scenario == "missingAttempt") { ...repo, incoming: 0 }
      else if (scenario == "sameAttempt") { ...repo, incoming: 1 }
      else if (scenario == "wrongRequest") { ...repo, incoming: 4, attempts: repo.attempts.union(Set(4)) }
      else if (scenario == "badAttempt") { ...repo, incoming: 5, attempts: repo.attempts.union(Set(5)) }
      else if (scenario == "legacyBasis") { ...repo, base: legacy }
      else if (scenario == "badAncestor") { ...repo, base: List(1, 4, 3), attempts: repo.attempts.union(Set(4)) }
      else if (scenario == "occupied") { ...repo, left: List(1, 2) }
      else if (scenario == "unrelatedMain") { ...repo, main: 8, plan: -1 } else repo
    progress(ready, "adopt", { ...noEvent, version: if (scenario == "legacyBasis" or scenario == "badAncestor")
      ready.base else genesis, attempt: if (Set("sameAttempt", "wrongRequest", "badAttempt").contains(scenario))
      ready.incoming else 2 })
  } else if (phase == "adopt") adopt(0, event.version, event.attempt, 1, "forkSetup")
  else if (phase == "forkSetup") {
    nondet scenario = Set("sibling", "revert", "single").oneOf()
    if (scenario == "single") sweep else
      progress({ ...repo, incoming: if (scenario == "sibling") 3 else 1 },
        if (scenario == "sibling") "sibling" else "revert", noEvent)
  } else if (phase == "sibling") adopt(0, genesis, 3, 2, "sweep")
  else if (phase == "revert") adopt(1, List(1, 2), 1, 2, "sweep")
  else if (phase == "sweep") sweep
  else if (phase == "publishSetup") {
    nondet scenario = Set("left", "right", "moved", "missing", "staleMain", "missingPlan",
      "movedPlan", "occupied", "invalidAncestor", "sameAdjacent", "sameAttemptVersion", "legacy").oneOf()
    // Perturbations may introduce synthetic versions with their own closure.
    val snapshots = if (scenario == "moved") { ...repo, left: List(1, 3), attempts: repo.attempts.union(Set(3)) }
      else if (scenario == "missing") { ...repo, left: none }
      else if (scenario == "staleMain") { ...repo, main: 8 }
      else if (scenario == "missingPlan") { ...repo, plan: -1 }
      else if (scenario == "movedPlan") { ...repo, plan: 8 }
      else if (scenario == "occupied") { ...repo, reuse: { tip: 6, version: repo.left } }
      else if (scenario == "invalidAncestor") { ...repo, left: List(1, 4, 2), attempts: repo.attempts.union(Set(4)) }
      else if (scenario == "sameAdjacent") { ...repo, left: List(1, 1, 2) }
      else if (scenario == "sameAttemptVersion") { ...repo, left: List(1, 2, 1) }
      else if (scenario == "legacy") { ...repo, left: legacy } else repo
    val side = if (scenario == "right") 2 else 1
    val v = if (Set("moved", "missing").contains(scenario)) repo.left
      else if (scenario == "sameAttemptVersion") genesis
      else if (side == 2 and repo.right == none) List(1, 3) else pin(snapshots, side)
    progress(snapshots, "publish", { ...noEvent, version: v, side: side })
  } else if (phase == "publish") publish(event.side, event.version, 6, "newPlan")
  else if (phase == "newPlan") {
    if (repo.right == none or repo.reuse.version == repo.right or repo.left == legacy)
      progress(repo, "done", noEvent)
    else progress({ ...repo, plan: 7, earlierReuse: repo.reuse, reuse: noReuse }, "publishSibling", noEvent)
  } else if (phase == "publishSibling") publish(2, repo.right, 7, "done")
  else progress(repo, "done", noEvent)

  // Independent fixture oracle for this bounded version space. Do not call
  // the transition's lineage matcher to predict acceptance.
  pure val good = Set(List(1), List(1, 2), List(1, 3), List(1, 2, 1))
  val prior = event.before
  val basis = event.version
  val a = event.attempt
  val adopting = event.op == "adopt"
  val publishing = event.op == "publish"
  val accepted = event.ok
  val exactBasis = pin(prior, event.side) == basis
  val exactAttempt = prior.incoming == a
  val free = pin(prior, event.tip) == none

  invariant adoptionChecksExactIdentityAndLineage = not(adopting) or
    (accepted iff (exactBasis and exactAttempt and free and good.contains(basis) and
      Set(1, 2, 3).contains(a) and a != last(basis)))
  invariant adoptionWritesOnlyFreshVersion = not(adopting and accepted) or {
    val version = basis.append(a)
    repo == (if (event.tip == 1) { ...prior, left: version } else { ...prior, right: version })
  }
  invariant workNeverAdopts = event.op != "fresh" or
    repo == { ...prior, attempts: prior.attempts.union(Set(3)) }
  invariant publicationChecksExactVersionAndPlan = not(publishing) or
    (accepted iff (exactBasis and (good.contains(basis) or basis == legacy) and
      prior.plan == event.tip and prior.main == event.tip and prior.reuse == noReuse))
  invariant publicationWritesOriginalResultAndExactProof = not(publishing and accepted) or
    repo == { ...prior, main: 7, plan: -1, reuse: { tip: event.tip, version: basis } }
  invariant rejectionIsAtomic = not(adopting or publishing) or accepted or repo == prior
  invariant collectionRetainsHistoryNotEqualResults = event.op != "sweep" or {
    val expected = if (prior.right == List(1, 3)) Set(1, 2, 3) else Set(1, 2)
    repo == { ...prior, base: none, incoming: 0, attempts: expected }
  }

  observation freshDoesNotAdopt = event.op == "fresh" and repo.base == genesis and repo.attempts.contains(3)
  observation equalResultAdoption = adopting and accepted and basis == genesis and a == 2
  observation adoptionIgnoresMainAndPlan = adopting and accepted and prior.main != prior.plan
  observation siblingsPreserveTwoChoices = adopting and accepted and repo.left == List(1, 2) and repo.right == List(1, 3)
  observation explicitReversion = adopting and accepted and basis == List(1, 2) and repo.right == List(1, 2, 1)
  observation rejectsMovedBasis = adopting and not(accepted) and not(exactBasis) and prior.base == List(1, 3)
  observation rejectsMovedAttempt = adopting and not(accepted) and prior.incoming == 3 and a == 2
  observation rejectsMissingBasis = adopting and not(accepted) and prior.base == none
  observation rejectsMissingAttempt = adopting and not(accepted) and prior.incoming == 0
  observation rejectsOccupiedIdenticalVersion = adopting and not(accepted) and exactBasis and exactAttempt and
    prior.left == basis.append(a)
  observation rejectsCurrentAttempt = adopting and not(accepted) and exactBasis and exactAttempt and a == last(basis)
  observation rejectsOtherRequest = adopting and not(accepted) and a == 4
  observation rejectsMalformedAttempt = adopting and not(accepted) and a == 5
  observation rejectsLegacyBasis = adopting and not(accepted) and basis == legacy
  observation rejectsMalformedAncestorOnAdopt = adopting and not(accepted) and basis == List(1, 4, 3)
  observation rejectsMalformedAncestorOnReuse = publishing and not(accepted) and basis == List(1, 4, 2)
  observation rejectsDuplicateAdjacentOnReuse = publishing and not(accepted) and basis == List(1, 1, 2)
  observation rejectsMovedVersion = publishing and not(accepted) and basis == List(1, 2) and prior.left == List(1, 3)
  observation rejectsMovedVersionWithSameAttempt = publishing and not(accepted) and
    basis == genesis and prior.left == List(1, 2, 1)
  observation rejectsStaleMain = publishing and not(accepted) and exactBasis and prior.main != event.tip
  observation rejectsConsumedPlan = publishing and not(accepted) and exactBasis and prior.plan == -1 and prior.main == 6
  observation rejectsMovedPlan = publishing and not(accepted) and exactBasis and prior.plan == 8 and prior.main == 6
  observation rejectsOccupiedIdenticalProof = publishing and not(accepted) and exactBasis and
    prior.reuse == { tip: event.tip, version: basis }
  observation legacyReuseStillWorks = publishing and accepted and basis == legacy
  observation reuseAfterSourcePinsRemoved = publishing and accepted and basis == List(1, 2) and
    prior.base == none and prior.incoming == 0 and prior.attempts == Set(1, 2)
  observation unrelatedEqualResultIsCollected = event.op == "sweep" and prior.attempts.contains(3) and
    repo.attempts == Set(1, 2)
  observation twoPublicationsRetainDifferentChoices = publishing and accepted and
    repo.earlierReuse.version == List(1, 2) and repo.reuse.version == List(1, 3) and prior.main == repo.main
}
