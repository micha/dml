module ref_histories {
  type Request = { op: str, args: List[str] }

  pure def createRef(name: str, target: str): Request =
    { op: "create_ref", args: List(name, target) }

  pure val createA = createRef("main", "A")
  pure val createB = createRef("main", "B")

  var histories: List[List[Request]]

  action init = histories' = List(
    List(createA),
    List(createA, createA),
    List(createA, createB)
  )

  // Feed a different name, initial target, and request count to the same runner.
  action changedInit = histories' = List(List(
    createRef("candidate-1", "B"),
    createRef("other", "A"),
    createRef("candidate-1", "A")
  ))

  action step = histories' = histories
}
