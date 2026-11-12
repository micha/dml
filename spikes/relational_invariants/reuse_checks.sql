-- Selected independent graph obligations for retained composed-node reuse.
-- Not a replacement for public packet, execution, or full profile validation.
CREATE OR REPLACE VIEW h_fields AS
SELECT f.dag, f.name, f.node, n.kind AS node_kind, n.target,
       d.kind AS datum_kind, d.scalar
FROM fields f LEFT JOIN nodes n ON n.oid = f.node
LEFT JOIN datums d ON n.kind = 'literal' AND d.oid = n.target;
CREATE OR REPLACE VIEW h_roles AS
SELECT dag, scalar AS role FROM h_fields
WHERE name = 'role' AND node_kind = 'literal' AND datum_kind = 'string';
CREATE OR REPLACE VIEW h_values AS
SELECT dag, target AS value_id FROM h_fields WHERE name = 'value' AND node_kind = 'literal';
CREATE OR REPLACE VIEW h_requests AS
SELECT p.dag, occurrence.scalar AS occurrence, intent.scalar AS intent,
       binding.target AS binding, inputs.target AS inputs
FROM h_roles p JOIN dags d ON d.oid = p.dag
LEFT JOIN nodes n ON n.oid = d.root
LEFT JOIN datums occurrence ON occurrence.oid = n.target AND occurrence.kind = 'string'
LEFT JOIN h_fields intent ON intent.dag = p.dag AND intent.name = 'intent'
LEFT JOIN h_fields binding ON binding.dag = p.dag AND binding.name = 'binding'
LEFT JOIN h_fields inputs ON inputs.dag = p.dag AND inputs.name = 'inputs'
WHERE p.role = 'local-request-v1';
CREATE OR REPLACE VIEW h_attempts AS
SELECT p.dag, occurrence.scalar AS occurrence, request.target AS request,
       outcome.target AS outcome, status.scalar AS status
FROM h_roles p JOIN dags d ON d.oid = p.dag
LEFT JOIN nodes n ON n.oid = d.root
LEFT JOIN datums occurrence ON occurrence.oid = n.target AND occurrence.kind = 'string'
LEFT JOIN h_fields request ON request.dag = p.dag AND request.name = 'request'
LEFT JOIN h_fields outcome ON outcome.dag = p.dag AND outcome.name = 'outcome'
LEFT JOIN h_fields status ON status.dag = p.dag AND status.name = 'status'
WHERE p.role = 'local-attempt-v1';
CREATE OR REPLACE VIEW h_arguments AS
SELECT a.dag AS arguments, slot.name AS position, slot.target AS entry,
       k.target AS key_id, k.scalar AS key_name, s.target AS source, v.value_id
FROM h_roles a
JOIN h_fields ledger ON ledger.dag = a.dag AND ledger.name = 'entries'
JOIN h_fields slot ON slot.dag = ledger.target AND slot.name <> 'role'
LEFT JOIN h_fields k ON k.dag = slot.target AND k.name = 'key'
LEFT JOIN h_fields s ON s.dag = slot.target AND s.name = 'source'
LEFT JOIN h_values v ON v.dag = s.target
WHERE a.role = 'builtin-arguments-v1';
CREATE OR REPLACE VIEW h_expected_arguments AS
SELECT a.dag AS arguments, m.key_id, m.value_id FROM h_roles a
JOIN h_values v ON v.dag = a.dag JOIN map_entries m ON m.oid = v.value_id
WHERE a.role = 'builtin-arguments-v1';
CREATE OR REPLACE VIEW h_operations AS
SELECT p.dag, f.scalar AS func, b.target AS binding, a.target AS arguments, v.value_id
FROM h_roles p
LEFT JOIN h_fields f ON f.dag = p.dag AND f.name = 'func'
LEFT JOIN h_fields b ON b.dag = p.dag AND b.name = 'binding'
LEFT JOIN h_fields a ON a.dag = p.dag AND a.name = 'arguments'
LEFT JOIN h_values v ON v.dag = p.dag
WHERE p.role = 'builtin-operation-v1';
CREATE OR REPLACE VIEW h_trace_positions AS
SELECT p.dag AS trace, f.name AS position, f.target AS operation
FROM h_roles p JOIN h_fields f ON f.dag = p.dag AND starts_with(f.name, 'call-')
WHERE p.role = 'builtin-trace-v1';
CREATE OR REPLACE VIEW h_selections AS
SELECT p.dag, request.target AS request, attempt.target AS attempt, result.target AS result,
       binding.target AS binding, inputs.target AS inputs, intent.scalar AS intent,
       completion.scalar AS completion
FROM h_roles p
LEFT JOIN h_fields request ON request.dag = p.dag AND request.name = 'request'
LEFT JOIN h_fields attempt ON attempt.dag = p.dag AND attempt.name = 'attempt'
LEFT JOIN h_fields result ON result.dag = p.dag AND result.name = 'result'
LEFT JOIN h_fields binding ON binding.dag = p.dag AND binding.name = 'binding'
LEFT JOIN h_fields inputs ON inputs.dag = p.dag AND inputs.name = 'inputs'
LEFT JOIN h_fields intent ON intent.dag = p.dag AND intent.name = 'intent'
LEFT JOIN h_fields completion ON completion.dag = p.dag AND completion.name = 'completion'
WHERE p.role = 'example-reuse-selection-v1';
CREATE OR REPLACE VIEW h_reached AS
WITH RECURSIVE reached(root, kind, oid) AS (
 SELECT DISTINCT commit_id, 'commit', commit_id FROM roots
 UNION
 SELECT r.root, e.dst_kind, e.dst FROM reached r
 JOIN edges e ON e.src_kind = r.kind AND e.src = r.oid
) SELECT * FROM reached;
CREATE OR REPLACE VIEW h_ancestry AS
WITH RECURSIVE ancestry(descendant, ancestor) AS (
 SELECT oid, oid FROM commits
 UNION
 SELECT a.descendant, e.dst FROM ancestry a
 JOIN edges e ON e.src = a.ancestor AND e.src_kind = 'commit'
 AND e.dst_kind = 'commit' AND starts_with(e.label, 'parent-')
) SELECT * FROM ancestry;
CREATE OR REPLACE VIEW h_contexts AS
SELECT c.*, q.occurrence, q.intent, q.binding, q.inputs AS actual_inputs,
       parent.dst AS decision_commit, dt.dag AS decision_dag, basis.dst AS basis,
       action.scalar AS action, selected.target AS selection,
       wt.dag AS satisfaction_dag, wr.target AS satisfied_request,
       wa.target AS satisfied_attempt, result.target AS satisfied_result
FROM request_contexts c
LEFT JOIN h_requests q ON q.dag = c.request
LEFT JOIN edges parent ON parent.src = c.commit AND parent.src_kind = 'commit' AND parent.label = 'parent-0'
LEFT JOIN commits dc ON dc.oid = parent.dst
LEFT JOIN tree_entries dt ON dt.oid = dc.tree_id AND dt.name = c.decision
LEFT JOIN edges basis ON basis.src = dc.oid AND basis.src_kind = 'commit' AND basis.label = 'parent-0'
LEFT JOIN h_fields action ON action.dag = dt.dag AND action.name = 'action'
LEFT JOIN h_fields selected ON selected.dag = dt.dag AND selected.name = 'selection'
LEFT JOIN commits wc ON wc.oid = c.satisfaction
LEFT JOIN tree_entries wt ON wt.oid = wc.tree_id AND wt.name = 'reuse-' || q.occurrence
LEFT JOIN h_fields wr ON wr.dag = wt.dag AND wr.name = 'request'
LEFT JOIN h_fields wa ON wa.dag = wt.dag AND wa.name = 'attempt'
LEFT JOIN h_fields result ON result.dag = wt.dag AND result.name = 'result';

CREATE OR REPLACE VIEW h_shape_rules AS
SELECT * FROM (VALUES
 ('local-request-v1', ['role','intent','binding','inputs'], NULL),
 ('example-reuse-selection-v1', ['role','intent','binding','inputs','request','attempt','result','completion','validation'], 'result'),
 ('example-explicit-reuse-v1', ['role','request','attempt','result'], 'result'),
 ('example-node-composition-v1', ['role','arguments','key','selection-slot','selection','result'], 'role'),
 ('builtin-arguments-v1', ['role','value','entries'], 'value'),
 ('builtin-argument-entry-v1', ['role','key','source'], 'role'),
 ('builtin-operation-v1', ['role','func','binding','arguments','value'], 'value'),
 ('builtin-return-v1', ['role','returned','value','trace','request','inputs'], 'value'),
 ('builtin-literal-v1', ['role','value'], 'value'),
 ('builtin-binding-v1', ['role','adapter','interpreter','timeout-ms','source'], 'role')
) AS t(role, names, root_field);
CREATE OR REPLACE VIEW h_field_sets AS
SELECT dag, list(name ORDER BY name) AS names FROM fields GROUP BY dag;
CREATE OR REPLACE VIEW h_w_tree AS
SELECT c.request, t.name, t.dag FROM h_contexts c
JOIN commits w ON w.oid = c.satisfaction JOIN tree_entries t ON t.oid = w.tree_id
WHERE t.name <> 'reuse-' || c.occurrence;
CREATE OR REPLACE VIEW h_q_tree AS
SELECT c.request, t.name, t.dag FROM h_contexts c
JOIN commits q ON q.oid = c.commit JOIN tree_entries t ON t.oid = q.tree_id;

CREATE OR REPLACE VIEW reuse_violations AS
SELECT 'missing_object' AS invariant, e.src AS subject, e.label AS detail
FROM edges e LEFT JOIN objects o ON o.kind = e.dst_kind AND o.oid = e.dst
WHERE o.oid IS NULL
UNION ALL
SELECT 'empty_contexts', 'dataset', 'no request contexts'
WHERE NOT EXISTS (SELECT 1 FROM request_contexts)
UNION ALL
SELECT 'profile_shape', p.dag, p.role
FROM h_roles p JOIN h_shape_rules rule ON rule.role = p.role
LEFT JOIN h_field_sets f ON f.dag = p.dag
LEFT JOIN dags d ON d.oid = p.dag
LEFT JOIN fields root ON root.dag = p.dag AND root.name = rule.root_field
WHERE f.names IS DISTINCT FROM list_sort(rule.names)
 OR (rule.root_field IS NOT NULL AND d.root IS DISTINCT FROM root.node)
UNION ALL
SELECT 'satisfaction_tree_delta', COALESCE(q.request, w.request), COALESCE(q.name, w.name)
FROM h_q_tree q FULL OUTER JOIN h_w_tree w ON w.request = q.request AND w.name = q.name
WHERE q.dag IS DISTINCT FROM w.dag
UNION ALL
SELECT 'context_available', c.request, 'own Q/decision/W or pinned root absent'
FROM h_contexts c
LEFT JOIN h_roles d ON d.dag = c.decision_dag
LEFT JOIN h_roles w ON w.dag = c.satisfaction_dag
WHERE c.occurrence IS DISTINCT FROM c.request_id OR c.actual_inputs IS DISTINCT FROM c.inputs
 OR c.action IS DISTINCT FROM 'reuse-selected'
 OR d.role IS DISTINCT FROM 'example-composed-node-decision-v1'
 OR w.role IS DISTINCT FROM 'example-explicit-reuse-v1'
 OR NOT EXISTS (SELECT 1 FROM roots r WHERE r.commit_id = c.commit)
 OR NOT EXISTS (SELECT 1 FROM roots r WHERE r.commit_id = c.satisfaction)
UNION ALL
SELECT 'own_request_dimensions', c.request, 'Q differs from its declared decision'
FROM h_contexts c
LEFT JOIN h_fields intent ON intent.dag = c.decision_dag AND intent.name = 'intent'
LEFT JOIN h_fields binding ON binding.dag = c.decision_dag AND binding.name = 'binding'
LEFT JOIN h_fields inputs ON inputs.dag = c.decision_dag AND inputs.name = 'inputs'
LEFT JOIN h_fields value ON value.dag = c.decision_dag AND value.name = 'value'
LEFT JOIN h_values actual ON actual.dag = c.actual_inputs
WHERE c.intent IS DISTINCT FROM intent.scalar OR c.binding IS DISTINCT FROM binding.target
 OR c.actual_inputs IS DISTINCT FROM inputs.target OR value.target IS DISTINCT FROM actual.value_id
UNION ALL
SELECT 'selected_slot', c.request, 'basis slot does not contain captured S'
FROM h_contexts c
LEFT JOIN h_fields slot ON slot.dag = c.decision_dag AND slot.name = 'selection-slot'
LEFT JOIN commits basis ON basis.oid = c.basis
LEFT JOIN tree_entries entry ON entry.oid = basis.tree_id AND entry.name = slot.scalar
WHERE c.selection IS NULL OR entry.dag IS DISTINCT FROM c.selection
UNION ALL
SELECT 'reuse_value', c.request, 'func/full MAP value does not match selected producer'
FROM h_contexts c LEFT JOIN h_selections s ON s.dag = c.selection
LEFT JOIN h_values requested ON requested.dag = c.actual_inputs
LEFT JOIN h_values produced ON produced.dag = s.inputs
WHERE s.dag IS NULL OR c.intent IS DISTINCT FROM s.intent
 OR requested.value_id IS NULL OR requested.value_id IS DISTINCT FROM produced.value_id
UNION ALL
SELECT 'reuse_association', c.request, 'W must preserve own Q and OLD selected T/R'
FROM h_contexts c LEFT JOIN h_selections s ON s.dag = c.selection
WHERE c.satisfied_request IS DISTINCT FROM c.request
 OR c.satisfied_attempt IS DISTINCT FROM s.attempt OR c.satisfied_result IS DISTINCT FROM s.result
UNION ALL
SELECT 'reuse_new_attempt', c.request, a.dag
FROM h_contexts c JOIN h_attempts a ON a.request = c.request
UNION ALL
SELECT 'successful_selection', s.dag, 'S/Q/T/success/result dimensions differ'
FROM h_selections s LEFT JOIN h_requests q ON q.dag = s.request
LEFT JOIN h_attempts a ON a.dag = s.attempt
LEFT JOIN h_roles outcome ON outcome.dag = a.outcome
LEFT JOIN h_fields result ON result.dag = a.outcome AND result.name = 'result'
LEFT JOIN h_roles returned ON returned.dag = s.result
LEFT JOIN h_fields owner ON owner.dag = s.result AND owner.name = 'request'
LEFT JOIN h_fields inputs ON inputs.dag = s.result AND inputs.name = 'inputs'
LEFT JOIN commits completion ON completion.oid = s.completion
LEFT JOIN tree_entries final_attempt ON final_attempt.oid = completion.tree_id AND final_attempt.name = 'attempt-' || a.occurrence
WHERE q.dag IS NULL OR a.request IS DISTINCT FROM s.request OR a.status IS DISTINCT FROM 'done'
 OR outcome.role IS DISTINCT FROM 'local-success-v1' OR result.target IS DISTINCT FROM s.result
 OR returned.role IS DISTINCT FROM 'builtin-return-v1'
 OR owner.target IS DISTINCT FROM s.request OR inputs.target IS DISTINCT FROM s.inputs
 OR q.intent IS DISTINCT FROM s.intent OR q.binding IS DISTINCT FROM s.binding OR q.inputs IS DISTINCT FROM s.inputs
 OR final_attempt.dag IS DISTINCT FROM s.attempt
UNION ALL
SELECT 'completion_retention', c.request, 'selected F absent from basis all-parent ancestry'
FROM h_contexts c LEFT JOIN h_selections s ON s.dag = c.selection
WHERE NOT EXISTS (SELECT 1 FROM h_ancestry a WHERE a.descendant = c.basis AND a.ancestor = s.completion)
UNION ALL
SELECT 'argument_sources', COALESCE(a.arguments, e.arguments), COALESCE(a.key_id, e.key_id)
FROM h_arguments a FULL OUTER JOIN h_expected_arguments e
 ON a.arguments = e.arguments AND a.key_id = e.key_id
WHERE a.arguments IS NULL OR e.arguments IS NULL OR a.value_id IS DISTINCT FROM e.value_id
UNION ALL
SELECT 'duplicate_argument', arguments, key_id
FROM h_arguments GROUP BY arguments, key_id HAVING count(*) <> 1
UNION ALL
SELECT 'composition_provenance', p.dag, 'argument x must preserve exact selected OUTER R'
FROM h_roles p
LEFT JOIN h_fields args ON args.dag = p.dag AND args.name = 'arguments'
LEFT JOIN h_fields selection ON selection.dag = p.dag AND selection.name = 'selection'
LEFT JOIN h_fields result ON result.dag = p.dag AND result.name = 'result'
LEFT JOIN h_selections s ON s.dag = selection.target
LEFT JOIN h_arguments a ON a.arguments = args.target AND a.key_name = 'x'
WHERE p.role = 'example-node-composition-v1'
 AND (s.dag IS NULL OR result.target IS DISTINCT FROM s.result OR a.source IS DISTINCT FROM s.result)
UNION ALL
SELECT 'return_value', p.dag, 'returned node/value or owning trace differs'
FROM h_roles p
LEFT JOIN h_fields returned ON returned.dag = p.dag AND returned.name = 'returned'
LEFT JOIN h_values value ON value.dag = p.dag
LEFT JOIN h_values child ON child.dag = returned.target
LEFT JOIN h_fields trace ON trace.dag = p.dag AND trace.name = 'trace'
LEFT JOIN h_fields request ON request.dag = p.dag AND request.name = 'request'
LEFT JOIN h_fields inputs ON inputs.dag = p.dag AND inputs.name = 'inputs'
LEFT JOIN h_fields owner ON owner.dag = trace.target AND owner.name = 'request'
LEFT JOIN h_fields actual ON actual.dag = trace.target AND actual.name = 'inputs'
WHERE p.role = 'builtin-return-v1'
 AND (child.value_id IS NULL OR value.value_id IS DISTINCT FROM child.value_id
      OR request.target IS DISTINCT FROM owner.target OR inputs.target IS DISTINCT FROM actual.target)
UNION ALL
SELECT 'map_get_value', o.dag, 'fixed builtin lookup or binding differs'
FROM h_operations o
LEFT JOIN h_arguments container ON container.arguments = o.arguments AND container.key_name = 'map'
LEFT JOIN h_arguments key ON key.arguments = o.arguments AND key.key_name = 'key'
LEFT JOIN datums mapdatum ON mapdatum.oid = container.value_id
LEFT JOIN datums keydatum ON keydatum.oid = key.value_id
LEFT JOIN map_entries m ON m.oid = container.value_id AND m.key_id = key.value_id
LEFT JOIN h_roles binding ON binding.dag = o.binding
LEFT JOIN h_fields source ON source.dag = o.binding AND source.name = 'source'
WHERE o.func IS DISTINCT FROM 'dml://builtin/map/get'
 OR binding.role IS DISTINCT FROM 'builtin-binding-v1'
 OR source.scalar IS DISTINCT FROM 'dml://source/builtin/map/get/v1'
 OR mapdatum.kind IS DISTINCT FROM 'map' OR keydatum.kind IS DISTINCT FROM 'string'
 OR m.value_id IS NULL OR o.value_id IS DISTINCT FROM m.value_id
UNION ALL
SELECT 'trace_target', t.trace, t.position
FROM h_trace_positions t LEFT JOIN h_roles p ON p.dag = t.operation
WHERE p.role IS DISTINCT FROM 'builtin-operation-v1'
UNION ALL
SELECT 'trace_positions', trace, 'noncontiguous or excess positions'
FROM h_trace_positions GROUP BY trace
HAVING count(*) > 16 OR list(position ORDER BY position) <>
 list_transform(range(count(*)), i -> 'call-' || lpad(CAST(i AS VARCHAR), 2, '0'))
UNION ALL
SELECT 'trace_count', p.dag, 'getter positions differ from fixed add/double contract'
FROM h_roles p
LEFT JOIN h_fields owner ON owner.dag = p.dag AND owner.name = 'request'
LEFT JOIN h_requests q ON q.dag = owner.target
LEFT JOIN h_fields trace ON trace.dag = p.dag AND trace.name = 'trace'
LEFT JOIN h_trace_positions t ON t.trace = trace.target
WHERE p.role = 'builtin-return-v1'
GROUP BY p.dag, q.intent
HAVING count(t.position) <> CASE WHEN q.intent = 'urn:example:node-add' THEN 2
 WHEN q.intent = 'urn:example:node-double' THEN 1 ELSE -1 END
UNION ALL
SELECT 'submission_parents', c.request, 'submission must have one decision parent'
FROM h_contexts c LEFT JOIN edges e ON e.src = c.commit AND e.src_kind = 'commit'
 AND starts_with(e.label, 'parent-')
GROUP BY c.request HAVING count(e.dst) <> 1
UNION ALL
SELECT 'satisfaction_parent', c.request, 'W must have exactly own submission parent'
FROM h_contexts c LEFT JOIN edges e ON e.src = c.satisfaction AND e.src_kind = 'commit'
 AND starts_with(e.label, 'parent-')
GROUP BY c.request, c.commit HAVING count(e.dst) <> 1 OR min(e.dst) IS DISTINCT FROM c.commit;
