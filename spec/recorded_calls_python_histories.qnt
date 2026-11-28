module recorded_calls_python_histories {
  import recorded_calls_fixtures.* from "./recorded_calls_fixtures"

  type Rejection = { req: Request, diagnostic: str }
  type Story = { setup: List[Request], rejected: List[Rejection] }
  pure def reject(op: str, operands: List[str], diagnostic: str): Rejection =
    { req: source("python_call", List(op).concat(operands)), diagnostic: diagnostic }
  pure def beforeOpen(rejected: List[Rejection]): Story = { setup: List(), rejected: rejected }
  pure val zero = "hex:00000000000000000000000000000000"
  pure val shortId = "hex:73686f7274"
  pure val wrongIdType = "bytes-subclass:00000000000000000000000000000000"
  pure val invalidIds = List("text:00000000000000000000000000000000", "bytearray:00000000000000000000000000000000",
    wrongIdType, "hex:787878787878787878787878787878", "hex:7878787878787878787878787878787878")
  pure val longRef =
    "bytes:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  pure val planRefError = "plan ref must be a valid ASCII ref name in bytes"
  pure val planIdError = "plan commit must be a 16-byte ID"
  pure val wrongRefTypes = List("text:ref", "bytearray:726566", "bytes-subclass:726566")
  pure val wrongRefNames = List("bytes:", "bytes:-ref", "bytes:ref/name", "hex:72c3a966", "hex:7265660a", longRef)
  pure val aliases = List(List("bytes:main", "bytes:history", "bytes:dest"),
    List("bytes:plan", "bytes:main", "bytes:dest"), List("bytes:plan", "bytes:history", "bytes:main"),
    List("bytes:plan", "bytes:plan", "bytes:dest"), List("bytes:plan", "bytes:history", "bytes:history"),
    List("bytes:plan", "bytes:history", "bytes:plan"))

  pure def reuse(op: str, outputError: str, distinctError: str): Story = {
    val refErrors = List(planRefError, "result ref must be a valid ASCII ref name in bytes", outputError)
    val idErrors = List(planIdError, "result commit must be a 16-byte ID")
    val good = List("bytes:plan", zero, "bytes:history", zero, "bytes:dest")
    val refs = range(0, refErrors.length()).foldl(List(), (out, slot) =>
      wrongRefTypes.concat(wrongRefNames).foldl(out, (cases, invalid) =>
        cases.append(reject(op, good.replaceAt(2 * slot, invalid), refErrors[slot]))))
    val aliasCases = aliases.foldl(refs, (out, names) =>
      out.append(reject(op, List(names[0], zero, names[1], zero, names[2]), distinctError)))
    beforeOpen(range(0, idErrors.length()).foldl(aliasCases, (out, slot) =>
      invalidIds.foldl(out, (cases, invalid) =>
        cases.append(reject(op, good.replaceAt(2 * slot + 1, invalid), idErrors[slot])))))
  }

  pure val adoption = {
    val op = "adopt_scale_attempt"
    val good = List("bytes:chosen", zero, "bytes:incoming", zero, "bytes:next")
    val invalid = List((1, shortId, "basis selection commit must be a 16-byte ID"), (3, shortId, "attempt commit must be a 16-byte ID"),
      (0, "bytes:-", "basis ref must be a valid ASCII ref name in bytes"),
      (2, "text:incoming", "attempt ref must be a valid ASCII ref name in bytes"),
      (4, "bytes:-", "selection ref must be a valid ASCII ref name in bytes"))
    val distinct = List((2, "bytes:chosen"), (4, "bytes:chosen"), (4, "bytes:incoming"),
      (0, "bytes:main"), (2, "bytes:main"), (4, "bytes:main"))
    beforeOpen(distinct.foldl(invalid.foldl(List(), (out, x) => out.append(reject(op, good.replaceAt(x._1, x._2), x._3))),
      (out, x) => out.append(reject(op, good.replaceAt(x._1, x._2), "basis, attempt, selection, and main refs must be distinct"))))
  }

  pure val abandon = {
    val op = "abandon_scale_request"
    val badPins = List("text:plan", "bytearray:706c616e", "bytes-subclass:706c616e",
      "bytes:", "bytes:-plan", "bytes:plan/name", "hex:706cc3a16e", "hex:706c616e0a",
      "bytes:ppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppp")
    val pins = badPins.foldl(List(), (out, pin) => out.append(reject(op, List(pin, zero), planRefError)))
      .append(reject(op, List("bytes:main", zero), "plan ref must differ from main"))
    beforeOpen(invalidIds.foldl(pins, (out, id) => out.append(reject(op, List("bytes:plan", id), planIdError))))
  }

  pure val receipt = {
    val op = "publish_requested_scale"
    val good = List("bytes:plan", zero, "bytes:returned", zero, "keyword:receipt_ref", "bytes:ack")
    val names = wrongRefNames.concat(List("bytes:.ref", "bytes:_ref"))
    val slots = List((0, planRefError), (2, "staging ref must be a valid ASCII ref name in bytes"),
      (5, "receipt ref must be a valid ASCII ref name in bytes"))
    beforeOpen(slots.foldl(List(), (out, slot) => {
      val typeError = if (slot._1 == 5) slot._2 else "plan and staging refs must be bytes"
      val badTypes = wrongRefTypes.foldl(out, (cases, bad) =>
        cases.append(reject(op, good.replaceAt(slot._1, bad), typeError)))
      names.foldl(badTypes, (cases, bad) => cases.append(reject(op, good.replaceAt(slot._1, bad), slot._2)))
    }))
  }

  pure val publish = {
    val op = "publish_scale"
    val good = List("bytes:returned", zero, zero, "int:3", "none:")
    val exactTypes = List((0, "bytes-subclass:6d61696e", "staging ref must be bytes"),
      (1, wrongIdType, "result commit must be a 16-byte ID"), (2, wrongIdType, "producer commit must be a 16-byte ID"),
      (4, wrongIdType, "expected main commit must be a 16-byte ID"))
    val wrongFactors = List("bool:true", "int-subclass:3", "text:3", "int:-9223372036854775809", "int:9223372036854775808")
    val typeCases = exactTypes.foldl(List(), (out, x) => out.append(reject(op, good.replaceAt(x._1, x._2), x._3)))
    beforeOpen(wrongFactors.foldl(typeCases, (out, x) =>
      out.append(reject(op, good.replaceAt(3, x), "expected factor is not a signed 64-bit integer"))))
  }

  pure val producer = source("record_sum", List("producer", "7", "5"))
  pure val knowledge: Story = {
    setup: List(producer,
      source("define_scale_intent", List("basis", "example.scale@1", "execute-by-default", "slot-v1", "slot-v2")),
      source("request_intent_scale", List("producer", "producer", "basis", "basis", "pending", "decision", "3",
        "default", "default", "-")), source("inspect", List("decision"))),
    rejected: List(reject("inspect", List("bytes:decision", "keyword:knowledge_commit", "hex:696e76616c6964"),
      "knowledge commit must be a 16-byte ID"))
  }
  pure val overflowFactor = 4611686018427387904
  pure val attempt: Story = {
    setup: List(producer,
      source("request_scale", List("producer", "producer", "plan", "4611686018427387904")),
      source("export_request", List("plan", "plan", "request.dmlb")),
      source("stage_input", List("incoming", "request.dmlb")), source("inspect", List("incoming"))),
    rejected: List(
      reject("work_scale_attempt", List("bytes:incoming", "id:plan", "bytes:attempt", "text:a0000000-0000-4000-8000-000000000001"),
        "attempt ID must be a canonical lowercase UUIDv4 in bytes"),
      reject("work_scale_attempt", List("bytes:incoming", shortId, "bytes:attempt", "bytes:a0000000-0000-4000-8000-000000000001"),
        "request commit must be a 16-byte ID"))
  }

  pure val stories = List(
    reuse("stage_reused_scale", "destination ref must be a valid ASCII ref name in bytes",
      "plan, result, destination, and main refs must be distinct"),
    reuse("publish_reused_scale", "reuse ref must be a valid ASCII ref name in bytes",
      "plan, result, reuse, and main refs must be distinct"),
    adoption, abandon, receipt, publish, knowledge, attempt)
  pure def requests(story: Story): List[Request] =
    story.rejected.foldl(story.setup, (out, row) => out.append(row.req))
  var histories: List[List[Request]]
  action init = histories' = stories.foldl(List(), (out, story) => out.append(requests(story)))
  action step = histories' = histories
}
