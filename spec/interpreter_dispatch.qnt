module interpreter_dispatch {
  type Request = { op: str, args: List[str] }
  type Reply = { op: str, handle: str, status: str, code: int, detail: str, apiError: bool }
  type Probe = { mode: str, steps: List[Request], replies: List[Reply], bundle: List[str] }
  type CommandAttempt = { fields: List[str], length: int, value: str }
  type Change = { kind: str, key: str, before: str, after: str }
  type NativeAttempt = {
    op: str, args: List[str], status: str, value: str, count: int, items: List[str],
    changes: List[Change], otherChanges: List[Change], detail: str
  }
  type Failure = { kind: str, cause: str, arguments: List[List[str]] }
  type TransactionSlot = { alias: str, handle: str }
  type ProbeEvidence = {
    events: List[Request], commandAttempts: List[CommandAttempt], nativeAttempts: List[NativeAttempt],
    transactionSlots: List[List[TransactionSlot]], bundleItems: List[str], failure: Failure
  }
  type DispatchEvidence = List[ProbeEvidence]

  pure def req(op: str, args: List[str]): Request = { op: op, args: args }
  pure def commands(steps: List[Request]): Probe = { mode: "commands", steps: steps, replies: List(), bundle: List() }
  pure def native(steps: List[Request], replies: List[Reply]): Probe = {
    mode: "native", steps: steps, replies: replies, bundle: List()
  }
  pure def bundle(parts: List[str]): Probe = { mode: "bundle", steps: List(), replies: List(), bundle: parts }

  pure val appendA = req("append_value", List("a"))
  pure val appendB = req("append_value", List("b"))
  pure val read = req("read_value", List())
  pure val commandSteps = List(appendA, appendB, read)
  pure val unknownSteps = List(appendA, req("unknown", List()), read)
  pure val aritySteps = List(appendA, req("append_value", List()), read)

  pure val identifier = "000102030405060708090a0b0c0d0e0f"
  pure val nativeOpen = req("repo_open", List("repo", "create"))
  pure val nativeBegin = req("txn_begin", List("repo", "write", "writer"))
  pure val nativeWrite = req("txn_ref_create", List("writer", "main", identifier))
  pure val nativeCommit = req("txn_commit", List("writer"))
  pure val nativeAbort = req("txn_abort", List("writer"))
  pure val nativeClose = req("repo_close", List("repo"))
  pure val nativeSteps = List(nativeOpen, nativeBegin, nativeWrite, nativeCommit, nativeBegin, nativeAbort, nativeClose)
  pure def returns(op: str, handle: str): Reply = {
    op: op, handle: handle, status: "", code: 0, detail: "", apiError: false
  }
  pure def raises(op: str, detail: str, isAPI: bool): Reply = {
    op: op, handle: "", status: "invalid_state", code: 0, detail: detail, apiError: isAPI
  }
  pure val nativeReplies = List(
    returns("repo_open", "repo"), returns("txn_begin", "first"),
    raises("txn_ref_create", "ref already exists", true), raises("txn_commit", "transaction poisoned", true),
    returns("txn_begin", "second"), returns("txn_abort", ""), returns("repo_close", "")
  )

  // Independent wire bytes: little-endian envelope, commit frame, one-byte payload.
  pure val headerPrefix = List("444d4c42", "01000000", identifier)
  pure val header = headerPrefix.append("01000000")
  pure val frameHeader = List("0600", "0000", "01000000", identifier)
  pure val validBundle = header.concat(frameHeader).append("78")

  var requests: List[Probe]
  action init = requests' = List(
    commands(commandSteps), commands(unknownSteps), commands(aritySteps),
    native(nativeSteps, nativeReplies),
    native(List(nativeOpen), List(raises("repo_open", "unexpected binding failure", false))),
    bundle(validBundle), bundle(headerPrefix.append("010000")),
    bundle(header.concat(List("0600", "0000", "01000000", "0001"))),
    bundle(header.concat(frameHeader)), bundle(validBundle.append("78"))
  )
  action step = requests' = requests

  pure val empty: ProbeEvidence = {
    events: List(), commandAttempts: List(), nativeAttempts: List(), transactionSlots: List(),
    bundleItems: List(), failure: { kind: "", cause: "", arguments: List() }
  }
  pure def enter(history: str): Request = req("enter", List(history))
  pure def close(history: str): Request = req("close", List(history))
  pure val commandSuccess = {
    ...empty,
    events: List(enter("history-1")).concat(commandSteps).append(close("history-1")),
    commandAttempts: List(
      { fields: List("length"), length: 1, value: "" },
      { fields: List("length"), length: 2, value: "" },
      { fields: List("value"), length: 0, value: "b" }
    )
  }

  pure def containsWords(words: List[str], fragment: List[str]): bool = words.indices().exists(i =>
    if (i + fragment.length() <= words.length()) words.slice(i, i + fragment.length()) == fragment else false)
  pure def rejected(actual: ProbeEvidence, events: List[Request], cause: str, fragments: List[List[str]]): bool = {
    val failure = actual.failure
    if (failure.arguments.length() != 1) false
    else all {
      actual == { ...empty, events: events, failure: failure },
      failure.kind == "ValueError",
      failure.cause == cause,
      fragments.indices().forall(i => containsWords(failure.arguments[0], fragments[i]))
    }
  }
  pure def badCommand(actual: ProbeEvidence, history: str, context: str, cause: str, fragment: List[str]): bool =
    rejected(actual, List(enter(history), appendA, close(history)), cause,
      List(List(context, "step", "2:"), fragment))

  pure val openCall = req("repo_open", List("str:<history>/repo", "bool:True"))
  pure val beginCall = req("txn_begin", List("handle:repo", "int:2"))
  pure val scan = req("scan_inventory", List("str:scanner", "path:<history>/repo"))
  pure val nativeEvents = List(
    openCall, beginCall, req("txn_ref_create", List("handle:first", "bytes:6d61696e", "bytes:000102030405060708090a0b0c0d0e0f")),
    req("txn_commit", List("handle:first")), beginCall, req("txn_abort", List("handle:second")),
    req("repo_close", List("handle:repo"))
  ).foldl(List(), (out, event) => out.append(event).append(scan))
  pure def attempt(request: Request, status: str, detail: str): NativeAttempt = {
    op: request.op, args: request.args, status: status, value: "", count: 0, items: List(),
    changes: List(), otherChanges: List(), detail: detail
  }
  pure val firstWriter = List({ alias: "writer", handle: "handle:first" })
  pure val secondWriter = List({ alias: "writer", handle: "handle:second" })
  pure val nativeSuccess = {
    ...empty, events: nativeEvents,
    nativeAttempts: List(
      attempt(nativeOpen, "ok", ""), attempt(nativeBegin, "ok", ""),
      attempt(nativeWrite, "invalid_state", "ref already exists"),
      attempt(nativeCommit, "invalid_state", "transaction poisoned"),
      attempt(nativeBegin, "ok", ""), attempt(nativeAbort, "ok", ""), attempt(nativeClose, "ok", "")
    ),
    transactionSlots: List(List(), firstWriter, firstWriter, List(), secondWriter, List(), List())
  }
  pure val bindingFailure = {
    ...empty, events: List(openCall),
    failure: { kind: "RuntimeError", cause: "", arguments: List(List("invalid_state"), List("0"), List("unexpected", "binding", "failure")) }
  }

  pure def dispatchFailures(evidence: DispatchEvidence): List[str] =
    if (evidence.length() != 10) List("probe_count")
    else List(
      ("ordered_dispatch", evidence[0] == commandSuccess),
      ("unknown_command", badCommand(evidence[1], "history-2", "history-2,", "", List("unknown", "operation"))),
      ("command_arity", badCommand(evidence[2], "history-3", "history-3,", "TypeError", List("missing", "1", "required"))),
      ("native_dispatch", evidence[3] == nativeSuccess),
      ("binding_exception", evidence[4] == bindingFailure),
      ("valid_bundle", evidence[5] == { ...empty, bundleItems: List(identifier, "6", identifier, "78") }),
      ("short_header", rejected(evidence[6], List(), "", List(List("length")))),
      ("short_frame_header", rejected(evidence[7], List(), "", List(List("frame", "header")))),
      ("short_payload", rejected(evidence[8], List(), "", List(List("invalid", "exported", "bundle", "frame")))),
      ("trailing_bytes", rejected(evidence[9], List(), "", List(List("trailing"))))
    ).foldl(List(), (out, check) => if (check._2) out else out.append(check._1))
}
