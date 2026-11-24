module gc_rules {
  import retention_rules.* from "./retention_rules"
  export retention_rules.Observation
  export retention_rules.historyVerdicts
  import retention_fixture.* from "./retention_fixture"

  pure def verdictAccepted(verdict: str): bool = Set(
    "ok", "unpinned_import", "created_pin", "released_pin", "created_ref", "released_ref", "moved_ref",
    "swept_17", "swept_7", "swept_5", "swept_0", "target_swept", "poisoned_commit", "aborted_write", "committed"
  ).contains(verdict)

  pure val required = Set(
    // Abort the last-root release, observe another zero sweep, then repeat and commit.
    List("unpinned_import", "created_pin", "swept_0", "committed", "created_ref", "committed",
      "released_ref", "swept_0", "committed", "released_pin", "swept_17", "aborted_write", "swept_0", "committed",
      "released_pin", "swept_17", "committed", "swept_0", "committed"),
    // The same-transaction pin retains ancestors; dropping it retains the shared parent only.
    List("unpinned_import", "created_ref", "swept_7", "committed", "created_ref", "swept_0", "committed",
      "released_ref", "swept_5", "committed", "released_ref", "swept_5", "committed"),
    // A create after collection fails on the swept target and poisons the entire transaction.
    List("unpinned_import", "swept_17", "target_swept", "poisoned_commit", "swept_17", "committed", "swept_0", "committed"),
    List("unpinned_import", "created_ref", "swept_7", "committed", "created_ref", "swept_0", "committed",
      "moved_ref", "swept_5", "committed", "swept_0", "committed")
  )

  pure def coveragePass(_evidence: List[Observation], verdicts: List[List[str]]): bool =
    required.subseteq(verdicts.indices().map(i => verdicts[i].select(label => label != "ok")))

  pure val populated: Inventory = { ...empty, objects: idsOf(resultRecords) }
  pure val active: State = { ...initial, opened: Set("origin"), inventories: Map("origin" -> populated),
    repo: "origin", txn: "edit", mode: "write", staged: populated, ids: Map("selected" -> selected.id) }
  pure val sweep = { ...noOutput, op: "txn_collect_garbage", args: List("edit"), count: 17 }
  pure val afterSweep = transition(active, sweep.op, sweep.args).state
  pure val deleted = resultRecords.foldl(List(), (out, record) =>
    out.append({ kind: "removed", key: record.key, before: record.packed, after: "" }))
  pure val commitSweep = { ...noOutput, op: "txn_commit", args: List("edit"), changes: deleted }
  pure val abortSweep = { ...noOutput, op: "txn_abort", args: List("edit") }
  pure val afterFailedEdit = transition(afterSweep, "txn_ref_create", List("edit", "incoming", "selected")).state
  pure val rejectedCommit = { ...noOutput, op: "txn_commit", args: List("edit"), status: "invalid_state" }

  pure def frames(records: List[Record]): List[str] = records.foldl(List(result.id), (out, record) =>
    out.concat(List(record.tag, record.id, record.packed)))
  pure val reordered = List(outputDatum, outputNode).concat(selectedRecords)
    .concat(List(implementationDatum, implementationNode, resultDag, resultTree, result))
  pure val consumerFirst = List(baseNode, baseDatum).concat(resultRecords.slice(2, 17))

  pure val controlsPass = all {
    validExport(result.id, frames(resultRecords)),
    validExport(result.id, frames(reordered)), // independent frames need not be in fixture order
    not(validExport(result.id, frames(consumerFirst))),
    not(validExport(result.id, frames(resultRecords).replaceAt(3, implementationDatum.packed))),
    checkControl(active, sweep) == "swept_17",
    checkControl(active, { ...sweep, count: 16 }) == "count",
    checkControl(active, { ...sweep, changes: deleted }) == "inventory",
    checkControl(afterSweep, commitSweep) == "committed",
    checkControl(afterSweep, { ...commitSweep, changes: deleted.slice(0, 16) }) == "inventory",
    checkControl(afterSweep, { ...commitSweep, changes: deleted.append(deleted[0]) }) == "inventory",
    checkControl(afterSweep, abortSweep) == "aborted_write",
    checkControl(afterSweep, { ...abortSweep, changes: deleted }) == "inventory",
    checkControl(afterFailedEdit, rejectedCommit) == "poisoned_commit",
    checkControl(afterFailedEdit, { ...rejectedCommit, changes: deleted }) == "inventory"
  }
}
