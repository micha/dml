module builtin_primitive_evidence {
  type Entry = { name: str, id: str }
  type EntryEvent = { target: str, node: str }
  type Call = { dag: str, func: str, binding: str, sourceUri: str, inputs: str, entries: List[Entry] }
  type Attempt = { op: str, args: List[str], status: str, error: str, value: str, count: int, items: List[str],
    datumKind: int, datumPayload: str, datum: str, entries: List[Entry], sourceDag: str, sourceNode: str, name: str,
    sourceUri: str, binding: str, func: str, inputs: str, returned: str, trace: List[str], calls: List[Call],
    events: List[str], unchanged: bool, identity: str, entered: List[EntryEvent], caught: List[str], present: bool,
    intent: str, implementation: str }
  pure def accepted(a: Attempt): bool = a.status == "ok" and a.error == ""
}
