# PROPOSED ONLY; separate review before adding to the maintained append/execution selection.
def test_closure_copied_integration_plan_corruption_NOT_public_Request_proof(seed, tmp_path, monkeypatch):
    from dataclasses import replace
    with closure_live(seed, tmp_path, monkeypatch, "getters") as session:
        actual_request = p.inspect_request(session.path, commit=session.q.commit, request=session.q.request)
        assert actual_request == session.q
        selected = p.selection.inspect(session.path, commit=session.q.base, slot=p.ADD_SLOT)
        other = p.selection.inspect(session.path, commit=session.q.base, slot=p.DOUBLE_SLOT)
        with d.Repository(session.path) as repo, repo.read() as tx:
            original_fields = tx.get_dag(session.q.plan).bindings
            assert b.link(tx, original_fields["add-selection"]) == selected.dag != other.dag
        with d.Repository(session.path) as repo, repo.write() as tx:
            false_plan = clone(tx, session.q.plan, fields={"add-selection": tx.put_subdag(other.dag)})
            # This is ACTUAL native typed plan metadata with a deliberately false expectation.
            assert b.link(tx, tx.get_dag(false_plan).bindings["add-selection"]) == other.dag
        before = (session.path / "data.mdb").read_bytes()
        original = session.q
        # TEST-PRIVATE copied integration expectation corruption, NOT independently valid SDK Q.
        session.q = replace(original, plan=false_plan)
        try:
            with pytest.raises((ValueError, c.CallError), match="pinned double selection changed"):
                session.invoker.invoke(session.tokens[0], session.input)
        finally:
            session.q = original
        assert session.q == actual_request
        assert (session.path / "data.mdb").read_bytes() == before
