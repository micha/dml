// Source-local publication protocol after staging. Run TLC with observation search.
module recorded_publication_retry_design {
  // One retained receipt key and two disjoint pairs of ref names (modeled as
  // whole pairs; a third mode represents any alias). The two plans share a
  // request but capture different main states. Two exact results satisfy the request; one does not.
  // Commands interleave only at transaction boundaries. An unrelated writer
  // can move main and recreate/recycle either pair of pins, even at the old IDs.
  // Plan/result numbers stand for their closures except for the plan's old-main
  // edge. A receipt is a root with no outgoing ID edges. Occupied foreign or
  // malformed receipts are modeled as one unrecognized value. A trusted source
  // creates/retains the receipt; forgery, manual receipt edits, and hash
  // collisions are out of scope. Failed writes all have the same rollback.
  pure val absent = 0
  pure val oldMain = 1
  pure val unrelated = 2
  pure val planOld = 3
  pure val planEmpty = 4
  pure val resultA = 5
  pure val resultB = 6
  pure val wrong = 7
  pure val receiptObject = 8
  pure val foreignObject = 9

  type Intent = { pair: int, plan: int, result: int }
  type Pins = { plan: int, stage: int }
  type Repo = { main: int, pins: List[Pins], receipt: Intent, objects: Set[int] }
  type Event = { command: str, before: Repo, wanted: Intent, outcome: str }
  pure val noPins: Pins = { plan: absent, stage: absent }
  pure val unrelatedPins: Pins = { plan: unrelated, stage: unrelated }
  pure val noReceipt: Intent = { pair: -1, plan: absent, result: absent }
  pure val foreign: Intent = { ...noReceipt, pair: -2 }
  pure val empty: Repo = { main: absent, pins: List(noPins, noPins), receipt: noReceipt, objects: Set() }
  pure val noEvent: Event = { command: "", before: empty, wanted: noReceipt, outcome: "" }

  pure def capture(plan: int): int = if (plan == planOld) oldMain else absent
  pure def closure(root: int): Set[int] =
    if (root == absent) Set() else if (root == planOld) Set(planOld, oldMain) else Set(root)
  pure def roots(repo: Repo): Set[int] = {
    val receiptRoot = if (repo.receipt == noReceipt) absent
      else if (repo.receipt == foreign) foreignObject else receiptObject
    closure(repo.main).union(closure(receiptRoot)).union(
      repo.pins.foldl(Set(), (acc, pair) => acc.union(closure(pair.plan)).union(closure(pair.stage))))
  }
  pure def eligible(repo: Repo, wanted: Intent): bool =
    if (wanted.pair < 0) false else {
      val live = repo.pins[wanted.pair]
      live.plan == wanted.plan and repo.main == capture(wanted.plan) and
        Set(resultA, resultB).contains(wanted.result) and live.stage == wanted.result
    }

  var source: Repo
  var event: Event
  var committed: Intent // Ghost: the one publication this key witnessed.
  var lostAck: bool

  action init = {
    nondet existing = Set(noReceipt, foreign).oneOf()
    nondet main = Set(absent, oldMain).oneOf()
    val plan = if (main == absent) planEmpty else planOld
    val initial = { ...empty, main: main, pins: List({ plan: plan, stage: resultA }, noPins), receipt: existing }
    all {
      source' = { ...initial, objects: roots(initial) },
      event' = noEvent,
      committed' = noReceipt,
      lostAck' = false
    }
  }

  action update(after: Repo): bool = all {
    source' = after,
    event' = noEvent,
    committed' = committed,
    lostAck' = lostAck
  }

  action publish(wanted: Intent, abort: bool, dropAck: bool): bool = {
    val seen = source.receipt
    val outcome = if (wanted.pair < 0) "reject"
      else if (seen != noReceipt) (if (seen == wanted) "retry" else "reject")
      else if (eligible(source, wanted) and not(abort)) "publish" else "reject"
    val writes = outcome == "publish"
    all {
      source' = if (writes) { ...source, main: wanted.result,
        pins: source.pins.replaceAt(wanted.pair, noPins),
        receipt: wanted, objects: source.objects.union(Set(receiptObject)) } else source,
      event' = { command: if (abort) "abort-if-writing" else "submit", before: source,
        wanted: wanted, outcome: outcome },
      committed' = if (writes) wanted else committed,
      lostAck' = if (writes) dropAck else lostAck
    }
  }

  // At most one pair carries a candidate plan and result. The other can be
  // empty or independently occupied. Reinstallation can recreate an exact
  // plan/stage/main configuration without changing the receipt.
  action changePins(pair: int, pins: Pins, other: Pins): bool = update({ ...source,
    pins: List(other, other).replaceAt(pair, pins),
    objects: source.objects.union(closure(pins.plan)).union(closure(pins.stage)).union(closure(other.plan)) })

  action step = if (event.command != "") update(source) else any {
    nondet pair = Set(-1, 0, 1).oneOf()
    nondet plan = Set(planOld, planEmpty).oneOf()
    nondet result = Set(resultA, resultB, wrong).oneOf()
    nondet abort = Set(false, true).oneOf()
    nondet dropAck = Set(false, true).oneOf()
    publish({ pair: pair, plan: plan, result: result }, abort, dropAck),
    nondet pair = Set(0, 1).oneOf()
    nondet plan = Set(absent, planOld, planEmpty).oneOf()
    nondet stage = Set(absent, resultA, resultB, wrong).oneOf()
    nondet other = Set(noPins, unrelatedPins).oneOf()
    changePins(pair, { plan: plan, stage: stage }, other),
    nondet main = Set(absent, oldMain, unrelated, resultA, resultB).oneOf()
    update({ ...source, main: main, objects: source.objects.union(closure(main)) }),
    update({ ...source, objects: roots(source) })
  }

  // Separate history/fixture oracle rather than reusing the transition's
  // eligibility predicate: a receipt certifies its entire past invocation,
  // and a fresh call still needs every exact live guard and a successful commit.
  val submitted = event.command != ""
  val before = event.before
  val wanted = event.wanted
  val wasReady = if (wanted.pair < 0) false else {
    val pins = before.pins[wanted.pair]
    pins == { plan: wanted.plan, stage: wanted.result } and wanted.result != wrong and (
      (wanted.plan == planOld and before.main == oldMain) or
      (wanted.plan == planEmpty and before.main == absent))
  }
  invariant exactDecision = not(submitted) or event.outcome == (
    if (wanted.pair < 0) "reject"
    else if (before.receipt == wanted) "retry"
    else if (before.receipt == noReceipt and event.command == "submit" and wasReady) "publish"
    else "reject")
  invariant atomicFirstPublication = event.outcome != "publish" or source == {
    ...before, main: wanted.result,
    pins: if (wanted.pair == 0) List(noPins, before.pins[1]) else List(before.pins[0], noPins),
    receipt: wanted, objects: before.objects.union(Set(receiptObject)) }
  invariant noWritesOnRetryOrRejection = not(submitted) or event.outcome == "publish" or source == before
  invariant receiptProvesPriorTransaction =
    if (source.receipt == foreign) committed == noReceipt else committed == source.receipt
  invariant rootsSurvive = roots(source).subseteq(source.objects)

  observation firstPublishPreservesUnrelatedPins = event.outcome == "publish" and not(lostAck) and
    (source.pins[0] == unrelatedPins or source.pins[1] == unrelatedPins)
  observation lostAcknowledgmentRetried = event.outcome == "retry" and lostAck and before.main == wanted.result
  observation matchedAfterMainMovedAndCollection = event.outcome == "retry" and lostAck and
    before.main == unrelated and wanted.plan == planOld and not(before.objects.contains(wanted.plan)) and
    not(before.objects.contains(wanted.result)) and not(before.objects.contains(oldMain))
  observation matchedDoesNotReplayWithAllGuardsReady = event.outcome == "retry" and wasReady
  val rejectedSubmission = event.outcome == "reject" and event.command == "submit"
  observation differentResultRejectedEvenWhenReady = rejectedSubmission and wasReady and
    before.receipt.pair == wanted.pair and before.receipt.plan == wanted.plan and before.receipt.result != wanted.result
  observation differentPlanRejectedEvenWhenReady = rejectedSubmission and wasReady and
    before.receipt.pair == wanted.pair and before.receipt.plan != wanted.plan and before.receipt.result == wanted.result
  observation differentNamesRejectedEvenWhenReady = rejectedSubmission and wasReady and
    before.receipt.pair == 0 and wanted.pair == 1 and before.receipt.plan == wanted.plan and
    before.receipt.result == wanted.result
  observation noReceiptMainEqualityRejected = rejectedSubmission and
    before.receipt == noReceipt and wanted.result != wrong and before.main == wanted.result and
    (if (wanted.pair < 0) false else before.pins[wanted.pair] == { plan: wanted.plan, stage: wanted.result })
  observation occupiedForeignRejected = event.outcome == "reject" and event.command == "submit" and
    wasReady and before.receipt == foreign
  observation aliasRejected = event.outcome == "reject" and event.command == "submit" and wanted.pair < 0
  observation writeFailureRollsBackReceipt = event.outcome == "reject" and event.command == "abort-if-writing" and
    wasReady and before.receipt == noReceipt
}
