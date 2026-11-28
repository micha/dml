module argument_map_budget_histories {
  type Request = { op: str, args: List[str] }
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure def leaf(attempt, argument) = { attempt: attempt, argument: argument }
  // Fifty-nine attempts of one zero-valued request. Group the exact pins into four maps.
  pure val budgetLeaves = List(
    List(leaf("t-b01", "a=from:t-b01:@t-b01"), leaf("t-b02", "b=from:t-b02:@t-b02"),
      leaf("t-b03", "c=from:t-b03:@t-b03"), leaf("t-b04", "d=from:t-b04:@t-b04"),
      leaf("t-b05", "e=from:t-b05:@t-b05"), leaf("t-b06", "f=from:t-b06:@t-b06"),
      leaf("t-b07", "g=from:t-b07:@t-b07"), leaf("t-b08", "h=from:t-b08:@t-b08"),
      leaf("t-b09", "i=from:t-b09:@t-b09"), leaf("t-b10", "j=from:t-b10:@t-b10"),
      leaf("t-b11", "k=from:t-b11:@t-b11"), leaf("t-b12", "l=from:t-b12:@t-b12"),
      leaf("t-b13", "m=from:t-b13:@t-b13"), leaf("t-b14", "n=from:t-b14:@t-b14"),
      leaf("t-b15", "o=from:t-b15:@t-b15")),
    List(leaf("t-b16", "a=from:t-b16:@t-b16"), leaf("t-b17", "b=from:t-b17:@t-b17"),
      leaf("t-b18", "c=from:t-b18:@t-b18"), leaf("t-b19", "d=from:t-b19:@t-b19"),
      leaf("t-b20", "e=from:t-b20:@t-b20"), leaf("t-b21", "f=from:t-b21:@t-b21"),
      leaf("t-b22", "g=from:t-b22:@t-b22"), leaf("t-b23", "h=from:t-b23:@t-b23"),
      leaf("t-b24", "i=from:t-b24:@t-b24"), leaf("t-b25", "j=from:t-b25:@t-b25"),
      leaf("t-b26", "k=from:t-b26:@t-b26"), leaf("t-b27", "l=from:t-b27:@t-b27"),
      leaf("t-b28", "m=from:t-b28:@t-b28"), leaf("t-b29", "n=from:t-b29:@t-b29"),
      leaf("t-b30", "o=from:t-b30:@t-b30")),
    List(leaf("t-b31", "a=from:t-b31:@t-b31"), leaf("t-b32", "b=from:t-b32:@t-b32"),
      leaf("t-b33", "c=from:t-b33:@t-b33"), leaf("t-b34", "d=from:t-b34:@t-b34"),
      leaf("t-b35", "e=from:t-b35:@t-b35"), leaf("t-b36", "f=from:t-b36:@t-b36"),
      leaf("t-b37", "g=from:t-b37:@t-b37"), leaf("t-b38", "h=from:t-b38:@t-b38"),
      leaf("t-b39", "i=from:t-b39:@t-b39"), leaf("t-b40", "j=from:t-b40:@t-b40"),
      leaf("t-b41", "k=from:t-b41:@t-b41"), leaf("t-b42", "l=from:t-b42:@t-b42"),
      leaf("t-b43", "m=from:t-b43:@t-b43"), leaf("t-b44", "n=from:t-b44:@t-b44"),
      leaf("t-b45", "o=from:t-b45:@t-b45")),
    List(leaf("t-b46", "a=from:t-b46:@t-b46"), leaf("t-b47", "b=from:t-b47:@t-b47"),
      leaf("t-b48", "c=from:t-b48:@t-b48"), leaf("t-b49", "d=from:t-b49:@t-b49"),
      leaf("t-b50", "e=from:t-b50:@t-b50"), leaf("t-b51", "f=from:t-b51:@t-b51"),
      leaf("t-b52", "g=from:t-b52:@t-b52"), leaf("t-b53", "h=from:t-b53:@t-b53"),
      leaf("t-b54", "i=from:t-b54:@t-b54"), leaf("t-b55", "j=from:t-b55:@t-b55"),
      leaf("t-b56", "k=from:t-b56:@t-b56"), leaf("t-b57", "l=from:t-b57:@t-b57"),
      leaf("t-b58", "m=from:t-b58:@t-b58"), leaf("t-b59", "n=from:t-b59:@t-b59"))
  )
  pure val budgetBase = budgetLeaves.foldl(List(source("request", List("p-leaf", "d-leaf", "double@1", "--arg", "x=i64:0"))),
    (steps, group) => group.foldl(steps, (out, row) =>
      out.append(source("work", List("p-leaf", "@p-leaf", row.attempt)))))

  pure def cliArguments(args: List[str]): List[str] = args.foldl(List(), (out, arg) => out.append("--arg").append(arg))
  pure def budgetAdd(pending, pin, decision, attempt, args) = List(
    source("request", List(pending, decision, "add@1").concat(cliArguments(args))),
    source("inspect", List(decision)),
    source("work", List(pending, pin, attempt)),
    source("inspect", List(attempt))
  )
  pure def leafArgs(i: int): List[str] = budgetLeaves[i].foldl(List(), (out, row) => out.append(row.argument))
  pure val budgetGroups = List(
    budgetAdd("p-group-a", "@p-group-a", "d-group-a", "t-group-a", leafArgs(0)),
    budgetAdd("p-group-b", "@p-group-b", "d-group-b", "t-group-b", leafArgs(1)),
    budgetAdd("p-group-c", "@p-group-c", "d-group-c", "t-group-c", leafArgs(2)),
    budgetAdd("p-group-d", "@p-group-d", "d-group-d", "t-group-d", leafArgs(3))
  ).foldl(List(), (out, group) => out.concat(group))
  // The four group attempts reach 63 distinct attempts in total, even with the first used twice.
  pure val budgetRoots = List("a=from:t-group-a:@t-group-a", "b=from:t-group-a:@t-group-a",
    "c=from:t-group-b:@t-group-b", "d=from:t-group-c:@t-group-c", "e=from:t-group-d:@t-group-d")
  pure val budgetFull = budgetAdd("p-budget-full", "@p-budget-full", "d-budget-full", "t-budget-full", budgetRoots)
  pure val budgetSibling = List(source("work", List("p-group-a", "@p-group-a", "t-b-sibling")),
    source("inspect", List("t-b-sibling")))
  // Direct and multi-source walks both reach 64 attempts, leaving no slot for new work.
  pure val budgetRejections = List(
    source("request", List("p-budget-next", "d-budget-next", "double@1",
      "--arg", "prefix=i64:1731", "--arg", "x=from:t-budget-full:@t-budget-full")),
    source("request", List("p-budget-union", "d-budget-union", "add@1").concat(
      cliArguments(List("prefix=i64:1732").concat(budgetRoots.replaceAt(1, "b=from:t-b-sibling:@t-b-sibling"))))))
  pure val reachedBudget = budgetBase.concat(budgetGroups).concat(budgetSibling).concat(budgetFull).concat(budgetRejections)
  var histories: List[List[Request]]
  action init = histories' = List(reachedBudget)
  action step = histories' = histories
}
