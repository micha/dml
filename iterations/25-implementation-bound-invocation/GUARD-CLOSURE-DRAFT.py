# Append-only maintained draft for test_implementation_call_source_authority.py.
# SOURCE-ONLY: never imported/executed as part of this preparation.
from contextlib import contextmanager
from daggerml import exchange as ex, transfer
from test_exchange_records import clone
from test_implementation_calls import bridge


@contextmanager
def closure_live(seed, tmp_path, monkeypatch, stage="initial", add_control="require-selected", double_control="require-selected", changed=False, alias_basis=False):
    """One real metadata owner; only explicit handoff tests request fresh HOST work."""
    path = tmp_path / "owner.dml"
    bundle = transfer.export_commit(seed["path"], commit=seed["backend"].current)
    with d.Repository(path, create=True):
        pass
    imported = transfer.import_commit(path, bundle, ref="base")
    assert isinstance(imported, transfer.ImportResult)
    base = imported.commit
    for call, slot, ref in zip(seed["got"]["calls"], (p.ADD_SLOT, p.DOUBLE_SLOT), ("pin-add", "pin-double")):
        base = p.pin_leaf(path, commit=base, call=call, slot=slot, ref=ref)
    if alias_basis:
        selected = p.selection.inspect(path, commit=base, slot=p.ADD_SLOT)
        with d.Repository(path) as repo, repo.write() as tx:
            qid = b.scalar(tx, tx.get_dag(selected.request).root, "string")
            values = p.tree(tx, base)
            assert values.pop("request-" + qid) == selected.request
            base = tx.put_commit(tx.put_tree(values), parents=(base,))
            tx.create_ref("alias-basis", base)
        # Historical q/producer remains retained through ancestry, not mutable ref navigation.
        assert p.selection.inspect(path, commit=base, slot=p.ADD_SLOT).request == selected.request
    inputs_name = "inputs"
    if changed:
        inputs_name = "closure-changed"
        base = p.prepare_arguments(path, commit=base, values={"a": 13, "b": 30}, inputs_name=inputs_name, ref="closure-changed")
    request = p.record_request(path, commit=base, inputs_name=inputs_name, ref="owner", control="fresh",
        add_control=add_control, double_control=double_control)
    session = bridge.Session(path, request, tmp_path / "metadata-work")
    context = session.context
    context.__enter__()
    try:
        session.start()
        if stage in ("key", "getter", "getters", "add", "double"):
            if stage == "key":
                key_node = session.nodes.literal("a")
                session.test_key_description = session.context.describe(key_node)
            else:
                session.nodes.map_get(session.input, "a")
        if stage in ("getters", "add", "double"):
            session.nodes.map_get(session.input, "b")
        if stage in ("add", "double"):
            result = session.invoker.invoke(session.tokens[0], session.input)
            session.test_add_node = result
        if stage == "double":
            arguments = session.nodes.arguments({"x": session.test_add_node})
            session.test_double_arguments = arguments
            session.test_double_node = session.invoker.invoke(session.tokens[1], arguments)
        yield session
    finally:
        exception = sys.exc_info()
        if exception[0] is None and context.poisoned:
            with pytest.raises(c.CallError, match="caught callback/verifier/state error poisoned success"):
                context.__exit__(None, None, None)
        else:
            context.__exit__(*exception)


def closure_spine_positive(seed, kind, slot=None):
    """Select an actual prefix by kind/slot, not an assumed ordinal/template graph."""
    path = seed["path"]
    got = p.inspect_completion(path, commit=seed["first"].commit)
    with d.Repository(path) as repo, repo.read() as tx:
        aid = b.scalar(tx, tx.get_dag(got["initial"]).root, "string")
        matches = []
        for commit in p.history(tx, seed["first"].commit):
            parents = tx.get_commit(commit).parents
            if not parents:
                continue
            old, now = p.tree(tx, parents[0]), p.tree(tx, commit)
            names = [n for n in set(now) - set(old) if n.startswith("phase-" + aid + "-")]
            if len(names) != 1:
                continue
            fields = tx.get_dag(now[names[0]]).bindings
            if b.scalar(tx, fields["kind"], "string") != kind:
                continue
            actual_slot = b.scalar(tx, fields["slot"], "i64") if "slot" in fields else None
            matches.append((commit, names[0], now[names[0]], parents[0], actual_slot))
    if slot is not None:
        matches = [row for row in matches if (row[4] if row[4] is not None else
            len(p.inspect_spine(path, row[3], got["request"], got["initial"], aid, set())["calls"])) == slot]
    assert len(matches) == 1
    prefix = matches[0][:3]
    p.inspect_spine(path, prefix[0], got["request"], got["initial"], aid, set())
    return path, got, aid, prefix


@pytest.mark.parametrize("case", ["A100", "A115", "L68", "L93"])
def test_closure_entry_and_shallow_native_boundaries(seed, tmp_path, monkeypatch, case):
    path, base = seed["path"], seed["backend"].current
    if case.startswith("A"):
        events = []
        backend = adapter.EntryBackend(path, base, "outer-B", "inputs",
            dict(control="require-selected", add_control="fresh", double_control="fresh"),
            "closure-" + case, tmp_path / "NEVER-job", lambda name, row: events.append((name, row)))
        bound = c.Bound("ordinary", p.INTENT, backend.closure["dag"])
        arguments = backend.read(backend.inputs)
        receipt = backend.perform(bound, arguments)
        assert len(events) == 1 and events[0][0] == "outer-request"
        actual = p.inspect_request(path, commit=backend.request.commit, request=backend.request.request)
        assert events[0][1]["request"] == str(actual.request)
        assert events[0][1]["submission"] == str(actual.commit)
        assert backend.verify(bound, arguments, receipt).dag == actual.selected["result"]
        if case == "A115":
            other = p.record_request(path, commit=base, closure_name="outer-B", inputs_name="other-input",
                control="require-selected", ref="closure-other-W")
            assert p.inspect_reuse(path, commit=other.reused).request == other.request != actual.request
            backend.current = other.reused  # TEST-PRIVATE copied integration navigation, native authorities intact.
            before = (path / "data.mdb").read_bytes()
            with pytest.raises(c.CallError, match="THIS outer W does not consume pinned OLD S"):
                backend._authority()
            assert (path / "data.mdb").read_bytes() == before
        assert not (tmp_path / "NEVER-job").exists()
    else:
        with d.Repository(path) as repo, repo.write() as tx:
            if case == "L68":
                value = p.event(tx, "legal-wide-metadata", values={"field-%02d" % i: i for i in range(8)})
                assert len(tx.get_record("dag", value)) > 148
            else:
                entries = p.tree(tx, base)
                original = c.inspect_closure(tx, entries["add-A"])
                wrong = leaf.ADD[:-1] + ("x" if not leaf.ADD.endswith("x") else "y")
                assert len(wrong) == len(leaf.ADD)
                value = c.put_closure(tx, intent=wrong, binding=original.binding, environment=original.environment)
                assert c.inspect_closure(tx, value).intent == wrong
        before = (path / "data.mdb").read_bytes()
        with d.Repository(path) as repo, repo.read() as tx:
            if case == "L68":
                with pytest.raises(ValueError, match="native shallow DAG exceeds profile size"):
                    leaf.shallow_shape(tx, value, "legal-wide-metadata", ("role",), 148)
            else:
                with pytest.raises(ValueError, match="fixed shallow closure intent differs"):
                    leaf.shallow_closure(tx, value, leaf.ADD, {"map-get": ("builtin", b.MAP_GET), "list-get": ("builtin", b.LIST_GET)})
        assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("case,stage,message", [
    ("S26", "initial", "session ended or poisoned"),
    ("S103", "initial", "unsupported builtin target"),
    ("S107", "initial", "unsupported ordinary captured target"),
    ("S113", "initial", "outer phase head changed"),
    ("S130", "initial", "phase fields differ from fixed kind"),
    ("S132", "key", "phase name already present"),
    ("S164", "initial", "duplicate prepared argument keys"),
    ("S169", "key", "getter preparation must use THIS input and key"),
    ("S174", "initial", "only double map from THIS exact returned add node is supported"),
    ("S195", "getters", "only next prepared fixed getter may invoke"),
    ("S220", "getter", "THIS getter native position differs"),
    ("S226", "add", "THIS ordinary native call position differs"),
    ("S232", "getters", "THIS ownQ/target/input/OLD-or-fresh result association differs"),
    ("S238", "initial", "call order/getter dispatch guard"),
    ("S242", "getters", "ordinary call must consume exact captured target/input node"),
    ("S246", "getters", "actual getter/call guard differs before dispatch"),
    ("S272", "getters", "required double selection does not match"),
    ("S377", "double", "outer success requires both actual calls/exact returned node"),
    ("S382", "double", "actual successful spine differs before return"),
])
def test_closure_real_session_native_state_and_receipts(seed, tmp_path, monkeypatch, case, stage, message):
    with closure_live(seed, tmp_path, monkeypatch, stage, changed=(case == "S272")) as session:
        arguments = session.context.describe(session.input)
        bound = c.Bound("ordinary", leaf.ADD, session.q.closure["add"]["dag"])
        with d.Repository(session.path) as repo, repo.read() as tx:
            entries = p.tree(tx, session.current)
            other_c = c.inspect_closure(tx, entries["add-B"])
            other_result = b.link(tx, tx.get_dag(seed["got"]["calls"][1]).bindings["result"])
            assert b.Inspector(tx, commit=session.current).node(other_result).value == d.Datum.i64(84)
        if case == "S26":
            session.fail(bridge.SessionError("closed test integration"))
        if case == "S113":
            with d.Repository(session.path) as repo, repo.write() as tx:
                tx.update_ref("outer-head-" + session.aid, session.q.commit)
        if case == "S132":
            session.index = 0  # copied expected ordinal; the existing real phase remains unchanged.
        if case in ("S220", "S246"):
            session.getters = []  # copied expected positions, not a fake native inspector.
        if case in ("S226", "S382"):
            session.calls = list(reversed(session.calls)) if len(session.calls) == 2 else session.calls * 2
        if case == "S232":
            original = session._invoke_ordinary
            def actual_then_other(*args):
                actual = original(*args)
                assert actual != other_result
                assert p.inspect_spine(session.path, session.current, session.q.request, session.initial, session.aid, set())["calls"] == session.calls
                return other_result  # REAL retained native R, not an invented descriptor/receipt.
            monkeypatch.setattr(session, "_invoke_ordinary", actual_then_other)
        before = (session.path / "data.mdb").read_bytes()
        with pytest.raises((ValueError, c.CallError), match=message):
            if case == "S26":
                session.read(session.q.inputs.dag)
            elif case == "S103":
                session.bind(c.Bound("builtin", b.MAP_GET, dict(other_c.captures)["map-get"].target))
            elif case == "S107":
                session.bind(c.Bound("ordinary", leaf.ADD, other_c.dag))
            elif case == "S113":
                session._advance(session.q.commit)
            elif case == "S130":
                session._phase("get-key-a")
            elif case == "S132":
                session._phase("get-key-a", links={"node": session.key_node})
            elif case == "S164":
                session.arguments([("map", arguments), ("map", arguments)])
            elif case == "S169":
                session.arguments([("map", session.read(entries["other-input"])), ("key", session.test_key_description)])
            elif case == "S174":
                session.arguments([("x", arguments)])
            elif case == "S195":
                session.perform(c.Bound("builtin", b.MAP_GET, dict(other_c.captures)["map-get"].target), arguments)
            elif case in ("S220", "S226"):
                receipt = session.last_receipt
                with d.Repository(session.path) as repo, repo.read() as tx:
                    description = b.Inspector(tx, commit=session.current).node(receipt[1])
                session.verify(receipt[0], description, receipt)
            elif case == "S232":
                session.invoker.invoke(session.tokens[0], session.input)
            elif case == "S238":
                session._invoke_ordinary(bound, arguments)
            elif case == "S242":
                session._invoke_ordinary(c.Bound("ordinary", leaf.ADD, other_c.dag), arguments)
            elif case == "S246":
                session._invoke_ordinary(bound, arguments)
            elif case == "S272":
                # The message says double, but this same guard also owns ADD require-selected misses.
                session._invoke_ordinary(bound, arguments)
            elif case == "S377":
                session.finish(session.input)
            else:
                session.finish(session.test_double_node)
        if case not in ("S232", "S272"):
            assert (session.path / "data.mdb").read_bytes() == before


def test_closure_history_scaled_unit_limit_exact_and_next(tmp_path, monkeypatch):
    """Scaled algorithm unit proof, NOT actual MAX_OBJECTS+1/production admission assurance."""
    path = tmp_path / "history.dml"
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        tree = tx.put_tree({})
        first = tx.put_commit(tree)
        second = tx.put_commit(tree, parents=(first,))
        third = tx.put_commit(tree, parents=(second,))
    with monkeypatch.context() as scaled:
        scaled.setattr(transfer, "MAX_OBJECTS", 2)
        with d.Repository(path) as repo, repo.read() as tx:
            assert p.history(tx, second) == {first, second}
            with pytest.raises(ValueError, match="history exceeds transfer profile"):
                p.history(tx, third)


@pytest.mark.parametrize("kind,slot,case,message", [
    ("leaf-join", 0, "P898", "ordered leaf F join parents differ"),
    ("get-key-a", None, "P944", "getter key preparation order differs"),
    ("get-key-a", None, "P949", "getter key actual literal differs"),
    ("get-arguments-a", None, "P955", "getter arguments preparation order differs"),
    ("double-input", None, "P979", "double input before actual successful add"),
    ("leaf-prepare", 0, "P987", "call before getter checks/ordered slot differs"),
    ("leaf-prepare", 0, "P994", "leaf decision exact B/E differs"),
    ("leaf-prepare", 0, "P999", "leaf decision exact basis/named dimensions differ"),
    ("leaf-prepare", 0, "P1002", "prepared leaf decision owner/capture/input differs"),
    ("leaf-prepare", 0, "P1004", "add must forward SAME original input DAG"),
    ("leaf-prepare", 1, "P1008", "double must use THIS constructed map"),
    ("leaf-prepare", 1, "P1012", "double THIS upstream S/T/R ledger differs"),
    ("leaf-prepare", 0, "P1028", "leaf action differs from actual pinned plan"),
    ("leaf-pending", 0, "P1032", "leaf pending without preparation"),
    ("leaf-pending", 0, "P1037", "pending call exact owner/target/input differs"),
    ("leaf-selected", 0, "P1057", "public S before exact fresh join or duplicated"),
    ("leaf-done", 0, "P1064", "leaf completion without pending completion authority"),
    ("returned", None, "P1067", "outer return before both successful calls"),
    ("leaf-done", 0, "P1089", "leaf final pending association differs"),
    ("leaf-done", 0, "P1096", "fresh DONE requires THIS exact prior S phase"),
    ("leaf-done", 0, "P1116", "call success public ORIGINAL S/T/R differs"),
])
def test_closure_actual_prefix_typed_phase_guards(seed, tmp_path, kind, slot, case, message):
    path, got, aid, (current, name, phase) = closure_spine_positive(seed, kind, slot)
    early_data = None
    if case in ("P955", "P979", "P1032", "P1057", "P1064", "P1067"):
        early_kind = "get-b" if case in ("P979", "P1032", "P1067") else "get-arguments-a" if case == "P955" else "leaf-prepare" if case == "P1064" else "leaf-pending"
        early_slot = 0 if early_kind in ("leaf-pending", "leaf-prepare") else None
        early_data = closure_spine_positive(seed, early_kind, early_slot)[3]
    with d.Repository(path) as repo, repo.write() as tx:
        fields = dict(tx.get_dag(phase).bindings)
        index = b.scalar(tx, fields["index"], "i64")
        parents = tx.get_commit(current).parents
        previous = parents[0]
        entries = p.tree(tx, current)
        payloads = p.payload_names(aid, index, kind)
        if case == "P898":
            parents = (previous,)
        elif case in ("P944", "P949"):
            if case == "P944":
                fields["kind"] = b.literal(tx, "get-key-b")
            else:
                fields["node"] = tx.put_subdag(b.record(tx, b.LITERAL_ROLE, values={"value": "b"}, root="value"))
                entries[payloads["node"]] = b.link(tx, fields["node"])
        elif case in ("P955", "P979", "P1032", "P1057", "P1064", "P1067"):
            # Build the same typed phase as an exact only-addition atop a REAL earlier legal prefix.
            early, _, early_phase = early_data
            if case == "P955":
                early = tx.get_commit(early).parents[0]
            previous = early
            parents = (previous,)
            old = p.tree(tx, previous)
            if case == "P955":
                previous = tx.get_commit(previous).parents[0]
                parents = (previous,)
                old = p.tree(tx, previous)
            if case == "P1032":
                actual_request = b.link(tx, tx.get_dag(b.link(tx, fields["call"])).bindings["request"])
                request_id = b.scalar(tx, tx.get_dag(actual_request).root, "string")
                query_tree = dict(old)
                assert "request-" + request_id not in query_tree
                query_tree["request-" + request_id] = actual_request
                submission = tx.put_commit(tx.put_tree(query_tree), parents=(previous,))
                fields["submission"] = b.literal(tx, submission.bytes)
                previous = submission
                parents = (previous,)
                old = query_tree
            prior_indices = []
            for key, value in old.items():
                if key.startswith("phase-" + aid + "-"):
                    prior_indices.append(b.scalar(tx, tx.get_dag(value).bindings["index"], "i64"))
            index = max(prior_indices, default=-1) + 1
            fields["index"] = b.literal(tx, index)
            fields["previous"] = b.literal(tx, previous.bytes)
            name = p.phase_name(aid, index)
            payloads = p.payload_names(aid, index, kind)
            entries = dict(old)
            entries.update({payloads[n]: b.link(tx, fields[n]) for n in p.PHASE_LINKS[kind]})
        elif case in ("P987", "P994", "P999", "P1002", "P1004", "P1008", "P1012", "P1028"):
            decision = b.link(tx, fields["decision"])
            changes = {}
            if case == "P987":
                fields["slot"] = b.literal(tx, 1)
            elif case == "P994":
                other = leaf.inspect(tx, entries["add-B"], *leaf.sources())
                changes = {n: tx.put_subdag(other[n]) for n in ("binding", "environment")}
            elif case == "P999":
                changes["binding-name"] = b.literal(tx, "add-A")
            elif case == "P1002":
                changes["outer-attempt"] = tx.put_subdag(got["attempt"])
            elif case in ("P1004", "P1008"):
                if case == "P1004":
                    other = entries["other-input"]
                else:
                    with b.Recorder(tx, commit=current) as recorder:
                        other = recorder.dag(recorder.arguments({"x": recorder.literal(42)}))
                assert other != b.link(tx, fields["inputs"])
                fields["inputs"] = tx.put_subdag(other)
                entries[payloads["inputs"]] = other
                changes["inputs"] = tx.put_subdag(other)
            elif case == "P1012":
                double = tx.get_dag(got["calls"][1]).bindings
                changes["upstream-slot"] = double["selection-slot"]
            else:
                changes["control"] = b.literal(tx, "reuse-selected")
            if changes:
                invalid = clone(tx, decision, fields=changes)
                fields["decision"] = tx.put_subdag(invalid)
                entries[payloads["decision"]] = invalid
        elif case in ("P1037", "P1089", "P1096", "P1116"):
            call = b.link(tx, fields["call"])
            if case == "P1037":
                changes = {"outer-attempt": tx.put_subdag(got["attempt"])}
            elif case == "P1089":
                changes = {"pending": tx.put_subdag(b.link(tx, tx.get_dag(got["calls"][1]).bindings["pending"]))}
            elif case == "P1096":
                changes = {"selection-slot": tx.get_dag(got["calls"][1]).bindings["selection-slot"]}
            else:
                changes = {"result": tx.put_subdag(b.link(tx, tx.get_dag(got["calls"][1]).bindings["result"]))}
            invalid = clone(tx, call, fields=changes)
            fields["call"] = tx.put_subdag(invalid)
            entries[payloads["call"]] = invalid
        invalid_phase = tx.put_dag(root=tx.get_dag(phase).root, bindings=fields)
        entries[name] = invalid_phase
        variant = tx.put_commit(tx.put_tree(entries), parents=parents)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        p.inspect_spine(path, variant, got["request"], got["initial"], aid, set())
    assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("case,message", [("P535", "actual public leaf submission differs"), ("P1078", "pending public Q exact dimensions differ")])
def test_closure_public_prepare_REAL_other_spec_owning_association(seed, tmp_path, monkeypatch, case, message):
    path, base = seed["path"], seed["backend"].current
    own = p.selection.inspect(path, commit=base, slot=seed["add_slot"])
    with d.Repository(path) as repo, repo.read() as tx:
        cq = tx.get_commit(tx.get_commit(own.completion).parents[0]).parents[0]
        dc = tx.get_commit(cq).parents[0]
        entries = p.tree(tx, dc)
        decisions = [tx.get_dag(v).bindings for v in entries.values() if "role" in tx.get_dag(v).bindings
            and b.scalar(tx, tx.get_dag(v).bindings["role"], "string") == p.LEAF_D_ROLE]
        assert len(decisions) == 1
        bn, inn = (b.scalar(tx, decisions[0][n], "string") for n in ("binding-name", "inputs-name"))
    target_prefix = None
    if case == "P1078":
        _, target_got, target_aid, target_prefix = closure_spine_positive(seed, "leaf-pending", 0)
    current = p.public_prepare(path, cq, bn, inn, leaf.ADD, own.request)
    assert (current.binding, current.inputs) == (own.binding, own.inputs)
    with d.Repository(path) as repo, repo.write() as tx:
        values = p.tree(tx, base)
        values["sdk-other-binding"] = leaf.inspect(tx, values["add-B"], *leaf.sources())["binding"]
        other_base = tx.put_commit(tx.put_tree(values), parents=(base,))
    other_q = ex.record_exchange_request(path, commit=other_base, binding_name="sdk-other-binding", inputs_name="inputs",
        intent_uri=leaf.ADD, ref="sdk-other-Q")
    other = p.public_prepare(path, other_q.commit, "sdk-other-binding", "inputs", leaf.ADD, other_q.request)
    assert other.binding != current.binding
    original = p.public_prepare
    replacements = []
    def native_then_other(*a, **kw):
        actual = original(*a, **kw)
        actual_request = a[5] if len(a) > 5 else kw.get("request")
        if a[1] == cq and actual_request == own.request:
            assert (actual.binding, actual.inputs) == (current.binding, current.inputs)
            replacements.append(actual)
            return other  # Independent REAL SDK Spec, no forged field or inspector response.
        return actual
    monkeypatch.setattr(p, "public_prepare", native_then_other)
    with pytest.raises(ValueError, match=message):
        if case == "P535":
            p.inspect_leaf_success(path, commit=base, slot=seed["add_slot"])
        else:
            p.inspect_spine(path, target_prefix[0], target_got["request"], target_got["initial"], target_aid, set())
    assert replacements


@pytest.mark.parametrize("boundary,message", [
    ("select", "actual S must follow THIS joined phase"),
])
def test_closure_live_public_handoff_REAL_other_response(seed, tmp_path, monkeypatch, boundary, message):
    old_packet = seed["root"] / "HOST-two" / "packet-0"
    old_expected = seed["root"] / "HOST-two" / "expected-0.json"
    expected = ex.load_exchange_handle(old_expected).expected
    peer = ex.read_observation(old_packet, expected=expected)
    assert peer.completion.outcome == "success" and peer.request == expected.request
    publications = host_fixture.__wrapped__(monkeypatch)
    original_receive, original_select = ex.receive_exchange, p.selection.select
    if boundary == "receive":
        def actual_then_peer(*a, **kw):
            actual = original_receive(*a, **kw)
            assert actual.completion.outcome == "success" and actual.commit != peer.commit
            return peer
        monkeypatch.setattr(ex, "receive_exchange", actual_then_peer)
    else:
        def actual_then_peer_selection(*a, **kw):
            actual = original_select(*a, **kw)
            other_kw = dict(kw, packet=old_packet, expected_file=old_expected, ref=kw["ref"] + "-peer")
            other = original_select(*a, **other_kw)
            with d.Repository(a[0]) as repo, repo.read() as tx:
                assert p.single_delta(tx, actual.commit, (kw["slot"],)) == kw["commit"]
                assert p.single_delta(tx, other.commit, (kw["slot"],)) == kw["commit"]
                assert tx.get_ref(kw["ref"]) == actual.commit != other.commit
            assert p.selection.inspect(a[0], commit=other.commit, slot=kw["slot"]).dag == other.dag
            return other
        monkeypatch.setattr(p.selection, "select", actual_then_peer_selection)
    with closure_live(seed, tmp_path, monkeypatch, "getters", add_control="fresh", double_control="fresh") as session:
        with pytest.raises((ValueError, c.CallError), match=message):
            session.invoker.invoke(session.tokens[0], session.input)
        assert len(publications) == 1  # HOST publication assertion, Popen blocker; NOT OS custody census.


@pytest.mark.parametrize("case,message", [
    ("P262", "outer captured intent/retention differs"),
    ("P371", "only the two known leaf selection slots are supported"),
    ("P378", "adopted leaf selection intent/actual call differs"),
    ("P382", "initial known selection slot must be absent"),
    ("P619", "outer occurrence collision"),
    ("P719", "outer selection requires absent slot/retained completion"),
    ("P752", "outer F not retained by ALL-parent history"),
])
def test_closure_native_retention_adoption_and_occurrence(seed, tmp_path, monkeypatch, case, message):
    path, base = seed["path"], seed["backend"].current
    if case == "P262":
        with d.Repository(path) as repo, repo.write() as tx:
            original = c.inspect_closure(tx, p.tree(tx, base)["outer-A"])
            other_b = clone(tx, original.binding, fields={"adapter": b.literal(tx, d.Datum.uri("urn:example:other-inprocess"))})
            value = c.put_closure(tx, intent=p.INTENT, binding=other_b, environment=original.environment)
            assert c.inspect_closure(tx, value).intent == p.INTENT
        before = (path / "data.mdb").read_bytes()
        with d.Repository(path) as repo, repo.read() as tx:
            with pytest.raises(ValueError, match=message):
                p.inspect_closure(tx, base, value)
        assert (path / "data.mdb").read_bytes() == before
    elif case == "P619":
        actual = p.inspect_reuse(path, commit=base)
        nonce = p.uuid.UUID(actual.request_id.removeprefix("iq-"))
        monkeypatch.setattr(p.uuid, "uuid4", lambda: nonce)
        before = (path / "data.mdb").read_bytes()
        with pytest.raises(ValueError, match=message):
            p.record_request(path, commit=base, ref="collision-must-abort")
        assert (path / "data.mdb").read_bytes() == before
    elif case == "P719":
        before = (path / "data.mdb").read_bytes()
        with pytest.raises(ValueError, match=message):
            p.select_outer(path, commit=base, completion=seed["first"].commit, ref="duplicate-outer")
        assert (path / "data.mdb").read_bytes() == before
    elif case == "P752":
        # Actual S DAG retained, but inspected branch does NOT retain its completion ancestry.
        with d.Repository(path) as repo, repo.write() as tx:
            known = p.tree(tx, base)[p.SLOT]
            entries = p.tree(tx, seed["first"].request.base)
            entries[p.SLOT] = known
            branch = tx.put_commit(tx.put_tree(entries), parents=(seed["first"].request.base,))
        before = (path / "data.mdb").read_bytes()
        with pytest.raises(ValueError, match=message):
            p.inspect_selection(path, commit=branch)
        assert (path / "data.mdb").read_bytes() == before
    else:
        call = seed["got"]["calls"][1] if case == "P378" else seed["got"]["calls"][0]
        slot = "unsupported-slot" if case == "P371" else p.ADD_SLOT
        if case == "P382":
            base = p.pin_leaf(path, commit=base, call=call, slot=slot, ref="once-only-pin")
        before = (path / "data.mdb").read_bytes()
        with pytest.raises(ValueError, match=message):
            p.pin_leaf(path, commit=base, call=call, slot=slot, ref="pin-must-refuse-" + case)
        assert (path / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("case,message", [
    ("P470", "ORIGINAL leaf capture/input/fresh association differs"),
    ("P479", "ORIGINAL captured target/outer T/slot differs"),
])
def test_closure_PUBLIC_valid_ORIGINAL_D_first_authority(seed, tmp_path, case, message):
    changed = []
    def corrupt(read, write, old, fields, root):
        original = read.get_dag(old).bindings
        if ("role" in original and b.scalar(read, original["role"], "string") == p.LEAF_D_ROLE
            and b.scalar(read, original["slot"], "i64") == 0):
            if case == "P470":
                fields["control"] = b.literal(write, "reuse-selected")
            else:
                fields["slot"] = b.literal(write, 1)
            changed.append(old)
        return fields, root
    destination = tmp_path / "ORIGINAL.dml"
    current, mapping = rewrite(seed["path"], destination, seed["backend"].current, corrupt)
    assert changed
    public = p.selection.inspect(destination, commit=current, slot=seed["add_slot"])
    with d.Repository(destination) as repo, repo.read() as tx:
        assert b.Inspector(tx, commit=current).node(public.result).value == d.Datum.i64(42)
    before = (destination / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        p.inspect_leaf_success(destination, commit=current, slot=seed["add_slot"])
    assert (destination / "data.mdb").read_bytes() == before


def test_closure_initialT_exact_delta_and_real_missing_initial(seed, tmp_path):
    path, got, aid, prefix = closure_spine_positive(seed, "get-key-a")
    with d.Repository(path) as repo, repo.write() as tx:
        current = tx.get_commit(prefix[0]).parents[0]
        assert p.tree(tx, current)["outer-attempt-" + aid] == got["initial"]
        values = p.tree(tx, current)
        values["unrelated-real-C"] = got["closure"]["dag"]
        wrong = tx.put_commit(tx.put_tree(values), parents=tx.get_commit(current).parents)
        roots = [v for v in p.history(tx, seed["first"].commit) if not tx.get_commit(v).parents]
        assert roots
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="initial T exact delta differs"):
        p.inspect_spine(path, wrong, got["request"], got["initial"], aid, set())
    with pytest.raises(ValueError, match="bounded outer phase spine missing initial"):
        p.inspect_spine(path, roots[0], got["request"], got["initial"], aid, set())
    assert (path / "data.mdb").read_bytes() == before


def test_closure_real_reuse_Request_is_not_pending_fresh(seed, tmp_path):
    actual = p.inspect_reuse(seed["path"], commit=seed["backend"].current)
    assert isinstance(actual, p.Request) and actual.action == "reuse-selected"
    assert p.inspect_request(seed["path"], commit=actual.commit, request=actual.request) == actual
    before = (seed["path"] / "data.mdb").read_bytes()
    with pytest.raises(bridge.SessionError, match="only actual pending fresh outer Q may execute"):
        bridge.Session(seed["path"], actual, tmp_path / "NEVER-fresh-work")
    assert not (tmp_path / "NEVER-fresh-work").exists()
    assert (seed["path"] / "data.mdb").read_bytes() == before


def test_closure_real_postcommit_Q_ref_mutation_is_reported(seed, monkeypatch):
    path, base = seed["path"], seed["backend"].current
    original = d.Transaction.commit
    changed = []
    def actual_then_move(tx):
        original(tx)
        if not changed:
            with d.Repository(path) as repo, repo.read() as probe:
                try:
                    current = probe.get_ref("closure-postcommit-Q")
                except d.NotFoundError:
                    return
            with monkeypatch.context() as native_commit:
                native_commit.setattr(d.Transaction, "commit", original)
                with d.Repository(path) as repo, repo.write() as writer:
                    writer.update_ref("closure-postcommit-Q", base)
            changed.append(current)
    monkeypatch.setattr(d.Transaction, "commit", actual_then_move)
    with pytest.raises(ValueError, match="actual outer Q/decision/reservation refs differ"):
        p.record_request(path, commit=base, ref="closure-postcommit-Q")
    assert changed
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("closure-postcommit-Q") == base != changed[0]


@pytest.mark.parametrize("case,message", [
    ("P457", "ORIGINAL leaf decision absent/ambiguous"),
    ("P504", "ORIGINAL leaf preparation phase absent/ambiguous"),
    ("P482", "add Q must consume ORIGINAL exact outer input DAG"),
    ("P850", "outer return exact leaf R/owner/ledger differs"),
])
def test_closure_PUBLIC_valid_original_presence_source_and_return(seed, tmp_path, case, message):
    path, base = seed["path"], seed["backend"].current
    destination = tmp_path / "coherent-source.dml"
    with d.Repository(destination, create=True):
        pass
    # Only real public import preloads OTHER native DAG dependencies; no forward put_subdag.
    transfer.import_commit(destination, transfer.export_commit(path, commit=base), ref="preloaded")
    with d.Repository(path) as repo, repo.read() as tx:
        other = p.tree(tx, base)["other-input"]
        original = p.tree(tx, seed["first"].request.commit)["outer-request-" + seed["first"].request.request_id]
        query = tx.get_dag(original).bindings
        owner_decision = b.link(tx, query["decision"])
        outer_return = seed["got"]["result"]
        second_call = seed["got"]["calls"][1]
    changed = []
    def corrupt(read, write, old, fields, root):
        native = read.get_dag(old).bindings
        if case == "P457" and "role" in native and b.scalar(read, native["role"], "string") == p.LEAF_D_ROLE:
            fields["role"] = root = b.literal(write, "ordinary-unrelated-metadata")
            changed.append(old)
        elif case == "P504" and "role" in native and b.scalar(read, native["role"], "string") == p.PHASE_ROLE:
            if b.scalar(read, native["kind"], "string") == "leaf-prepare":
                fields["role"] = root = b.literal(write, "ordinary-unrelated-metadata")
                changed.append(old)
        elif case == "P482" and old in (original, owner_decision):
            write.get_dag(other)
            fields["inputs"] = write.put_subdag(other)
            if old == owner_decision:
                root = fields["inputs"]
            changed.append(old)
        elif case == "P850" and old == outer_return:
            write.get_dag(second_call)
            fields["call0"] = write.put_subdag(second_call)
            changed.append(old)
        return fields, root
    current, mapping = rewrite(path, destination, base, corrupt)
    assert changed
    public = p.selection.inspect(destination, commit=current, slot=seed["add_slot"])
    with d.Repository(destination) as repo, repo.read() as tx:
        assert b.Inspector(tx, commit=current).node(public.result).value == d.Datum.i64(42)
    before = (destination / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match=message):
        if case == "P850":
            p.inspect_completion(destination, commit=mapping[("commit", seed["first"].commit)])
        else:
            p.inspect_leaf_success(destination, commit=current, slot=seed["add_slot"])
    assert (destination / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("case,message", [
    ("P910", "reuse phase publication differs"),
    ("P916", "reuse phase W tree differs"),
    ("P1053", "reuse phase NEW Q/THIS D/pinned S/OLD T/R differs"),
    ("P1098", "reuse DONE requires pinned S and prior W only"),
    ("P1101", "failed DONE requires pending fresh F, not success S"),
])
def test_closure_reuse_prefix_public_W_and_done(seed, closure_failure, tmp_path, monkeypatch, case, message):
    with closure_live(seed, tmp_path, monkeypatch, "add") as session:
        transfer.import_commit(session.path, transfer.export_commit(closure_failure["path"], commit=closure_failure["final"]), ref="genuine-failure-peer")
        with d.Repository(session.path) as repo, repo.read() as tx:
            aid = session.aid
            kind = "leaf-done" if case in ("P1098", "P1101") else "leaf-reused"
            matches = []
            for current in p.history(tx, session.current):
                parents = tx.get_commit(current).parents
                if not parents:
                    continue
                now, old = p.tree(tx, current), p.tree(tx, parents[0])
                for name in set(now) - set(old):
                    if name.startswith("phase-" + aid + "-"):
                        fields = tx.get_dag(now[name]).bindings
                        if b.scalar(tx, fields["kind"], "string") == kind:
                            matches.append((current, name, now[name]))
            assert len(matches) == 1
            current, name, phase = matches[0]
        p.inspect_spine(session.path, current, session.q.request, session.initial, aid, set())
        other = p.selection.inspect(session.path, commit=session.current, slot=p.DOUBLE_SLOT)
        with d.Repository(session.path) as repo, repo.write() as tx:
            fields = dict(tx.get_dag(phase).bindings)
            previous = tx.get_commit(current).parents[0]
            values = p.tree(tx, current)
            index = b.scalar(tx, fields["index"], "i64")
            payloads = p.payload_names(aid, index, kind)
            if case == "P910":
                fields["reuse-commit"] = b.literal(tx, session.q.commit.bytes)
            elif case in ("P1098", "P1101"):
                done = b.link(tx, fields["call"])
                if case == "P1098":
                    wrong = clone(tx, done, fields={"selection-slot": b.literal(tx, seed["add_slot"])})
                else:
                    pending = b.link(tx, tx.get_dag(done).bindings["pending"])
                    wrong = b.record(tx, p.CALL_ROLE, values={"status": "failure"}, links={"pending": pending, "witness": closure_failure["witness"]})
                fields["call"] = tx.put_subdag(wrong)
                values[payloads["call"]] = wrong
            else:
                actual = b.link(tx, fields["reuse"])
                wrong = clone(tx, actual, fields={"attempt": tx.put_subdag(other.attempt)})
                fields["reuse"] = tx.put_subdag(wrong)
                values[payloads["reuse"]] = wrong
                if case == "P1053":
                    request = b.link(tx, tx.get_dag(actual).bindings["request"])
                    qid = b.scalar(tx, tx.get_dag(request).root, "string")
                    prior = p.tree(tx, previous)
                    prior["reuse-" + qid] = wrong
                    values["reuse-" + qid] = wrong
                    new_previous = tx.put_commit(tx.put_tree(prior), parents=tx.get_commit(previous).parents)
                    assert p.single_delta(tx, new_previous, ("reuse-" + qid,)) == tx.get_commit(previous).parents[0]
                    previous = new_previous
                    fields["previous"] = b.literal(tx, previous.bytes)
                    fields["reuse-commit"] = b.literal(tx, previous.bytes)
            new_phase = tx.put_dag(root=tx.get_dag(phase).root, bindings=fields)
            values[name] = new_phase
            variant = tx.put_commit(tx.put_tree(values), parents=(previous,))
        before = (session.path / "data.mdb").read_bytes()
        with pytest.raises(ValueError, match=message):
            p.inspect_spine(session.path, variant, session.q.request, session.initial, aid, set())
        assert (session.path / "data.mdb").read_bytes() == before


def test_closure_selected_tree_payload_source_and_ordinal(seed, tmp_path):
    path, got, aid, (current, name, phase) = closure_spine_positive(seed, "leaf-selected", 0)
    with d.Repository(path) as repo, repo.write() as tx:
        fields = dict(tx.get_dag(phase).bindings)
        values = p.tree(tx, current)
        selected_slot = b.scalar(tx, fields["selection-slot"], "string")
        index = b.scalar(tx, fields["index"], "i64")
        other = b.link(tx, tx.get_dag(got["calls"][1]).bindings["selection"])
        fields["selection"] = tx.put_subdag(other)
        values[p.payload_names(aid, index, "leaf-selected")["selection"]] = other
        values[name] = tx.put_dag(root=tx.get_dag(phase).root, bindings=fields)
        variant = tx.put_commit(tx.put_tree(values), parents=tx.get_commit(current).parents)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="selected phase S tree differs"):
        p.inspect_spine(path, variant, got["request"], got["initial"], aid, set())
    assert (path / "data.mdb").read_bytes() == before
    path, got, aid, (current, name, phase) = closure_spine_positive(seed, "get-key-a")
    with d.Repository(path) as repo, repo.write() as tx:
        previous = tx.get_commit(current).parents[0]
        values = p.tree(tx, previous)
        fields = dict(tx.get_dag(phase).bindings)
        fields["index"] = b.literal(tx, 1)
        values[p.payload_names(aid, 1, "get-key-a")["node"]] = b.link(tx, fields["node"])
        values[p.phase_name(aid, 1)] = tx.put_dag(root=tx.get_dag(phase).root, bindings=fields)
        variant = tx.put_commit(tx.put_tree(values), parents=(previous,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="phase positions not consecutive"):
        p.inspect_spine(path, variant, got["request"], got["initial"], aid, set())
    assert (path / "data.mdb").read_bytes() == before


def test_closure_initial_T_plan_and_error_reason_native(seed, tmp_path, monkeypatch):
    path, got, aid, (current, name, phase) = closure_spine_positive(seed, "get-key-a")
    peer = p.inspect_reuse(path, commit=seed["backend"].current)
    with d.Repository(path) as repo, repo.write() as tx:
        initial_commit = tx.get_commit(current).parents[0]
        before = tx.get_commit(initial_commit).parents[0]
        wrong_initial = clone(tx, got["initial"], fields={"plan": tx.put_subdag(peer.plan)})
        values = p.tree(tx, initial_commit)
        values["outer-attempt-" + aid] = wrong_initial
        variant = tx.put_commit(tx.put_tree(values), parents=(before,))
    baseline = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="ORIGINAL fresh outer Q/initial T/plan authority differs"):
        p.inspect_spine(path, variant, got["request"], wrong_initial, aid, set())
    assert (path / "data.mdb").read_bytes() == baseline
    with closure_live(seed, tmp_path, monkeypatch) as session:
        session.fail(bridge.SessionError("real known integration failure"))
        assert p.inspect_completion(session.path, commit=session.current)["outcome"] == "failure"
        with d.Repository(session.path) as repo, repo.write() as tx:
            parent = tx.get_commit(session.current).parents[0]
            old, now = p.tree(tx, parent), p.tree(tx, session.current)
            added = set(now) - set(old)
            assert len(added) == 1
            completion_name = added.pop()
            completion = now[completion_name]
            aid = session.aid
            wrong_f = clone(tx, completion, fields={"reason": b.literal(tx, "wrong-native-reason")})
            wrong_t = clone(tx, now["outer-attempt-" + aid], fields={"completion": tx.put_subdag(wrong_f)})
            now[completion_name] = wrong_f
            now["outer-attempt-" + aid] = wrong_t
            variant = tx.put_commit(tx.put_tree(now), parents=(parent,))
        baseline = (session.path / "data.mdb").read_bytes()
        with pytest.raises(ValueError, match="session failure detail differs"):
            p.inspect_completion(session.path, commit=variant)
        assert (session.path / "data.mdb").read_bytes() == baseline


@pytest.mark.parametrize("case,message", [("P1043", "fresh F join outside pending fresh call"), ("P1047", "reuse phase outside pinned reuse call")])
def test_closure_real_pending_mode_not_interchangeable_with_join_or_reuse(seed, tmp_path, monkeypatch, case, message):
    with closure_live(seed, tmp_path, monkeypatch, "add") as session:
        if case == "P1043":
            path, request, initial, aid = session.path, session.q.request, session.initial, session.aid
            with d.Repository(path) as repo, repo.read() as tx:
                prefixes = []
                for v in p.history(tx, session.current):
                    parents = tx.get_commit(v).parents
                    if not parents:
                        continue
                    old, now = p.tree(tx, parents[0]), p.tree(tx, v)
                    for name in set(now) - set(old):
                        if name.startswith("phase-" + aid + "-"):
                            fields = tx.get_dag(now[name]).bindings
                            if b.scalar(tx, fields["kind"], "string") == "leaf-pending":
                                prefixes.append((v, b.scalar(tx, fields["index"], "i64")))
                assert len(prefixes) == 1
                previous, prior_index = prefixes[0]
            selected = p.selection.inspect(path, commit=session.current, slot=p.ADD_SLOT)
            with d.Repository(path) as repo, repo.write() as tx:
                values = p.tree(tx, previous)
                index = prior_index + 1
                phase = p.event(tx, p.PHASE_ROLE, values={"kind": "leaf-join", "index": index, "previous": previous.bytes,
                    "completion": selected.completion.bytes}, links={"request": request, "initial-attempt": initial})
                values[p.phase_name(aid, index)] = phase
                variant = tx.put_commit(tx.put_tree(values), parents=(previous, selected.completion))
        else:
            path, got, aid, (previous, _, phase) = closure_spine_positive(seed, "leaf-pending", 0)
            request, initial = got["request"], got["initial"]
            selected = p.selection.inspect(seed["path"], commit=seed["backend"].current, slot=seed["add_slot"])
            with d.Repository(path) as repo, repo.write() as tx:
                fields = tx.get_dag(phase).bindings
                pending = tx.get_dag(b.link(tx, fields["call"])).bindings
                own_q = b.link(tx, pending["request"])
                qid = b.scalar(tx, tx.get_dag(own_q).root, "string")
                preparation = tx.get_commit(tx.get_commit(previous).parents[0]).parents[0]
                prep_values = p.tree(tx, preparation)
                decision = [v for n, v in prep_values.items() if n.endswith("decision") and n.startswith("payload-" + aid + "-")][-1]
                reuse = b.record(tx, p.LEAF_W_ROLE, links={"request": own_q, "decision": decision,
                    "selection": selected.dag, "attempt": selected.attempt, "result": selected.result}, root="result")
                values = p.tree(tx, previous)
                values["reuse-" + qid] = reuse
                publication = tx.put_commit(tx.put_tree(values), parents=(previous,))
                assert p.single_delta(tx, publication, ("reuse-" + qid,)) == previous
                index = b.scalar(tx, fields["index"], "i64") + 1
                phase = p.event(tx, p.PHASE_ROLE, values={"kind": "leaf-reused", "index": index, "previous": publication.bytes,
                    "reuse-commit": publication.bytes}, links={"request": request, "initial-attempt": initial, "reuse": reuse})
                values[p.payload_names(aid, index, "leaf-reused")["reuse"]] = reuse
                values[p.phase_name(aid, index)] = phase
                variant = tx.put_commit(tx.put_tree(values), parents=(publication,))
        before = (path / "data.mdb").read_bytes()
        with pytest.raises(ValueError, match=message):
            p.inspect_spine(path, variant, request, initial, aid, set())
        assert (path / "data.mdb").read_bytes() == before


def test_closure_failed_witness_actual_PUBLIC_F_not_other_joined_commit(closure_failure):
    path, got = closure_failure["path"], closure_failure["got"]
    received = p.inspect_failed_witness(path, closure_failure["final"], closure_failure["witness"], closure_failure["own_q"])
    assert received.completion.outcome == "failure"
    with d.Repository(path) as repo, repo.read() as tx:
        aid = b.scalar(tx, tx.get_dag(got["initial"]).root, "string")
        actual = []
        for current in p.history(tx, closure_failure["final"]):
            parents = tx.get_commit(current).parents
            if not parents:
                continue
            now, old = p.tree(tx, current), p.tree(tx, parents[0])
            for name in set(now) - set(old):
                if name.startswith("phase-" + aid + "-"):
                    fields = tx.get_dag(now[name]).bindings
                    kind = b.scalar(tx, fields["kind"], "string")
                    if kind in ("leaf-join", "leaf-done"):
                        actual.append((kind, current, name, now[name]))
        assert len(actual) == 2
        join = next(x for x in actual if x[0] == "leaf-join")
        done = next(x for x in actual if x[0] == "leaf-done")
        assert b.scalar(tx, tx.get_dag(join[3]).bindings["completion"], "bytes") == received.commit.bytes
        assert closure_failure["final"] != received.commit
    with d.Repository(path) as repo, repo.write() as tx:
        joined_fields = dict(tx.get_dag(join[3]).bindings)
        joined_fields["completion"] = b.literal(tx, closure_failure["final"].bytes)
        values = p.tree(tx, join[1])
        values[join[2]] = tx.put_dag(root=tx.get_dag(join[3]).root, bindings=joined_fields)
        wrong_join = tx.put_commit(tx.put_tree(values), parents=(tx.get_commit(join[1]).parents[0], closure_failure["final"]))
        done_fields = dict(tx.get_dag(done[3]).bindings)
        done_fields["previous"] = b.literal(tx, wrong_join.bytes)
        values = p.tree(tx, done[1])
        values[join[2]] = p.tree(tx, wrong_join)[join[2]]
        values[done[2]] = tx.put_dag(root=tx.get_dag(done[3]).root, bindings=done_fields)
        variant = tx.put_commit(tx.put_tree(values), parents=(wrong_join,))
        assert received.commit in p.history(tx, variant)  # Actual failed F retained through real outer completion.
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="failed call witness must certify THIS joined F"):
        p.inspect_spine(path, variant, got["request"], got["initial"], aid, set())
    assert (path / "data.mdb").read_bytes() == before


def test_closure_actual_required_pinned_plan_miss_before_pending(seed, tmp_path, monkeypatch):
    with closure_live(seed, tmp_path, monkeypatch, "getters", changed=True) as session:
        selected = p.selection.inspect(session.path, commit=session.q.base, slot=p.ADD_SLOT)
        with d.Repository(session.path) as repo, repo.read() as tx:
            actual, _ = p.arguments(tx, session.current, session.q.inputs.dag, ("a", "b"), set())
            old, _ = p.arguments(tx, session.current, selected.inputs, ("a", "b"), set())
            assert actual.datum != old.datum
            fields = tx.get_dag(session.q.plan).bindings
            assert b.scalar(tx, fields["add-control"], "string") == "require-selected"
        prefix = p.inspect_spine(session.path, session.current, session.q.request, session.initial, session.aid, set())
        assert len(prefix["getters"]) == 2 and not prefix["calls"]
        with d.Repository(session.path) as repo, repo.write() as tx:
            previous, index = session.current, session.index
            names = p.payload_names(session.aid, index, "leaf-prepare")
            target = session.q.closure["add"]
            decision = b.record(tx, p.LEAF_D_ROLE, values={"slot": 0, "control": "fresh", "binding-name": names["binding"],
                "inputs-name": names["inputs"], "basis": previous.bytes}, links={"outer-request": session.q.request,
                "outer-attempt": session.initial, "closure": target["dag"], "binding": target["binding"],
                "environment": target["environment"], "inputs": session.q.inputs.dag})
            phase = p.event(tx, p.PHASE_ROLE, values={"kind": "leaf-prepare", "index": index, "previous": previous.bytes, "slot": 0},
                links={"request": session.q.request, "initial-attempt": session.initial, "decision": decision,
                    "binding": target["binding"], "inputs": session.q.inputs.dag})
            values = p.tree(tx, previous)
            values.update({names["decision"]: decision, names["binding"]: target["binding"], names["inputs"]: session.q.inputs.dag,
                p.phase_name(session.aid, index): phase})
            variant = tx.put_commit(tx.put_tree(values), parents=(previous,))
        before = (session.path / "data.mdb").read_bytes()
        with pytest.raises(ValueError, match="required pinned leaf selection mismatch"):
            p.inspect_spine(session.path, variant, session.q.request, session.initial, session.aid, set())
        assert (session.path / "data.mdb").read_bytes() == before


def test_closure_live_receive_REAL_other_public_response(seed, tmp_path, monkeypatch):
    expected = ex.load_exchange_handle(seed["root"] / "HOST-two" / "expected-0.json").expected
    peer = ex.read_observation(seed["root"] / "HOST-two" / "packet-0", expected=expected)
    assert peer.completion.outcome == "success"
    original = ex.receive_exchange
    replaced = []
    def actual_then_peer(*args, **kwargs):
        actual = original(*args, **kwargs)
        assert type(actual) is type(peer)
        assert actual.completion.outcome == "success" and actual.commit != peer.commit
        replaced.append(actual)
        return peer
    publications = host_fixture.__wrapped__(monkeypatch)
    monkeypatch.setattr(ex, "receive_exchange", actual_then_peer)
    with closure_live(seed, tmp_path, monkeypatch, "getters", add_control="fresh", double_control="fresh") as session:
        with pytest.raises((ValueError, c.CallError), match="public completion/observation differs"):
            session.invoker.invoke(session.tokens[0], session.input)
        assert len(publications) == 1 and replaced


def test_closure_PUBLIC_valid_leaf_original_requires_full_outer_getter_prefix(seed, tmp_path):
    """P527 ONLY: fixed parent-aware public copy, no shared rewriter/inspector/packed-codec patch."""
    import json
    source = seed["path"]
    _, got, aid, get_a = closure_spine_positive(seed, "get-a")
    _, _, _, get_b = closure_spine_positive(seed, "get-b")
    with d.Repository(source) as repo, repo.read() as tx:
        a_tree, b_tree = p.tree(tx, get_a[0]), p.tree(tx, get_b[0])
        skipped = set(b_tree) - set(a_tree)
        assert len(skipped) == 6
        assert all(n.startswith(("phase-" + aid + "-", "payload-" + aid + "-")) for n in skipped)
    destination = tmp_path / "short-getter-prefix.dml"
    mapped = {}
    def remap_bytes(raw):
        if len(raw) == 16:
            for (_, old), new in mapped.items():
                if old.bytes == raw:
                    return new.bytes
        if raw.startswith(b"{"):
            try:
                value = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                return raw
            def header(value):
                if type(value) is str:
                    for (_, old), new in mapped.items():
                        if value == str(old):
                            return str(new)
                if type(value) is list:
                    return [header(v) for v in value]
                if type(value) is dict:
                    return {n: header(v) for n, v in value.items()}
                return value
            return json.dumps(header(value), separators=(",", ":")).encode()
        return raw
    with d.Repository(source) as src, src.read() as read, d.Repository(destination, create=True) as dst, dst.write() as write:
        def copy(kind, old):
            key = (kind, old)
            if key in mapped:
                return mapped[key]
            if kind == "commit" and old == get_b[0]:
                new = copy("commit", get_a[0])
            elif kind == "commit":
                actual = read.get_commit(old)
                parents = tuple(copy("commit", p_) for p_ in actual.parents)
                new = write.put_commit(copy("tree", actual.tree), parents=parents)
            elif kind == "tree":
                new = write.put_tree({n: copy("dag", value) for n, value in read.get_tree(old).items() if n not in skipped})
            elif kind == "dag":
                actual = read.get_dag(old)
                fields = {n: copy("node", value) for n, value in actual.bindings.items()}
                new = write.put_dag(root=copy("node", actual.root), bindings=fields)
            elif kind == "node":
                actual = read.get_node(old)
                new = write.put_literal(copy("datum", actual.datum)) if isinstance(actual, d.LiteralNode) else write.put_subdag(copy("dag", actual.dag))
            else:
                actual = read.get_datum(old)
                if actual.kind == "bytes":
                    actual = d.Datum.bytes(remap_bytes(actual.value))
                elif actual.kind in ("list", "set"):
                    actual = d.Datum(actual.kind, tuple(copy("datum", value) for value in actual.value))
                elif actual.kind == "map":
                    actual = d.Datum.map((copy("datum", k), copy("datum", v)) for k, v in actual.value)
                new = write.put_datum(actual)
            mapped[key] = new
            return new
        current = copy("commit", seed["backend"].current)
        write.create_ref("short-prefix", current)
        assert mapped[("commit", get_b[0])] == mapped[("commit", get_a[0])]
    public = p.selection.inspect(destination, commit=current, slot=seed["add_slot"])
    with d.Repository(destination) as repo, repo.read() as tx:
        inspector = b.Inspector(tx, commit=current)
        result = inspector.node(public.result)
        assert result.value == d.Datum.i64(42)
        returned = tx.get_dag(public.result).bindings
        trace = inspector.trace(b.link(tx, returned["trace"]), request=public.request, inputs=public.inputs)
        assert len(trace) == len(leaf.contract(leaf.ADD)[1]) == 2
        pre = tx.get_commit(public.completion).parents[0]
        cq = tx.get_commit(pre).parents[0]
        dc = tx.get_commit(cq).parents[0]
        basis = tx.get_commit(dc).parents[0]
        assert basis == mapped[("commit", get_a[0])]
        old, now = p.tree(tx, basis), p.tree(tx, dc)
        declarations = [(n, v) for n, v in now.items() if n not in old and "role" in tx.get_dag(v).bindings
            and b.scalar(tx, tx.get_dag(v).bindings["role"], "string") == p.LEAF_D_ROLE]
        phases = [(n, v) for n, v in now.items() if n not in old and "role" in tx.get_dag(v).bindings
            and b.scalar(tx, tx.get_dag(v).bindings["role"], "string") == p.PHASE_ROLE]
        assert len(declarations) == len(phases) == 1
        decision_name, decision = declarations[0]
        phase_name, phase = phases[0]
        df, pf = tx.get_dag(decision).bindings, tx.get_dag(phase).bindings
        assert p.oid(tx, df["basis"]) == basis  # Exact466 earlier-stage positive.
        assert p.oid(tx, pf["previous"]) == basis
        index = b.scalar(tx, pf["index"], "i64")
        names = p.payload_names(aid, index, "leaf-prepare")
        assert phase_name == p.phase_name(aid, index)
        assert set(now) - set(old) == set(names.values()) | {phase_name}
        assert all(now[n] == value for n, value in old.items())
        assert b.scalar(tx, pf["kind"], "string") == "leaf-prepare" and b.scalar(tx, pf["slot"], "i64") == 0
        assert decision_name == names["decision"] and b.link(tx, pf["decision"]) == decision
        assert all(now[names[n]] == b.link(tx, pf[n]) for n in ("decision", "binding", "inputs"))
        assert b.link(tx, pf["request"]) == b.link(tx, df["outer-request"]) == mapped[("dag", got["request"])]
        assert b.link(tx, pf["initial-attempt"]) == b.link(tx, df["outer-attempt"]) == mapped[("dag", got["initial"])]
        assert b.link(tx, pf["inputs"]) == b.link(tx, df["inputs"]) == public.inputs
        assert b.link(tx, pf["binding"]) == b.link(tx, df["binding"]) == public.binding
        assert b.scalar(tx, df["binding-name"], "string") == names["binding"]
        assert b.scalar(tx, df["inputs-name"], "string") == names["inputs"]
        assert b.scalar(tx, df["slot"], "i64") == 0 and b.scalar(tx, df["control"], "string") == "fresh"
    prefix = p.inspect_spine(destination, basis, mapped[("dag", got["request"])], mapped[("dag", got["initial"])], aid, set())
    assert len(prefix["getters"]) == 1 and not prefix["calls"] and prefix["failed"] is None and prefix["returned"] is None
    before = (destination / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="ORIGINAL leaf requires exact outer getter/call/input prefix"):
        p.inspect_leaf_success(destination, commit=current, slot=seed["add_slot"])
    assert (destination / "data.mdb").read_bytes() == before



def test_closure_reuse_ownQ_alias_is_NOT_fresh_original_join(seed, tmp_path, monkeypatch):
    """P1114 counterexample: real namespace-legal Q ID dedup, not a fake Request/inspector."""
    with closure_live(seed, tmp_path, monkeypatch, "getters", alias_basis=True) as session:
        selected = p.selection.inspect(session.path, commit=session.q.base, slot=p.ADD_SLOT)
        with d.Repository(session.path) as repo, repo.read() as tx:
            old_qid = b.scalar(tx, tx.get_dag(selected.request).root, "string")
            assert "request-" + old_qid not in p.tree(tx, session.current)
            assert p.tree(tx, session.current)[p.ADD_SLOT] == selected.dag
            with pytest.raises(d.NotFoundError):
                tx.get_ref("request-" + old_qid)
        nonce = ex.uuid.UUID(old_qid.removeprefix("q-"))
        original_phase = session._phase
        alias = []
        def actual_then_validate(kind, **kw):
            result = original_phase(kind, **kw)
            if kind == "leaf-pending":
                with d.Repository(session.path) as repo, repo.read() as tx:
                    fields = tx.get_dag(result["call"]).bindings
                    assert b.link(tx, fields["request"]) == selected.request
                    assert b.scalar(tx, fields["control"], "string") == "reuse-selected"
                alias.append(result["call"])
            return result
        monkeypatch.setattr(session, "_phase", actual_then_validate)
        with monkeypatch.context() as namespace:
            namespace.setattr(ex.uuid, "uuid4", lambda: nonce)
            with pytest.raises((ValueError, c.CallError), match="fresh call ORIGINAL Q/joined F differs"):
                session.invoker.invoke(session.tokens[0], session.input)
        assert alias


@pytest.fixture(scope="module")
def closure_failure(seed, tmp_path_factory):
    root = tmp_path_factory.mktemp("closure-failure")
    path = root / "caller.dml"
    with d.Repository(path, create=True):
        pass
    base = transfer.import_commit(path, transfer.export_commit(seed["path"], commit=seed["backend"].current), ref="base").commit
    with pytest.MonkeyPatch.context() as patch:
        publications = host_fixture.__wrapped__(patch)
        original = local._execute
        def observed_failure(context, source, interpreter, timeout):
            observed = original(context, source, interpreter, timeout)
            # Existing qualified HOST failure protocol; NOT an OS exit/custody assertion.
            return local._Observation(7, "child-exit", "HOST nonzero AFTER native publication", observed.stdout, observed.stderr)
        patch.setattr(local, "_execute", observed_failure)
        request = p.record_request(path, commit=base, ref="failure-owner")
        final = adapter.execute(path, request, workspace=root / "HOST-one")
        assert len(publications) == 1
    got = p.inspect_completion(path, commit=final)
    assert got["outcome"] == "failure" and len(got["calls"]) == 1
    with d.Repository(path) as repo, repo.read() as tx:
        done = tx.get_dag(got["calls"][0]).bindings
        pending = tx.get_dag(b.link(tx, done["pending"])).bindings
        witness, own_q = b.link(tx, done["witness"]), b.link(tx, pending["request"])
    received = p.inspect_failed_witness(path, final, witness, own_q)
    assert received.completion.outcome == "failure" and received.completion.exit_code == 7
    return dict(path=path, final=final, request=request, got=got, witness=witness, own_q=own_q, root=root)


def test_closure_failed_PUBLIC_return_contract_REAL_other_success(seed, closure_failure, monkeypatch):
    old_expected = ex.load_exchange_handle(seed["root"] / "HOST-two" / "expected-0.json").expected
    peer = ex.read_observation(seed["root"] / "HOST-two" / "packet-0", expected=old_expected)
    assert peer.completion.outcome == "success"
    original = ex.read_observation
    seen = []
    def actual_then_peer(*args, **kwargs):
        actual = original(*args, **kwargs)
        assert actual.completion.outcome == "failure" and actual.request == closure_failure["own_q"]
        seen.append(actual)
        return peer
    monkeypatch.setattr(ex, "read_observation", actual_then_peer)
    before = (closure_failure["path"] / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="failed witness PUBLIC completion differs"):
        p.inspect_failed_witness(closure_failure["path"], closure_failure["final"], closure_failure["witness"], closure_failure["own_q"])
    assert seen and (closure_failure["path"] / "data.mdb").read_bytes() == before


def test_closure_reuse_W_actual_native_old_attempt_association(seed, tmp_path, monkeypatch):
    with closure_live(seed, tmp_path, monkeypatch, "add") as session:
        with d.Repository(session.path) as repo, repo.read() as tx:
            actual = tx.get_dag(session.calls[0]).bindings
            pending = tx.get_dag(b.link(tx, actual["pending"])).bindings
            own_q = b.link(tx, pending["request"])
            qid = b.scalar(tx, tx.get_dag(own_q).root, "string")
            reuse = p.tree(tx, session.current)["reuse-" + qid]
            decision = b.link(tx, tx.get_dag(reuse).bindings["decision"])
        selected = p.selection.inspect(session.path, commit=session.current, slot=p.ADD_SLOT)
        other = p.selection.inspect(session.path, commit=session.current, slot=p.DOUBLE_SLOT)
        with d.Repository(session.path) as repo, repo.read() as tx:
            p.inspect_leaf_reuse(tx, session.current, own_q, selected, decision)
        with d.Repository(session.path) as repo, repo.write() as tx:
            wrong = clone(tx, reuse, fields={"attempt": tx.put_subdag(other.attempt)})
            values = p.tree(tx, session.current)
            values["reuse-" + qid] = wrong
            variant = tx.put_commit(tx.put_tree(values), parents=(session.current,))
        before = (session.path / "data.mdb").read_bytes()
        with d.Repository(session.path) as repo, repo.read() as tx:
            with pytest.raises(ValueError, match="leaf ownQ/THIS D/pinned S/OLD T/R W differs"):
                p.inspect_leaf_reuse(tx, variant, own_q, selected, decision)
        assert (session.path / "data.mdb").read_bytes() == before
