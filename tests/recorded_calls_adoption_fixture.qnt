module recorded_calls_adoption_fixture {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  pure val firstUuid = "a0000000-0000-4000-8000-000000000001"
  pure val secondUuid = "b0000000-0000-4000-8000-000000000002"
  pure def parent(view: str, index: str, id: str): Request =
    coreRequest("object_view_parent", List(view, index, id))
  pure def work(attemptRef: str, uuid: str): Request =
    source("work_scale_attempt", List("incoming", "native:request-id", attemptRef, uuid))
  pure def adopt(basisRef: str, basisId: str, attemptRef: str, attemptId: str, output: str): Request =
    source("adopt_scale_attempt", List(basisRef, basisId, attemptRef, attemptId, output))

  pure val setup = List(source("record_sum", List("producer", "7", "5")),
    source("request_scale", List("producer", "producer", "plan", "3")))
    .concat(openNative("write")).concat(viewObject("commit", "plan:plan", "fixture-plan"))
    .concat(List(parent("fixture-plan", "0", "request-id"), pin("incoming", "request-id")))
    .concat(closeNative("txn_commit"))
    .concat(List(work("first", firstUuid),
      source("select_scale_attempt", List("plan", "plan", "first", "first", "chosen")),
      work("second", secondUuid)))
}
