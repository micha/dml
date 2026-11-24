module staged_import_rules {
  import retention_rules.* from "./retention_rules"
  export retention_rules.Observation
  export retention_rules.historyVerdicts
  import retention_fixture.* from "./retention_fixture"

  pure def verdictAccepted(verdict: str): bool = Set(
    "ok", "reopened", "created_ref", "unpinned_import", "bad_ref", "short_bundle", "duplicate_same",
    "duplicate_different", "staged_fresh", "staged_present", "staged", "swept_17", "retained_stage", "retained_main",
    "swept_7", "captured_main", "moved_ref", "stale_main", "current_main", "aborted_write", "released_ref",
    "read_returned", "read_incoming", "read_main", "inspected_commit", "absent_ref", "committed"
  ).contains(verdict)

  pure val required = Set(
    List("created_ref", "unpinned_import", "swept_17", "committed", "bad_ref", "staged_fresh", "duplicate_same",
      "duplicate_different", "short_bundle", "captured_main", "moved_ref", "committed", "staged", "retained_stage",
      "committed", "stale_main", "aborted_write", "reopened", "read_returned", "inspected_commit", "released_ref",
      "committed", "reopened", "absent_ref", "swept_7", "committed", "reopened", "read_incoming", "inspected_commit"),
    List("created_ref", "unpinned_import", "staged_present", "retained_stage", "committed", "captured_main", "current_main",
      "moved_ref", "committed", "released_ref", "committed", "retained_main", "committed", "reopened", "read_main",
      "inspected_commit")
  )

  pure def linkedReadback(attempts: List[Attempt], index: int): bool = {
    if (index < 3) false else {
      val reopened = attempts[index - 3]
      val began = attempts[index - 2]
      val read = attempts[index - 1]
      all {
        reopened.op == "repo_open" and reopened.args == List("origin", "existing"),
        began.op == "txn_begin" and began.args == List("origin", "read", "readback"),
        read.op == "txn_ref_get" and read.args[0] == began.args[2],
        attempts[index].args.slice(0, 3) == List(read.args[0], "commit", read.args[2])
      }
    }
  }

  pure def linkedPublication(attempts: List[Attempt], verdicts: List[str]): bool = {
    val stage = attempts.select(attempt => attempt.op == "repo_import_commit_staged" and attempt.status == "ok"
      and attempt.args[2] == "returned")
    val releases = attempts.select(attempt => attempt.op == "txn_ref_delete_expected")
    val comparisons = verdicts.indices().filter(i => Set("current_main", "stale_main").contains(verdicts[i]))
    val captures = verdicts.indices().filter(i => verdicts[i] == "captured_main")
    if (stage.length() != 1 or releases.length() != 1 or comparisons.size() != 1 or captures.size() != 1) false
    else {
      val saved = stage[0].args[3]
      releases[0].args.slice(1, 3) == List("returned", saved) and comparisons.forall(i => {
        val matched = captures.exists(j => attempts[j].value == attempts[i].value)
        val txn = attempts[i].args[0]
        if (i == 0 or i + 2 >= attempts.length()) false
        else {
          val begin = attempts[i - 1]
          val follow = attempts[i + 1]
          begin.op == "txn_begin" and begin.args == List("origin", "write", txn)
            and (if (matched) all {
              verdicts[i] == "current_main",
              follow.op == "txn_ref_update" and follow.args == List(txn, "main", saved),
              attempts[i + 2].op == "txn_commit" and attempts[i + 2].args == List(txn)
            } else verdicts[i] == "stale_main" and follow.op == "txn_abort" and follow.args == List(txn))
        }
      })
    }
  }

  pure def coveragePass(evidence: List[Observation], verdicts: List[List[str]]): bool = {
    val patterns = verdicts.indices().map(i => verdicts[i].select(label => label != "ok"))
    required.subseteq(patterns) and evidence.indices().forall(i => {
      val attempts = evidence[i].attempts
      linkedPublication(attempts, verdicts[i])
        and attempts.indices().forall(j => attempts[j].op != "txn_get_object" or linkedReadback(attempts, j))
    })
  }

  pure val beforeStage: State = { ...initial, opened: Set("origin", "worker"),
    inventories: Map("origin" -> { ...empty, objects: idsOf(keepRecords), refs: Map("main" -> keep.id) }),
    bundles: Map("selectedBundle" -> selected.id, "resultBundle" -> result.id) }
  pure val stageArgs = List("origin", "selectedBundle", "incoming", "selectedTip")
  pure val inserted = selectedRecords.foldl(List({ kind: "added", key: refKeys.get("incoming"), before: "", after: selected.id }),
    (out, record) => out.append({ kind: "added", key: record.key, before: "", after: record.packed }))
  pure val staged = { ...noOutput, op: "repo_import_commit_staged", args: stageArgs, value: selected.id, changes: inserted }
  pure val afterStage = transition(beforeStage, staged.op, staged.args).state
  pure val duplicate = { ...noOutput, op: "repo_import_commit_staged", args: List("origin", "resultBundle", "incoming", "ignored"),
    status: "invalid_state", value: sentinel }
  pure val resultObject = { kind: "added", key: result.key, before: "", after: result.packed }

  pure val controlsPass = all {
    checkControl(beforeStage, staged) == "staged_fresh",
    checkControl(beforeStage, { ...staged, changes: inserted.tail() }) == "inventory",
    checkControl(beforeStage, { ...staged, changes: List(inserted[0]) }) == "inventory",
    checkControl(beforeStage, { ...staged, otherChanges: List(resultObject) }) == "inventory",
    checkControl(afterStage, duplicate) == "duplicate_different",
    checkControl(afterStage, { ...duplicate, changes: List(resultObject) }) == "inventory",
    checkControl(afterStage, { ...duplicate, value: result.id }) == "value"
  }
}
