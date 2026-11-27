module recorded_calls_outbound_histories {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"
  import recorded_calls_stored_histories.readLinkedGraph from "./recorded_calls_stored_histories"

  type TransferStep = { request: Request, label: str, mark: str }
  pure def expectTransfer(request: Request, label: str, mark: str): TransferStep = { request: request, label: label, mark: mark }
  pure def nativeTransfer(requests: List[Request]): List[TransferStep] =
    requests.foldl(List(), (steps, req) => steps.append(expectTransfer(req, "native_ok", "")))
  pure def observeNative(request: Request, mark: str): TransferStep = expectTransfer(request, "native_ok", mark)
  pure def absentNative(request: Request): TransferStep = expectTransfer(request, "native_not_found", "")
  pure def getObject(kind: str, id: str, alias: str): Request = coreRequest("txn_get_object", List("snapshot", kind, id, alias))
  pure def movePin(ref: str, id: str): Request = coreRequest("txn_ref_update", List("snapshot", ref, id))
  pure def readWorker(requests: List[Request]): List[TransferStep] =
    nativeTransfer(openRepo("worker", "existing", "read").concat(requests).concat(closeRepo("worker", "txn_abort")))

  // Transfer two different producers of the same stored result. The worker
  // must use the selected physical lineage after both bundles and pins are gone.
  pure val outboundCollection = nativeTransfer(storedSum("source", "producer", "example.sum@1")).concat(List(
    expectTransfer(source("record_sum", List("decoy", "6", "-23")), "recorded", "decoy"),
    expectTransfer(source("checkpoint_file", List("origin")), "file_observed", "")
  )).concat(nativeTransfer(openNative("read").concat(snapshotAt("sum:decoy", "origin-decoy-commit", "origin-decoy-tree", "origin-decoy-dag", ""))
    .concat(viewObject("dag", "origin-decoy-dag", "origin-decoy-root")).concat(closeNative("txn_abort")))).concat(List(
    expectTransfer(source("export_sum", List("producer", "native:stored-sum-commit", "selected.dmlb")), "exported", "selected-export"),
    expectTransfer(worker("stage_input", List("incoming", "selected.dmlb")), "staged", "selected-stage"),
    expectTransfer(coreRequest("unlink_bundle", List("selected.dmlb")), "file_observed", ""),
    expectTransfer(source("export_sum", List("decoy", "decoy", "decoy.dmlb")), "exported", "decoy-export"),
    expectTransfer(worker("stage_input", List("discard", "decoy.dmlb")), "staged", "decoy-stage"),
    expectTransfer(coreRequest("unlink_bundle", List("decoy.dmlb")), "file_observed", ""),
    expectTransfer(worker("record_scale", List("incoming", "native:stored-sum-commit", "main", "6")), "recorded", "scaled"),
    expectTransfer(worker("release_input", List("incoming", "native:stored-sum-commit", "main")), "released", "released")
  )).concat(nativeTransfer(openRepo("worker", "existing", "write"))).append(absentNative(refRead("incoming", "released-incoming")))
    .concat(nativeTransfer(List(drop("discard", "sum:decoy")).concat(closeRepo("worker", "txn_commit"))))
    .concat(readWorker(List(getObject("commit", "sum:decoy", "unrooted-decoy"))))
    .append(expectTransfer(worker("collect", List()), "collected", "swept"))
    .concat(nativeTransfer(openRepo("worker", "existing", "read"))).concat(List(
      absentNative(getObject("commit", "sum:decoy", "swept-decoy")),
      absentNative(refRead("producer", "origin-producer")), absentNative(refRead("decoy", "origin-decoy-ref")),
      absentNative(refRead("incoming", "collected-incoming")), absentNative(refRead("discard", "collected-discard"))
    )).concat(nativeTransfer(readLinkedGraph("main", true).concat(closeRepo("worker", "txn_abort")))).concat(List(
      expectTransfer(worker("inspect", List()), "inspected", "collected-report"),
      expectTransfer(source("compare_file", List("origin")), "file_observed", "")
    ))

  // Keep every other guard satisfied: first prove the selected import pin,
  // then choose a missing result, wrong parent, and finally a right parent
  // whose scale input DAG belongs to a different, equal-root producer.
  pure val outboundGuards = List(
    expectTransfer(source("record_sum", List("producer", "7", "5")), "recorded", "producer"),
    expectTransfer(source("record_sum", List("decoy", "9", "3")), "recorded", "decoy"),
    expectTransfer(source("export_sum", List("decoy", "producer", "selected.dmlb")), "rejected", "wrong-export-pin"),
    expectTransfer(source("export_sum", List("producer", "producer", "selected.dmlb")), "exported", "selected-export"),
    expectTransfer(source("export_sum", List("decoy", "decoy", "decoy.dmlb")), "exported", "decoy-export"),
    expectTransfer(source("export_sum", List("decoy", "decoy", "selected.dmlb")), "rejected", "no-clobber"),
    expectTransfer(worker("stage_input", List("incoming", "decoy.dmlb")), "staged", "decoy-stage"),
    expectTransfer(worker("stage_input", List("incoming", "decoy.dmlb")), "rejected", "same-occupied"),
    expectTransfer(worker("stage_input", List("incoming", "selected.dmlb")), "rejected", "other-occupied"),
    expectTransfer(worker("record_scale", List("incoming", "producer", "main", "3")), "rejected", "stale-scale"),
    expectTransfer(worker("record_scale", List("incoming", "decoy", "other", "3")), "recorded", "decoy-scale")
  ).concat(nativeTransfer(openRepo("worker", "existing", "write"))).append(absentNative(refRead("main", "missing-result")))
    .concat(nativeTransfer(List(drop("incoming", "sum:decoy")).concat(closeRepo("worker", "txn_commit")))).concat(List(
      expectTransfer(worker("stage_input", List("incoming", "selected.dmlb")), "staged", "selected-stage"),
      expectTransfer(worker("release_input", List("incoming", "producer", "main")), "rejected", "missing-result"),
      expectTransfer(worker("release_input", List("incoming", "producer", "other")), "rejected", "wrong-parent"),
      expectTransfer(worker("record_scale", List("incoming", "producer", "main", "3")), "recorded", "scaled")
    )).concat(nativeTransfer(openRepo("worker", "existing", "write")
      .concat(snapshotAt("scale:worker:other", "other-scale-commit", "other-scale-tree", "other-scale-dag", "other-scale-parent"))
      .concat(snapshotAt("other-scale-parent", "other-sum-commit", "other-sum-tree", "other-sum-dag", ""))
      .concat(snapshotAt("sum:producer", "selected-sum-commit", "selected-sum-tree", "selected-sum-dag", ""))
      .concat(viewSubdag("other-scale-dag", "wrong-input", "wrong-input-target"))
      .concat(viewObject("dag", "other-sum-dag", "other-sum-root"))
      .concat(viewObject("dag", "selected-sum-dag", "selected-sum-root"))
      .concat(putObject("commit", List("other-scale-commit", "sum:producer"), "forged-result"))
      .append(pin("forged", "forged-result")).concat(closeRepo("worker", "txn_commit"))))
    .concat(readWorker(List(refRead("forged", "persisted-forgery"), refRead("incoming", "selected-incoming"),
      refRead("other", "decoy-result-pin"), refRead("main", "valid-result-pin"))
      .concat(snapshotAt("persisted-forgery", "forged-scale-commit", "forged-scale-tree", "forged-scale-dag", "forged-scale-parent"))))
    .append(expectTransfer(worker("release_input", List("incoming", "producer", "forged")), "rejected", "wrong-input"))
    .concat(nativeTransfer(openRepo("worker", "existing", "write").append(movePin("incoming", "sum:decoy"))
      .concat(closeRepo("worker", "txn_commit"))))
    .append(expectTransfer(worker("release_input", List("incoming", "producer", "main")), "rejected", "moved-incoming"))
    .concat(nativeTransfer(openRepo("worker", "existing", "read")))
    .append(observeNative(refRead("incoming", "moved-incoming-pin"), "kept-decoy-pin"))
    .concat(nativeTransfer(closeRepo("worker", "txn_abort")))

  // Read all known IDs in the selected closure, not just the first bad frame.
  pure val outboundSumLiterals = List(
    ("stored-sum-implementation", "stored-sum-implementation-datum"), ("stored-a", "stored-a-datum"),
    ("stored-b", "stored-b-datum"), ("stored-sum-root", "stored-sum-root-datum")
  )
  pure val absentImport: List[TransferStep] =
    nativeTransfer(openRepo("worker", "create", "read")).append(absentNative(refRead("incoming", "absent-import-pin")))
      .concat(List(("commit", "stored-sum-commit"), ("tree", "stored-sum-tree"), ("dag", "stored-sum-dag"))
        .foldl(List(), (steps, object) => steps.append(absentNative(getObject(object._1, object._2, "absent-import-object")))))
      .concat(outboundSumLiterals.foldl(List(), (out, ids) => out.concat(List(
        absentNative(getObject("node", ids._1, "absent-import-literal")),
        absentNative(coreRequest("txn_get_datum", List("snapshot", ids._2, "absent-import-datum")))
      )))).concat(nativeTransfer(closeRepo("worker", "txn_abort")))

  pure val outboundTruncation = nativeTransfer(storedSum("source", "producer", "example.sum@1")).concat(List(
    expectTransfer(source("export_sum", List("producer", "native:stored-sum-commit", "selected.dmlb")), "exported", "selected-export"),
    expectTransfer(coreRequest("truncate_bundle", List("selected.dmlb", "truncated.dmlb", "1")), "file_observed", "truncated-copy"),
    expectTransfer(worker("stage_input", List("incoming", "truncated.dmlb")), "rejected", "fresh-truncated")
  )).concat(absentImport).append(
    expectTransfer(worker("stage_input", List("incoming", "truncated.dmlb")), "rejected", "existing-truncated")
  ).concat(absentImport).append(
    expectTransfer(worker("stage_input", List("incoming", "selected.dmlb")), "staged", "selected-stage")
  ).concat(nativeTransfer(openRepo("worker", "existing", "read")))
    .append(observeNative(refRead("incoming", "intact-incoming"), "intact-pin"))
    .concat(nativeTransfer(snapshotAt("intact-incoming", "intact-sum-commit", "intact-sum-tree", "intact-sum-dag", "")))
    .append(observeNative(getObject("dag", "intact-sum-dag", "intact-dag-record"), "intact-closure"))
    .concat(nativeTransfer(closeRepo("worker", "txn_abort")))

  pure def latePublish(staging: str, oldMain: str): Request =
    source("publish_scale", List(staging, "native:rollback-result", "producer", "3", oldMain))
  pure val outboundLateGuard = List(
    expectTransfer(source("record_sum", List("producer", "7", "5")), "recorded", "producer"),
    expectTransfer(source("record_scale", List("producer", "producer", "result", "3")), "recorded", "scaled"),
    expectTransfer(source("record_scale", List("producer", "producer", "other", "4")), "recorded", "other-scale")
  ).concat(nativeTransfer(openNative("write").append(refRead("result", "rollback-result"))
    .append(pin("returned", "rollback-result")).concat(closeNative("txn_commit"))))
    .append(expectTransfer(source("inspect", List("returned")), "inspected", "ready-result"))
    .concat(nativeTransfer(openNative("write").append(movePin("returned", "scale:source:other")).concat(closeNative("txn_commit"))))
    .append(expectTransfer(latePublish("returned", "-"), "rejected", "rollback-create"))
    .concat(nativeTransfer(openNative("write"))).concat(List(
      absentNative(refRead("main", "rollback-main-absent")),
      observeNative(refRead("returned", "returned-after-create"), "kept-other-pin"),
      observeNative(refRead("producer", "rollback-prior"), "kept-producer")
    )).concat(nativeTransfer(List(pin("main", "rollback-prior")).concat(closeNative("txn_commit"))))
    .concat(List(
      expectTransfer(latePublish("returned", "native:rollback-prior"), "rejected", "rollback-update"),
      expectTransfer(latePublish("main", "native:rollback-prior"), "rejected", "alias-main")
    )).concat(nativeTransfer(openNative("write"))).concat(List(
      observeNative(refRead("main", "main-after-update"), "kept-producer"),
      observeNative(refRead("returned", "returned-after-update"), "kept-other-pin")
    )).concat(nativeTransfer(List(drop("returned", "scale:source:other")).concat(closeNative("txn_commit"))))
    .append(expectTransfer(latePublish("returned", "native:rollback-prior"), "rejected", "missing-staging"))
    .concat(nativeTransfer(openNative("read"))).concat(List(
      observeNative(refRead("main", "main-after-missing"), "kept-producer"),
      absentNative(refRead("returned", "released-staging"))
    )).concat(nativeTransfer(closeNative("txn_abort")))

  pure val outboundCases = List(outboundCollection, outboundGuards, outboundTruncation, outboundLateGuard)
  pure val outboundRequests: List[List[Request]] = outboundCases.foldl(List(), (out, steps) =>
    out.append(steps.foldl(List(), (reqs, step) => reqs.append(step.request))))
  pure val outboundExpected: List[List[str]] = outboundCases.foldl(List(), (out, steps) =>
    out.append(steps.foldl(List(), (labels, step) => labels.append(step.label))))
}
