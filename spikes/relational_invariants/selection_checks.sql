-- Independent selection/profile/header claims on decoded facts; no public validator calls.
CREATE OR REPLACE VIEW s_targets AS
SELECT c.*, entry.dag, validation.target AS validation, completion.target AS completion_datum,
       completion.scalar AS completion_id
FROM selection_scopes c LEFT JOIN commits root ON root.oid=c.commit_id
LEFT JOIN tree_entries entry ON entry.oid=root.tree_id AND entry.name=c.slot
LEFT JOIN h_fields validation ON validation.dag=entry.dag AND validation.name='validation'
LEFT JOIN h_fields completion ON completion.dag=entry.dag AND completion.name='completion';
CREATE OR REPLACE VIEW s_headers AS
SELECT s.scope_id, expected.document AS handle, json_extract(expected.document,'$.expected') AS expected_job,
       job.document AS job, observed.document AS observation,
       expected.parse_error AS expected_error, job.parse_error AS job_error, observed.parse_error AS observation_error
FROM s_targets s
LEFT JOIN capsules expected ON expected.dag=s.validation AND expected.field='expected'
LEFT JOIN capsules job ON job.dag=s.validation AND job.field='job'
LEFT JOIN capsules observed ON observed.dag=s.validation AND observed.field='observation';
CREATE OR REPLACE VIEW s_scalar_rules AS
SELECT * FROM (VALUES ('role','string'),('intent','uri'),('completion','bytes')) AS t(name,kind);
CREATE OR REPLACE VIEW s_link_rules AS
SELECT * FROM (VALUES ('binding'),('inputs'),('request'),('attempt'),('result'),('validation')) AS t(name);

CREATE OR REPLACE VIEW s_faults AS
SELECT s.scope_id, 'selection_shape' AS invariant FROM s_targets s
LEFT JOIN h_roles role ON role.dag=s.dag LEFT JOIN h_field_sets fields ON fields.dag=s.dag
LEFT JOIN dags dag ON dag.oid=s.dag LEFT JOIN h_fields result ON result.dag=s.dag AND result.name='result'
WHERE s.dag IS NULL OR role.role IS DISTINCT FROM 'example-reuse-selection-v1'
 OR fields.names IS DISTINCT FROM list_sort(['role','intent','binding','inputs','request','attempt','result','completion','validation'])
 OR dag.root IS DISTINCT FROM result.node
UNION ALL
SELECT s.scope_id, 'selection_scalar_type' FROM s_targets s CROSS JOIN s_scalar_rules rule
LEFT JOIN h_fields f ON f.dag=s.dag AND f.name=rule.name
WHERE f.node_kind IS DISTINCT FROM 'literal' OR f.datum_kind IS DISTINCT FROM rule.kind
UNION ALL
SELECT s.scope_id, 'selection_link_type' FROM s_targets s CROSS JOIN s_link_rules rule
LEFT JOIN h_fields f ON f.dag=s.dag AND f.name=rule.name LEFT JOIN dags target ON target.oid=f.target
WHERE f.node_kind IS DISTINCT FROM 'subdag' OR target.oid IS NULL
UNION ALL
SELECT s.scope_id, 'completion_id_size' FROM s_targets s
WHERE s.completion_id IS NULL OR length(s.completion_id)<>32
UNION ALL
SELECT s.scope_id, 'validation_shape_or_header' FROM s_targets s
LEFT JOIN dags v ON v.oid=s.validation LEFT JOIN h_fields root ON root.dag=v.oid AND root.name='expected'
LEFT JOIN h_field_sets fields ON fields.dag=v.oid
WHERE v.oid IS NULL OR v.root IS DISTINCT FROM root.node
 OR fields.names IS DISTINCT FROM list_sort(['expected','job','observation'])
 OR EXISTS(SELECT 1 FROM capsules c WHERE c.dag=s.validation AND (c.parse_error IS NOT NULL OR c.byte_count>8192))
UNION ALL
SELECT s.scope_id, 'header_shape_format_or_agreement' FROM s_targets s JOIN s_headers h USING(scope_id)
WHERE h.handle IS NULL OR h.job IS NULL OR h.observation IS NULL
 OR list_sort(json_keys(h.handle)) IS DISTINCT FROM list_sort(['format','workspace','expected'])
 OR list_sort(json_keys(h.job)) IS DISTINCT FROM list_sort(['format','token','commit','binding_name','inputs_name','binding','inputs','intent_uri','worker_ref','request'])
 OR list_sort(json_keys(h.observation)) IS DISTINCT FROM list_sort(['format','token','commit','phase','selected_commit','pre_dispatch','request_id','attempt_id'])
 OR json_extract_string(h.handle,'$.format') IS DISTINCT FROM 'daggerml-local-exchange-handle-v2'
 OR json_extract_string(h.job,'$.format') IS DISTINCT FROM 'daggerml-local-exchange-job-v2'
 OR json_extract_string(h.observation,'$.format') IS DISTINCT FROM 'daggerml-local-exchange-observation-v1'
 OR h.expected_job IS DISTINCT FROM h.job
 OR json_extract_string(h.observation,'$.token') IS DISTINCT FROM json_extract_string(h.job,'$.token')
 OR json_extract_string(h.observation,'$.commit') IS DISTINCT FROM json_extract_string(h.job,'$.commit')
 OR json_extract_string(h.observation,'$.phase') IS DISTINCT FROM 'completion'
 OR json_extract_string(h.observation,'$.selected_commit') IS DISTINCT FROM s.completion_id
UNION ALL
SELECT s.scope_id, 'stored_producer_authority' FROM s_targets s
LEFT JOIN h_selections choice ON choice.dag=s.dag LEFT JOIN h_requests q ON q.dag=choice.request
LEFT JOIN h_attempts a ON a.dag=choice.attempt LEFT JOIN h_roles outcome ON outcome.dag=a.outcome
LEFT JOIN h_fields result ON result.dag=a.outcome AND result.name='result'
LEFT JOIN h_fields code ON code.dag=a.outcome AND code.name='exit-code'
LEFT JOIN commits completion ON completion.oid=s.completion_id
LEFT JOIN tree_entries final ON final.oid=completion.tree_id AND final.name='attempt-'||a.occurrence
WHERE choice.dag IS NULL OR q.dag IS NULL OR a.request IS DISTINCT FROM choice.request
 OR a.status IS DISTINCT FROM 'done' OR outcome.role IS DISTINCT FROM 'local-success-v1'
 OR code.datum_kind IS DISTINCT FROM 'i64' OR code.scalar IS DISTINCT FROM '0'
 OR result.target IS DISTINCT FROM choice.result OR final.dag IS DISTINCT FROM choice.attempt
 OR q.intent IS DISTINCT FROM choice.intent OR q.binding IS DISTINCT FROM choice.binding OR q.inputs IS DISTINCT FROM choice.inputs
UNION ALL
SELECT s.scope_id, 'header_native_claims' FROM s_targets s JOIN s_headers h USING(scope_id)
LEFT JOIN h_selections choice ON choice.dag=s.dag LEFT JOIN h_requests q ON q.dag=choice.request
LEFT JOIN h_attempts a ON a.dag=choice.attempt
LEFT JOIN edges parent ON parent.src=s.completion_id AND parent.src_kind='commit' AND parent.label='parent-0'
LEFT JOIN edges submission ON submission.src=parent.dst AND submission.src_kind='commit' AND submission.label='parent-0'
WHERE json_extract_string(h.job,'$.request') IS DISTINCT FROM choice.request
 OR json_extract_string(h.job,'$.binding') IS DISTINCT FROM choice.binding
 OR json_extract_string(h.job,'$.inputs') IS DISTINCT FROM choice.inputs
 OR json_extract_string(h.job,'$.intent_uri') IS DISTINCT FROM choice.intent
 OR json_extract_string(h.job,'$.commit') IS DISTINCT FROM submission.dst
 OR json_extract_string(h.observation,'$.pre_dispatch') IS DISTINCT FROM parent.dst
 OR json_extract_string(h.observation,'$.request_id') IS DISTINCT FROM q.occurrence
 OR json_extract_string(h.observation,'$.attempt_id') IS DISTINCT FROM a.occurrence
UNION ALL
SELECT s.scope_id, 'completion_not_retained' FROM s_targets s
WHERE NOT EXISTS(SELECT 1 FROM h_ancestry a WHERE a.descendant=s.commit_id AND a.ancestor=s.completion_id)
UNION ALL
SELECT s.scope_id, 'requested_full_dimensions' FROM s_targets s
LEFT JOIN h_selections choice ON choice.dag=s.dag LEFT JOIN commits current ON current.oid=s.commit_id
LEFT JOIN tree_entries binding ON binding.oid=current.tree_id AND binding.name=s.binding_name
LEFT JOIN tree_entries inputs ON inputs.oid=current.tree_id AND inputs.name=s.inputs_name
WHERE s.binding_name IS NOT NULL AND (binding.dag IS DISTINCT FROM choice.binding
 OR inputs.dag IS DISTINCT FROM choice.inputs OR s.intent IS DISTINCT FROM choice.intent);

-- The public candidate call also validates its packet, not merely the native outcome.
CREATE OR REPLACE VIEW p_candidate_results AS
SELECT c.scope_id, coalesce(c.phase='completion' AND c.bundle_root=c.commit_id AND a.status='done'
 AND a.request=c.request AND q.binding=c.binding AND q.inputs=c.inputs AND q.intent=c.intent
 AND outcome.role='local-success-v1' AND result.target IS NOT NULL
 AND c.job_document=c.expected_document
 AND json_extract_string(c.receipt_document,'$.format')='daggerml-local-exchange-observation-v1'
 AND json_extract_string(c.receipt_document,'$.token')=json_extract_string(c.expected_document,'$.token')
 AND json_extract_string(c.receipt_document,'$.commit')=json_extract_string(c.expected_document,'$.commit')
 AND json_extract_string(c.receipt_document,'$.request_id')=q.occurrence
 AND json_extract_string(c.receipt_document,'$.attempt_id')=a.occurrence
 AND json_extract_string(c.receipt_document,'$.pre_dispatch')=parent.dst
 AND pre_parent.dst=json_extract_string(c.expected_document,'$.commit'), false) AS accepted
FROM candidate_scopes c LEFT JOIN commits f ON f.oid=c.commit_id
LEFT JOIN tree_entries entry ON entry.oid=f.tree_id AND entry.name='attempt-'||c.attempt_id
LEFT JOIN h_attempts a ON a.dag=entry.dag LEFT JOIN h_requests q ON q.dag=a.request
LEFT JOIN h_roles outcome ON outcome.dag=a.outcome LEFT JOIN h_fields result ON result.dag=a.outcome AND result.name='result'
LEFT JOIN edges parent ON parent.src=c.commit_id AND parent.src_kind='commit' AND parent.label='parent-0'
LEFT JOIN edges pre_parent ON pre_parent.src=parent.dst AND pre_parent.src_kind='commit' AND pre_parent.label='parent-0';
