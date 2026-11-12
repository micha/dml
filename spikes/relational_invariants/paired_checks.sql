-- Scope-based counterparts, NOT a blanket assertion that all stored test data is valid.
CREATE OR REPLACE VIEW p_compositions AS
SELECT c.*, t.dag, parent.dst AS basis, input.dag AS inputs,
       arguments.target AS declared_inputs, slot.scalar AS slot, selected.target AS selected,
       result.target AS result, key.scalar AS key, source.source AS actual_source
FROM composition_scopes c LEFT JOIN commits current ON current.oid=c.commit_id
LEFT JOIN tree_entries t ON t.oid=current.tree_id AND t.name=c.composition_name
LEFT JOIN tree_entries input ON input.oid=current.tree_id AND input.name=c.inputs_name
LEFT JOIN edges parent ON parent.src=c.commit_id AND parent.src_kind='commit' AND parent.label='parent-0'
LEFT JOIN h_fields arguments ON arguments.dag=t.dag AND arguments.name='arguments'
LEFT JOIN h_fields slot ON slot.dag=t.dag AND slot.name='selection-slot'
LEFT JOIN h_fields selected ON selected.dag=t.dag AND selected.name='selection'
LEFT JOIN h_fields result ON result.dag=t.dag AND result.name='result'
LEFT JOIN h_fields key ON key.dag=t.dag AND key.name='key'
LEFT JOIN h_arguments source ON source.arguments=input.dag AND source.key_name='x';

CREATE OR REPLACE VIEW p_composition_faults AS
SELECT c.scope_id, 'composition_profile' AS invariant FROM p_compositions c
LEFT JOIN h_roles role ON role.dag=c.dag
LEFT JOIN dags d ON d.oid=c.dag
LEFT JOIN fields root ON root.dag=c.dag AND root.name='role'
LEFT JOIN h_field_sets fields ON fields.dag=c.dag
WHERE role.role IS DISTINCT FROM 'example-node-composition-v1'
 OR d.root IS DISTINCT FROM root.node
 OR fields.names IS DISTINCT FROM list_sort(['role','arguments','key','selection-slot','selection','result'])
 OR c.key IS DISTINCT FROM 'x' OR c.declared_inputs IS DISTINCT FROM c.inputs
UNION ALL
SELECT c.scope_id, 'composition_parent' FROM p_compositions c
LEFT JOIN edges e ON e.src=c.commit_id AND e.src_kind='commit' AND starts_with(e.label,'parent-')
GROUP BY c.scope_id HAVING count(e.dst)<>1
UNION ALL
SELECT c.scope_id, 'composition_slot_or_exact_source' FROM p_compositions c
LEFT JOIN commits b ON b.oid=c.basis
LEFT JOIN tree_entries slot ON slot.oid=b.tree_id AND slot.name=c.slot
LEFT JOIN h_selections s ON s.dag=c.selected
WHERE slot.dag IS DISTINCT FROM c.selected OR s.dag IS NULL
 OR c.result IS DISTINCT FROM s.result OR c.actual_source IS DISTINCT FROM s.result
UNION ALL
SELECT c.scope_id, 'composition_tree_delta' FROM p_compositions c
WHERE EXISTS (SELECT 1 FROM commits b JOIN tree_entries t ON t.oid=b.tree_id
 WHERE b.oid=c.basis AND t.name IN(c.inputs_name,c.composition_name))
 OR EXISTS (SELECT 1 FROM commits b JOIN tree_entries old ON old.oid=b.tree_id
 WHERE b.oid=c.basis AND NOT EXISTS (SELECT 1 FROM commits n JOIN tree_entries new ON new.oid=n.tree_id
 WHERE n.oid=c.commit_id AND new.name=old.name AND new.dag=old.dag))
 OR EXISTS (SELECT 1 FROM commits n JOIN tree_entries new ON new.oid=n.tree_id
 WHERE n.oid=c.commit_id AND new.name NOT IN(c.inputs_name,c.composition_name)
 AND NOT EXISTS (SELECT 1 FROM commits b JOIN tree_entries old ON old.oid=b.tree_id
 WHERE b.oid=c.basis AND old.name=new.name AND old.dag=new.dag));

CREATE OR REPLACE VIEW p_candidate_results AS
SELECT c.scope_id, coalesce(c.phase='completion' AND a.status='done'
 AND a.request=c.request AND q.binding=c.binding AND q.inputs=c.inputs AND q.intent=c.intent
 AND outcome.role='local-success-v1' AND result.target IS NOT NULL, false) AS accepted
FROM candidate_scopes c LEFT JOIN commits f ON f.oid=c.commit_id
LEFT JOIN tree_entries entry ON entry.oid=f.tree_id AND entry.name='attempt-'||c.attempt_id
LEFT JOIN h_attempts a ON a.dag=entry.dag
LEFT JOIN h_requests q ON q.dag=a.request
LEFT JOIN h_roles outcome ON outcome.dag=a.outcome
LEFT JOIN h_fields result ON result.dag=a.outcome AND result.name='result';

CREATE OR REPLACE VIEW p_resolution_results AS
SELECT r.scope_id,
 CASE WHEN r.intent NOT IN('urn:example:node-add','urn:example:node-double') OR binding.dag IS NULL THEN 'reject'
 WHEN EXISTS(SELECT 1 FROM p_composition_faults f JOIN composition_scopes c USING(scope_id)
   WHERE c.commit_id=r.commit_id AND c.composition_name=r.composition_name AND c.inputs_name=r.inputs_name
    AND c.depth=r.depth)
 THEN 'reject'
 WHEN r.control='fresh' THEN 'execute-fresh'
 WHEN r.intent=s.intent AND requested.value_id IS NOT NULL AND requested.value_id=produced.value_id THEN 'reuse-selected'
 WHEN r.control='require-selected' THEN 'reject' ELSE 'execute-fresh' END AS action
FROM resolution_scopes r LEFT JOIN commits root ON root.oid=r.commit_id
LEFT JOIN tree_entries binding ON binding.oid=root.tree_id AND binding.name=r.binding_name
LEFT JOIN tree_entries args ON args.oid=root.tree_id AND args.name=r.inputs_name
LEFT JOIN h_values requested ON requested.dag=args.dag
LEFT JOIN tree_entries choice ON choice.oid=root.tree_id AND choice.name='selected-double'
LEFT JOIN h_selections s ON s.dag=choice.dag
LEFT JOIN h_values produced ON produced.dag=s.inputs;

CREATE OR REPLACE VIEW p_table_rows AS
SELECT c.oid AS commit_id, table_slot.name AS table_name, table_slot.dag AS table_dag,
       slot.name AS key, slot.target AS entry, inputs.target AS inputs,
       selected.target AS selected, name.scalar AS selection_slot
FROM commits c JOIN tree_entries table_slot ON table_slot.oid=c.tree_id
JOIN h_roles table_role ON table_role.dag=table_slot.dag AND table_role.role='example-intent-scoped-table-v1'
JOIN h_fields ledger ON ledger.dag=table_slot.dag AND ledger.name='entries'
JOIN h_fields slot ON slot.dag=ledger.target AND slot.name<>'role'
LEFT JOIN h_fields inputs ON inputs.dag=slot.target AND inputs.name='inputs'
LEFT JOIN h_fields selected ON selected.dag=slot.target AND selected.name='selection'
LEFT JOIN h_fields name ON name.dag=slot.target AND name.name='selection-slot';

CREATE OR REPLACE VIEW p_transition_faults AS
SELECT t.transition_id, 'transition_parent' AS invariant FROM transition_scopes t
LEFT JOIN edges e ON e.src=t.after_commit AND e.src_kind='commit' AND starts_with(e.label,'parent-')
GROUP BY t.transition_id, t.before_commit HAVING count(e.dst)<>1 OR min(e.dst) IS DISTINCT FROM t.before_commit
UNION ALL
SELECT t.transition_id, 'transition_tree_delta' FROM transition_scopes t
WHERE EXISTS(SELECT 1 FROM commits b JOIN tree_entries old ON old.oid=b.tree_id WHERE b.oid=t.before_commit
 AND old.name<>t.slot AND NOT EXISTS(SELECT 1 FROM commits n JOIN tree_entries new ON new.oid=n.tree_id
 WHERE n.oid=t.after_commit AND old.name=new.name AND old.dag=new.dag))
 OR EXISTS(SELECT 1 FROM commits n JOIN tree_entries new ON new.oid=n.tree_id WHERE n.oid=t.after_commit
 AND new.name<>t.slot AND NOT EXISTS(SELECT 1 FROM commits b JOIN tree_entries old ON old.oid=b.tree_id
 WHERE b.oid=t.before_commit AND old.name=new.name AND old.dag=new.dag))
UNION ALL
SELECT t.transition_id, 'adoption_not_distinct' FROM transition_scopes t
LEFT JOIN commits b ON b.oid=t.before_commit LEFT JOIN commits n ON n.oid=t.after_commit
LEFT JOIN tree_entries old ON old.oid=b.tree_id AND old.name=t.slot
LEFT JOIN tree_entries new ON new.oid=n.tree_id AND new.name=t.slot
LEFT JOIN h_selections os ON os.dag=old.dag LEFT JOIN h_selections ns ON ns.dag=new.dag
LEFT JOIN h_attempts oa ON oa.dag=os.attempt LEFT JOIN h_attempts na ON na.dag=ns.attempt
WHERE t.kind='adopt' AND (os.dag IS NULL OR ns.dag IS NULL OR oa.occurrence IS NOT DISTINCT FROM na.occurrence
 OR os.intent IS DISTINCT FROM ns.intent OR os.binding IS DISTINCT FROM ns.binding OR os.inputs IS DISTINCT FROM ns.inputs)
UNION ALL
SELECT t.transition_id, 'removed_key_survives_or_missing_old' FROM transition_scopes t
WHERE t.kind='remove' AND (NOT EXISTS(SELECT 1 FROM p_table_rows r WHERE r.commit_id=t.before_commit
 AND r.table_name=t.slot AND r.inputs=t.inputs)
 OR EXISTS(SELECT 1 FROM p_table_rows r WHERE r.commit_id=t.after_commit AND r.table_name=t.slot AND r.inputs=t.inputs))
UNION ALL
SELECT t.transition_id, 'unrelated_table_entry_changed' FROM transition_scopes t
JOIN p_table_rows old ON old.commit_id=t.before_commit AND old.table_name=t.slot
WHERE t.kind IN('remove','insert') AND (t.kind<>'remove' OR old.inputs<>t.inputs)
 AND NOT EXISTS(SELECT 1 FROM p_table_rows new WHERE new.commit_id=t.after_commit AND new.table_name=t.slot
 AND new.key=old.key AND new.entry=old.entry AND new.selected=old.selected)
UNION ALL
SELECT t.transition_id, 'selection_slot_crosslink' FROM transition_scopes t
JOIN p_table_rows r ON r.commit_id=t.after_commit AND r.table_name=t.slot
LEFT JOIN commits n ON n.oid=t.after_commit
LEFT JOIN tree_entries slot ON slot.oid=n.tree_id AND slot.name=r.selection_slot
LEFT JOIN h_selections s ON s.dag=r.selected
WHERE r.key IS DISTINCT FROM 'input-'||r.inputs OR slot.dag IS DISTINCT FROM r.selected
 OR s.inputs IS DISTINCT FROM r.inputs;

CREATE OR REPLACE VIEW p_reuse_choices AS
SELECT w.*, coalesce(nullif(w.selection,''), slot.dag) AS choice
FROM reuse_scopes w LEFT JOIN commits b ON b.oid=w.basis
LEFT JOIN tree_entries slot ON slot.oid=b.tree_id AND slot.name=w.slot;

CREATE OR REPLACE VIEW p_reuse_faults AS
SELECT w.reuse_id, 'W_ownQ_oldT_R' AS invariant FROM p_reuse_choices w
LEFT JOIN commits f ON f.oid=w.satisfaction LEFT JOIN h_requests q ON q.dag=w.request
LEFT JOIN tree_entries satisfaction ON satisfaction.oid=f.tree_id AND satisfaction.name='reuse-'||q.occurrence
LEFT JOIN h_fields own ON own.dag=satisfaction.dag AND own.name='request'
LEFT JOIN h_fields attempt ON attempt.dag=satisfaction.dag AND attempt.name='attempt'
LEFT JOIN h_fields result ON result.dag=satisfaction.dag AND result.name='result'
LEFT JOIN h_selections captured ON captured.dag=w.choice
WHERE own.target IS DISTINCT FROM w.request OR attempt.target IS DISTINCT FROM captured.attempt
 OR result.target IS DISTINCT FROM captured.result
UNION ALL
SELECT w.reuse_id, 'reuse_eligibility' FROM p_reuse_choices w
LEFT JOIN h_requests q ON q.dag=w.request LEFT JOIN h_selections s ON s.dag=w.choice
LEFT JOIN h_values requested ON requested.dag=q.inputs LEFT JOIN h_values produced ON produced.dag=s.inputs
WHERE s.dag IS NULL OR q.intent IS DISTINCT FROM s.intent
 OR CASE WHEN requested.value_id IS NOT NULL AND produced.value_id IS NOT NULL
 THEN requested.value_id IS DISTINCT FROM produced.value_id ELSE q.inputs IS DISTINCT FROM s.inputs END
UNION ALL
SELECT w.reuse_id, 'reuse_parent' FROM p_reuse_choices w
LEFT JOIN edges e ON e.src=w.satisfaction AND e.src_kind='commit' AND starts_with(e.label,'parent-')
GROUP BY w.reuse_id, w.submission HAVING count(e.dst)<>1 OR min(e.dst) IS DISTINCT FROM w.submission
UNION ALL
SELECT w.reuse_id, 'reuse_has_own_attempt' FROM reuse_scopes w JOIN h_attempts a ON a.request=w.request;
