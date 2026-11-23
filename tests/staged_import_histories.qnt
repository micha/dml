module staged_import_histories {
  type Request = { op: str, args: List[str] }

  pure def stepOf(op: str): Request = { op: op, args: List() }
  pure def stage(target: str, ref: str, bundle: str): Request = { op: "stage", args: List(target, ref, bundle) }
  pure def readRef(ref: str): Request = { op: "read_ref", args: List(ref) }
  pure val importResult = stepOf("import_result")
  pure val collect = stepOf("collect")
  pure val capture = stepOf("capture_main")
  pure val publish = stepOf("publish_returned")
  pure val release = stepOf("release_returned")

  var histories: List[List[Request]]

  action init = histories' = List(
    // Collection removes the unpinned copy. Staging then restores and roots the selected closure.
    List(importResult, collect, stage("result", "bad/ref", "valid"),
      stage("selected", "incoming", "valid"), stage("selected", "incoming", "valid"),
      stage("result", "incoming", "valid"), stage("result", "returned", "truncated"),
      capture, stepOf("advance_main"), stage("result", "returned", "valid"), collect,
      publish, readRef("returned"), release, readRef("returned"), collect, readRef("incoming")),
    // An already present closure only needs a ref row. Publishing takes over as its root.
    List(importResult, stage("result", "returned", "valid"), collect, capture, publish,
      release, collect, readRef("main"))
  )

  action step = histories' = histories
}
