module gc_histories {
  import retention_histories.* from "./retention_histories"

  pure val fixture = seedWorker.concat(List(exportCommit("worker", "result", "bundle"),
    close("worker"), open("origin", "create"), importCommit("origin", "bundle", "importedResult")))

  pure val write = begin("origin", "write", "edit")
  pure val sweep = collect("edit")
  pure val finish = commit("edit")
  pure val stop = abort("edit")
  pure val createIncoming = createRef("edit", "incoming", "selected")
  pure val createMain = createRef("edit", "main", "base")
  pure val deleteIncoming = dropRef("edit", "incoming", "selected")
  pure val deleteMain = dropRef("edit", "main", "base")
  pure val createPin = createRef("edit", "result-pin", "importedResult")
  pure val deletePin = dropRef("edit", "result-pin", "importedResult")
  pure val moveIncoming = moveRef("edit", "incoming", "base")

  pure def withFixture(steps: List[Request]): List[Request] = fixture.concat(steps).append(close("origin"))

  var histories: List[List[Request]]

  action init = histories' = List(
    withFixture(List(write, createPin, sweep, finish,
      write, createIncoming, finish,
      write, deleteIncoming, sweep, finish,
      write, deletePin, sweep, stop,
      write, sweep, finish,
      write, deletePin, sweep, finish,
      write, sweep, finish)),
    withFixture(List(write, createIncoming, sweep, finish,
      write, createMain, sweep, finish,
      write, deleteIncoming, sweep, finish,
      write, deleteMain, sweep, finish)),
    withFixture(List(write, sweep, createIncoming, finish,
      write, sweep, finish, write, sweep, finish)),
    withFixture(List(write, createIncoming, sweep, finish,
      write, createMain, sweep, finish,
      write, moveIncoming, sweep, finish,
      write, sweep, finish))
  )

  action step = histories' = histories
}
