// Finite workflow design for quint verify --backend=tlc (not the replay model).
module committed_calls_design {
  // Two distinct commits and DAGs with the same stored result, two producer
  // pin names, and one disjoint create-only result ref. Zero is an absent
  // commit/DAG. Duplicate or malformed physical records are outside the model.
  type Product = { parent: int, input: int, value: int }
  type Repository = { sums: Set[int], pins: str -> int, products: Set[Product], result: Product }
  type Evidence = { pin: str, expected: int, overflow: bool, before: Repository, after: Repository }

  pure val producerPins = Set("producer", "decoy")
  pure val sumCommits = Set(1, 2)
  pure def sumDag(commit: int): int = 100 + commit
  pure def storedValue(_commit: int): int = 12
  pure val emptyProduct: Product = { parent: 0, input: 0, value: 0 }
  pure val emptyRepo: Repository = {
    sums: Set(), pins: Map("producer" -> 0, "decoy" -> 0), products: Set(), result: emptyProduct
  }

  var repo: Repository
  var lastScale: Evidence

  action init = all {
    repo' = emptyRepo,
    lastScale' = { pin: "producer", expected: 0, overflow: false, before: emptyRepo, after: emptyRepo }
  }

  action recordSum(pin: str, commit: int): bool = all {
    repo.pins.get(pin) == 0,
    repo' = { ...repo, sums: repo.sums.union(Set(commit)), pins: repo.pins.set(pin, commit) },
    lastScale' = lastScale
  }

  // A separate repository client may move or release a producer pin between
  // invocations. There is no GC in this model; an ID alone is not a pin.
  action changePin(pin: str, target: int): bool = all {
    repo' = { ...repo, pins: repo.pins.set(pin, target) },
    lastScale' = lastScale
  }

  // A scale step models one serialized write transaction. Factor is 3 or a
  // representative overflowing factor; partial native writes are abstracted.
  action recordScale(pin: str, expected: int, overflow: bool): bool = {
    val selected = repo.pins.get(pin)
    val allowed = selected == expected and not(overflow) and repo.result == emptyProduct
    val product: Product = { parent: selected, input: sumDag(selected), value: storedValue(selected) * 3 }
    val updated = if (allowed) { ...repo, products: repo.products.union(Set(product)), result: product } else repo
    all {
      lastScale' = { pin: pin, expected: expected, overflow: overflow, before: repo, after: updated },
      repo' = updated
    }
  }

  action step = any {
    nondet pin = producerPins.oneOf()
    nondet commit = sumCommits.oneOf()
    recordSum(pin, commit),
    nondet pin = producerPins.oneOf()
    nondet target = repo.sums.union(Set(0)).oneOf()
    changePin(pin, target),
    nondet pin = producerPins.oneOf()
    nondet expected = sumCommits.oneOf()
    nondet overflow = Set(false, true).oneOf()
    recordScale(pin, expected, overflow)
  }

  // Read a committed product, then independently resolve the parent and
  // check that its DAG is the recorded input. Never read producer pins here.
  pure def inspect(snapshot: Repository): Product = {
    val selected = snapshot.products.fold(emptyProduct,
      (found, product) => if (product == snapshot.result) product else found)
    if (snapshot.sums.contains(selected.parent) and selected.input == sumDag(selected.parent)) selected
    else emptyProduct
  }

  val pinsRetainProducers = producerPins.forall(pin => repo.sums.union(Set(0)).contains(repo.pins.get(pin)))
  val retainedAndConsistent =
    if (repo.result == emptyProduct) repo.products == Set()
    else all {
      repo.products == Set(repo.result),
      repo.sums.contains(repo.result.parent),
      repo.result.input == sumDag(repo.result.parent),
      repo.result.value == 3 * storedValue(repo.result.parent),
      inspect(repo) == repo.result
    }

  val resolved = lastScale.before.pins.get(lastScale.pin)
  val scaleRefAndObjects = {
    val before = lastScale.before
    val after = lastScale.after
    val requested = lastScale.expected
    all {
      repo.result == after.result,
      repo.products == after.products,
      after.sums == before.sums,
      after.pins == before.pins,
      if (requested == 0 or resolved != requested or lastScale.overflow or before.result != emptyProduct)
        after == before
      else
        after.result == { parent: requested, input: sumDag(requested), value: storedValue(requested) * 3 }
    }
  }

  // Reachability checks: these observations must be found, not proved invariant.
  val selectedWithDecoy = lastScale.before.pins.get("producer") == 1 and lastScale.before.pins.get("decoy") == 2 and
    lastScale.before.result == emptyProduct and not(lastScale.overflow) and resolved == lastScale.expected
  observation selectsFirstWithDecoy = selectedWithDecoy and repo.result.parent == 1
  observation selectsSecondWithDecoy = selectedWithDecoy and repo.result.parent == 2
  observation staleRejected = lastScale.expected != 0 and resolved != 0 and resolved != lastScale.expected and
    lastScale.before.sums.contains(lastScale.expected) and lastScale.before.result == emptyProduct and
    not(lastScale.overflow) and repo.result == emptyProduct
  observation missingRejected = lastScale.expected != 0 and resolved == 0 and
    lastScale.before.sums.contains(lastScale.expected) and lastScale.before.result == emptyProduct and
    not(lastScale.overflow) and repo.result == emptyProduct
  observation overflowRejected = lastScale.expected != 0 and resolved == lastScale.expected and
    lastScale.before.result == emptyProduct and lastScale.overflow and repo.result == emptyProduct
  observation duplicateRejected = lastScale.before.result != emptyProduct and lastScale.expected != 0 and
    resolved == lastScale.expected and not(lastScale.overflow) and repo.result == lastScale.before.result
  observation inspectAfterRelease = repo.result != emptyProduct and
    repo.pins.get("producer") == 0 and repo.pins.get("decoy") == 0 and inspect(repo).input == sumDag(repo.result.parent)
}
