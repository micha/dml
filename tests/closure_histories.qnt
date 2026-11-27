module closure_histories {
  import workflow_native_fixture as n from "./workflow_native_fixture"
  type Request = { op: str, args: List[str] }
  pure def source(op: str, args: List[str]): Request = { op: op, args: List("source").concat(args) }
  pure val pins = Map(
    "c1" -> "@c1", "c2" -> "@c2", "c3" -> "@c3", "q1" -> "@q1", "q3" -> "@q3", "q5" -> "@q5", "q6" -> "@q6",
    "d1" -> "@d1", "d2" -> "@d2", "d4" -> "@d4", "d6" -> "@d6",
    "t1" -> "@t1", "t3" -> "@t3", "t5" -> "@t5", "t6" -> "@t6",
    "subtotal-q" -> "@subtotal-q", "product-q" -> "@product-q",
    "snapshot-hit" -> "@snapshot-hit", "snapshot-fresh" -> "@snapshot-fresh", "source-graft" -> "@source-graft",
    "binding-graft" -> "@binding-graft", "key-graft" -> "@key-graft", "original-graft" -> "@original-graft")
  pure val ids = Map(
    "1" -> "12345678-abcd-4abc-8abc-123456789ab1", "2" -> "12345678-abcd-4abc-8abc-123456789ab2",
    "3" -> "12345678-abcd-4abc-8abc-123456789ab3", "4" -> "12345678-abcd-4abc-8abc-123456789ab4",
    "5" -> "12345678-abcd-4abc-8abc-123456789ab5", "6" -> "12345678-abcd-4abc-8abc-123456789ab6",
    "7" -> "12345678-abcd-4abc-8abc-123456789ab7", "8" -> "12345678-abcd-4abc-8abc-123456789ab8")
  pure def pin(ref: str): str = pins.get(ref)
  pure def uuid(n: str): str = ids.get(n)
  pure def defaults(ref: str, version: str, scale: str, origin: str, expected: str): Request =
    source("defaults", List(ref, version, scale, origin)
      .concat(if (expected == "") List() else List("--expected", expected)))
  pure def capture(defaultsRef: str, expected: str, output: str): Request =
    source("capture", List(defaultsRef, expected, output))
  pure def request(c: str, expected: str, q: str, d: str, a: str, b: str, n: str, selection: List[str]): Request =
    source("request", List(c, expected, q, d, a, b, "--invocation", uuid(n)).concat(selection))
  pure def fresh(c: str, q: str, d: str, n: str): Request =
    request(c, pin(c), q, d, "13", "29", n, List())
  pure def selectionArgs(mode: str, ref: str, expected: str): List[str] =
    List("--mode", mode, "--selected-ref", ref, "--selected", expected)
  pure def require(c: str, q: str, d: str, n: str): Request =
    request(c, pin(c), q, d, "13", "29", n, selectionArgs("require-selected", "t1", "@t1"))
  pure def work(q: str, t: str, n: str): Request =
    source("work", List(q, pin(q), t, "--attempt-id", uuid(n)))
  pure def inspect(repo: str, ref: str): Request = { op: "inspect", args: List(repo, ref, "--expected", pin(ref)) }
  pure def replicate(repo: str, ref: str, output: str): Request = { op: "replicate", args: List(repo, ref, output) }
  pure def graft(repo: str, kind: str, fromRef: str, alternate: str, output: str): Request =
    { op: "graft", args: List(repo, kind, fromRef, alternate, output) }

  pure val maxI64Arg = "9223372036854775807"

  // t1 is the first successful attempt ref. No later work changes it. The
  // first six requests yield four attempts and eight trace positions.
  // The two final requests are left pending by overflow.
  pure val story: List[Request] = List(
    defaults("defaults", "1", "2", "origin-a", ""),                             // 0
    capture("defaults", "@defaults", "c1"),                                      // 1
    fresh("c1", "q1", "d1", "1"),                                                // 2
    inspect("source", "d1"),                                                      // 3
    work("q1", "t1", "1"),                                                        // 4
    inspect("source", "t1"),                                                      // 5
    defaults("defaults", "2", "3", "origin-c", "@defaults"),                    // 6
    capture("defaults", "@initial-defaults", "stale-c"),                          // 7 stale defaults
    capture("defaults", "@defaults", "c3"),                                      // 8
    require("c1", "unused2", "d2", "2"),                                        // 9
    inspect("source", "d2"),                                                      // 10
    fresh("c1", "q3", "d3", "3"),                                                // 11
    work("q3", "t3", "3"),                                                        // 12
    inspect("source", "t3"),                                                      // 13
    defaults("equivalent", "2", "2", "origin-b", ""),                           // 14
    capture("equivalent", "@equivalent", "c1"),                                   // 15 late capture
    capture("equivalent", "@equivalent", "c2"),                                   // 16
    request("c2", "@c1", "bad-q", "bad-d", "13", "29", "7", List()),              // 17 stale closure
    request("c2", "@c2", "bad-q", "bad-d", "13", "29", "7",
      selectionArgs("try-selected", "t1", "@t3")),                                       // 18 stale selection
    request("c1", "@c1", "bad-q", "bad-d", "29", "13", "7",
      selectionArgs("require-selected", "t1", "@t1")),                             // 19 different full MAP, equal sum
    require("c1", "bad-q", "bad-d", "1"),                                       // 20 would reuse own Q
    require("c2", "bad-q", "d2", "7"),                                          // 21 late hit
    require("c2", "unused4", "d4", "4"),                                        // 22
    inspect("source", "d4"),                                                      // 23
    fresh("c2", "q5", "d5", "5"),                                                // 24
    work("q5", "t3", "5"),                                                        // 25 occupied attempt ref
    work("q5", "t5", "5"),                                                        // 26 retry with the same attempt ID
    inspect("source", "t5"),                                                      // 27
    require("c3", "bad-q", "bad-d", "7"),                                       // 28 changed scale, require miss
    request("c3", "@c3", "q6", "d6", "13", "29", "6",
      selectionArgs("try-selected", "t1", "@t1")),                                // 29
    inspect("source", "d6"),                                                      // 30
    work("q6", "t6", "6"),                                                        // 31
    inspect("source", "t6"),                                                      // 32
    graft("source", "selection", "t1", "c2", "poison"),                         // 33
    request("c3", "@c3", "bad-q", "bad-d", "13", "29", "7",
      selectionArgs("try-selected", "poison", "@poison")),                        // 34 validate original even on miss
    request("c1", "@c1", "subtotal-q", "subtotal-d", maxI64Arg, "1", "7", List()),  // 35
    work("subtotal-q", "overflow-attempt", "7"),                                  // 36 subtotal overflow
    request("c1", "@c1", "product-q", "product-d", maxI64Arg, "0", "8", List()),    // 37
    work("product-q", "overflow-attempt", "7"),                                   // 38 product overflow
    replicate("hit", "d4", "snapshot-hit"),                                      // 39
    replicate("miss", "t6", "snapshot-fresh"),                                   // 40
    source("retire", List()),                                                     // 41
    inspect("hit", "snapshot-hit"),                                               // 42
    inspect("miss", "snapshot-fresh"),                                            // 43
    graft("hit", "source", "snapshot-hit", "", "source-graft"),                   // 44 equal scale, wrong origin
    inspect("hit", "source-graft"),                                               // 45
    graft("hit", "binding", "snapshot-hit", "", "binding-graft"),                 // 46 equivalent getter, wrong binding
    inspect("hit", "binding-graft"),                                              // 47
    graft("hit", "key", "snapshot-hit", "", "key-graft"),                         // 48 false computational key
    inspect("hit", "key-graft"),                                                  // 49
    graft("hit", "original", "snapshot-hit", "", "original-graft"),               // 50 poison only the producing closure
    inspect("hit", "original-graft")                                              // 51
  )

  pure val overrideBuild = n::open("write")
    .append(n::readRef("q1", "genuine-q"))
    .concat(n::snapshot("genuine-q", "genuine-q-commit", "genuine-q-dag"))
    .append(n::parent("genuine-q-commit", "0", "captured-closure"))
    .concat(n::target("genuine-q-dag", "inputs", "genuine-inputs"))
    .concat(n::target("genuine-inputs", "source-00", "source-a"))
    .concat(n::target("genuine-inputs", "source-01", "source-b"))
    .concat(n::target("genuine-inputs", "key-00", "arg-a-datum"))
    .concat(n::target("genuine-inputs", "key-01", "arg-b-datum"))
    .concat(n::target("source-a", "value", "literal-a-datum"))
    .concat(n::target("source-b", "value", "literal-b-datum"))
    .concat(n::literal("i64", "3", "scale-value"))
    .append(n::lookup("source-a", "role", "literal-role"))
    .concat(n::putObject("dag", List("scale-value", "value", "scale-value", "role", "literal-role"), "scale-source"))
    .concat(n::target("scale-source", "value", "scale-value-datum"))
    .concat(n::link("scale-source", "scale-link"))
    .concat(n::literal("string", "scale", "scale-key"))
    .append(n::step("datum_encode", List("map", "arg-a-datum", "literal-a-datum", "arg-b-datum", "literal-b-datum",
      "literal-datum", "scale-value-datum", "override-map")))
    .append(n::step("txn_put_datum", List("snapshot", "override-map", "override-map")))
    .concat(n::putObject("node", List("literal", "override-map"), "override-map-node"))
    .concat(List("role", "key-00", "source-00", "key-01", "source-01").foldl(List(), (out, name) =>
      out.append(n::lookup("genuine-inputs", name, name))))
    .concat(n::putObject("dag", List("override-map-node", "value", "override-map-node", "role", "role",
      "key-00", "key-00", "source-00", "source-00", "key-01", "key-01", "source-01", "source-01",
      "key-02", "scale-key", "source-02", "scale-link"), "override-inputs"))
    .concat(n::link("override-inputs", "override-inputs-link"))
    .concat(n::patchDag("genuine-q-dag", "func", List("func", "invocation", "closure", "inputs"),
      "inputs", "override-inputs-link", "override-q-dag"))
    .concat(n::publish("closure-example-request-v1", "override-q-dag", List("captured-closure"), "override-q"))
    .append(n::pin("override-q", "override-q")).concat(n::close("txn_commit"))

  pure val overrideRead = n::open("read")
    .append(n::readRef("override-q", "stored-override-q"))
    .concat(n::snapshot("stored-override-q", "stored-override-commit", "stored-override-dag"))
    .append(n::parent("stored-override-commit", "0", "stored-override-closure"))
    .concat(n::target("stored-override-dag", "inputs", "stored-override-inputs"))
    .concat(n::target("stored-override-inputs", "value", "stored-override-map"))
    .concat(n::target("stored-override-inputs", "key-02", "stored-scale-key"))
    .concat(n::readDatum("stored-scale-key", "stored-scale-key-bytes"))
    .concat(n::target("stored-override-inputs", "source-02", "stored-scale-source"))
    .concat(n::target("stored-scale-source", "value", "stored-scale-value"))
    .concat(n::readDatum("stored-scale-value", "stored-scale-value-bytes"))
    .concat(n::close("txn_abort"))

  // Copy the valid v2 trace into the v1 return. The request / closure, inputs,
  // returned literal and attempt identity still come from the original v1 run.
  pure val getterBuild = n::open("write")
    .append(n::readRef("t1", "old-t"))
    .append(n::readRef("t6", "alternate-t"))
    .concat(n::snapshot("old-t", "old-t-commit", "old-t-dag"))
    .append(n::parent("old-t-commit", "1", "old-r"))
    .concat(n::snapshot("old-r", "old-r-commit", "old-r-dag"))
    .concat(n::snapshot("alternate-t", "alternate-t-commit", "alternate-t-dag"))
    .append(n::parent("alternate-t-commit", "1", "alternate-r"))
    .concat(n::snapshot("alternate-r", "alternate-r-commit", "alternate-r-dag"))
    .append(n::lookup("alternate-r-dag", "trace", "v2-trace-node"))
    .concat(n::patchDag("old-r-dag", "value", List("role", "value", "returned", "trace", "inputs"),
      "trace", "v2-trace-node", "grafted-return"))
    .concat(n::publish("closure-example-result-v1", "grafted-return", List("genuine-q"), "grafted-result"))
    .concat(n::publish("closure-example-attempt-v1", "old-t-dag", List("genuine-q", "grafted-result"), "grafted-attempt"))
    .append(n::pin("getter-poison", "grafted-attempt")).concat(n::close("txn_commit"))

  pure val getterRead = n::open("read")
    .append(n::readRef("getter-poison", "stored-grafted-attempt"))
    .concat(n::snapshot("stored-grafted-attempt", "stored-graft-commit", "stored-graft-dag"))
    .append(n::parent("stored-graft-commit", "0", "getter-owner"))
    .append(n::parent("stored-graft-commit", "1", "getter-result"))
    .concat(n::snapshot("getter-result", "stored-return-commit", "stored-return-dag"))
    .append(n::parent("stored-return-commit", "0", "getter-result-owner"))
    .concat(n::target("stored-return-dag", "value", "stored-result-value"))
    .concat(n::readDatum("stored-result-value", "original-scale-result"))
    .concat(n::target("stored-return-dag", "inputs", "stored-result-inputs"))
    .concat(n::targetVia("stored-return-dag", "trace", "stored-trace-node", "getter-trace"))
    .concat(n::target("getter-trace", "call-00", "stored-v2-a"))
    .concat(n::target("getter-trace", "call-01", "stored-v2-b"))
    .concat(n::target("stored-v2-a", "binding", "stored-v2-binding-a"))
    .concat(n::target("stored-v2-b", "binding", "stored-v2-binding-b"))
    .concat(n::close("txn_abort"))

  pure val overrideReject = 9 + overrideBuild.length() + overrideRead.length()
  pure val getterReject = overrideReject + 4 + getterBuild.length() + getterRead.length()
  pure val forgeryStory = story.slice(0, 9).concat(overrideBuild).concat(overrideRead)
    .append(source("work", List("override-q", "native:stored-override-q", "bad-attempt", "--attempt-id", uuid("2"))))
    .append(story[29]).append(story[31]).append(story[32])
    .concat(getterBuild).concat(getterRead)
    .append(request("c3", "@c3", "miss-q", "miss-d", "13", "29", "2",
      selectionArgs("try-selected", "getter-poison", "native:stored-grafted-attempt")))
    .append(request("c3", "@c3", "miss-q", "miss-d", "13", "29", "2", selectionArgs("try-selected", "t1", "@t1")))

  var histories: List[List[Request]]
  action init = histories' = List(story, forgeryStory)
  action step = histories' = histories
}
