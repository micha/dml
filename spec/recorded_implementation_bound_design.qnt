// Iteration 25 routing/provenance design: one retained A success and one new
// invocation, two immutable implementations, three full MAP values, two source
// ledgers and two fixed leaf positions. IDs denote independently validated,
// retained native graph links. Atomic publication and a verified success record
// are premises; this does not model record encoding, bounds or execution faults.
module recorded_implementation_bound_design {
  type Control = { mode: str, pin: str }
  type Attempt = { id: int, request: int, impl: int, inputNode: int }
  type State = { phase: str, defaultImpl: int, captured: int, outerSlot: str, doubleSlot: str,
    outerQ: int, outerT: Attempt, addQ: int, addSource: int, doubleQ: int, doubleT: Attempt,
    doubleSource: int, value: int, getters: int, fault: str }

  pure val noAttempt: Attempt = { id: 0, request: 0, impl: 0, inputNode: 0 }
  pure val oldOuter: Attempt = { id: 11, request: 10, impl: 1, inputNode: 31 }
  pure val oldDouble: Attempt = { id: 15, request: 14, impl: 1, inputNode: 40 }
  pure val empty: State = { phase: "capture", defaultImpl: 1, captured: 0, outerSlot: "absent", doubleSlot: "absent",
    outerQ: 0, outerT: noAttempt, addQ: 0, addSource: 0, doubleQ: 0, doubleT: noAttempt,
    doubleSource: 0, value: 0, getters: 0, fault: "" }
  pure val controls: Set[Control] = Set({ mode: "fresh", pin: "none" },
    { mode: "try", pin: "absent" }, { mode: "try", pin: "old" }, { mode: "try", pin: "poison" },
    { mode: "require", pin: "absent" }, { mode: "require", pin: "old" }, { mode: "require", pin: "poison" })

  // MAP identities 1={a:13,b:29}, 2={a:29,b:13}, 3={a:13,b:30}.
  // Source ledger 2 is a new construction of the same value, not an equal node.
  pure def sameOuterMap(mapId: int): bool = mapId == 1
  pure def subtotal(mapId: int): int = if (mapId == 3) 43 else 42
  pure def validPin(c: Control, slot: str): bool = c.mode == "fresh" or (c.pin == slot and slot != "poison")
  pure def selected(c: Control, matches: bool): bool = c.pin == "old" and matches

  var state: State
  var before: State
  var outer: Control
  var inner: Control
  var input: int
  var source: int
  var inspectSubstitution: bool
  var acceptedRead: bool

  pure def inputNode(mapId, sourceId) = 29 + 2 * mapId + sourceId - 1

  action record(s: State, substitute: bool, read: bool): bool = all {
    state' = s, before' = state,
    outer' = outer, inner' = inner, input' = input, source' = source,
    inspectSubstitution' = substitute, acceptedRead' = read,
  }
  action init = {
    nondet out = controls.oneOf()
    nondet innerControl = controls.oneOf()
    nondet mapId = Set(1, 2, 3).oneOf()
    nondet sourceId = Set(1, 2).oneOf()
    nondet version = Set(1, 2).oneOf()
    all {
      state' = { ...empty, defaultImpl: version }, before' = empty,
      outer' = out, inner' = innerControl, input' = mapId, source' = sourceId,
      inspectSubstitution' = false, acceptedRead' = false,
    }
  }
  action step = if (state.phase == "capture")
      record({ ...state, phase: "promote", captured: state.defaultImpl }, false, false)
    else if (state.phase == "promote") {
      nondet version = Set(1, 2).oneOf()
      nondet outSlot = Set("absent", "old", "poison").oneOf()
      nondet inSlot = Set("absent", "old", "poison").oneOf()
      record({ ...state, phase: "pinned", defaultImpl: version, outerSlot: outSlot, doubleSlot: inSlot }, false, false)
    } else if (state.phase == "pinned") {
      val hit = selected(outer, sameOuterMap(input))
      val err = if (not(validPin(outer, state.outerSlot) and validPin(inner, state.doubleSlot))) "pin"
        else if (outer.mode == "require" and not(hit)) "miss" else ""
      val routed = if (err != "") { ...state, phase: "rejected", fault: err }
        else if (hit) { ...state, phase: "hit", outerQ: 20, outerT: oldOuter, value: 84 }
        else { ...state, phase: "start", outerQ: 20,
          outerT: { id: 21, request: 20, impl: state.captured, inputNode: inputNode(input, source) } }
      record(routed, false, false)
    } else if (state.phase == "start") {
      // The new bookmark may change after Q. The inner decision uses only the
      // pin already validated and retained in Q, not the current bookmark.
      nondet changed = Set("absent", "old", "poison").oneOf()
      record({ ...state, phase: "add", addQ: 22, addSource: inputNode(input, source),
        getters: 4, doubleSlot: changed }, false, false)
    } else if (state.phase == "add") {
      val hit = selected(inner, subtotal(input) == 42)
      val doubled = if (inner.mode == "require" and not(hit)) { ...state, phase: "partial", fault: "miss" }
        else { ...state, phase: "finished", doubleQ: 24, doubleSource: 41,
          doubleT: if (hit) oldDouble else { id: 25, request: 24, impl: state.captured, inputNode: 41 },
          value: 2 * subtotal(input), getters: state.getters + (if (hit) 0 else 1) }
      record(doubled, false, false)
    } else if (state.phase == "hit" or state.phase == "finished") {
      nondet swap = Set(false, true).oneOf()
      record({ ...state, phase: "read" }, swap, not(swap))
    } else record(state, inspectSubstitution, acceptedRead)

  invariant capturesIgnorePromotion = state.phase != "pinned" or state.captured == before.captured
  invariant rejectedMakesNoRequest = state.phase != "rejected" or
    (state.outerQ == 0 and state.outerT == noAttempt and state.addQ == 0 and state.doubleQ == 0 and state.value == 0)
  invariant routedUsesFullMap = before.phase != "pinned" or {
    val valid = (outer.mode == "fresh" or (outer.pin == before.outerSlot and outer.pin != "poison")) and
      (inner.mode == "fresh" or (inner.pin == before.doubleSlot and inner.pin != "poison"))
    val matchKey = outer.mode != "fresh" and outer.pin == "old" and input == 1
    state.phase == (if (not(valid) or (outer.mode == "require" and not(matchKey))) "rejected"
      else if (matchKey) "hit" else "start")
  }
  invariant outerHitRetainsOldAndDoesNotDispatch = state.outerT.id != 11 or
    (state.outerQ == 20 and state.outerT == oldOuter and state.addQ == 0 and state.doubleQ == 0 and
     state.getters == 0 and state.value == 84)
  invariant freshRetainsExactInputAndCapture = state.outerT.id != 21 or
    (state.outerQ == state.outerT.request and state.outerT.impl == state.captured and
     state.outerT.inputNode == inputNode(input, source) and (state.addQ == 0 or state.addSource == state.outerT.inputNode))
  invariant doubleDerivesFromCurrentAdd = state.doubleQ == 0 or
    (state.addQ == 22 and state.doubleSource == 41 and
     (if (inner.pin == "old" and input != 3)
        state.doubleT == oldDouble and state.doubleQ != state.doubleT.request and state.getters == 4
      else state.doubleT == { id: 25, request: state.doubleQ, impl: state.captured, inputNode: state.doubleSource }
        and state.getters == 5))
  invariant partialIsNotSuccess = state.phase != "partial" or
    (state.addQ == 22 and state.doubleT == noAttempt and state.value == 0 and state.getters == 4)
  invariant readerRejectsSubstitutionsWithoutWrites = state.phase != "read" or
    (state == { ...before, phase: "read" } and acceptedRead == not(inspectSubstitution))

  observation bRequestsA = state.phase == "hit" and state.captured == 2 and state.outerT == oldOuter and source == 2
  observation bFreshWithSelectionPresent = state.phase == "finished" and state.captured == 2 and
    state.outerSlot == "old" and outer.mode == "fresh" and state.doubleT.impl == 2
  observation pinnedAAfterPromotion = state.phase == "finished" and state.captured == 1 and
    state.defaultImpl == 2 and state.doubleT.impl == 1 and state.doubleT.id == 25
  observation sameResultDifferentMapMiss = state.phase == "rejected" and state.fault == "miss" and input == 2
  observation malformedSelectionBeforeMismatch = state.phase == "rejected" and state.fault == "pin" and
    outer.pin == "poison" and state.outerSlot == "poison" and input == 3
  observation staleSelectionBeforeHit = state.phase == "rejected" and state.fault == "pin" and
    outer.pin == "old" and state.outerSlot == "absent" and input == 1
  observation innerHitSurvivesMovingRef = state.phase == "finished" and state.captured == 2 and
    state.doubleSlot != "old" and state.doubleT == oldDouble and state.doubleSource != oldDouble.inputNode
  observation innerRequireMissKeepsAdd = state.phase == "partial" and state.addQ == 22 and input == 3
  observation substituteRejected = state.phase == "read" and inspectSubstitution and not(acceptedRead)
}
