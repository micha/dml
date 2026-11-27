module argument_map_trace_histories {
  type Request = { op: str, args: List[str] }
  pure def cli(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure def native(op: str, args: List[str]): Request = { op: "native", args: List(op).concat(args) }
  pure def inspect(ref: str): Request = cli("inspect", List(ref))
  pure def request(pending: str, decision: str, implementation: str, args: List[str]): Request =
    cli("request", List(pending, decision, implementation).concat(args))
  pure def work(pending: str, expected: str, attempt: str): Request = cli("work", List(pending, expected, attempt))

  pure def openTxn(mode: str): List[Request] = List(native("repo_open", List("source", "existing")),
    native("txn_begin", List("source", mode, "txn")))
  pure def closeTxn(end: str): List[Request] = List(native(end, List("txn")), native("repo_close", List("source")))
  pure def view(kind: str, id: str, alias: str): List[Request] = List(
    native("txn_get_object", List("txn", kind, id, alias)), native("object_decode", List(alias, alias)))
  pure def atRef(ref: str, id: str, alias: str): List[Request] = List(native("txn_ref_get", List("txn", ref, id)))
    .concat(view("commit", id, alias))
  pure def parent(alias: str, index: str, output: str): Request = native("object_view_parent", List(alias, index, output))
  pure def treeDag(commitView: str, treeView: str, dag: str): List[Request] =
    view("tree", commitView, treeView).append(native("object_view_entry", List(treeView, "0", dag)))
  pure def lookup(dag: str, name: str, node: str): Request = native("txn_lookup_node", List("txn", dag, name, node))
  pure def putCommit(operands: List[str], alias: str): List[Request] = List(
    native("object_encode", List("commit").concat(operands).append(alias)),
    native("txn_put_object", List("txn", "commit", alias, alias)))

  pure val graftSetup = List(
    request("p-literal", "d-literal", "double@1", List("--arg", "x=i64:42")),
    work("p-literal", "@p-literal", "t-literal"), inspect("t-literal"),
    request("p-upstream", "d-upstream", "add@1", List("--arg", "a=i64:13", "--arg", "b=i64:29")),
    work("p-upstream", "@p-upstream", "t-upstream"), inspect("t-upstream"),
    request("p-returned", "d-returned", "double@1", List("--arg", "x=from:t-upstream:@t-upstream")),
    work("p-returned", "@p-returned", "t-returned"), inspect("t-returned")
  )
  // Keep the literal attempt and result bodies; replace only the producing request and the result's parent.
  pure val transplant = openTxn("write")
    .concat(atRef("t-literal", "literal-attempt", "literal-attempt-view"))
    .append(parent("literal-attempt-view", "0", "literal-request"))
    .append(parent("literal-attempt-view", "1", "literal-result"))
    .concat(view("commit", "literal-result", "literal-result-view"))
    .concat(view("commit", "literal-request", "literal-request-view"))
    .concat(treeDag("literal-request-view", "literal-request-tree", "literal-request-dag"))
    .append(lookup("literal-request-dag", "construction", "literal-construction"))
    .concat(treeDag("literal-result-view", "literal-result-tree", "literal-result-dag"))
    .append(lookup("literal-result-dag", "get-00", "literal-get"))
    .concat(view("node", "literal-get", "literal-get-view"))
    .append(lookup("literal-get-view", "construction", "getter-construction"))
    .concat(atRef("p-returned", "returned-request", "returned-request-view"))
    .append(parent("returned-request-view", "0", "returned-origin"))
    .concat(treeDag("returned-request-view", "returned-request-tree", "returned-request-dag"))
    .append(lookup("returned-request-dag", "construction", "returned-construction"))
    .concat(putCommit(List("literal-result-view", "returned-request"), "new-result"))
    .concat(putCommit(List("literal-attempt-view", "returned-request", "new-result"), "new-attempt"))
    .append(native("txn_ref_create", List("txn", "grafted-result", "new-result")))
    .append(native("txn_ref_create", List("txn", "grafted-attempt", "new-attempt")))
    .concat(closeTxn("txn_commit"))
  pure val readGraft = openTxn("read")
    .concat(atRef("grafted-attempt", "grafted-attempt-pin", "grafted-attempt-view"))
    .append(parent("grafted-attempt-view", "0", "grafted-attempt-owner"))
    .append(parent("grafted-attempt-view", "1", "grafted-attempt-result"))
    .concat(atRef("grafted-result", "grafted-result-pin", "grafted-result-view"))
    .append(parent("grafted-result-view", "0", "grafted-result-owner"))
    .concat(closeTxn("txn_abort"))
  pure val graft = graftSetup.concat(transplant).concat(readGraft)
    .concat(List(inspect("grafted-attempt"), inspect("t-literal"), inspect("t-returned")))

  type Link = (str, str, str, str, str)
  // pending, decision, attempt, immutable pending receipt, argument for the following link.
  pure val links: List[Link] = List(
    ("p01", "d01", "t01", "@p01", "x=from:t01:@t01"), ("p02", "d02", "t02", "@p02", "x=from:t02:@t02"),
    ("p03", "d03", "t03", "@p03", "x=from:t03:@t03"), ("p04", "d04", "t04", "@p04", "x=from:t04:@t04"),
    ("p05", "d05", "t05", "@p05", "x=from:t05:@t05"), ("p06", "d06", "t06", "@p06", "x=from:t06:@t06"),
    ("p07", "d07", "t07", "@p07", "x=from:t07:@t07"), ("p08", "d08", "t08", "@p08", "x=from:t08:@t08"),
    ("p09", "d09", "t09", "@p09", "x=from:t09:@t09"), ("p10", "d10", "t10", "@p10", "x=from:t10:@t10"),
    ("p11", "d11", "t11", "@p11", "x=from:t11:@t11"), ("p12", "d12", "t12", "@p12", "x=from:t12:@t12"),
    ("p13", "d13", "t13", "@p13", "x=from:t13:@t13"), ("p14", "d14", "t14", "@p14", "x=from:t14:@t14"),
    ("p15", "d15", "t15", "@p15", "x=from:t15:@t15"), ("p16", "d16", "t16", "@p16", "x=from:t16:@t16"),
    ("p17", "d17", "t17", "@p17", "x=from:t17:@t17"), ("p18", "d18", "t18", "@p18", "x=from:t18:@t18"),
    ("p19", "d19", "t19", "@p19", "x=from:t19:@t19"), ("p20", "d20", "t20", "@p20", "x=from:t20:@t20"),
    ("p21", "d21", "t21", "@p21", "x=from:t21:@t21"), ("p22", "d22", "t22", "@p22", "x=from:t22:@t22"),
    ("p23", "d23", "t23", "@p23", "x=from:t23:@t23"), ("p24", "d24", "t24", "@p24", "x=from:t24:@t24"),
    ("p25", "d25", "t25", "@p25", "x=from:t25:@t25"), ("p26", "d26", "t26", "@p26", "x=from:t26:@t26"),
    ("p27", "d27", "t27", "@p27", "x=from:t27:@t27"), ("p28", "d28", "t28", "@p28", "x=from:t28:@t28"),
    ("p29", "d29", "t29", "@p29", "x=from:t29:@t29"), ("p30", "d30", "t30", "@p30", "x=from:t30:@t30"),
    ("p31", "d31", "t31", "@p31", "x=from:t31:@t31"), ("p32", "d32", "t32", "@p32", "x=from:t32:@t32"),
    ("p33", "d33", "t33", "@p33", "x=from:t33:@t33"), ("p34", "d34", "t34", "@p34", "x=from:t34:@t34"),
    ("p35", "d35", "t35", "@p35", "x=from:t35:@t35"), ("p36", "d36", "t36", "@p36", "x=from:t36:@t36"),
    ("p37", "d37", "t37", "@p37", "x=from:t37:@t37"), ("p38", "d38", "t38", "@p38", "x=from:t38:@t38"),
    ("p39", "d39", "t39", "@p39", "x=from:t39:@t39"), ("p40", "d40", "t40", "@p40", "x=from:t40:@t40"),
    ("p41", "d41", "t41", "@p41", "x=from:t41:@t41"), ("p42", "d42", "t42", "@p42", "x=from:t42:@t42"),
    ("p43", "d43", "t43", "@p43", "x=from:t43:@t43"), ("p44", "d44", "t44", "@p44", "x=from:t44:@t44"),
    ("p45", "d45", "t45", "@p45", "x=from:t45:@t45"), ("p46", "d46", "t46", "@p46", "x=from:t46:@t46"),
    ("p47", "d47", "t47", "@p47", "x=from:t47:@t47"), ("p48", "d48", "t48", "@p48", "x=from:t48:@t48"),
    ("p49", "d49", "t49", "@p49", "x=from:t49:@t49"), ("p50", "d50", "t50", "@p50", "x=from:t50:@t50"),
    ("p51", "d51", "t51", "@p51", "x=from:t51:@t51"), ("p52", "d52", "t52", "@p52", "x=from:t52:@t52"),
    ("p53", "d53", "t53", "@p53", "x=from:t53:@t53"), ("p54", "d54", "t54", "@p54", "x=from:t54:@t54"),
    ("p55", "d55", "t55", "@p55", "x=from:t55:@t55"), ("p56", "d56", "t56", "@p56", "x=from:t56:@t56"),
    ("p57", "d57", "t57", "@p57", "x=from:t57:@t57"), ("p58", "d58", "t58", "@p58", "x=from:t58:@t58"),
    ("p59", "d59", "t59", "@p59", "x=from:t59:@t59"), ("p60", "d60", "t60", "@p60", "x=from:t60:@t60"),
    ("p61", "d61", "t61", "@p61", "x=from:t61:@t61"), ("p62", "d62", "t62", "@p62", "x=from:t62:@t62"),
    ("p63", "d63", "t63", "@p63", "x=from:t63:@t63"), ("p64", "d64", "t64", "@p64", "x=from:t64:@t64")
  )
  pure def buildLink(i: int): List[Request] = {
    val link = links[i]
    val arg = if (i == 0) "x=i64:0" else links[i - 1]._5
    List(request(link._1, link._2, "double@1", List("--arg", arg)), work(link._1, link._4, link._3))
  }
  pure def readLink(i: int): List[Request] = {
    val link = links[i]
    atRef(link._3, "attempt-id", "attempt-view").append(parent("attempt-view", "0", "own-request"))
      .append(parent("attempt-view", "1", "own-result"))
      .concat(atRef(link._1, "request-id", "request-view"))
      .concat(if (i == 0) List() else List(parent("request-view", "0", "previous-attempt")))
  }
  pure val buildChain = range(0, links.length()).foldl(List(), (out, i) => out.concat(buildLink(i)))
  pure val nativeChain = openTxn("read")
    .concat(range(0, links.length()).foldl(List(), (out, i) => out.concat(readLink(i))))
    .concat(closeTxn("txn_abort"))
  pure val deep = buildChain.concat(nativeChain).append(inspect(links[links.length() - 1]._3))

  var histories: List[List[Request]]
  action init = histories' = List(graft, deep)
  action step = histories' = histories
}
