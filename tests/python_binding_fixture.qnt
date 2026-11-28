module python_binding_fixture {
  type Request = { op: str, args: List[str] }
  type Value = NoValue | Exact(str) | Saved(str) | SavedPacked(str)
  type Expected = { status: str, error: str, detail: str, shape: List[str], value: Value,
    count: int, items: List[Value], writes: bool, creates: str, onOwner: bool, finalized: List[str] }
  type Check = { request: Request, expect: Expected, save: str }

  pure def mapList(xs: List[a], f: a => b): List[b] = xs.foldl(List(), (out, x) => out.append(f(x)))

  pure val ok: Expected = { status: "ok", error: "", detail: "", shape: List("NoneType"),
    value: NoValue, count: 0, items: List(), writes: false, creates: "", onOwner: true, finalized: List() }
  pure val handle = { ...ok, shape: List("PyCapsule") }
  pure val bytesResult = { ...ok, shape: List("bytes") }
  pure def nativeError(status: str, detail: str): Expected =
    { ...ok, status: status, error: "Error", detail: detail, shape: List() }
  pure def pythonError(error: str, detail: str): Expected =
    { ...ok, status: "python_error", error: error, detail: detail, shape: List() }
  pure def check(op: str, args: List[str], expected: Expected): Check =
    { request: { op: op, args: args }, expect: expected, save: "" }
  pure def save(op: str, args: List[str], expected: Expected, label: str): Check =
    { ...check(op, args, expected), save: label }

  pure def decode(from: str, kind: int, payload: str): Check = check("datum_decode", List(from),
    { ...ok, shape: List("tuple:2", "bytes", "int"), count: kind, value: Exact(payload) })
  pure def members(from: str, shape: List[str], count: int, items: List[Value]): Check =
    check("datum_members", List(from), { ...ok, shape: shape, count: count, items: items })
  pure def writer(repo: str): List[Check] = List(
    check("repo_open", List(repo, "create"), { ...handle, writes: true, creates: repo }),
    check("txn_begin", List(repo, "write", "txn"), handle))
  pure def begin(repo: str, mode: str): Check = check("txn_begin", List(repo, mode, "txn"), handle)
  pure val abort = check("txn_abort", List("txn"), ok)
  pure val commit = check("txn_commit", List("txn"), { ...ok, writes: true })
  pure def close(repo: str): Check = check("repo_close", List(repo), ok)
  pure def putDatum(kind: str, operands: List[str], label: str): List[Check] = List(
    save("datum_encode", List(kind).concat(operands).append(label), bytesResult, label),
    save("txn_put_datum", List("txn", label, label), bytesResult, label))
  pure def putObject(kind: str, operands: List[str], label: str): List[Check] = List(
    check("object_encode", List(kind).concat(operands).append(label), bytesResult),
    save("txn_put_object", List("txn", kind, label, label), bytesResult, label))
  pure def readDatum(id: str): Check = check("txn_get_datum", List("txn", id, "read"),
    { ...bytesResult, value: SavedPacked(id) })
}
