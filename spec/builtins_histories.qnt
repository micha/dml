module builtins_histories {
  type Request = { op: str, args: List[str] }
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure val selected = List("--selected-ref", "t1", "--selected", "@t1")
  pure val story: List[Request] = List(
    source("define_choice", List("initial")),
    source("request", List("initial", "@initial", "p1", "d1", "42")),
    source("promote", List("initial", "@initial", "promoted")),
    source("compatibility", List("promoted", "@promoted", "compat")),
    source("inspect", List("compat")),
    source("work", List("p1", "@p1", "t1")),
    source("inspect", List("t1")),
    source("request", List("promoted", "@promoted", "unused", "hit", "42", "--source", "named",
      "--mode", "require-selected").concat(selected)),
    source("inspect", List("hit")),
    source("request", List("promoted", "@promoted", "p3", "d3", "43", "--mode", "try-selected").concat(selected)),
    source("inspect", List("d3")),
    source("work", List("p3", "@p3", "t3")),
    source("inspect", List("t3")),
    source("request", List("promoted", "@promoted", "p-bad", "d-bad", "42", "--version", "v99",
      "--mode", "require-selected").concat(selected)),
    source("request", List("promoted", "@promoted", "p-bad", "d-bad", "42", "--mode", "try-selected",
      "--selected-ref", "t1", "--selected", "@initial")),
    source("request", List("promoted", "@promoted", "p-bad", "d-bad", "43", "--mode", "try-selected",
      "--selected-ref", "initial", "--selected", "@initial")),
    source("request", List("promoted", "@promoted", "p-bad", "d1", "42", "--mode", "try-selected").concat(selected)),
    source("request", List("promoted", "@promoted", "p3", "d-bad", "42", "--mode", "try-selected").concat(selected)),
    source("work", List("p1", "@p1", "t3")),
    { op: "replicate", args: List("replica", "hit", "snapshot") },
    { op: "inspect", args: List("replica", "snapshot") },
    { op: "fixture", args: List("replica", "source-graft") },
    { op: "inspect", args: List("replica", "source-graft") },
    { op: "fixture", args: List("replica", "version-graft") },
    { op: "inspect", args: List("replica", "version-graft") }
  )
  var histories: List[List[Request]]
  action init = histories' = List(story)
  action step = histories' = histories
}
