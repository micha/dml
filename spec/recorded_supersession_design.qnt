// Advisory implementation declarations in the recorded scale example.
module recorded_supersession_design {
  // Two implementation labels, one producer/factor, two implementation slots,
  // and at most four intent nodes on any path. Whole commands are atomic; ref
  // names, byte encodings, hashing, garbage collection, and worker execution
  // are out of scope. A fresh request is modeled without running its worker.
  type Fields = { implementation: int, mode: str, slots: (int, int) }
  type Claim = { predecessor: int, successor: int, reason: str }
  type Snapshot = { kind: str, fields: Fields, claim: Claim, parents: List[int] }
  type Notice = { commit: int, basis: int, evidence: int, claim: Claim }
  type Ancestry = { next: int, valid: bool, genesis: int, fields: Fields, notice: Notice }
  type Decision = { intent: int, implementation: int, slot: int, selection: int, outcome: str }
  type Repo = { versions: int -> Snapshot, basis: int, evidence: int, output: int, promoted: int,
    slotA: int, slotB: int, decisions: List[Decision] }
  type Declare = { basis: int, evidence: int, claim: Claim, obstacle: str }
  type Request = { selected: int, expected: int, override: int, selection: int }
  type View = { intent: int, relation: str, notice: Notice }
  type Inspection = { historical: View, knowledge: View }

  pure val v1: Fields = { implementation: 1, mode: "reuse-by-default", slots: (1, 2) }
  pure val v2 = { ...v1, implementation: 2 }
  pure val noFields: Fields = { implementation: 0, mode: "", slots: (0, 0) }
  pure val forward: Claim = { predecessor: 1, successor: 2, reason: "correctness-fix" }
  pure val reverse: Claim = { predecessor: 2, successor: 1, reason: "operational-replacement" }
  pure val noClaim: Claim = { predecessor: 0, successor: 0, reason: "" }
  pure val noNotice: Notice = { commit: 0, basis: 0, evidence: 0, claim: noClaim }
  pure val noView: View = { intent: 0, relation: "omitted", notice: noNotice }
  pure val noInspection: Inspection = { historical: noView, knowledge: noView }
  pure val noDecision: Decision = { intent: 0, implementation: 0, slot: 0, selection: 0, outcome: "" }

  pure def definition(settings: Fields, parents: List[int]): Snapshot =
    { kind: "intent", fields: settings, claim: noClaim, parents: parents }
  pure def declaration(claim: Claim, parents: List[int]): Snapshot =
    { kind: "declaration", fields: noFields, claim: claim, parents: parents }

  // 2 is a sibling of a declaration on 1; 3 has the same fields as 2,
  // but is a different genesis. 4 is a conflicting yet compatible sibling
  // of a declaration on 1. 5--9 are invalid intent histories.
  pure val initial: Repo = {
    versions: Map(
      1 -> definition(v1, List()),
      2 -> definition(v2, List(1)),
      3 -> definition(v2, List()),
      4 -> declaration(reverse, List(2, 51)),
      5 -> declaration(forward, List(50, 1)),
      6 -> declaration(forward, List(1, 52)),
      7 -> declaration(forward, List(4, 50)),
      8 -> definition({ ...v1, slots: (1, 3) }, List(4)),
      9 -> declaration({ ...forward, successor: 1 }, List(1, 50))
    ),
    basis: 1, evidence: 50, output: 0, promoted: 0, slotA: 101, slotB: 0, decisions: List()
  }
  // These abstract ordinary commits have nonempty trees. 52 is an empty
  // commit and 53 does not exist. Intent commits are also opaque as evidence;
  // the reader must not follow the evidence edge when resolving ancestry.
  pure def nonemptyCommit(r: Repo, id: int): bool =
    Set(50, 51).contains(id) or r.versions.keys().contains(id)
  pure def validClaim(c: Claim): bool =
    Set(1, 2).contains(c.predecessor) and Set(1, 2).contains(c.successor) and
      c.predecessor != c.successor and Set("correctness-fix", "operational-replacement").contains(c.reason)
  pure def sameContract(a: Fields, b: Fields): bool = a.mode == b.mode and a.slots == b.slots

  pure def readAncestor(r: Repo, a: Ancestry): Ancestry = {
    if (not(a.valid) or a.next == 0) a
    else if (not(r.versions.keys().contains(a.next))) { ...a, valid: false }
    else {
      val node = r.versions.get(a.next)
      if (node.kind == "intent") {
        val n = node.parents.length()
        val settings = node.fields
        if (n > 1 or not(Set(1, 2).contains(settings.implementation)) or settings.slots._1 == settings.slots._2 or
          not(Set("reuse-by-default", "execute-by-default").contains(settings.mode)) or
          (a.fields != noFields and not(sameContract(a.fields, settings)))) { ...a, valid: false }
        else { ...a, next: if (n == 0) 0 else node.parents[0], genesis: if (n == 0) a.next else 0,
          fields: if (a.fields == noFields) settings else a.fields }
      } else if (node.kind == "declaration" and node.parents.length() == 2 and validClaim(node.claim) and
        a.notice == noNotice) {
        val basis = node.parents[0]
        val evidence = node.parents[1]
        if (basis == evidence or not(nonemptyCommit(r, evidence))) { ...a, valid: false }
        else { ...a, next: basis, notice: { commit: a.next, basis: basis, evidence: evidence, claim: node.claim } }
      } else { ...a, valid: false }
    }
  }
  pure def readIntent(r: Repo, id: int): Ancestry = {
    val start = { next: id, valid: true, genesis: 0, fields: noFields, notice: noNotice }
    val end = List(0, 1, 2, 3).foldl(start, (a, _) => readAncestor(r, a))
    { ...end, valid: end.valid and end.genesis != 0 and end.next == 0 }
  }

  pure val defaultDeclaration: Declare = { basis: 1, evidence: 50, claim: forward, obstacle: "" }
  pure val defaultRequest: Request = { selected: 1, expected: 1, override: 0, selection: 101 }
  var repo: Repo
  var before: Repo
  var phase: str
  var command: Declare
  var request: Request
  var query: (int, int)
  var report: Inspection
  var accepted: bool

  pure val noQuery = (-1, 0)
  action progress(r: Repo, b: Repo, p: str, c: Declare, q: Request, k: (int, int), i: Inspection, ok: bool): bool = all {
    repo' = r, before' = b, phase' = p, command' = c, request' = q, query' = k, report' = i, accepted' = ok
  }
  action init = all {
    repo' = initial, before' = initial, phase' = "ready", command' = defaultDeclaration,
    request' = defaultRequest, query' = noQuery, report' = noInspection, accepted' = false
  }

  action declare(r: Repo, c: Declare, p: str): bool = {
    val selected = readIntent(r, c.basis)
    val ok = r.basis == c.basis and r.evidence == c.evidence and c.basis != c.evidence and
      selected.valid and selected.notice == noNotice and nonemptyCommit(r, c.evidence) and
      validClaim(c.claim) and r.output == 0 and c.obstacle == ""
    val pending = { ...r, output: 20,
      versions: r.versions.put(20, declaration(c.claim, List(c.basis, c.evidence))) }
    progress(if (ok) pending else r, r, p, c, request, noQuery, noInspection, ok)
  }

  action promote(r: Repo, expected: int, aborting: bool): bool = {
    val basis = readIntent(r, expected)
    val ok = expected == r.output and basis.valid and r.promoted == 0 and not(aborting)
    val pending = { ...r, promoted: 21,
      versions: r.versions.put(21, definition({ ...basis.fields, implementation: 2 }, List(expected))) }
    progress(if (ok) pending else r, r, "promotion",
      { ...command, basis: expected, obstacle: if (aborting) "late" else "" }, request, noQuery, noInspection, ok)
  }

  action route(q: Request, p: str): bool = {
    val intent = readIntent(repo, q.expected)
    val chosen = if (q.override == 0) intent.fields.implementation else q.override
    val slot = if (chosen == 1) intent.fields.slots._1 else intent.fields.slots._2
    val selected = if (slot == 1) repo.slotA else repo.slotB
    val ok = q.selected == q.expected and intent.valid and Set(1, 2).contains(chosen) and selected == q.selection
    val decision = { intent: q.expected, implementation: chosen, slot: slot, selection: selected,
      outcome: if (selected == 0) "execute" else "reuse" }
    progress(if (ok) { ...repo, decisions: repo.decisions.append(decision) } else repo,
      repo, p, command, q, noQuery, noInspection, ok)
  }

  pure def view(intent: int, implementation: int, n: Notice): View = {
    { intent: intent, notice: n, relation: if (n == noNotice) "none"
      else if (implementation == n.claim.predecessor) "predecessor" else "successor" }
  }
  action inspect(r: Repo, index: int, k: int): bool = {
    val d = if (r.decisions.indices().contains(index)) r.decisions[index] else noDecision
    val historical = readIntent(r, d.intent)
    val known = readIntent(r, k)
    val ok = historical.valid and (k == 0 or (known.valid and historical.genesis == known.genesis and
      sameContract(historical.fields, known.fields)))
    val result = { historical: view(d.intent, d.implementation, historical.notice),
      knowledge: if (k == 0) noView else view(k, d.implementation, known.notice) }
    progress(r, r, "inspection", command, request, (index, k), if (ok) result else noInspection, ok)
  }

  action step = if (phase == "ready") any {
    {
      nondet actualBasis = Set(0, 1, 2, 4, 5).oneOf()
      nondet expectedBasis = Set(1, 2, 4, 5).oneOf()
      nondet actualEvidence = Set(0, 1, 4, 50, 51, 52).oneOf()
      nondet expectedEvidence = Set(1, 4, 50, 51, 52).oneOf()
      nondet c = Set(forward, reverse, { ...forward, reason: reverse.reason }, { ...reverse, reason: forward.reason },
        { ...forward, successor: 1 }, { ...forward, successor: 3 }, { ...forward, reason: "unsupported-reason" }).oneOf()
      nondet obstacle = Set("", "alias", "occupied", "late").oneOf()
      val ready = { ...repo, basis: actualBasis, evidence: actualEvidence, output: if (obstacle == "occupied") 3 else 0 }
      declare(ready, { basis: expectedBasis, evidence: expectedEvidence, claim: c, obstacle: obstacle }, "declaration")
    },
    route(defaultRequest, "original")
  } else if (phase == "original") declare(repo, defaultDeclaration, "sequence")
  else if (phase == "sequence") any {
    route({ ...defaultRequest, selected: 20, expected: 20 }, "declared"),
    // Inspect a stored declaration with all live pins unrelated to its content.
    {
      nondet k = Set(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 20, 52, 53).oneOf()
      inspect({ ...repo, basis: 3, evidence: 0, output: 0 }, 0, k)
    }
  } else if (phase == "declared") {
    nondet expected = Set(1, 20).oneOf()
    nondet occupied = Set(0, 2).oneOf()
    nondet aborting = Set(false, true).oneOf()
    promote({ ...repo, promoted: occupied }, expected, aborting)
  } else if (phase == "promotion" and accepted) any {
    route({ ...defaultRequest, selected: 21, expected: 21, selection: 0 }, "promoted"),
    route({ ...defaultRequest, selected: 21, expected: 21 }, "wrong-slot"),
    route({ ...defaultRequest, selected: 21, expected: 20 }, "moved-pin"),
    route({ ...defaultRequest, selected: 21, expected: 21, override: 1 }, "explicit-old")
  } else if (phase == "promoted") any {
    {
      nondet k = Set(0, 1, 2, 3, 4, 20, 21).oneOf()
      nondet i = Set(0, 1, 2).oneOf()
      inspect({ ...repo, basis: 3, evidence: 0, output: 0, promoted: 0 }, i, k)
    },
    // A compatible v2 result is selected independently of declaring or
    // promoting. It does not replace or consume v1's selected result.
    progress({ ...repo, slotB: 201 }, repo, "selected-successor", command, request, noQuery, noInspection, true)
  } else if (phase == "selected-successor")
    route({ ...defaultRequest, selected: 21, expected: 21, selection: 201 }, "successor-reuse")
  else if (phase == "successor-reuse") route(defaultRequest, "retained-old")
  else progress(repo, repo, "done", command, request, noQuery, noInspection, false)

  // Check publication independently against the bounded input classes, then
  // verify exact output, preserved input refs/slots, and rollback of objects.
  val declaring = Set("declaration", "sequence").contains(phase)
  val exactBasis = before.basis == command.basis and Set(1, 2).contains(command.basis)
  val exactEvidence = before.evidence == command.evidence and before.evidence != before.basis and
    Set(1, 4, 50, 51).contains(before.evidence)
  val eligible = exactBasis and exactEvidence and Set(forward, reverse, { ...forward, reason: reverse.reason },
    { ...reverse, reason: forward.reason }).contains(command.claim) and command.obstacle == "" and before.output == 0
  invariant exactDeclaration = not(declaring) or ((accepted iff eligible) and
    if (eligible) repo == { ...before, output: 20, versions: before.versions.put(20,
      { kind: "declaration", fields: noFields, claim: command.claim, parents: List(before.basis, before.evidence) }) }
    else repo == before)
  invariant declarationInherits = not(declaring and accepted) or {
    val original = readIntent(before, before.basis)
    val declared = readIntent(repo, 20)
    declared.valid and declared.genesis == original.genesis and declared.fields == original.fields and
      declared.notice == { commit: 20, basis: before.basis, evidence: before.evidence, claim: command.claim }
  }
  invariant exactPromotion = phase != "promotion" or {
    val ok = command.basis == 20 and before.promoted == 0 and command.obstacle == ""
    (accepted iff ok) and (if (not(ok)) repo == before else {
      val promoted = readIntent(repo, 21)
      repo == { ...before, promoted: 21, versions: before.versions.put(21, definition(v2, List(20))) } and
        promoted.valid and promoted.fields == v2 and promoted.genesis == 1 and
        promoted.notice == { commit: 20, basis: 1, evidence: 50, claim: forward }
    })
  }

  val routing = Set("original", "declared", "promoted", "wrong-slot", "moved-pin", "explicit-old", "successor-reuse",
    "retained-old")
  val last = if (repo.decisions.length() > 0) repo.decisions[repo.decisions.length() - 1] else noDecision
  invariant advisoryDoesNotRoute = not(routing.contains(phase)) or {
    if (Set("wrong-slot", "moved-pin").contains(phase)) not(accepted) and repo == before
    else {
      val expected = if (phase == "promoted") { intent: 21, implementation: 2, slot: 2, selection: 0, outcome: "execute" }
        else if (phase == "successor-reuse") { intent: 21, implementation: 2, slot: 2, selection: 201, outcome: "reuse" }
        else { intent: request.expected, implementation: 1, slot: 1, selection: 101, outcome: "reuse" }
      accepted and repo == { ...before, decisions: before.decisions.append(expected) }
    }
  }

  // An independent table checks ancestry vs. compatibility, including
  // malformed lookups and a valid unrelated genesis with identical fields.
  pure val localNotice: Notice = { commit: 20, basis: 1, evidence: 50, claim: forward }
  pure val siblingNotice: Notice = { commit: 4, basis: 2, evidence: 51, claim: reverse }
  pure def expectedView(id: int, implementation: int): View = {
    if (id == 0) noView
    else if (Set(20, 21).contains(id)) { intent: id, notice: localNotice,
      relation: if (implementation == 1) "predecessor" else "successor" }
    else if (id == 4) { intent: id, notice: siblingNotice,
      relation: if (implementation == 1) "successor" else "predecessor" }
    else { intent: id, notice: noNotice, relation: "none" }
  }
  // The inspection target is independent of the most recently recorded decision.
  val knowledge = query._2
  val compatibleKnowledge = Set(0, 1, 2, 4, 20, 21).contains(knowledge)
  invariant inspectionIsOffline = phase != "inspection" or (repo == before and (accepted iff compatibleKnowledge) and
    (if (accepted) {
      val d = before.decisions[query._1]
      report == { historical: expectedView(d.intent, d.implementation), knowledge: expectedView(knowledge, d.implementation) }
    } else report == noInspection))

  observation publishesDeclaration = phase == "sequence" and accepted
  observation declarationPreservesPromotedDefault = phase == "declaration" and accepted and command.basis == 2
  observation opaqueEvidenceMayHaveItsOwnAncestry = phase == "declaration" and accepted and command.evidence == 4
  observation rejectsMovedBasis = phase == "declaration" and not(accepted) and not(exactBasis) and
    before.basis == 2 and command.basis == 1 and exactEvidence and command.claim == forward and command.obstacle == ""
  observation rejectsMovedEvidence = phase == "declaration" and not(accepted) and exactBasis and
    before.evidence == 51 and command.evidence == 50 and command.claim == forward and command.obstacle == ""
  observation rejectsOccupiedOutput = phase == "declaration" and not(accepted) and exactBasis and exactEvidence and
    command.claim == forward and before.output != 0
  observation declarationRollsBack = phase == "declaration" and not(accepted) and exactBasis and exactEvidence and
    command.claim == forward and command.obstacle == "late"
  observation rejectsRepeatedDeclaration = phase == "declaration" and not(accepted) and before.basis == 4 and
    command.basis == 4 and exactEvidence and command.claim == forward and command.obstacle == ""
  observation rejectsEmptyEvidence = phase == "declaration" and not(accepted) and exactBasis and
    before.evidence == 52 and command.evidence == 52 and command.claim == forward and command.obstacle == ""
  observation rejectsBasisAsEvidence = phase == "declaration" and not(accepted) and exactBasis and
    before.evidence == before.basis and command.evidence == before.evidence and command.claim == forward and command.obstacle == ""
  observation rejectsEqualEndpoints = phase == "declaration" and not(accepted) and exactBasis and exactEvidence and
    command.claim.successor == 1 and command.claim.predecessor == 1 and command.obstacle == ""
  observation rejectsUnknownReason = phase == "declaration" and not(accepted) and exactBasis and exactEvidence and
    command.claim.reason == "unsupported-reason" and command.obstacle == ""
  observation declarationStillUsesOldSelection = phase == "declared" and accepted and last.selection == 101
  observation oldOverrideStillReusesAfterPromotion = phase == "explicit-old" and accepted and last.selection == 101
  observation promotionUsesEmptySuccessorSlot = phase == "promoted" and accepted and last.slot == 2 and last.outcome == "execute"
  observation rejectsPredecessorSelectionInSuccessorSlot = phase == "wrong-slot" and not(accepted)
  observation bothVersionsKeepTheirSelections = phase == "retained-old" and accepted and last.selection == 101 and
    repo.decisions[repo.decisions.length() - 2].selection == 201
  observation oldHistoryWithoutKnowledge = phase == "inspection" and accepted and report.historical.intent == 1 and
    report.historical.relation == "none" and report.knowledge == noView
  observation oldHistoryWithNewKnowledge = phase == "inspection" and accepted and report.historical.intent == 1 and
    report.historical.relation == "none" and report.knowledge.intent == 21 and report.knowledge.relation == "predecessor"
  observation compatibleUnannotatedSibling = phase == "inspection" and accepted and report.historical.intent == 20 and
    report.historical.relation == "predecessor" and report.knowledge.intent == 2 and report.knowledge.relation == "none"
  observation compatibleConflictingSibling = phase == "inspection" and accepted and report.historical.intent == 20 and
    report.historical.relation == "predecessor" and report.knowledge.intent == 4 and report.knowledge.relation == "successor"
  observation promotedHistoryInherits = phase == "inspection" and accepted and report.historical.intent == 21 and
    report.historical.relation == "successor" and report.knowledge == noView
  observation unrelatedGenesisRejected = phase == "inspection" and not(accepted) and knowledge == 3
  observation swappedParentsRejected = phase == "inspection" and not(accepted) and knowledge == 5
  observation malformedKnowledgeRejected = phase == "inspection" and not(accepted) and knowledge == 7
  observation missingKnowledgeRejected = phase == "inspection" and not(accepted) and knowledge == 53
}
