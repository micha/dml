module interpreter_verdict_histories {
  type Request = { op: str, args: List[str] }
  var histories: List[List[Request]]
  action init = histories' = List(List({ op: "datum_encode", args: List("i64", "42", "packed") }))
  action missingVerdict = histories' = List(List({ op: "datum_encode", args: List("i64", "0", "packed") }))
  action step = histories' = histories
}
