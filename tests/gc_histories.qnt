module gc_histories {
  type Request = { op: str, args: List[str] }

  pure val importResult: Request = { op: "import_result", args: List() }
  pure val damage: Request = { op: "damage", args: List() }
  pure val collect: Request = { op: "transact", args: List("none", "none", "", "", "commit") }
  pure def edit(order: str, verb: str, ref: str, target: str, finish: str): Request = {
    op: "transact", args: List(order, verb, ref, target, finish)
  }

  var histories: List[List[Request]]

  action init = histories' = List(
    List(importResult, edit("before", "create", "result-pin", "result", "commit"),
         edit("only", "create", "incoming", "selected", "commit"),
         edit("before", "delete", "incoming", "selected", "commit"),
         edit("before", "delete", "result-pin", "result", "abort"), collect,
         edit("before", "delete", "result-pin", "result", "commit"), collect),
    List(importResult, edit("before", "create", "incoming", "selected", "commit"),
         edit("before", "create", "main", "base", "commit"),
         edit("before", "delete", "incoming", "selected", "commit"),
         edit("before", "delete", "main", "base", "commit")),
    List(importResult, edit("after", "create", "incoming", "selected", "commit"), collect, collect),
    List(importResult, damage, edit("before", "create", "incoming", "selected", "commit"), collect),
    List(importResult, edit("before", "create", "incoming", "selected", "commit"),
         edit("before", "create", "main", "base", "commit"),
         edit("before", "update", "incoming", "base", "commit"), collect)
  )

  action step = histories' = histories
}
