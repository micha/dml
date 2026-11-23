module transfer_histories {
  type Request = { op: str, args: List[str] }

  pure def exportCommit(testCase: str): Request = { op: "export_commit", args: List(testCase) }
  pure def importCommit(testCase: str): Request = { op: "import_commit", args: List(testCase) }
  pure val readValue: Request = { op: "read_value", args: List("all", "z-bound") }
  pure val readParentValue: Request = { op: "read_parent_value", args: List("0", "all", "z-bound") }
  pure val readMain: Request = { op: "read_main", args: List() }
  pure val readStaged: Request = { op: "read_staged", args: List() }
  pure val readStagedValue: Request = { op: "read_staged_value", args: List("all", "z-bound") }
  pure val readStagedParent: Request = {
    op: "read_staged_parent_value", args: List("0", "all", "z-bound")
  }
  pure def recordLineage(implementation: str): Request = {
    op: "record_lineage", args: List(implementation)
  }
  pure val readLineage: Request = { op: "read_lineage", args: List() }
  pure val returnLineage: List[Request] = List("capture_source_main", "export_return", "import_return",
    "repeat_return", "read_source_main", "inspect_return", "reject_stale_return", "read_source_main",
    "publish_return", "read_returned_main", "read_source_pin")
    .foldl(List(), (out, op) => out.append({ op: op, args: List() }))

  pure val releaseStaging: List[Request] = List("reject_stale_release", "read_staged", "abort_release",
    "read_staged", "release_staged", "read_staged", "reject_missing_release", "read_lineage",
    "read_returned_main", "check_released", "check_published_source")
    .foldl(List(), (out, op) => out.append({ op: op, args: List() }))

  var histories: List[List[Request]]

  // The replay must execute these attempts regardless of the statuses it observes.
  action init = histories' = List(
    List(exportCommit("export"), importCommit("import_exported"), exportCommit("reexport"),
         importCommit("import"), importCommit("thin"), importCommit("forward")),
    List(exportCommit("export"), importCommit("alternative"), exportCommit("reexport"),
         exportCommit("repeat")),
    List(exportCommit("export"), importCommit("import_exported"), readMain, readValue,
         readStaged, { op: "stage_imported", args: List() }, readStaged, readStagedValue,
         readStagedParent, readMain, { op: "publish_imported", args: List() }, readMain,
         readValue, readParentValue),
    List(exportCommit("export"), importCommit("import_exported"), { op: "check_unpinned", args: List() },
         { op: "stage_imported", args: List() }, { op: "check_staged", args: List() }, readStagedValue,
         recordLineage("add-one"), readLineage,
         recordLineage("add-two"), readLineage, readMain, readStaged)
      .concat(returnLineage).concat(List(readMain, readStaged, readLineage)).concat(releaseStaging),
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
