module recorded_calls_python_rules {
  import recorded_calls_python_histories as h from "./recorded_calls_python_histories"
  import recorded_calls_rules as r from "./recorded_calls_rules"

  type Attempt = (r::Attempt)
  type Observation = { scenario: int, attempts: List[Attempt] }

  pure def rejection(a: Attempt, wanted: h::Rejection, existing: bool): str =
    if (not(r::sameRequest(a, wanted.req))) "wrong_step"
    else if (a.code != 1 or a.errorType != "ValueError" or a.commit != "") "wrong_python_rejection"
    else if (a.stderr != wanted.diagnostic) "wrong_python_diagnostic"
    else if (a.pathUses != 0) "invalid_python_input_reached_repository"
    else if (a.repoExisted != existing or a.repoExists != existing or not(a.unchanged)) "storage_changed"
    else "rejected"

  pure def fixture(rows: List[Attempt], story: h::Story, i: int): str = {
    val a = rows[i]
    val req = story.setup[i]
    val producer = rows[0].commit
    val correct = if (i == 0) not(a.repoExisted) and a.repoExists
      else if (story == h::knowledge) {
        if (i == 1) a.expectedCommit == ""
        else if (i == 2) a.expectedCommit == producer and a.expectedIntent == rows[1].commit
        else a.unchanged and a.commit == rows[2].commit and a.decision.intent == rows[1].commit and
          a.decision.route == "execute-fresh" and a.decision.planRef == "pending"
      } else {
        if (i == 1) a.expectedCommit == producer
        else if (i == 2) a.expectedCommit == rows[1].commit and a.unchanged and a.bundlePresent
        else if (i == 3) a.commit == rows[2].commit
        else a.unchanged and a.commit == rows[3].commit and a.requestCommit == a.commit and
          a.producerCommit == producer and a.requestFactor == h::overflowFactor
      }
    if (r::writeVerdict(a, req) != "recorded" or not(a.repoExists and correct)) "wrong_python_fixture"
    else if (req.op == "inspect") "inspected" else "recorded"
  }

  pure def historyVerdicts(row: Observation): List[str] = {
    if (not(h::stories.indices().contains(row.scenario))) List("unknown_history")
    else {
      val story = h::stories[row.scenario]
      val setup = story.setup.length()
      val rows = row.attempts
      if (rows.length() != setup + story.rejected.length()) List("missing_steps")
      else range(0, rows.length()).foldl(List(), (out, i) => out.append(
        if (i < setup) fixture(rows, story, i) else rejection(rows[i], story.rejected[i - setup], setup != 0)))
    }
  }
  pure val expected = h::stories.foldl(List(), (out, story) => out.append(
    story.rejected.foldl(story.setup.foldl(List(), (steps, req) => steps.append(
      if (req.op == "inspect") "inspected" else "recorded")), (steps, _) => steps.append("rejected"))))
  pure def verdictAccepted(verdict: str): bool = Set("recorded", "inspected", "rejected").contains(verdict)
  pure def coveragePass(rows: List[Observation], verdicts: List[List[str]]): bool =
    rows.length() == expected.length() and verdicts == expected

  pure val shortKnowledge = h::knowledge.rejected[0]
  pure val rejected = { ...r::recorded, op: shortKnowledge.req.op, args: shortKnowledge.req.args, code: 1,
    errorType: "ValueError", stderr: shortKnowledge.diagnostic, pathUses: 0, commit: "",
    repoExisted: true, repoExists: true, unchanged: true }
  pure val controlsPass = all {
    rejection(rejected, shortKnowledge, true) == "rejected",
    rejection({ ...rejected, errorType: "TypeError" }, shortKnowledge, true) == "wrong_python_rejection",
    rejection({ ...rejected, stderr: "knowledge commit must be a 32-digit hexadecimal ID" }, shortKnowledge, true)
      == "wrong_python_diagnostic",
    rejection({ ...rejected, pathUses: 1 }, shortKnowledge, true) == "invalid_python_input_reached_repository",
    rejection({ ...rejected, unchanged: false }, shortKnowledge, true) == "storage_changed",
    rejection(rejected, shortKnowledge, false) == "storage_changed"
  }
}
