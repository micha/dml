// Intent defaults for the recorded-scale example: one atomic source transaction.
module recorded_policy_design {
  // One portable request (10); two eligible selection versions (1, 2) select
  // the same attempt and result (7). The other slot values stand for another
  // request, malformed history, and a dangling ref. Policy versions 1 and 3
  // share the reuse default; version 2 executes; version 4 is malformed.
  // ID 0 means absent. Expected selection -1 means no slot was named.
  // Two successful decisions maximum, with unique occurrence IDs abstracted as
  // sequence positions. Native framing, derivation of IDs, concurrency within
  // a writer transaction, dispatch and actual collection are out of scope.
  type Call = { policy: int, override: str, selection: int, obstacle: str }
  type Decision = { id: int, request: int, policy: int, override: str,
    reason: str, selection: int, expectedMain: int }
  type Repo = { policyPin: int, selectionPin: int, main: int, onlinePlans: int,
    decisions: List[Decision], attempts: int }

  pure val first: Repo = { policyPin: 1, selectionPin: 1, main: 6, onlinePlans: 0,
    decisions: List(), attempts: 2 }
  pure val noCall: Call = { policy: 0, override: "default", selection: -1, obstacle: "none" }
  pure val noDecision: Decision = { id: 0, request: 0, policy: 0, override: "", reason: "",
    selection: -1, expectedMain: 0 }
  var repo: Repo
  var before: Repo
  var call: Call
  var phase: str
  var accepted: bool

  action progress(r: Repo, prior: Repo, c: Call, p: str, ok: bool): bool = all {
    repo' = r, before' = prior, call' = c, phase' = p, accepted' = ok
  }

  action init = all { repo' = first, before' = first, call' = noCall, phase' = "setup", accepted' = false }

  pure def usesSelection(r: Repo, c: Call): bool = c.override == "reuse-selected" or
    (c.override == "default" and r.policyPin != 2)

  pure def resolve(r: Repo, c: Call): str = {
    if (c.policy != r.policyPin or not(Set(1, 2, 3).contains(c.policy))) "error"
    else if (c.override == "fresh") "override-fresh"
    else if (c.override == "default" and r.policyPin == 2) "default-execution"
    else if (not(usesSelection(r, c)) or c.selection == -1 or c.selection != r.selectionPin) "error"
    else if (c.selection == 0 and c.override == "default") "default-no-selection"
    else if (Set(1, 2).contains(c.selection)) {
      if (c.override == "default") "default-selection" else "override-selected-reuse"
    } else "error"
  }

  action decide(following: str): bool = {
    val reason = resolve(repo, call)
    val ok = reason != "error" and call.obstacle == "none"
    val reusing = Set("default-selection", "override-selected-reuse").contains(reason)
    val d = { id: repo.decisions.length() + 1, request: 10, policy: call.policy, override: call.override,
      reason: reason, selection: if (usesSelection(repo, call)) repo.selectionPin else -1, expectedMain: repo.main }
    val after = { ...repo, decisions: repo.decisions.append(d),
      main: if (reusing) 7 else repo.main, onlinePlans: repo.onlinePlans + (if (reusing) 0 else 1) }
    progress(if (ok) after else repo, repo, call, following, ok)
  }

  action step = if (phase == "setup") {
    nondet policyPin = Set(0, 1, 2, 3, 4).oneOf()
    nondet policy = Set(1, 2, 3, 4).oneOf()
    nondet override = Set("default", "fresh", "reuse-selected", "typo").oneOf()
    nondet selectionPin = Set(0, 1, 2, 3, 4, 5).oneOf()
    nondet selection = Set(-1, 0, 1, 2, 3, 4, 5).oneOf()
    nondet obstacle = Set("none", "producerMoved", "planOccupied", "decisionOccupied", "lateFailure").oneOf()
    val ready = { ...repo, policyPin: policyPin, selectionPin: selectionPin }
    progress(ready, ready, { policy: policy, override: override, selection: selection, obstacle: obstacle },
      "firstDecision", false)
  } else if (phase == "firstDecision") decide("afterFirst")
  else if (phase == "afterFirst" and accepted) {
    // Move both refs after the first decision. The next decision uses the new
    // policy, but the first decision remains bound to the old one and its choice.
    val nextPolicy = if (repo.policyPin == 2) 3 else 2
    val ready = { ...repo, policyPin: nextPolicy, selectionPin: 2 }
    progress(ready, ready, { ...noCall, policy: nextPolicy, selection: 2 }, "secondDecision", false)
  } else if (phase == "secondDecision") decide("afterSecond")
  else progress(repo, repo, noCall, "done", false)

  // Independent truth table and effect assertions. In particular, do not use
  // resolve/usesSelection to specify what must be accepted or retained.
  val judged = Set("afterFirst", "afterSecond").contains(phase)
  val current = if (repo.decisions.length() == 0) noDecision else repo.decisions[repo.decisions.length() - 1]
  val exactPolicy = before.policyPin == call.policy and Set(1, 2, 3).contains(call.policy)
  val selectionMatches = Set(1, 2).contains(before.selectionPin) and before.selectionPin == call.selection
  val miss = before.selectionPin == 0 and call.selection == 0
  val expectedReason = if (call.override == "fresh") "override-fresh"
    else if (call.override == "default" and call.policy == 2) "default-execution"
    else if (call.override == "default" and miss) "default-no-selection"
    else if (call.override == "default" and selectionMatches) "default-selection"
    else if (call.override == "reuse-selected" and selectionMatches) "override-selected-reuse"
    else "error"
  val expectsReuse = Set("default-selection", "override-selected-reuse").contains(expectedReason)

  invariant checksPinsAndDecisionTable = not(judged) or
    (accepted iff (exactPolicy and expectedReason != "error" and call.obstacle == "none"))
  invariant rejectionRollsBack = not(judged and not(accepted)) or repo == before
  invariant recordsExactDecision = not(judged and accepted) or {
    val expected = { id: before.decisions.length() + 1, request: 10, policy: call.policy,
      override: call.override, reason: expectedReason, expectedMain: before.main,
      selection: if (expectsReuse) call.selection else if (expectedReason == "default-no-selection") 0 else -1 }
    repo.decisions == before.decisions.append(expected)
  }
  invariant changesOnlyPublicationOrPlan = not(judged and accepted) or
    repo == { ...before, decisions: before.decisions.append(current), main: if (expectsReuse) 7 else before.main,
      onlinePlans: before.onlinePlans + (if (expectsReuse) 0 else 1) }

  val rejected = judged and not(accepted) and call.obstacle == "none"
  observation defaultReuse = judged and accepted and current.reason == "default-selection"
  observation defaultMiss = judged and accepted and current.reason == "default-no-selection"
  observation defaultExecuteIgnores = judged and accepted and current.reason == "default-execution" and
    before.selectionPin == 4 and call.selection == 1
  observation overrideFreshIgnores = judged and accepted and current.reason == "override-fresh" and
    before.policyPin == 1 and before.selectionPin == 5 and call.selection == 1
  observation overrideReuseOfExecuteDefault = judged and accepted and current.reason == "override-selected-reuse" and
    before.policyPin == 2
  observation rejectsOverrideMiss = rejected and exactPolicy and call.override == "reuse-selected" and miss
  observation rejectsNoSlot = rejected and exactPolicy and call.policy == 1 and call.override == "default" and
    call.selection == -1 and before.selectionPin == 0
  observation rejectsUnknownOverride = rejected and exactPolicy and call.override == "typo"
  observation rejectsSameModePolicyMove = rejected and before.policyPin == 3 and call.policy == 1 and selectionMatches
  observation rejectsMalformedPolicy = rejected and before.policyPin == 4 and call.policy == 4 and selectionMatches
  observation rejectsMissingPolicy = rejected and before.policyPin == 0 and call.policy == 1 and selectionMatches
  observation rejectsSameAttemptVersionMove = rejected and exactPolicy and call.policy == 1 and
    call.override == "default" and before.selectionPin == 2 and call.selection == 1
  observation rejectsUnexpectedPresence = rejected and exactPolicy and call.policy == 1 and
    call.override == "default" and before.selectionPin == 1 and call.selection == 0
  observation rejectsUnexpectedAbsence = rejected and exactPolicy and call.policy == 1 and
    call.override == "default" and before.selectionPin == 0 and call.selection == 1
  observation rejectsWrongRequest = rejected and exactPolicy and call.policy == 1 and call.override == "default" and
    before.selectionPin == 3 and call.selection == 3
  observation rejectsMalformedSelection = rejected and exactPolicy and call.policy == 1 and call.override == "default" and
    before.selectionPin == 4 and call.selection == 4
  observation rejectsDanglingSelection = rejected and exactPolicy and call.policy == 1 and call.override == "default" and
    before.selectionPin == 5 and call.selection == 5
  observation rejectsMovedProducer = judged and not(accepted) and exactPolicy and selectionMatches and
    call.override == "reuse-selected" and call.obstacle == "producerMoved"
  observation rejectsOccupiedPlan = judged and not(accepted) and exactPolicy and selectionMatches and
    call.override == "reuse-selected" and call.obstacle == "planOccupied"
  observation rejectsOccupiedDecision = judged and not(accepted) and exactPolicy and selectionMatches and
    call.override == "reuse-selected" and call.obstacle == "decisionOccupied"
  observation rollsBackLateFailure = judged and not(accepted) and exactPolicy and selectionMatches and
    call.override == "reuse-selected" and call.obstacle == "lateFailure"
  observation branchesRetainIndependentDecisions = phase == "afterSecond" and accepted and
    repo.decisions[0].policy == 1 and repo.decisions[0].selection == 1 and current.policy == 2 and current.selection == -1
}
