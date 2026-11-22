module export_walk_rules {
  // Abstract typed record identity; an edge list is already in stored order.
  type Key = (str, str)
  type Graph = Key -> List[Key]

  pure def keySet(items: List[Key]): Set[Key] =
    items.foldl(Set(), (seen, key) => seen.union(Set(key)))

  // An order-independent fixed point, not the walk's visited set.
  pure def reachable(graph: Graph, root: Key): Set[Key] =
    range(0, graph.keys().size()).foldl(Set(root), (seen, _) =>
      graph.keys().fold(seen, (expanded, key) =>
        if (seen.contains(key)) expanded.union(keySet(graph.get(key))) else expanded))

  // Only tests ordering among emitted rows. It cannot establish completeness.
  pure def orderedSubset(graph: Graph, root: Key, rows: List[Key]): bool = {
    val emitted = keySet(rows)
    if (rows.length() == 0) false else and {
      rows.nth(rows.length() - 1) == root,
      emitted.subseteq(graph.keys()),
      rows.indices().forall(index => {
        val key = rows.nth(index)
        if (not(graph.keys().contains(key))) false
        else keySet(graph.get(key)).intersect(emitted).subseteq(keySet(rows.slice(0, index)))
      }),
    }
  }

  pure def completeAndUnique(graph: Graph, root: Key, rows: List[Key]): bool = {
    val emitted = keySet(rows)
    emitted == reachable(graph, root) and emitted.size() == rows.length()
  }

  pure def exactOrder(expected: List[Key], rows: List[Key]): bool = rows == expected
}
