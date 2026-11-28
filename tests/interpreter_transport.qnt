module interpreter_transport {
  type BatchObservation = { scenario: int, attempts: List[{ value: int }] }
  pure def values(start: int, end: int): List[{ value: int }] =
    range(start, end).foldl(List(), (out, i) => out.append({ value: i }))
  pure val batches: List[BatchObservation] = List(
    { scenario: 4, attempts: values(0, 16) },
    { scenario: 7, attempts: values(16, 33) },
    { scenario: 9, attempts: List({ value: 41 }) }
  )

  type Ref = { name: str, target: str }
  type RefObservation = { attempts: List[{ refs: List[Ref] }] }
  pure val old = { name: "main", target: "A" }
  pure val pinned = { name: "selected", target: "A" }
  pure val moved = { name: "main", target: "B" }
  pure val refs: List[RefObservation] = List({ attempts: List(
    { refs: List() }, { refs: List(old, pinned) }, { refs: List(pinned, moved, old, old) }
  ) })
  pure val extraRefField = List({ attempts: List({ refs: List({ name: "main", target: "A", extra: "field" }) }) })

  type Attempt = { value: int, details: { ok: bool }, empty: str }
  type ColumnObservation = { scenario: int, attempts: List[Attempt] }
  pure val defaults: Attempt = { value: 0, details: { ok: false }, empty: "" }
  pure val columns: List[ColumnObservation] = List(
    { scenario: 4, attempts: List(defaults, { ...defaults, value: 1, details: { ok: true } }) },
    { scenario: 7, attempts: List(defaults, { ...defaults, details: { ok: true } }, defaults) }
  )
  // Python considers these nested records equal; Quint's type checker does not.
  pure val zeroInsteadOfFalse = List({ scenario: 4, attempts: List({ value: 0, details: { ok: 0 }, empty: "" }) })
  pure val missingColumn = List({ attempts: List({ value: 0 }) })
  pure val extraColumn = List({ attempts: List({ value: 0, details: { ok: false }, empty: "", extra: 0 }) })

  var requests: {
    batches: List[BatchObservation], refs: List[RefObservation],
    extraRefField: List[{ attempts: List[{ refs: List[{ name: str, target: str, extra: str }] }] }],
    defaults: Attempt, columns: List[ColumnObservation],
    zeroInsteadOfFalse: List[{ scenario: int, attempts: List[{ value: int, details: { ok: int }, empty: str }] }],
    missingColumn: List[{ attempts: List[{ value: int }] }],
    extraColumn: List[{ attempts: List[{ value: int, details: { ok: bool }, empty: str, extra: int }] }]
  }
  action init = requests' = {
    batches: batches, refs: refs, extraRefField: extraRefField,
    defaults: defaults, columns: columns, zeroInsteadOfFalse: zeroInsteadOfFalse,
    missingColumn: missingColumn, extraColumn: extraColumn
  }
  action step = requests' = requests
}
