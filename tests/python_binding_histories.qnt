module python_binding_histories {
  import python_binding_fixture.* from "./python_binding_fixture"

  pure val typeError = pythonError("TypeError", "")
  pure val idLength = pythonError("ValueError", "object ID must contain 16 bytes")
  pure val duplicateKey = nativeError("invalid_payload", "record_type=datum;detail=map_keys_not_strictly_sorted")
  pure val low = "00000000000000000000000000000000"
  pure val high = "ffffffffffffffffffffffffffffffff"
  pure val lowBytes = "bytes:00000000000000000000000000000000"
  pure val highBytes = "bytes:ffffffffffffffffffffffffffffffff"
  pure val mutableId = "bytearray:00000000000000000000000000000000"
  pure val longId = "bytes:0000000000000000000000000000000021"
  pure def pair(first: str, second: str): List[str] = List("tuple:2", first, second)
  pure def twoRows(container: str, first: List[str], second: List[str]): List[str] =
    List(container).concat(first).concat(second)
  pure def typedEncode(kind: str, operands: List[str], alias: str, expected: Expected): Check =
    check("datum_encode", List(kind, "py").concat(operands).append(alias), expected)
  pure def mapEncode(operands: List[str], alias: str, expected: Expected): Check = typedEncode("map", operands, alias, expected)
  pure def listEncode(operands: List[str], alias: str, expected: Expected): Check = typedEncode("list", operands, alias, expected)

  pure val repository = List(
    check("repo_open", List("source", "existing"), nativeError("not_found", "repository path does not exist")),
    check("repo_open", List("source", "py:int:1"), pythonError("TypeError", "create must be a bool")),
    check("repo_open", List("source~nul", "create"), pythonError("ValueError", "embedded null byte")),
    check("repo_open", List("source", "create", "-1"), pythonError("OverflowError", "")),
    check("repo_open", List("source", "create", "py:float:1.5"), typeError),
    check("repo_open", List("source", "create", "1024"),
      nativeError("invalid_argument", "repository map size must be at least 1 MiB")),
    check("repo_open", List("source", "create", "1048576"), { ...handle, writes: true, creates: "source" }),
    close("source"))

  pure val workingWriter = writer("source").concat(putDatum("string", List("kept"), "kept")).concat(List(
    check("txn_put_datum", List("txn", "py:mutable_packed:kept", "invalid"), typeError),
    check("txn_ref_create", List("py:repo:source", "main", "kept"), typeError),
    check("txn_ref_create", List("txn", "main", "py:short_id:kept"), idLength),
    commit, begin("source", "read"), readDatum("kept"), decode("read", 6, "6b657074"),
    check("txn_ref_get", List("txn", "main", "unexpected"), nativeError("not_found", "")), abort, close("source")))

  pure val ascending = pair(lowBytes, highBytes)
  pure val descending = pair(highBytes, lowBytes)
  pure val canonicalMap = List(
    mapEncode(List("tuple:0"), "empty", bytesResult), decode("empty", 10, "00000000"),
    { ...mapEncode(twoRows("list:2", descending, ascending), "reverse", bytesResult), save: "reverse" },
    // LE count 2 followed by (low, high) and (high, low).
    decode("reverse", 10, "0200000000000000000000000000000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff00000000000000000000000000000000"),
    mapEncode(twoRows("tuple:2", ascending, descending), "sorted", { ...bytesResult, value: SavedPacked("reverse") }),
    mapEncode(twoRows("list:2", ascending, pair(lowBytes, lowBytes)), "duplicate", duplicateKey))

  pure val badMapShapes = List(List("iter:0"), List("dict:1", lowBytes, lowBytes),
    List("tuple:1", "list:2", lowBytes, lowBytes), List("tuple:1", "tuple:1", lowBytes),
    List("tuple:1", "tuple:3", lowBytes, lowBytes, lowBytes), List("tuple:1").concat(pair(mutableId, lowBytes)))
    .mapList(operands => mapEncode(operands, "bad", typeError)).concat(List(
    mapEncode(List("tuple:1").concat(pair("bytes:000000000000000000000000000000", lowBytes)), "bad", idLength),
    mapEncode(twoRows("tuple:2", pair(lowBytes, lowBytes), pair(lowBytes, longId)), "bad", idLength)))

  pure val canonicalUri = "dml://source/builtin/map/get/v1"
  pure val canonicalUriBytes = "646d6c3a2f2f736f757263652f6275696c74696e2f6d61702f6765742f7631"
  pure val nullUri = List(
    check("datum_encode", List("null", "none", "null"), bytesResult), decode("null", 1, ""),
    check("datum_encode", List("null", "py:bytes:", "bad"), pythonError("TypeError", "NULL datum value must be None")),
    typedEncode("uri", List("str:646d6c3a2f2f736f757263652f6275696c74696e2f6d61702f6765742f7631"), "bad", typeError),
    check("datum_encode", List("uri", canonicalUri, "uri"), bytesResult), decode("uri", 7, canonicalUriBytes))
    .concat(List("bytes:72656c6174697665", "bytes:646d6c3a00", "bytes:646d6c3a78ff", "bytes:646d6c3a257a7a",
      "bytes:444d4c3a2f2f534f555243452f6275696c74696e2f6d61702f6765742f25373631")
      .mapList(payload => typedEncode("uri", List(payload), "bad", nativeError("invalid_payload", ""))))

  pure val listAndMapMembers = List("list:3", "tuple:3").foldl(List(), (out, container) => out.concat(List(
    listEncode(List(container, highBytes, lowBytes, highBytes), "list", bytesResult),
    members("list", List("tuple:3", "bytes", "bytes", "bytes"), 3, List(Exact(high), Exact(low), Exact(high))))))
    .concat(List(
      listEncode(List("tuple:0"), "emptyList", bytesResult), members("emptyList", List("tuple:0"), 0, List()),
      mapEncode(List("tuple:0"), "emptyMap", bytesResult), members("emptyMap", List("tuple:0"), 0, List()),
      mapEncode(twoRows("tuple:2", descending, ascending), "map", bytesResult),
      members("map", List("tuple:2", "tuple:2", "bytes", "bytes", "tuple:2", "bytes", "bytes"), 2,
        List(Exact(low), Exact(high), Exact(high), Exact(low))),
      check("datum_members", List("py:short_packed:map"), nativeError("invalid_header", "record_type=unknown;detail=total_len")),
      check("datum_members", List("py:mutable_packed:map"), typeError),
      check("datum_encode", List("null", "none", "null"), bytesResult),
      check("datum_members", List("null"), pythonError("ValueError", "datum members require a LIST or MAP"))))

  pure val badListShapes = List(List("iter:0"), List("set:1", lowBytes), List(lowBytes), List("tuple:1", mutableId))
    .mapList(operands => listEncode(operands, "bad", typeError)).append(
      listEncode(List("tuple:2", lowBytes, longId), "bad", idLength))

  pure val poisonedMap = writer("source").concat(putDatum("string", List("key"), "key"))
    .concat(putObject("node", List("key"), "node")).concat(List(
      check("datum_encode", List("map", "key", "node", "badmap"), bytesResult),
      check("txn_put_datum", List("txn", "badmap", "unexpected"),
        nativeError("invalid_kind", "record_type=datum;detail=composite_ref_not_datum")),
      check("txn_commit", List("txn"), nativeError("invalid_state", "")), begin("source", "read"),
      check("txn_get_datum", List("txn", "key", "absent-key"), nativeError("not_found", "")),
      check("txn_get_object", List("txn", "node", "node", "absent-node"), nativeError("not_found", "")),
      abort, close("source")))

  pure val futureUri = "dml://source/future/v99"
  pure val futureUriBytes = "646d6c3a2f2f736f757263652f6675747572652f763939"
  pure val nestedTransfer = writer("source").concat(putDatum("string", List("py:bytes:636166c3a9"), "key")).concat(List(
    check("datum_encode", List("string", "py:bytes:63616665cc81", "equivalent"), { ...bytesResult, value: SavedPacked("key") }),
    check("txn_put_datum", List("txn", "equivalent", "equivalent"), { ...bytesResult, value: Saved("key") })))
    .concat(putDatum("i64", List("42"), "value")).concat(List(
      check("datum_encode", List("map", "key", "value", "equivalent", "value", "duplicate"), duplicateKey)))
    .concat(putDatum("uri", List(futureUri), "uri")).concat(putDatum("null", List("none"), "null"))
    .concat(putDatum("list", List("value", "null", "uri"), "listing"))
    .concat(putDatum("map", List("key", "listing"), "inner")).concat(putDatum("map", List("key", "inner"), "outer"))
    .concat(putObject("node", List("literal", "outer"), "literal"))
    .concat(putObject("dag", List("literal", "arguments", "literal"), "dag"))
    .concat(putObject("tree", List("snapshot", "dag"), "tree")).concat(putObject("commit", List("tree"), "root"))
    .concat(List(check("txn_ref_create", List("txn", "main", "root"), ok), commit,
      check("repo_export_commit", List("source", "root", "bundle"), bytesResult), close("source"),
      check("repo_open", List("replica", "create"), { ...handle, writes: true, creates: "replica" }),
      check("repo_import_commit_staged", List("replica", "bundle", "staged", "imported"),
        { ...bytesResult, writes: true, value: Saved("root") }), begin("replica", "read"),
      check("txn_ref_get", List("txn", "staged", "staged"), { ...bytesResult, value: Saved("root") }),
      check("txn_lookup_node", List("txn", "dag", "arguments", "found"), { ...bytesResult, value: Saved("literal") }),
      readDatum("outer"), members("read", List("tuple:1", "tuple:2", "bytes", "bytes"), 1, List(Saved("key"), Saved("inner"))),
      readDatum("inner"), members("read", List("tuple:1", "tuple:2", "bytes", "bytes"), 1, List(Saved("key"), Saved("listing"))),
      readDatum("listing"),
      members("read", List("tuple:3", "bytes", "bytes", "bytes"), 3, List(Saved("value"), Saved("null"), Saved("uri"))),
      readDatum("uri"), decode("read", 7, futureUriBytes), readDatum("null"), decode("read", 1, ""),
      readDatum("key"), decode("read", 6, "636166c3a9"), readDatum("value"), decode("read", 3, "2a00000000000000"),
      abort, close("replica")))

  pure val bundleBoundary = writer("source").concat(putObject("tree", List(), "tree"))
    .concat(putObject("commit", List("tree"), "root")).concat(List(commit,
      check("repo_export_commit", List("source", "py:text_id:root", "invalid"), idLength),
      check("repo_import_commit_staged", List("source", "py:bytearray:", "incoming", "invalid"), typeError),
      save("repo_export_commit", List("source", "root", "bundle"), bytesResult, "bundle"),
      begin("source", "read"),
      check("repo_export_commit", List("source", "root", "invalid"), nativeError("invalid_state", "transfer requires no active transactions")),
      check("repo_import_commit_staged", List("source", "bundle", "incoming", "invalid"), nativeError("invalid_state", "transfer requires no active transactions")),
      check("txn_collect_garbage", List("txn"), nativeError("invalid_state", "transaction is not writable")), abort,
      check("repo_import_commit_staged", List("source", "hex:", "incoming", "invalid"), nativeError("invalid_bounds", "invalid bundle size")),
      check("repo_import_commit_staged", List("source", "bundle", "incoming", "imported"),
        { ...bytesResult, value: Saved("root"), writes: true }),
      check("repo_import_commit_staged", List("source", "bundle", "incoming", "invalid"), nativeError("invalid_state", "ref already exists")),
      begin("source", "write"), check("txn_ref_delete_expected", List("txn", "incoming", "imported"), ok),
      check("txn_collect_garbage", List("txn"), { ...ok, count: 2, shape: List("int") }), abort,
      check("repo_export_commit", List("source", "imported", "restored"), { ...bytesResult, value: Saved("bundle") }),
      begin("source", "read"), check("txn_ref_get", List("txn", "incoming", "restored-ref"),
        { ...bytesResult, value: Saved("root") }), abort, close("source")))

  pure val cases = List(repository, workingWriter, canonicalMap, badMapShapes, nullUri,
    listAndMapMembers, badListShapes, poisonedMap, nestedTransfer, bundleBoundary)
  var histories: List[List[Request]]
  action init = histories' = cases.foldl(List(), (out, history) => out.append(history.mapList(checkRow => checkRow.request)))
  action step = histories' = histories
}
