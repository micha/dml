module transfer_histories {
  type Request = { op: str, args: List[str] }

  pure def exportCommit(testCase: str): Request = { op: "export_commit", args: List(testCase) }
  pure def importCommit(testCase: str): Request = { op: "import_commit", args: List(testCase) }
  pure val readValue: Request = { op: "read_value", args: List("all", "z-bound") }
  pure val readParentValue: Request = { op: "read_parent_value", args: List("0", "all", "z-bound") }

  var histories: List[List[Request]]

  // The replay must execute these attempts regardless of the statuses it observes.
  action init = histories' = List(
    List(exportCommit("export"), importCommit("import_exported"), exportCommit("reexport"),
         importCommit("import"), importCommit("thin"), importCommit("forward")),
    List(exportCommit("export"), importCommit("alternative"), exportCommit("reexport"),
         exportCommit("repeat")),
    List(exportCommit("export"), importCommit("import_exported"), { op: "read_main", args: List() },
         readValue, { op: "publish_imported", args: List() }, { op: "read_main", args: List() },
         readValue, readParentValue),
    List("busy_import", "bad_magic", "bad_version", "reserved", "short_header", "short_frame",
         "short_record", "trailing", "wrong_kind", "embedded_kind", "wrong_id", "wrong_root",
         "wrong_root_type", "bad_packed", "duplicate", "extra", "thin", "forward", "import")
      .foldl(List(), (out, testCase) => out.append(importCommit(testCase))),
    List(importCommit("map_full"), importCommit("import"), exportCommit("reexport")),
    List(importCommit("corrupt_store")),
    List(exportCommit("missing_root"), exportCommit("busy_export"), exportCommit("dirty_export"),
         exportCommit("missing_edge")),
    List(exportCommit("oversize_export"), importCommit("oversize_record"),
         importCommit("oversize_count"), importCommit("oversize_bundle"), importCommit("import"))
  )

  action step = histories' = histories
}
