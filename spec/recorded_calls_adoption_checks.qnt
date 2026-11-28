module recorded_calls_adoption_checks {
  import recorded_calls_rules.* from "./recorded_calls_rules"
  import recorded_calls_adoption_fixture as f from "./recorded_calls_adoption_fixture"
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  pure val setupExpected = List("recorded", "recorded", "native_ok", "native_ok", "native_ok", "native_ok",
    "native_ok", "native_ok", "native_ok", "native_ok", "recorded", "selected", "recorded")
  pure def setupVerdicts(rows: List[Attempt]): List[str] = {
    val request = rows[6].nativeValue
    val first = rows[10].commit
    range(0, f::setup.length()).foldl(List(), (out, i) => {
      val a = rows[i]
      val req = f::setup[i]
      val verdict =
        if (i == 0) writeVerdict(a, req)
        else if (i == 1) scaleWriteVerdict(a, req, rows[0].commit)
        else if (i == 6 and request == "") "missing_request_parent"
        else if (i == 10 or i == 12) {
          if (i == 12 and a.commit == first) "wrong_attempt_identity"
          else scaleWriteVerdict(a, req, request)
        } else if (i == 11) selectAttemptVerdict(a, req, rows[1].commit, first, true)
        else rejectionNativeVerdict(a, req, "ok")
      out.append(verdict)
    })
  }

  pure val adoptionRole = "7363616c652d617474656d70742d61646f7074696f6e2d7631" // scale-attempt-adoption-v1
  pure val adoptionFields = List(List("attempt_commit", "attempt_id", "attempt_ref", "commit",
    "previous_selection_commit", "request_commit", "request_implementation", "result_commit"))
  pure def adoptionReport(a: Attempt, req: Request, commit: str, previous: str, request: str, attempt: str,
                          result: str, uuid: str, name: str): str =
    if (not(matches(a, req))) "wrong_inspect"
    else if (not(a.unchanged)) "storage_changed"
    else if (a.commit != commit or a.previousSelection != previous) "wrong_adoption_identity"
    else if (a.requestCommit != request or a.requestImplementation != scaleV1 or a.calls != [] or
      a.reportFields != adoptionFields or a.occurrence != { id: uuid, commit: attempt, result: result, historicalRef: name })
      "wrong_adoption_report"
    else "inspected"

  pure def objectRead(id: str, alias: str): Request = coreRequest("txn_get_object", List("snapshot", "commit", id, alias))
  pure def nativeRead(reqs: List[Request]): List[Request] = openNative("read").concat(reqs).concat(closeNative("txn_abort"))
  pure def nativeWrite(reqs: List[Request]): List[Request] = openNative("write").concat(reqs).concat(closeNative("txn_commit"))
  pure val pins = List(refRead("producer", "producer-id"), refRead("plan", "absent-plan"), refRead("main", "absent-main"),
    refRead("incoming", "incoming-id"), refRead("chosen", "chosen-id"), refRead("first", "first-id"), refRead("second", "second-id"))
  pure val attemptResults = viewObject("commit", "first-id", "first-view").append(f::parent("first-view", "1", "first-result"))
    .concat(viewObject("commit", "second-id", "second-view")).append(f::parent("second-view", "1", "second-result"))
  pure def adoptionShape(id: str): List[Request] = snapshotAt(id, "adoption-view", "adoption-tree", "adoption-dag", "adoption-basis")
    .append(f::parent("adoption-view", "1", "adoption-attempt"))
    .concat(viewObject("dag", "adoption-dag", "adoption-root"))
    .append(lookupNode("adoption-dag", "attempt_ref", "adoption-name"))
    .concat(viewLiteral("adoption-name", "adoption-name-value"))
  pure def adoptionGraph(rows: List[Attempt], previous: str, attempt: str, name: str): bool = {
    val nameValue = nativeOutput(rows, "datum_decode", "adoption-name-value")
    decoded(rows, "adoption-view").nativeCount == 2 and
    outputId(rows, "object_view_parent", "adoption-basis") == previous and
    outputId(rows, "object_view_parent", "adoption-attempt") == attempt and
    treeEntry(rows, "adoption-tree", "adoption-dag", adoptionRole) and
    decoded(rows, "adoption-root").nativeCount == 1 and
    decoded(rows, "adoption-root").nativeValue == outputId(rows, "txn_lookup_node", "adoption-name") and
    nativeNodeMatches(rows, "adoption-name-value") and nameValue.nativeCount == 6 and nameValue.nativeItems == List(name)
  }

  pure val abandon = source("abandon_scale_request", List("plan", "plan"))
  pure val occupied = f::adopt("chosen", "chosen", "second", "second", "producer")
  pure val change = f::adopt("chosen", "chosen", "second", "second", "changed")
  pure val retentionPins = pins.append(refRead("changed", "changed-id"))
  pure val retentionRead = nativeRead(retentionPins.concat(attemptResults).concat(adoptionShape("changed-id")))
  pure val release = nativeWrite(List(drop("first", "first-id"), drop("second", "second-id"),
    drop("chosen", "chosen-id"), drop("incoming", "incoming-id")))
  pure val retentionAfter = nativeRead(List(refRead("producer", "kept-producer"), refRead("changed", "kept-changed"),
    refRead("first", "absent-first"), refRead("second", "absent-second"), refRead("chosen", "absent-chosen"),
    refRead("incoming", "absent-incoming"), refRead("plan", "swept-plan-pin"), refRead("main", "absent-main"),
    objectRead("plan:plan", "swept-plan"), objectRead("chosen-id", "retained-chosen"), objectRead("first-id", "retained-first"),
    objectRead("second-id", "retained-second"), objectRead("incoming-id", "retained-request")))
  pure val beforeChange = f::setup.append(abandon).concat(nativeRead(List(refRead("plan", "absent-plan"))))
    .append(occupied)
  pure val changeIndex = beforeChange.length()
  pure val retention = beforeChange.concat(List(change, change)).concat(retentionRead).concat(release)
    .append(source("collect", List())).concat(retentionAfter).append(source("inspect", List("changed")))

  // Rotate three aliases so writes do not consume the two most recent IDs.
  // Each link is a separate encode and native put, with the attempt alternating.
  pure val depth = 1025
  pure def link(i: int): str = if (i == 0) "chosen-id" else List("link-a", "link-b", "link-c")[(i - 1) % 3]
  pure val deepPins = List(refRead("chosen", "chosen-id"), refRead("first", "first-id"), refRead("second", "second-id"))
  pure val chainTree = putLiteral("string", "historical", "chain-name-datum", "chain-name")
    .concat(putObject("dag", List("chain-name", "attempt_ref", "chain-name"), "chain-dag"))
    .concat(putObject("tree", List("scale-attempt-adoption-v1", "chain-dag"), "chain-tree"))
  pure val chainHead = openNative("write").concat(deepPins).concat(attemptResults).concat(chainTree)
  pure val chainLinks = range(1, depth + 1).foldl(List(), (out, i) => out.concat(putObject("commit",
    List("chain-tree", link(i - 1), if (i % 2 == 1) "second-id" else "first-id"), link(i))))
  pure val chainTail = List(pin("tip", link(depth))).concat(closeNative("txn_commit"))
    .concat(nativeRead(List(refRead("tip", "tip-id")).concat(adoptionShape("tip-id"))
      .concat(viewObject("commit", "adoption-basis", "penultimate-view"))
      .concat(List(f::parent("penultimate-view", "0", "penultimate-basis"), f::parent("penultimate-view", "1", "penultimate-attempt")))))
  pure val deep = f::setup.concat(chainHead).concat(chainLinks).concat(chainTail).append(source("inspect", List("tip")))

  pure val absentAliases = Set("absent-plan", "absent-main", "absent-first", "absent-second", "absent-chosen",
    "absent-incoming", "swept-plan-pin", "swept-plan")
  pure def hasAbsentTarget(req: Request): bool =
    Set("txn_ref_get", "txn_get_object").contains(req.op) and absentAliases.contains(req.args[req.args.length() - 1])
  pure def retentionLabel(req: Request, i: int): str =
    if (i < f::setup.length()) setupExpected[i]
    else if (req.op == "abandon_scale_request") "abandoned"
    else if (req.op == "adopt_scale_attempt") (if (i == changeIndex) "adopted" else "rejected")
    else if (req.op == "collect") "collected"
    else if (req.op == "inspect") "inspected"
    else if (hasAbsentTarget(req)) "native_not_found"
    else "native_ok"
  pure val retentionExpected = range(0, retention.length()).foldl(List(), (out, i) => out.append(retentionLabel(retention[i], i)))
  pure val deepExpected = setupExpected.concat(range(f::setup.length(), deep.length() - 1)
    .foldl(List(), (out, _) => out.append("native_ok"))).append("inspected")

  pure def adoptionNativeVerdict(rows: List[Attempt], i: int, req: Request, expected: str -> str): str = {
    val a = rows[i]
    if (hasAbsentTarget(req)) rejectionNativeReadVerdict(a, req, "")
    else if (req.op == "txn_ref_get" and expected.keys().contains(req.args[2]))
      rejectionNativeReadVerdict(a, req, expected.get(req.args[2]))
    else rejectionNativeVerdict(a, req, "ok")
  }
  pure def sameResult(rows: List[Attempt]): str = {
    val first = outputId(rows, "object_view_parent", "first-result")
    val second = outputId(rows, "object_view_parent", "second-result")
    if (first == second) first else ""
  }
  pure def retentionVerdicts(rows: List[Attempt]): List[str] = {
    if (rows.length() != retention.length()) List("missing_steps")
    else {
      val changed = rows[changeIndex].commit
      val producer = rows[0].commit
      val plan = rows[1].commit
      val request = rows[6].nativeValue
      val first = rows[10].commit
      val chosen = rows[11].commit
      val second = rows[12].commit
      val result = sameResult(rows)
      val expected = Map("producer-id" -> producer, "incoming-id" -> request, "chosen-id" -> chosen, "first-id" -> first,
        "second-id" -> second, "changed-id" -> changed, "kept-producer" -> producer, "kept-changed" -> changed)
      range(f::setup.length(), rows.length()).foldl(setupVerdicts(rows), (out, i) => {
        val a = rows[i]
        val req = retention[i]
        val verdict =
          if (req == abandon) abandonVerdict(a, req, plan)
          else if (req.op == "adopt_scale_attempt") {
            if (i == changeIndex) adoptVerdict(a, req, chosen, second, true)
            else if (a.expectedAttempt != second) "wrong_attempt_guard"
            else existingRejectionVerdict(a, req, chosen,
              a.stderr == "adopt-scale-attempt: ('invalid_state', -30799, 'ref already exists')")
          } else if (req.op == "inspect") {
            if (result == "") "wrong_common_result"
            else adoptionReport(a, req, changed, chosen, request, second, result, f::secondUuid, "second")
          } else if (req.op == "collect") {
            if (matches(a, req) and a.removed > 0) "collected" else "wrong_collection"
          } else {
            val native = adoptionNativeVerdict(rows, i, req, expected)
            if (native == "native_ok" and req.op == "datum_decode" and not(adoptionGraph(rows, chosen, second, "second")))
              "wrong_adoption_graph"
            else native
          }
        out.append(verdict)
      })
    }
  }

  pure def deepVerdicts(rows: List[Attempt]): List[str] = {
    if (rows.length() != deep.length()) List("missing_steps")
    else {
      val start = f::setup.length() + chainHead.length()
      val end = start + chainLinks.length()
      val shapes = rows.slice(end, rows.length())
      val ids = range(0, depth).foldl(Set(), (out, i) => out.union(Set(rows[start + 2 * i + 1].nativeValue)))
      val tip = rows[end - 1].nativeValue
      val previous = rows[end - 3].nativeValue
      val prior = rows[end - 5].nativeValue
      val request = rows[6].nativeValue
      val first = rows[10].commit
      val second = rows[12].commit
      val chosen = rows[11].commit
      val result = sameResult(rows)
      val expected = Map("chosen-id" -> chosen, "first-id" -> first, "second-id" -> second, "tip-id" -> tip)
      range(f::setup.length(), rows.length()).foldl(setupVerdicts(rows), (out, i) => {
        val a = rows[i]
        val req = deep[i]
        val verdict =
          if (i == end - 1 and (ids.size() != depth or ids.contains("") or ids.contains(chosen))) "wrong_chain_length"
          else if (req.op == "inspect") {
            if (result == "") "wrong_common_result"
            else adoptionReport(a, req, tip, previous, request, second, result, f::secondUuid, "historical")
          } else {
            val native = adoptionNativeVerdict(rows, i, req, expected)
            if (native == "native_ok" and req.op == "datum_decode" and req.args == List("adoption-name-value") and
              not(adoptionGraph(shapes, previous, second, "historical") and decoded(shapes, "penultimate-view").nativeCount == 2 and
              decoded(shapes, "penultimate-view").nativeValue == decoded(shapes, "adoption-view").nativeValue and
              outputId(shapes, "object_view_parent", "penultimate-basis") == prior and
              outputId(shapes, "object_view_parent", "penultimate-attempt") == first)) "wrong_chain_tip_graph"
            else native
          }
        out.append(verdict)
      })
    }
  }

  pure val sampleReq = source("inspect", List("tip"))
  pure val sample = { ...recorded, op: sampleReq.op, args: sampleReq.args, code: 0, quiet: true, unchanged: true,
    commit: "tip", previousSelection: "previous", requestCommit: "request", requestImplementation: scaleV1,
    reportFields: adoptionFields,
    occurrence: { id: f::secondUuid, commit: "second", result: "result", historicalRef: "historical" } }
  pure def sampleVerdict(a: Attempt): str =
    adoptionReport(a, sampleReq, "tip", "previous", "request", "second", "result", f::secondUuid, "historical")
  pure val controls = all {
    sampleVerdict(sample) == "inspected",
    sampleVerdict({ ...sample, commit: "previous" }) == "wrong_adoption_identity",
    sampleVerdict({ ...sample, previousSelection: "chosen" }) == "wrong_adoption_identity",
    sampleVerdict({ ...sample, occurrence: { ...sample.occurrence, commit: "first" } }) == "wrong_adoption_report",
    sampleVerdict({ ...sample, unchanged: false }) == "storage_changed"
  }
}
