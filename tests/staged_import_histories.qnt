module staged_import_histories {
  import retention_histories.* from "./retention_histories"

  pure val fixture = seedWorker.concat(List(exportCommit("worker", "selected", "selectedBundle"),
    exportCommit("worker", "result", "resultBundle"))).concat(seedMain)
  pure val unpinned = importCommit("origin", "resultBundle", "unpinned")
  pure val capture = List(begin("origin", "read", "capture"), readRef("capture", "main", "expected"), abort("capture"))
  pure val advance = List(begin("origin", "write", "advance"), moveRef("advance", "main", "selected"), commit("advance"))
  pure val stage = stageCommit("origin", "resultBundle", "returned", "returnedTip")

  pure def readback(ref: str, found: bool): List[Request] = {
    val read = List(close("origin"), open("origin", "existing"), begin("origin", "read", "readback"),
                    readRef("readback", ref, "readTip"))
    (if (found) read.append(getCommit("readback", "readTip", "commitRecord")) else read).append(abort("readback"))
  }

  // The caller attempts a fixed path; the model checks the observed comparison
  // made inside this write transaction and the resulting update or abort.
  pure def publish(current: bool): List[Request] = {
    val compare = List(begin("origin", "write", "publish"), readRef("publish", "main", "actual"))
    if (current) compare.concat(List(moveRef("publish", "main", "returnedTip"), commit("publish")))
    else compare.append(abort("publish"))
  }

  pure val release = List(begin("origin", "write", "release"), dropRef("release", "returned", "returnedTip"), commit("release"))

  pure def withFixture(steps: List[Request]): List[Request] =
    fixture.concat(steps).concat(List(close("origin"), close("worker")))

  var histories: List[List[Request]]

  action init = histories' = List(
    withFixture(List(unpinned).concat(collectOrigin).concat(List(
      stageCommit("origin", "resultBundle", "bad/ref", "badName"),
      stageCommit("origin", "selectedBundle", "incoming", "selectedTip"),
      stageCommit("origin", "selectedBundle", "incoming", "occupiedSame"),
      stageCommit("origin", "resultBundle", "incoming", "occupiedDifferent"),
      stageCommit("origin", "resultBundle~1", "returned", "shortBundle")
    )).concat(capture).concat(advance).append(stage).concat(collectOrigin).concat(publish(false))
      .concat(readback("returned", true)).concat(release).concat(readback("returned", false))
      .concat(collectOrigin).concat(readback("incoming", true))),
    withFixture(List(unpinned, stage).concat(collectOrigin).concat(capture).concat(publish(true))
      .concat(release).concat(collectOrigin).concat(readback("main", true)))
  )

  action step = histories' = histories
}
