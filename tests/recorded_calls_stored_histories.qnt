module recorded_calls_stored_histories {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  pure val storedProducer = storedSum("source", "producer", "example.sum@1")
  pure val producerId = "native:stored-sum-commit"
  pure val storedResultId = "native:stored-scale-commit"

  pure def scaleGraph(input: str): List[Request] =
    putLiteral("string", "example.scale@1", "stored-scale-implementation-datum", "stored-scale-implementation")
      .concat(putLiteral("i64", "6", "stored-factor-datum", "stored-factor"))
      .concat(putLiteral("i64", "-98", "stored-scale-root-datum", "stored-scale-root"))
      .concat(putObject("dag", List("stored-scale-root", "implementation", "stored-scale-implementation",
        "input", input, "factor", "stored-factor"), "stored-scale-dag"))
  pure val linkedInput = putObject("node", List("subdag", "stored-sum-dag"), "stored-input")

  pure def readScale(ref: str, split: bool): List[Request] = List(refRead(ref, "observed-scale-id"))
    .concat(commitAt("observed-scale-id", ("observed-scale-commit", "observed-scale-tree", "observed-scale-dag",
      if (split) "observed-scale-parent" else "")))
  pure def readLinkedGraph(ref: str, split: bool): List[Request] = readScale(ref, split)
      .concat(if (split) commitAt("observed-scale-parent",
         ("observed-parent-commit", "observed-parent-tree", "observed-parent-dag", "")) else List())
      .concat(viewObject("dag", "observed-scale-dag", "observed-scale-root"))
      .concat(viewSubdag("observed-scale-dag", "observed-input", "observed-sum-dag"))
      .concat(viewObject("dag", "observed-sum-dag", "observed-sum-root"))
      .concat(viewLiteral("observed-scale-root", "observed-scale-value"))
      .concat(viewLiteral("observed-sum-root", "observed-sum-value"))

  pure val storedExecutionRequests = storedProducer.append(source("record_scale", List("producer", producerId, "main", "6")))
    .concat(openNative("read")).concat(readLinkedGraph("main", true)).concat(closeNative("txn_abort"))
    .append(source("inspect", List()))

  pure val unsupportedSumRequests = storedSum("source", "producer", "example.sum@2")
    .concat(openNative("read")).append(refRead("producer", "unsupported-id"))
    .concat(commitAt("unsupported-id", ("unsupported-commit", "unsupported-tree", "unsupported-dag", "")))
    .append(lookupNode("unsupported-dag", "implementation", "unsupported-version"))
    .concat(viewLiteral("unsupported-version", "unsupported-value")).concat(closeNative("txn_abort"))
    .append(source("record_scale", List("producer", producerId, "main", "3")))
    .concat(openNative("read")).append(refRead("producer", "unchanged-producer"))
    .append(refRead("main", "absent-main")).concat(closeNative("txn_abort"))

  // The genuine result and forged result share a tree; only the sole parent is replaced.
  pure val mismatchedParentRequests = List(
    source("record_sum", List("producer", "7", "5")), source("record_sum", List("decoy", "9", "3")),
    source("record_scale", List("producer", "producer", "main", "3")), source("inspect", List())
  ).concat(openNative("write")).append(refRead("main", "genuine-id"))
    .concat(commitAt("genuine-id", ("genuine-commit", "genuine-tree", "genuine-dag", "genuine-parent")))
    .concat(commitAt("sum:producer", ("selected-sum-commit", "selected-sum-tree", "selected-sum-dag", "")))
    .concat(commitAt("sum:decoy", ("decoy-sum-commit", "decoy-sum-tree", "decoy-sum-dag", "")))
    .concat(viewObject("dag", "selected-sum-dag", "selected-sum-root"))
    .concat(viewObject("dag", "decoy-sum-dag", "decoy-sum-root"))
    .concat(viewSubdag("genuine-dag", "genuine-input", "genuine-input-dag"))
    .concat(putObject("commit", List("genuine-commit", "sum:decoy"), "mismatch-id"))
    .append(pin("mismatch", "mismatch-id")).concat(closeNative("txn_commit"))
    .concat(openNative("read")).append(refRead("mismatch", "persisted-mismatch"))
    .concat(commitAt("persisted-mismatch", ("mismatch-commit", "mismatch-tree", "mismatch-dag", "mismatch-parent")))
    .concat(closeNative("txn_abort"))
    .concat(List(source("inspect", List("mismatch")),
      source("export_scale", List("mismatch", "native:mismatch-id", "mismatch.bundle")),
      source("publish_scale", List("mismatch", "native:mismatch-id", "decoy", "3", "native:genuine-id"))))
    .concat(openNative("read")).append(refRead("main", "unchanged-main"))
    .append(refRead("mismatch", "unchanged-mismatch")).concat(closeNative("txn_abort"))

  pure def combinedStoredRequests(link: bool): List[Request] = openRepo("source", "create", "write")
    .concat(sumGraph("example.sum@1"))
    // Same exact result node and different actual DAG (the arguments are swapped).
    .concat(putObject("dag", List("stored-sum-root", "implementation", "stored-sum-implementation",
      "a", "stored-b", "b", "stored-a"), "equal-root-decoy"))
    .concat(if (link) linkedInput else List())
    .concat(scaleGraph(if (link) "stored-input" else "stored-sum-root"))
    .concat(putObject("tree", List("recorded-calls-v1", "stored-scale-dag"), "stored-scale-tree"))
    .concat(putObject("commit", List("stored-scale-tree"), "stored-scale-commit"))
    .append(pin("main", "stored-scale-commit")).concat(closeNative("txn_commit"))
    .concat(openNative("read"))
    .concat(viewObject("dag", "equal-root-decoy", "equal-root-decoy-root"))
    .concat(if (link) readLinkedGraph("main", false) else
      readScale("main", false)
        .append(lookupNode("observed-scale-dag", "input", "observed-input"))
        .concat(viewLiteral("observed-input", "observed-sum-value")))
    .concat(closeNative("txn_abort")).append(source("inspect", List()))

  pure val storedReturnRequests = storedProducer.concat(List(
    source("record_sum", List("decoy", "6", "-23")),
    source("export_sum", List("producer", producerId, "sum.bundle")),
    worker("stage_input", List("incoming", "sum.bundle"))
  )).concat(openRepo("worker", "existing", "write")).concat(linkedInput).concat(scaleGraph("stored-input"))
    .concat(putObject("tree", List("recorded-scale-v1", "stored-scale-dag"), "stored-scale-tree"))
    .concat(putObject("commit", List("stored-scale-tree", "stored-sum-commit"), "stored-scale-commit"))
    .append(pin("result", "stored-scale-commit")).concat(closeRepo("worker", "txn_commit"))
    .concat(List(
      worker("inspect", List("result")), worker("checkpoint_file", List("worker-before")),
      worker("export_scale", List("result", storedResultId, "scale.bundle")),
      source("stage_input", List("returned", "scale.bundle")), source("inspect", List("returned")),
      coreRequest("unlink_bundle", List("sum.bundle")), coreRequest("unlink_bundle", List("scale.bundle"))
    )).concat(openNative("write")).concat(List(drop("producer", "stored-sum-commit"), drop("decoy", "sum:decoy")))
    .concat(closeNative("txn_commit")).concat(openNative("read"))
    .append(refRead("producer", "absent-producer-before-publish"))
    .append(refRead("main", "absent-main")).append(refRead("returned", "staged-result"))
    .concat(closeNative("txn_abort"))
    .append(source("publish_scale", List("returned", storedResultId, producerId, "5", "-")))
    .concat(openNative("read")).append(refRead("main", "absent-main-after-wrong-factor"))
    .append(refRead("returned", "retained-result")).concat(closeNative("txn_abort"))
    .append(source("publish_scale", List("returned", storedResultId, producerId, "6", "-")))
    .concat(openNative("read"))
    .append(coreRequest("txn_get_object", List("snapshot", "commit", "sum:decoy", "unrooted-return-decoy")))
    .concat(closeNative("txn_abort")).append(source("collect", List()))
    .concat(openNative("read")).concat(List(refRead("producer", "absent-producer"), refRead("decoy", "absent-decoy"),
      refRead("returned", "absent-returned"), refRead("incoming", "absent-incoming"), refRead("result", "absent-result")))
    .append(coreRequest("txn_get_object", List("snapshot", "commit", "sum:decoy", "swept-decoy")))
    .concat(readLinkedGraph("main", true)).concat(closeNative("txn_abort"))
    .append(source("inspect", List())).append(worker("compare_file", List("worker-before")))

  pure val storedEvidenceRequests = List(storedExecutionRequests, unsupportedSumRequests, mismatchedParentRequests,
    combinedStoredRequests(true), combinedStoredRequests(false), storedReturnRequests)
}
