module ref_histories {
  type Request = { op: str, args: List[str] }

  pure def createRef(name: str, target: str): Request =
    { op: "create_ref", args: List(name, target) }

  pure def publishSnapshot(name: str, parent: str, finish: str, extra: str): Request =
    { op: "publish_snapshot", args: List(name, parent, finish, extra) }

  pure val createA = createRef("main", "A")
  pure val createB = createRef("main", "B")
  pure val publishMain = publishSnapshot("main", "B", "commit", "")

  var histories: List[List[Request]]

  action init = histories' = List(
    List(createA),
    List(createA, createA),
    List(createA, createB),
    List(createB, publishMain),
    List(createB, publishSnapshot("main", "B", "abort", ""), publishMain),
    List(createB, publishSnapshot("main", "B", "commit", "missing"), publishMain)
  )

  // Feed a different name, initial target, and request count to the same runner.
  action changedInit = histories' = List(List(
    createRef("candidate-1", "B"),
    createRef("other", "A"),
    createRef("candidate-1", "A"),
    publishSnapshot("other", "A", "commit", "")
  ))

  action step = histories' = histories
}
