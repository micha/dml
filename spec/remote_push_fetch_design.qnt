// Bounded design for a single receiving ref; not a storage or wire specification.
module remote_push_fetch_design {
  // Two one-shot clients race for one destination slot. Each run models either
  // push or fetch. Push sources can be two snapshots of one movable ref; fetch
  // uses one remote ref and one distinct local tracking slot. Writes and GC
  // interleave only at transaction boundaries. IDs stand for commits and their
  // separate payload objects. Storage corruption, identity collisions, wire
  // framing, ref spelling, authentication, and acknowledgment are not modeled.
  pure val absent = 0
  pure val base = 1
  pure val left = 2
  pure val right = 3
  pure val merge = 4 // Ordered parents [left, right].
  pure val ownHead = 5
  pure val orphan = 99
  pure val sourceTips = Set(absent, base, left, right, merge)
  pure val parents = Map(
    absent -> Set(), base -> Set(), left -> Set(base), right -> Set(base),
    merge -> Set(left, right), ownHead -> Set())

  // Longest path in this graph is two edges.
  pure def ancestry(c: int): Set[int] = {
    val direct = parents.get(c)
    direct.fold(direct, (acc, p) => acc.union(parents.get(p)))
  }
  pure def closure(c: int): Set[int] = if (c == absent) Set() else {
    val commits = ancestry(c).union(Set(c))
    commits.union(commits.map(i => i + 10))
  }

  type Source = { tip: int, objects: Set[int] }
  type Destination = { target: int, head: int, objects: Set[int] }
  type Client = { expected: int, candidate: int, bundle: Set[int], phase: str }
  type Event = { actionName: str, before: Destination, seenSource: int, request: Client, fault: str, result: str }
  pure val idle: Client = { expected: absent, candidate: absent, bundle: Set(), phase: "idle" }
  pure val blank: Event = { actionName: "", before: { target: absent, head: ownHead, objects: Set() },
    seenSource: absent, request: idle, fault: "", result: "" }

  var push: bool
  var source: Source
  var dest: Destination
  var clients: List[Client]
  var event: Event

  action init = {
    nondet pushing = Set(false, true).oneOf()
    nondet target = Set(absent, base, right).oneOf()
    all {
      push' = pushing,
      source' = { tip: left, objects: closure(left) },
      dest' = { target: target, head: ownHead, objects: closure(target).union(closure(ownHead)).union(Set(orphan)) },
      clients' = List(idle, idle),
      event' = blank
    }
  }

  action update(s: Source, d: Destination, cs: List[Client], ev: Event): bool = all {
    push' = push,
    source' = s,
    dest' = d,
    clients' = cs,
    event' = ev
  }
  action captureExpected(i: int, c: Client): bool = all {
    c.phase == "idle",
    update(source, dest, clients.replaceAt(i, { ...c, expected: dest.target, phase: "expected" }), blank)
  }
  action exportSnapshot(i: int, c: Client): bool = {
    val tip = source.tip
    val exported = { ...c, candidate: tip, bundle: closure(tip),
      phase: if (tip == absent) "missing-source" else "ready" }
    all {
      c.phase == "expected",
      update(source, dest, clients.replaceAt(i, exported),
        { ...blank, actionName: "export", before: dest, seenSource: source.tip, request: exported })
    }
  }
  action receive(i: int, c: Client, fault: str): bool = {
    val allowed = not(push) or dest.target == absent or c.candidate == dest.target or
      ancestry(c.candidate).contains(dest.target)
    val result = if (fault == "invalid-bundle" or dest.target != c.expected or not(allowed)) "reject"
      else if (dest.target == c.candidate) "same-tip"
      else if (fault == "commit-failure") "reject"
      else "publish"
    val d = if (result == "publish") { ...dest, target: c.candidate, objects: dest.objects.union(c.bundle) } else dest
    all {
      c.phase == "ready",
      update(source, d, clients.replaceAt(i, { ...c, phase: result }),
        { ...blank, actionName: "receive", before: dest, request: c, fault: fault, result: result })
    }
  }
  action step = any {
    nondet i = Set(0, 1).oneOf()
    captureExpected(i, clients[i]),
    nondet i = Set(0, 1).oneOf()
    exportSnapshot(i, clients[i]),
    nondet i = Set(0, 1).oneOf()
    nondet fault = Set("none", "invalid-bundle", "commit-failure").oneOf()
    receive(i, clients[i], fault),
    nondet tip = sourceTips.oneOf()
    update({ tip: tip, objects: source.objects.union(closure(tip)) }, dest, clients, blank),
    update({ ...source, objects: closure(source.tip) }, dest, clients, blank),
    update(source, { ...dest, objects: closure(dest.target).union(closure(dest.head)) }, clients,
      { ...blank, actionName: "collect", before: dest })
  }

  val old = event.before.target
  val incoming = event.request.candidate
  val receiving = event.actionName == "receive"
  // Fixture oracle enumerates admissible transitions independently of the
  // action's ancestry traversal; commit equality is not an ancestry shortcut.
  val advance = (old == base and Set(left, right, merge).contains(incoming)) or
    (Set(left, right).contains(old) and incoming == merge)
  val allowed = not(push) or old == absent or old == incoming or advance
  val matched = old == event.request.expected
  val accepted = receiving and event.fault != "invalid-bundle" and matched and allowed

  invariant decision = not(receiving) or event.result == (
    if (not(accepted)) "reject"
    else if (old == incoming) "same-tip"
    else if (event.fault == "none") "publish"
    else "reject")
  invariant atomicPublish = event.result != "publish" or dest == {
    target: incoming, head: event.before.head, objects: event.before.objects.union(closure(incoming)) }
  invariant noResidue = not(receiving) or event.result == "publish" or dest == event.before
  invariant exactExport = event.actionName != "export" or (
    event.request.candidate == event.seenSource and
    event.request.phase == (if (event.seenSource == absent) "missing-source" else "ready") and
    dest == event.before)
  invariant snapshotsAndRetention = dest.head == ownHead and
    closure(dest.target).union(closure(ownHead)).subseteq(dest.objects) and
    closure(source.tip).subseteq(source.objects) and
    Set(0, 1).forall(i => clients[i].bundle == closure(clients[i].candidate))
  invariant exclusiveDivergentPush = not(push and clients[0].phase == "publish" and clients[1].phase == "publish" and
    clients[0].expected == clients[1].expected and Set(clients[0].candidate, clients[1].candidate) == Set(left, right))

  observation create = event.result == "publish" and old == absent and push
  observation pushViaSecondParent = event.result == "publish" and push and old == right and incoming == merge
  observation rejectDivergentPush = receiving and push and old == right and incoming == left and matched and event.result == "reject"
  observation sameTipPush = event.result == "same-tip" and push
  observation staleSameTip = receiving and old == incoming and not(matched) and event.fault == "none" and event.result == "reject"
  observation competingPushLost = receiving and push and not(matched) and event.fault == "none" and
    event.request.expected == base and Set(old, incoming) == Set(left, right) and event.result == "reject"
  observation staleOtherwiseEligiblePush = receiving and push and allowed and old != incoming and
    not(matched) and event.fault == "none" and event.result == "reject"
  observation invalidBundleRejectsOtherwiseEligible = receiving and matched and allowed and
    old != incoming and event.fault == "invalid-bundle" and event.result == "reject"
  observation failedCommitLeavesNoResidue = accepted and old != incoming and
    event.fault == "commit-failure" and event.result == "reject"
  observation transferAfterSourceMoveAndSweep = event.result == "publish" and not(source.objects.contains(incoming))
  observation missingRemoteLeavesTracking = not(push) and event.actionName == "export" and
    event.request.phase == "missing-source" and dest.target == right
  observation fetchRecordsRewindWithoutMovingHead = event.result == "publish" and not(push) and old == right and incoming == base
  observation staleFetch = receiving and not(push) and not(matched) and event.fault == "none" and event.result == "reject"
  observation publishedTipSurvivesSweep = event.actionName == "collect" and
    event.before.objects.contains(orphan) and not(dest.objects.contains(orphan)) and
    Set(0, 1).exists(i => clients[i].phase == "publish" and clients[i].candidate == dest.target)
}
