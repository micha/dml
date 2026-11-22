module export_walk_model {
  import export_walk_rules.* from "./export_walk_rules"

  pure val root: Key = ("commit", "root")
  pure val left: Key = ("commit", "left")
  pure val right: Key = ("commit", "right")
  pure val base: Key = ("commit", "base")
  pure val rootTree: Key = ("tree", "root")
  pure val baseTree: Key = ("tree", "base")
  pure val mainDag: Key = ("dag", "main")
  pure val otherDag: Key = ("dag", "other")
  // A same-token distinct-kind pair is an abstract control, not a fabricated native collision.
  pure val mainNode: Key = ("node", "shared")
  pure val shared: Key = ("datum", "shared")
  pure val subDagNode: Key = ("node", "subdag")
  pure val otherNode: Key = ("node", "other")
  pure val listDatum: Key = ("datum", "list")
  pure val listOnly: Key = ("datum", "list-only")
  pure val rightTree: Key = ("tree", "right")
  pure val rightDag: Key = ("dag", "right")
  pure val rightNode: Key = ("node", "right")
  pure val mapDatum: Key = ("datum", "map")
  pure val mapKey: Key = ("datum", "map-key")
  pure val mapValue: Key = ("datum", "set")
  pure val setFirst: Key = ("datum", "set-first")
  pure val setSecond: Key = ("datum", "set-second")
  pure val unrelated: Key = ("datum", "unrelated")

  type Shape = { parents: List[Key], reverseList: bool, hasBinding: bool }
  pure val shapes: Set[Shape] = tuples(Set(List(left), List(left, right), List(right, left)), Bool, Bool)
    .map(parts => { parents: parts._1, reverseList: parts._2, hasBinding: parts._3 })

  pure def fixture(shape: Shape): Graph = Map(
    root -> List(rootTree).concat(shape.parents),
    rootTree -> List(mainDag, otherDag),
    mainDag -> (if (shape.hasBinding) List(mainNode, subDagNode) else List(mainNode)),
    mainNode -> List(listDatum),
    listDatum -> (if (shape.reverseList) List(listOnly, shared) else List(shared, listOnly)),
    listOnly -> List(), shared -> List(),
    subDagNode -> List(otherDag), otherDag -> List(otherNode), otherNode -> List(shared),
    left -> List(baseTree, base), base -> List(baseTree), baseTree -> List(),
    right -> List(rightTree, base), rightTree -> List(rightDag), rightDag -> List(rightNode),
    rightNode -> List(mapDatum), mapDatum -> List(mapKey, mapValue),
    mapKey -> List(), mapValue -> List(shared, setFirst, setSecond),
    setFirst -> List(), setSecond -> List(), unrelated -> List(),
  )

  // Fixture expectations written without consulting graph edges or running a DFS.
  pure def expectedOrder(shape: Shape): List[Key] = {
    val listRows = if (shape.reverseList) List(listOnly, shared, listDatum) else List(shared, listOnly, listDatum)
    val treeRows = if (shape.hasBinding) List(mainNode, otherNode, otherDag, subDagNode, mainDag, rootTree)
                   else List(mainNode, mainDag, otherNode, otherDag, rootTree)
    val baseRows = List(baseTree, base)
    val rightRows = List(mapKey, setFirst, setSecond, mapValue, mapDatum, rightNode, rightDag, rightTree)
    val historyRows = if (shape.parents.length() == 1) baseRows.append(left)
      else if (shape.parents.head() == left) baseRows.append(left).concat(rightRows).append(right)
      else rightRows.concat(baseRows).append(right).append(left)
    listRows.concat(treeRows).concat(historyRows).append(root)
  }

  type Frame = { key: Key, leaving: bool }
  type Walk = { todo: List[Frame], active: Set[Key], emitted: Set[Key], rows: List[Key], failure: str }

  pure def advance(graph: Graph, firstParentOnly: bool, state: Walk): Walk = {
    if (state.failure != "" or state.todo.length() == 0) state
    else {
      val frame = state.todo.head()
      val key = frame.key
      val rest = state.todo.tail()
      if (frame.leaving) { ...state, todo: rest, active: state.active.exclude(Set(key)),
                          emitted: state.emitted.union(Set(key)), rows: state.rows.append(key) }
      else if (state.active.contains(key)) { ...state, failure: "cycle" }
      else if (state.emitted.contains(key)) { ...state, todo: rest }
      else if (not(graph.keys().contains(key))) { ...state, failure: "missing typed key" }
      else {
        val edges = graph.get(key)
        val chosen = if (firstParentOnly and key._1 == "commit" and edges.length() > 2)
          edges.slice(0, 2) else edges
        val enters = chosen.foldl(List(), (items, child) => items.append({ key: child, leaving: false }))
        { ...state, todo: enters.append({ key: key, leaving: true }).concat(rest),
          active: state.active.union(Set(key)) }
      }
    }
  }

  pure def walk(graph: Graph, firstParentOnly: bool): Walk = {
    val start = { todo: List({ key: root, leaving: false }), active: Set(),
                  emitted: Set(), rows: List(), failure: "" }
    // One root entry, at most one entry per edge, and one exit per visited vertex.
    val fuel = graph.keys().fold(1, (count, key) => count + 1 + graph.get(key).length())
    range(0, fuel).foldl(start, (state, _) => advance(graph, firstParentOnly, state))
  }

  pure def finished(w: Walk): bool =
    w.failure == "" and w.todo.length() == 0 and w.active.size() == 0

  run boundedCanonicalWalkTest = and {
    shapes.size() == 12,
    shapes.forall(shape => {
      val graph = fixture(shape)
      val result = walk(graph, false)
      finished(result) and orderedSubset(graph, root, result.rows) and
        completeAndUnique(graph, root, result.rows) and exactOrder(expectedOrder(shape), result.rows)
    }),
  }

  run firstParentNegativeTest = {
    val merges = shapes.filter(shape => shape.parents.length() == 2)
    merges.size() == 8 and merges.forall(shape => {
      val graph = fixture(shape)
      val result = walk(graph, true)
      finished(result) and orderedSubset(graph, root, result.rows) and
        not(completeAndUnique(graph, root, result.rows)) and not(exactOrder(expectedOrder(shape), result.rows))
    })
  }

  run siblingOrderNegativeTest = {
    val shape = { parents: List(right, left), reverseList: false, hasBinding: true }
    val graph = fixture(shape)
    val reordered = Set(graph.set(root, List(rootTree, left, right)),
                        graph.set(mapDatum, List(mapValue, mapKey)),
                        graph.set(mapValue, List(shared, setSecond, setFirst)))
    reordered.forall(badOrder => {
      val result = walk(badOrder, false)
      finished(result) and orderedSubset(graph, root, result.rows) and
        completeAndUnique(graph, root, result.rows) and not(exactOrder(expectedOrder(shape), result.rows))
    })
  }

  run extraAndDuplicateNegativeTest = {
    val shape = { parents: List(left, right), reverseList: true, hasBinding: true }
    val graph = fixture(shape)
    val rows = expectedOrder(shape)
    Set(List(unrelated).concat(rows), List(shared).concat(rows)).forall(invalid =>
      orderedSubset(graph, root, invalid) and not(completeAndUnique(graph, root, invalid)))
  }

  run malformedGraphNegativeTest = {
    val shape = { parents: List(left, right), reverseList: false, hasBinding: true }
    val graph = fixture(shape)
    val missing = graph.keys().exclude(Set(shared)).mapBy(key => graph.get(key))
    val missingWalk = walk(missing, false)
    val cyclicWalk = walk(graph.set(subDagNode, List(mainDag)), false)
    not(finished(missingWalk)) and missingWalk.failure == "missing typed key" and
      not(finished(cyclicWalk)) and cyclicWalk.failure == "cycle"
  }
}
