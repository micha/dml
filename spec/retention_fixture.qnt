module retention_fixture {
  type Record = { kind: str, tag: str, id: str, key: str, packed: str, deps: Set[str] }

  // Golden v1 records computed from the documented byte layout and XXH3-128
  // hash domain, not from a repository scan, codec call, exporter or collector.
  pure val baseDatum: Record = {
    kind: "datum", tag: "2", id: "eeaf8d961b92e74dc2a41ae7374d613e",
    key: "6f626a656374732f646174756d732f6565616638643936316239326537346463326134316165373337346436313365",
    packed: "444d4c310100020030000000000000000000000003000000080000000000000028000000000000002900000000000000",
    deps: Set()
  }
  pure val baseNode: Record = {
    kind: "node", tag: "3", id: "6d3a7ce38c9c552e7c2e49028e817f65",
    key: "6f626a656374732f6e6f6465732f3664336137636533386339633535326537633265343930323865383137663635",
    packed: "444d4c310100030028000000000000000000000001000000eeaf8d961b92e74dc2a41ae7374d613e",
    deps: Set(baseDatum.id)
  }
  pure val baseDag: Record = {
    kind: "dag", tag: "4", id: "ceb91e3c74d722a73101939c43e3001e",
    key: "6f626a656374732f646167732f6365623931653363373464373232613733313031393339633433653330303165",
    packed: "444d4c31010004004300000000000000000000006d3a7ce38c9c552e7c2e49028e817f6501000000070000007a2d626f756e646d3a7ce38c9c552e7c2e49028e817f65",
    deps: Set(baseNode.id)
  }
  pure val baseTree: Record = {
    kind: "tree", tag: "5", id: "6fa142b4d5841fabe70c6cb6bdd84f9c",
    key: "6f626a656374732f74726565732f3666613134326234643538343166616265373063366362366264643834663963",
    packed: "444d4c31010005002f00000000000000000000000100000003000000616c6cceb91e3c74d722a73101939c43e3001e",
    deps: Set(baseDag.id)
  }
  pure val base: Record = {
    kind: "commit", tag: "6", id: "603267b66028c34ad7174f567fc6e89b",
    key: "6f626a656374732f636f6d6d6974732f3630333236376236363032386333346164373137346635363766633665383962",
    packed: "444d4c31010006002800000000000000000000006fa142b4d5841fabe70c6cb6bdd84f9c00000000",
    deps: Set(baseTree.id)
  }
  pure val selectedDatum: Record = {
    kind: "datum", tag: "2", id: "efa7793dbd6eec630ec4f2f0d8a194b9",
    key: "6f626a656374732f646174756d732f6566613737393364626436656563363330656334663266306438613139346239",
    packed: "444d4c310100020030000000000000000000000003000000080000000000000028000000000000002d00000000000000",
    deps: Set()
  }
  pure val selectedNode: Record = {
    kind: "node", tag: "3", id: "5c022a9b3e399e26c47a8d88a1658427",
    key: "6f626a656374732f6e6f6465732f3563303232613962336533393965323663343761386438386131363538343237",
    packed: "444d4c310100030028000000000000000000000001000000efa7793dbd6eec630ec4f2f0d8a194b9",
    deps: Set(selectedDatum.id)
  }
  pure val selectedDag: Record = {
    kind: "dag", tag: "4", id: "1de1cc27deca2fe8da03200605842d7b",
    key: "6f626a656374732f646167732f3164653163633237646563613266653864613033323030363035383432643762",
    packed: "444d4c31010004004300000000000000000000005c022a9b3e399e26c47a8d88a165842701000000070000007a2d626f756e645c022a9b3e399e26c47a8d88a1658427",
    deps: Set(selectedNode.id)
  }
  pure val selectedTree: Record = {
    kind: "tree", tag: "5", id: "6faf0377a8acbfb2a127c39f74f325e4",
    key: "6f626a656374732f74726565732f3666616630333737613861636266623261313237633339663734663332356534",
    packed: "444d4c31010005002f00000000000000000000000100000003000000616c6c1de1cc27deca2fe8da03200605842d7b",
    deps: Set(selectedDag.id)
  }
  pure val selected: Record = {
    kind: "commit", tag: "6", id: "ef1b82c2c13736279f42eb9e1e38206e",
    key: "6f626a656374732f636f6d6d6974732f6566316238326332633133373336323739663432656239653165333832303665",
    packed: "444d4c31010006003800000000000000000000006faf0377a8acbfb2a127c39f74f325e401000000603267b66028c34ad7174f567fc6e89b",
    deps: Set(selectedTree.id, base.id)
  }
  pure val keepDatum: Record = {
    kind: "datum", tag: "2", id: "d1d28b2e61b4579f9d7c1cc6dd4ca211",
    key: "6f626a656374732f646174756d732f6431643238623265363162343537396639643763316363366464346361323131",
    packed: "444d4c310100020030000000000000000000000003000000080000000000000028000000000000000903000000000000",
    deps: Set()
  }
  pure val keepNode: Record = {
    kind: "node", tag: "3", id: "6d9d921fc882523686be1cf3a5982dad",
    key: "6f626a656374732f6e6f6465732f3664396439323166633838323532333638366265316366336135393832646164",
    packed: "444d4c310100030028000000000000000000000001000000d1d28b2e61b4579f9d7c1cc6dd4ca211",
    deps: Set(keepDatum.id)
  }
  pure val keepDag: Record = {
    kind: "dag", tag: "4", id: "bda95a10b334a9d23b660eac0f824596",
    key: "6f626a656374732f646167732f6264613935613130623333346139643233623636306561633066383234353936",
    packed: "444d4c31010004002800000000000000000000006d9d921fc882523686be1cf3a5982dad00000000",
    deps: Set(keepNode.id)
  }
  pure val keepTree: Record = {
    kind: "tree", tag: "5", id: "ef21ddc1b377c1c19865cd304111edf3",
    key: "6f626a656374732f74726565732f6566323164646331623337376331633139383635636433303431313165646633",
    packed: "444d4c3101000500320000000000000000000000010000000600000073696e676c65bda95a10b334a9d23b660eac0f824596",
    deps: Set(keepDag.id)
  }
  pure val keep: Record = {
    kind: "commit", tag: "6", id: "81bcfac21b671ba5cd853b40e020acb7",
    key: "6f626a656374732f636f6d6d6974732f3831626366616332316236373162613563643835336234306530323061636237",
    packed: "444d4c3101000600280000000000000000000000ef21ddc1b377c1c19865cd304111edf300000000",
    deps: Set(keepTree.id)
  }
  pure val outputDatum: Record = {
    kind: "datum", tag: "2", id: "81a3c74587922365bc1b5274cd293833",
    key: "6f626a656374732f646174756d732f3831613363373435383739323233363562633162353237346364323933383333",
    packed: "444d4c310100020030000000000000000000000003000000080000000000000028000000000000002e00000000000000",
    deps: Set()
  }
  pure val outputNode: Record = {
    kind: "node", tag: "3", id: "902bc4966b8ded4853034dd735f55163",
    key: "6f626a656374732f6e6f6465732f3930326263343936366238646564343835333033346464373335663535313633",
    packed: "444d4c31010003002800000000000000000000000100000081a3c74587922365bc1b5274cd293833",
    deps: Set(outputDatum.id)
  }
  pure val implementationDatum: Record = {
    kind: "datum", tag: "2", id: "d202850b13abaae738cf5264847f11bd",
    key: "6f626a656374732f646174756d732f6432303238353062313361626161653733386366353236343834376631316264",
    packed: "444d4c310100020039000000000000000000000006000000110000000000000028000000000000006578616d706c652e6164642d6f6e654031",
    deps: Set()
  }
  pure val implementationNode: Record = {
    kind: "node", tag: "3", id: "1b4e351345186924174a88552e1595b1",
    key: "6f626a656374732f6e6f6465732f3162346533353133343531383639323431373461383835353265313539356231",
    packed: "444d4c310100030028000000000000000000000001000000d202850b13abaae738cf5264847f11bd",
    deps: Set(implementationDatum.id)
  }
  pure val resultDag: Record = {
    kind: "dag", tag: "4", id: "b702659c1e13d4daeaea31d5f8a81276",
    key: "6f626a656374732f646167732f6237303236353963316531336434646165616561333164356638613831323736",
    packed: "444d4c3101000400640000000000000000000000902bc4966b8ded4853034dd735f55163020000000e000000696d706c656d656e746174696f6e1b4e351345186924174a88552e1595b1060000006f7574707574902bc4966b8ded4853034dd735f55163",
    deps: Set(outputNode.id, implementationNode.id)
  }
  pure val resultTree: Record = {
    kind: "tree", tag: "5", id: "a82c48e57401e695deb75135814a50e6",
    key: "6f626a656374732f74726565732f6138326334386535373430316536393564656237353133353831346135306536",
    packed: "444d4c3101000500360000000000000000000000010000000a0000006c696e656167652d7631b702659c1e13d4daeaea31d5f8a81276",
    deps: Set(resultDag.id)
  }
  pure val result: Record = {
    kind: "commit", tag: "6", id: "36ee91cf6c626be80e9a81ae0e1c88f4",
    key: "6f626a656374732f636f6d6d6974732f3336656539316366366336323662653830653961383161653065316338386634",
    packed: "444d4c3101000600380000000000000000000000a82c48e57401e695deb75135814a50e601000000ef1b82c2c13736279f42eb9e1e38206e",
    deps: Set(resultTree.id, selected.id)
  }

  pure val baseRecords = List(baseDatum, baseNode, baseDag, baseTree, base)
  pure val selectedRecords = baseRecords.concat(List(selectedDatum, selectedNode, selectedDag, selectedTree, selected))
  pure val resultRecords = selectedRecords.concat(List(outputDatum, outputNode,
    implementationDatum, implementationNode, resultDag, resultTree, result))
  pure val keepRecords = List(keepDatum, keepNode, keepDag, keepTree, keep)
  pure val records = resultRecords.concat(keepRecords)
  pure val byId = records.foldl(Map(), (out, record) => out.put(record.id, record))
  pure val byPacked = records.foldl(Map(), (out, record) => out.put(record.packed, record))
  pure val closure = Map(base.id -> baseRecords, selected.id -> selectedRecords,
    result.id -> resultRecords, keep.id -> keepRecords)

  pure val recipes = Map(
    List("i64", "41") -> baseDatum,
    List("node", baseDatum.id) -> baseNode,
    List("dag", baseNode.id, "z-bound", baseNode.id) -> baseDag,
    List("tree", "all", baseDag.id) -> baseTree,
    List("commit", baseTree.id) -> base,
    List("i64", "45") -> selectedDatum,
    List("node", selectedDatum.id) -> selectedNode,
    List("dag", selectedNode.id, "z-bound", selectedNode.id) -> selectedDag,
    List("tree", "all", selectedDag.id) -> selectedTree,
    List("commit", selectedTree.id, base.id) -> selected,
    List("i64", "777") -> keepDatum,
    List("node", keepDatum.id) -> keepNode,
    List("dag", keepNode.id) -> keepDag,
    List("tree", "single", keepDag.id) -> keepTree,
    List("commit", keepTree.id) -> keep,
    List("i64", "46") -> outputDatum,
    List("node", outputDatum.id) -> outputNode,
    List("string", "example.add-one@1") -> implementationDatum,
    List("node", implementationDatum.id) -> implementationNode,
    List("dag", outputNode.id, "implementation", implementationNode.id, "output", outputNode.id) -> resultDag,
    List("tree", "lineage-v1", resultDag.id) -> resultTree,
    List("commit", resultTree.id, selected.id) -> result
  )
}
