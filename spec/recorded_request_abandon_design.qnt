// Source-local abandonment versus publication; each command is one transaction.
module recorded_request_abandon_design {
  pure val absent = 0
  pure val original = 1
  pure val replacement = 2
  pure val notPlan = 3
  pure val oldMain = 4
  pure val newerMain = 5
  pure val result = 6

  // One plan slot, one staging slot, one optional receipt for the original
  // publication, and main. The original plan captures oldMain; publication
  // considers only its exact result. A reused slot has a different ID. Main
  // can also point to a valid plan (via some other repository writer).
  // Immutable closures, native errors and byte-level validation are abstracted.
  type Repo = { plan: int, stage: int, main: int, receipt: bool }
  type Event = { command: str, before: Repo, expected: int, alias: bool, outcome: str }
  pure val initial: Repo = { plan: original, stage: absent, main: oldMain, receipt: false }
  pure val noEvent: Event = { command: "", before: initial, expected: absent, alias: false, outcome: "" }

  var source: Repo
  var event: Event
  // Ghost: the operation that consumed this incarnation of the original pin.
  var consumedBy: str
  var stagedAtAbandon: bool

  action init = all { source' = initial, event' = noEvent, consumedBy' = "", stagedAtAbandon' = false }

  action update(after: Repo): bool = all {
    source' = after, event' = noEvent, consumedBy' = consumedBy, stagedAtAbandon' = stagedAtAbandon
  }

  action abandon(expected: int, alias: bool): bool = {
    val target = if (alias) source.main else source.plan
    val accepted = not(alias) and target == expected and Set(original, replacement).contains(target)
    all {
      source' = if (accepted) { ...source, plan: absent } else source,
      event' = { command: "abandon", before: source, expected: expected, alias: alias,
        outcome: if (accepted) "abandoned" else "rejected" },
      consumedBy' = if (accepted and target == original) "abandon" else consumedBy,
      stagedAtAbandon' = if (accepted and target == original) source.stage == result else stagedAtAbandon
    }
  }

  action publish(keyed: bool): bool = {
    val decision = if (keyed and source.receipt) "acknowledged"
      else if (source.plan == original and source.stage == result and source.main == oldMain) "published"
      else "rejected"
    all {
      source' = if (decision == "published")
        { plan: absent, stage: absent, main: result, receipt: keyed } else source,
      event' = { ...noEvent, command: if (keyed) "keyed" else "one-shot", before: source, outcome: decision },
      consumedBy' = if (decision == "published") "publish" else consumedBy,
      stagedAtAbandon' = stagedAtAbandon
    }
  }

  action step = any {
    nondet expected = Set(original, replacement, notPlan).oneOf()
    nondet alias = Set(false, true).oneOf()
    abandon(expected, alias),
    nondet keyed = Set(false, true).oneOf()
    publish(keyed),
    all { source.stage == absent, update({ ...source, stage: result }) },
    all { source.plan == absent,
      nondet installed = Set(replacement, notPlan).oneOf()
      update({ ...source, plan: installed }) },
    nondet main = Set(oldMain, newerMain, original).oneOf()
    update({ ...source, main: main })
  }

  val before = event.before
  val abandonment = event.command == "abandon"
  val rejected = event.outcome == "rejected"
  val freshPublication = event.outcome == "published"
  val acknowledged = event.outcome == "acknowledged"
  invariant exactAbandonment = not(abandonment) or (
    event.outcome == "abandoned" iff (not(event.alias) and (
      (before.plan == original and event.expected == original) or
      (before.plan == replacement and event.expected == replacement))))
  invariant onlyPlanRemoved = event.outcome != "abandoned" or source == { ...before, plan: absent }
  invariant noWritesOnRejectionOrRetry = not(rejected or acknowledged) or source == before
  invariant exclusiveConsumption = all {
    not(freshPublication) or consumedBy == "publish" and before.plan == original,
    consumedBy != "abandon" or (source.plan != original and not(source.receipt) and not(freshPublication)),
    source.plan != original or consumedBy == "",
    not(source.receipt) or consumedBy == "publish"
  }
  invariant publicationUnaffected = abandonment or event.command == "" or (
    if (event.command == "keyed" and before.receipt) acknowledged
    else if (before.plan == original and before.stage == result and before.main == oldMain)
      freshPublication and source == { plan: absent, stage: absent, main: result, receipt: event.command == "keyed" }
    else rejected)

  observation abandonDespiteMovedMain = event.outcome == "abandoned" and before.main == newerMain
  observation abandonPreservesStagedResult = event.outcome == "abandoned" and before.stage == result
  observation lateResultCannotPublish = event.command == "keyed" and rejected and consumedBy == "abandon" and
    not(stagedAtAbandon) and before.plan == absent and before.stage == result and before.main == oldMain
  observation publishWins = abandonment and rejected and before.plan == absent and before.receipt and
    event.expected == original and not(event.alias)
  observation retryAfterPublish = acknowledged and before.plan == absent and before.receipt
  observation staleCannotRemoveReusedPin = abandonment and rejected and not(event.alias) and
    before.plan == replacement and event.expected == original and consumedBy == "abandon"
  observation matchingNonPlanRejected = abandonment and rejected and not(event.alias) and
    before.plan == notPlan and event.expected == notPlan
  observation matchingMainRejected = abandonment and rejected and event.alias and
    before.main == original and event.expected == original
}
