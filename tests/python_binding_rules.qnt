module python_binding_rules {
  import python_binding_fixture.* from "./python_binding_fixture"
  import python_binding_histories as h from "./python_binding_histories"

  type Change = { kind: str, key: str, before: str, after: str }
  type Attempt = { op: str, args: List[str], status: str, value: str, count: int, items: List[str],
    changes: List[Change], otherChanges: List[Change], detail: str, errorClass: str, errorTypes: List[str],
    nativeCode: int, resultTypes: List[str], paths: List[str] }
  type Observation = { attempts: List[Attempt] }
  type Values = (bool, str) -> str
  type State = { saved: Values, paths: Set[str], verdicts: List[str] }

  pure def request(a: Attempt): Request = { op: a.op, args: a.args }
  pure def equalSaved(saved: Values, key: (bool, str), value: str): bool =
    saved.keys().contains(key) and value == saved.get(key)
  pure def matches(saved: Values, value: str, expected: Value): bool = match expected {
    | NoValue => true
    | Exact(expectedValue) => value == expectedValue
    | Saved(key) => equalSaved(saved, (false, key), value)
    | SavedPacked(key) => equalSaved(saved, (true, key), value)
  }
  pure def verdict(a: Attempt, expected: Expected, saved: Values, paths: Set[str]): str = {
    val errorTypes = if (expected.error == "") List() else if (expected.error == "Error") List("str", "int", "str") else List("str")
    if (a.errorClass != expected.error or a.errorTypes != errorTypes or a.status != expected.status)
      "wrong_python_boundary"
    else if (expected.detail != "" and a.detail != expected.detail) "wrong_diagnostic"
    else if (a.resultTypes != expected.shape or a.count != expected.count or not(matches(saved, a.value, expected.value)))
      "wrong_result"
    else if (a.op == "datum_members" and (a.items.length() != expected.items.length() or
      not(expected.items.indices().forall(i => matches(saved, a.items[i], expected.items[i]))))) "wrong_members"
    else if (a.paths.length() != paths.size() or a.paths.foldl(Set(), (out, path) => out.union(Set(path))) != paths)
      "wrong_paths"
    else if ((a.changes.length() > 0) != expected.writes or a.otherChanges.length() != 0) "wrong_inventory"
    else "ok"
  }
  pure def requests(history: List[Check]): List[Request] = history.mapList(c => c.request)
  pure def historyVerdicts(row: Observation): List[str] = {
    val found = h::cases.select(history => requests(history) == row.attempts.mapList(request))
    if (found.length() != 1) row.attempts.mapList(_ => "unknown_history") else {
      val history = found[0]
      val initial: State = { saved: Map(), paths: Set(), verdicts: List() }
      range(0, history.length()).foldl(initial, (out, i) => {
        val a = row.attempts[i]
        val c = history[i]
        val paths = if (c.expect.creates == "") out.paths else out.paths.union(Set(c.expect.creates))
        val checked = verdict(a, c.expect, out.saved, paths)
        val result = if (checked == "ok" and c.save != "" and a.value == "") "missing_saved_value" else checked
        { saved: if (c.save == "" or result != "ok") out.saved else out.saved.put((a.op == "datum_encode", c.save), a.value),
          paths: paths, verdicts: out.verdicts.append(result) }
      }).verdicts
    }
  }
  pure def verdictAccepted(v: str): bool = v == "ok"
  pure def coveragePass(rows: List[Observation], results: List[List[str]]): bool =
    rows.foldl(List(), (out, row) => out.append(row.attempts.mapList(request))) ==
      h::cases.foldl(List(), (out, history) => out.append(requests(history))) and
      results.indices().forall(i => results[i].length() == h::cases[i].length() and
        results[i].indices().forall(j => verdictAccepted(results[i][j])))

  pure val missing: Attempt = { op: "repo_open", args: List("source", "existing"), status: "not_found", value: "",
    count: 0, items: List(), changes: List(), otherChanges: List(), detail: "repository path does not exist",
    errorClass: "Error", errorTypes: List("str", "int", "str"), nativeCode: 2, resultTypes: List(), paths: List() }
  pure val missingRule = h::repository[0].expect
  pure val controlsPass = and {
    verdict(missing, missingRule, Map(), Set()) == "ok",
    verdict({ ...missing, errorTypes: List("str", "bool", "str") }, missingRule, Map(), Set()) == "wrong_python_boundary",
    verdict({ ...missing, paths: List("source") }, missingRule, Map(), Set()) == "wrong_paths",
    verdict({ ...missing, detail: "other not-found error" }, missingRule, Map(), Set()) == "wrong_diagnostic"
  }
}
