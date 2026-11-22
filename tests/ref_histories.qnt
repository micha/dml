module ref_histories {
  type Request = { name: str, target: str }

  pure val createA: Request = { name: "main", target: "A" }
  pure val createB: Request = { name: "main", target: "B" }

  var histories: List[List[Request]]

  action init = histories' = List(
    List(createA),
    List(createA, createA),
    List(createA, createB)
  )

  // Feed a different name, initial target, and request count to the same runner.
  action changedInit = histories' = List(List(
    { name: "candidate-1", target: "B" },
    { name: "other", target: "A" },
    { name: "candidate-1", target: "A" }
  ))

  action step = histories' = histories
}
