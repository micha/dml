module recorded_calls_plan_rules {
  import recorded_calls_fixtures.Request from "./recorded_calls_fixtures"
  import recorded_calls_plan_histories.* from "./recorded_calls_plan_histories"
  import recorded_calls_rules.* from "./recorded_calls_rules"

  pure val planEntryHex = "7363616c652d706c616e2d7631"
  pure val requestEntryHex = "7363616c652d726571756573742d7631"
  pure val requestedEntryHex = "7265717565737465642d7363616c652d7631"

  pure def durableLineage(rows: List[Attempt], report: Attempt, producer: str, prior: str, request: str): bool = {
    val sumDag = outputId(rows, "object_view_entry", "producer-dag")
    val scaleDag = outputId(rows, "object_view_entry", "result-dag")
    val input = outputId(rows, "txn_lookup_node", "result-input")
    all {
      prior != producer, decoded(rows, "local-plan").nativeCount == 2,
      treeEntry(rows, "local-plan-tree", "local-plan-dag", planEntryHex),
      outputId(rows, "object_view_parent", "local-request") == request,
      outputId(rows, "object_view_parent", "local-prior") == prior,
      decoded(rows, "result-commit").nativeCount == 1, decoded(rows, "request-commit").nativeCount == 1,
      treeEntry(rows, "result-tree", "result-dag", requestedEntryHex),
      treeEntry(rows, "request-tree", "request-dag", requestEntryHex),
      outputId(rows, "object_view_entry", "local-plan-dag") == outputId(rows, "object_view_entry", "request-dag"),
      outputId(rows, "object_view_parent", "result-request") == request,
      outputId(rows, "object_view_parent", "request-producer") == producer,
      nativeNodeMatches(rows, "result-source"), decoded(rows, "result-source").nativeValue == sumDag,
      report.calls.length() == 2 and report.calls[0].dag == sumDag and report.calls[1].dag == scaleDag and
        report.calls[1].arguments.length() == 2 and report.calls[1].arguments[1].node == input
    }
  }

  pure def candidateRead(rows: List[Attempt], name: str): List[Attempt] = {
    val req = readCandidate(name)
    val start = range(0, rows.length()).select(i => sameRequest(rows[i], req[0])).head()
    rows.slice(start, start + req.length())
  }
  pure def candidateLayout(rows: List[Attempt], name: str, commit: str, factor: str, sumDag: str, value: str): bool = {
    val reads = candidateRead(rows, name)
    all {
      storedRef(reads, "candidate-pin") == commit,
      decoded(reads, "candidate-commit").nativeCount == 1,
      outputId(reads, "object_view_parent", "candidate-request") == outputId(rows, "object_view_parent", "request-parent"),
      treeEntry(reads, "candidate-tree", "candidate-dag", requestedEntryHex),
      decoded(reads, "candidate-root").nativeCount == 3,
      outputId(reads, "txn_lookup_node", "candidate-version") == outputId(rows, "txn_lookup_node", "version"),
      nativeLiteralMatches(reads, "observed-factor", 3, factor),
      nativeNodeMatches(reads, "candidate-sum"), decoded(reads, "candidate-sum").nativeValue == sumDag,
      nativeLiteralMatches(reads, "observed-value", 3, value)
    }
  }

  pure def candidateRejection(rows: List[Attempt], a: Attempt, r: Request, plan: str, mark: str): str = {
    val candidate = if (mark == "wrong-factor" or mark == "wrong-input") mark else "returned"
    val result = storedObject(rows, if (mark == "wrong-factor") "wrong-factor-id" else if (mark == "wrong-input") "wrong-input-id" else "returned-id")
    val producerDag = outputId(rows, "object_view_entry", "producer-dag")
    val decoyDag = outputId(rows, "object_view_entry", "decoy-dag")
    val wrongFactor = mark == "wrong-factor"
    val linkedDag = if (mark == "wrong-input") decoyDag else producerDag
    val expectedFactor = if (wrongFactor) "feffffffffffffff" else "0300000000000000"
    val diagnostic = if (wrongFactor) "publish-requested-scale: recorded factor does not match the request factor"
      else if (mark == "wrong-input") "publish-requested-scale: scale input DAG does not match the request's producer"
      else "publish-requested-scale: plan, staging, and main refs must be distinct"
    if (a.expectedResult != result) "wrong_selection"
    else if (producerDag == decoyDag or decoded(rows, "producer-root").nativeValue != decoded(rows, "decoy-root").nativeValue or
        not(candidateLayout(rows, candidate, result, expectedFactor, linkedDag,
          if (candidate == "returned") "9effffffffffffff" else "0000000000000000"))) "wrong_candidate_fixture"
    else existingRejectionVerdict(a, r, plan, a.stderr == diagnostic)
  }

  pure def storedCandidateReport(rows: List[Attempt], a: Attempt, r: Request, sum: Attempt, plan: Attempt): str = {
    val result = storedObject(rows, "returned-id")
    val sumDag = outputId(rows, "object_view_entry", "producer-dag")
    if (not(matches(a, r))) "wrong_inspect"
    else if (not(a.unchanged)) "storage_changed"
    else if (a.commit != result or a.requestCommit != plan.requestCommit or a.producerCommit != sum.commit or
        not(candidateLayout(rows, "returned", result, "0300000000000000", sumDag, "9effffffffffffff")) or
        a.calls.length() != 2 or a.calls[0] != sum.calls[0]) "wrong_requested_result"
    else {
      val scale = a.calls[1]
      val reads = candidateRead(rows, "returned")
      val factor = outputId(reads, "txn_lookup_node", "candidate-factor")
      val input = outputId(reads, "txn_lookup_node", "candidate-input")
      if (scale == { dag: outputId(reads, "object_view_entry", "candidate-dag"), implementation: scaleV1,
          resultNode: decoded(reads, "candidate-root").nativeValue, resultValue: -98,
          arguments: List({ name: "factor", node: factor, value: 3, producer: "" },
            { name: "input", node: input, value: 0, producer: sumDag }) }) "inspected" else "wrong_stored_graph"
    }
  }

  pure def futureLayout(rows: List[Attempt], producer: str): bool = all {
    decoded(rows, "future-commit").nativeCount == 1,
    treeEntry(rows, "future-tree", "future-dag", requestEntryHex),
    outputId(rows, "object_view_parent", "future-producer") == producer,
    decoded(rows, "future-root").nativeCount == 2,
    decoded(rows, "future-root").nativeValue == outputId(rows, "txn_lookup_node", "imported-implementation"),
    nativeLiteralMatches(rows, "future-name", 6, "6578616d706c652e7363616c654033"),
    nativeLiteralMatches(rows, "future-number", 3, "0300000000000000")
  }

  pure def malformedLayout(rows: List[Attempt], producer: str): bool = {
    val dag = outputId(rows, "object_view_entry", "malformed-dag")
    val requestDag = outputId(rows, "object_view_entry", "wrong-request-dag")
    all {
      decoded(rows, "local-plan").nativeCount == 1, decoded(rows, "malformed-commit").nativeCount == 1,
      decoded(rows, "local-plan").nativeValue == decoded(rows, "malformed-commit").nativeValue,
      treeEntry(rows, "malformed-tree", "malformed-dag", planEntryHex),
      dag == outputId(rows, "object_view_entry", "local-plan-dag"), dag != requestDag,
      requestDag == outputId(rows, "object_view_entry", "replacement-dag"),
      outputId(rows, "object_view_parent", "malformed-request") == outputId(rows, "object_view_parent", "replacement-request"),
      decoded(rows, "wrong-request-commit").nativeCount == 1,
      treeEntry(rows, "wrong-request-tree", "wrong-request-dag", requestEntryHex),
      outputId(rows, "object_view_parent", "same-producer") == producer
    }
  }

  pure def planRejection(rows: List[Attempt], marked: (str) => Attempt, a: Attempt, s: PlanStep): str = {
    val r = s.request
    val mark = s.mark
    val producer = marked("producer").commit
    def reject(expected: str, diagnostic: str): str = existingRejectionVerdict(a, r, expected, a.stderr == diagnostic)
    if (r.op == "request_scale") {
      val diagnostic = if (mark == "alias-main") "request-scale: plan ref must differ from main"
        else if (mark == "factor-range") "request-scale: factor is not a signed 64-bit integer"
        else if (mark == "occupied-plan") "request-scale: ('invalid_state', -30799, 'ref already exists')"
        else "request-scale: main already points to this request; stage requests under a separate ref"
      reject(producer, diagnostic)
    } else if (r.op == "export_request") {
      if (a.bundlePresent or not(a.bundleUnchanged)) "wrong_bundle"
      else reject(marked("plan").commit, "export-request: plan ref does not point to the expected plan commit")
    } else if (r.op == "work_scale") {
      if (mark == "worker-overflow") reject(marked("request-export").commit, "work-scale: example.scale@1 result is not a signed 64-bit integer")
      else if (not(futureLayout(rows, producer))) "wrong_future_fixture"
      else reject(storedObject(rows, "future-request"),
        "work-scale: unsupported scale implementation b'example.scale@3'; use example.scale@1 or example.scale@2")
    } else if (r.op == "publish_scale") {
      val result = storedObject(rows, "returned-id")
      if (a.expectedResult != result or a.expectedMain != "-") "wrong_selection"
      else reject(producer, "publish-scale: expected a split recorded-scale-v1 commit")
    } else if (r.op == "publish_requested_scale") {
      val plan = marked("plan").commit
      if (mark == "missing-plan-publish" or mark == "stale-main") {
        if (a.expectedResult != marked("result").commit) "wrong_selection"
        else existingRejectionVerdict(a, r, plan, if (mark == "missing-plan-publish") a.missingRef else
          a.stderr == "publish-requested-scale: main does not point to the expected commit")
      } else candidateRejection(rows, a, r, plan, mark)
    } else if (mark == "missing-plan") existingRejectionVerdict(a, r, marked("plan").commit, a.missingRef)
    else if (mark == "wrong-role") reject(producer,
      "abandon-scale-request: expected a scale-plan-v1 commit with a request and optional main parent")
    else if (mark == "wrong-dag") {
      if (malformedLayout(rows, producer)) reject(storedObject(rows, "malformed-plan"),
        "abandon-scale-request: plan DAG does not match the request DAG") else "wrong_plan_fixture"
    } else if (mark == "replaced-pin") reject(marked("plan").commit,
      "abandon-scale-request: plan ref does not point to the expected plan commit")
    else if (mark == "reserved-main") reject(marked("plan").commit, "abandon-scale-request: plan ref must differ from main")
    else "unclassified_rejection"
  }

  pure def planVerdicts(phase: int, rows: List[Attempt]): List[str] = {
    val steps = planCases[phase]
    if (rows.length() != steps.length()) List("missing_steps")
    else {
      val positions = range(0, steps.length())
      val marks = positions.foldl(Map(), (out, i) =>
        if (steps[i].mark == "") out else out.put(steps[i].mark, rows[i]))
      def marked(key: str): Attempt = marks.get(key)
      def id(key: str): str =
        if (key == "accepted-candidate") storedObject(rows, "returned-id")
        else if (key == "future-request" or key == "malformed-plan") storedObject(rows, key)
        else marked(key).commit
      val producer = id("producer")
      val sumScenario = if (phase == 1) { ...selected, b: ("-7", -7) } else selected
      val expectedResult = if (phase == 1) id("accepted-candidate") else if (phase == 0 or phase == 4) id("result") else ""
      val requestId = if (phase == 1) outputId(rows, "object_view_parent", "request-parent")
        else if (Set(5, 6).contains(phase)) outputId(rows, "object_view_parent", "local-request")
        else if (phase == 3) id("future-request") else id("request-export")
      positions.foldl(List(), (out, i) => {
        val a = rows[i]
        val s = steps[i]
        val r = s.request
        val mark = s.mark
        val verdict = if (s.label == "native_not_found") rejectionNativeReadVerdict(a, r, "")
          else if (s.label == "native_ok") {
            if (r.op == "txn_ref_get" and s.target != "") {
              val target = id(s.target)
              if (target == "") "missing_pin_target" else rejectionNativeReadVerdict(a, r, target)
            } else if (r.op == "repo_export_commit" and
                (a.nativeItems.length() == 0 or a.nativeItems[0] != id("future-request"))) "wrong_bundle_root"
            else if (r.op == "txn_get_object" and a.nativeValue == "") "missing_object"
            else rejectionNativeVerdict(a, r, "ok")
          } else if (s.label == "recorded") {
            if (r.op == "request_scale") scaleWriteVerdict(a, r, producer)
            else if (r.op == "work_scale") scaleWriteVerdict(a, r, requestId)
            else if (mark == "prior" and a.commit == producer) "wrong_prior_tip"
            else writeVerdict(a, r)
          } else if (s.label == "exported") {
            if (r.op == "export_request") requestExportVerdict(a, r, id("plan")) else exportVerdict(a, r, id("result"))
          } else if (s.label == "staged") stageVerdict(a, r, if (mark == "result-stage") id("result") else requestId)
          else if (s.label == "rejected") planRejection(rows, marked, a, s)
          else if (s.label == "published") publishVerdict(a, r, expectedResult, id("plan"), "", true)
          else if (s.label == "abandoned") abandonVerdict(a, r, id("plan"))
          else if (s.label == "collected") {
            if (matches(a, r) and not(a.stdoutEmpty) and (if (phase == 0 and mark == "collect") a.removed >= 0 else a.removed > 0))
              "collected" else "wrong_collection"
          } else if (s.label == "file_observed" and matches(a, r)) {
            val agrees = if (r.op == "unlink_bundle") not(a.bundlePresent) and a.bundleSize == -1
              else if (r.op == "write_bundle") a.bundlePresent and a.bundleSize > 0 and a.unchanged
              else a.repoExists and (r.op == "checkpoint_file" or a.unchanged)
            if (agrees) "file_observed" else "wrong_file_observation"
          } else if (mark == "sum-report") sumReadVerdict(sumScenario, a, r, producer)
          else if (mark == "plan-report") planReadWithTip(a, r, id("plan"), requestId, if (phase == 0) -3 else 3,
            marked("sum-report"), scaleV1, if (phase == 0) id("prior") else "-")
          else if (mark == "stored-report") storedCandidateReport(rows, a, r, marked("sum-report"), marked("plan-report"))
          else if (mark == "worker-report" or mark == "published-report") {
            val expected = { ...selected, factor: ("-3", -3) }
            val read = requestedReadVerdict(expected, a, r, id("result"), requestId, marked("sum-report"))
            if (read != "inspected" or mark == "worker-report") read
            else if (durableLineage(rows, a, producer, id("prior"), requestId) and
                equivalentReports(a, marked("worker-report"))) "inspected" else "wrong_durable_lineage"
          } else "unclassified_plan_step"
        out.append(verdict)
      })
    }
  }
}
