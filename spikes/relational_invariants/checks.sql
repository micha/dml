-- Independent, intentionally partial checker for this spike's builtin map/get profile.
CREATE OR REPLACE VIEW field_data AS
SELECT f.dag, f.name, f.node, n.kind AS node_kind, n.target,
       d.kind AS datum_kind, d.scalar
FROM fields f LEFT JOIN nodes n ON n.oid = f.node
LEFT JOIN datums d ON n.kind = 'literal' AND d.oid = n.target;

CREATE OR REPLACE VIEW profiles AS
SELECT dag, scalar AS role FROM field_data
WHERE name = 'role' AND node_kind = 'literal' AND datum_kind = 'string';

CREATE OR REPLACE VIEW expected_fields AS
SELECT * FROM (VALUES
 ('builtin-binding-v1', 'role', 'literal', 'string'),
 ('builtin-binding-v1', 'adapter', 'literal', 'null'),
 ('builtin-binding-v1', 'interpreter', 'literal', 'null'),
 ('builtin-binding-v1', 'timeout-ms', 'literal', 'null'),
 ('builtin-binding-v1', 'source', 'literal', 'uri'),
 ('builtin-literal-v1', 'role', 'literal', 'string'),
 ('builtin-literal-v1', 'value', 'literal', '*'),
 ('builtin-literal-source-v1', 'role', 'literal', 'string'),
 ('builtin-literal-source-v1', 'value', 'literal', '*'),
 ('builtin-literal-source-v1', 'source', 'subdag', '*'),
 ('builtin-literal-source-v1', 'name', 'literal', 'string'),
 ('builtin-literal-source-v1', 'node', 'literal', 'bytes'),
 ('builtin-arguments-v1', 'role', 'literal', 'string'),
 ('builtin-arguments-v1', 'value', 'literal', 'map'),
 ('builtin-arguments-v1', 'entries', 'subdag', '*'),
 ('builtin-argument-entry-v1', 'role', 'literal', 'string'),
 ('builtin-argument-entry-v1', 'key', 'literal', 'string'),
 ('builtin-argument-entry-v1', 'source', 'subdag', '*'),
 ('builtin-operation-v1', 'role', 'literal', 'string'),
 ('builtin-operation-v1', 'func', 'literal', 'uri'),
 ('builtin-operation-v1', 'binding', 'subdag', '*'),
 ('builtin-operation-v1', 'arguments', 'subdag', '*'),
 ('builtin-operation-v1', 'value', 'literal', '*')
) AS t(role, name, node_kind, datum_kind);

CREATE OR REPLACE VIEW argument_rows AS
SELECT a.dag AS arguments, slot.name AS position, slot.target AS entry,
       k.target AS key_id, k.scalar AS key_name, s.target AS source,
       v.target AS value_id
FROM profiles a
JOIN field_data ledger ON ledger.dag = a.dag AND ledger.name = 'entries'
JOIN field_data slot ON slot.dag = ledger.target AND slot.name <> 'role'
LEFT JOIN field_data k ON k.dag = slot.target AND k.name = 'key'
LEFT JOIN field_data s ON s.dag = slot.target AND s.name = 'source'
LEFT JOIN field_data v ON v.dag = s.target AND v.name = 'value'
WHERE a.role = 'builtin-arguments-v1';

CREATE OR REPLACE VIEW expected_argument_rows AS
SELECT a.dag AS arguments, m.key_id, m.value_id
FROM profiles a JOIN field_data v ON v.dag = a.dag AND v.name = 'value'
JOIN map_entries m ON m.oid = v.target
WHERE a.role = 'builtin-arguments-v1';

CREATE OR REPLACE VIEW operations AS
SELECT p.dag, f.scalar AS func, b.target AS binding, a.target AS arguments, v.target AS value_id
FROM profiles p
LEFT JOIN field_data f ON f.dag = p.dag AND f.name = 'func'
LEFT JOIN field_data b ON b.dag = p.dag AND b.name = 'binding'
LEFT JOIN field_data a ON a.dag = p.dag AND a.name = 'arguments'
LEFT JOIN field_data v ON v.dag = p.dag AND v.name = 'value'
WHERE p.role = 'builtin-operation-v1';

CREATE OR REPLACE VIEW trace_positions AS
SELECT p.dag AS trace, f.name AS position, f.target AS operation
FROM profiles p JOIN field_data f ON f.dag = p.dag AND f.name <> 'role'
WHERE p.role = 'builtin-trace-v1';

CREATE OR REPLACE VIEW violations AS
-- Missing typed records are not allowed to disappear through an inner join.
SELECT 'missing_object' AS invariant, e.src AS subject, e.label AS detail
FROM edges e LEFT JOIN objects o ON o.kind = e.dst_kind AND o.oid = e.dst
WHERE o.oid IS NULL
UNION ALL
SELECT 'missing_root', r.commit_id, CAST(r.checkpoint AS VARCHAR)
FROM roots r LEFT JOIN objects o ON o.kind = 'commit' AND o.oid = r.commit_id
WHERE o.oid IS NULL
UNION ALL
SELECT 'profile_fields', p.dag, x.name
FROM profiles p JOIN expected_fields x ON x.role = p.role
LEFT JOIN field_data f ON f.dag = p.dag AND f.name = x.name
WHERE f.node IS NULL OR f.node_kind IS DISTINCT FROM x.node_kind
 OR (x.datum_kind <> '*' AND f.datum_kind IS DISTINCT FROM x.datum_kind)
UNION ALL
SELECT 'extra_field', p.dag, f.name
FROM profiles p JOIN field_data f ON f.dag = p.dag
LEFT JOIN expected_fields x ON x.role = p.role AND x.name = f.name
WHERE p.role IN (SELECT DISTINCT role FROM expected_fields) AND x.name IS NULL
UNION ALL
SELECT 'profile_root', p.dag, 'root differs from designated field'
FROM profiles p JOIN dags d ON d.oid = p.dag
LEFT JOIN fields f ON f.dag = p.dag AND f.name = CASE
 WHEN p.role IN ('builtin-literal-v1', 'builtin-literal-source-v1',
                  'builtin-arguments-v1', 'builtin-operation-v1') THEN 'value' ELSE 'role' END
WHERE d.root IS DISTINCT FROM f.node
UNION ALL
SELECT 'source_association', p.dag, 'selected source/name/node/value differ'
FROM profiles p
LEFT JOIN field_data s ON s.dag = p.dag AND s.name = 'source'
LEFT JOIN field_data name ON name.dag = p.dag AND name.name = 'name'
LEFT JOIN field_data recorded ON recorded.dag = p.dag AND recorded.name = 'node'
LEFT JOIN field_data v ON v.dag = p.dag AND v.name = 'value'
LEFT JOIN fields selected ON selected.dag = s.target AND selected.name = name.scalar
LEFT JOIN nodes n ON n.oid = selected.node
WHERE p.role = 'builtin-literal-source-v1'
 AND (selected.node IS NULL OR recorded.scalar IS DISTINCT FROM selected.node
      OR n.kind IS DISTINCT FROM 'literal' OR n.target IS DISTINCT FROM v.target)
UNION ALL
SELECT 'argument_sources', COALESCE(a.arguments, e.arguments), COALESCE(a.key_id, e.key_id)
FROM argument_rows a FULL OUTER JOIN expected_argument_rows e
 ON a.arguments = e.arguments AND a.key_id = e.key_id
WHERE a.arguments IS NULL OR e.arguments IS NULL OR a.value_id IS DISTINCT FROM e.value_id
UNION ALL
SELECT 'duplicate_argument', arguments, key_id
FROM argument_rows GROUP BY arguments, key_id HAVING count(*) <> 1
UNION ALL
SELECT 'map_get_arguments', o.dag, 'expected exactly map and key'
FROM operations o LEFT JOIN argument_rows a ON a.arguments = o.arguments
GROUP BY o.dag HAVING count(a.key_name) <> 2
 OR count(*) FILTER (WHERE a.key_name = 'map') <> 1
 OR count(*) FILTER (WHERE a.key_name = 'key') <> 1
UNION ALL
SELECT 'map_get_binding', o.dag, 'unsupported func/binding/source'
FROM operations o LEFT JOIN profiles b ON b.dag = o.binding
LEFT JOIN field_data source ON source.dag = o.binding AND source.name = 'source'
WHERE o.func IS DISTINCT FROM 'dml://builtin/map/get'
 OR b.role IS DISTINCT FROM 'builtin-binding-v1'
 OR source.scalar IS NULL OR source.scalar NOT IN
 ('dml://source/builtin/map/get/v1', 'dml://source/builtin/map/get/v2')
UNION ALL
SELECT 'map_get_value', o.dag, 'result differs from map[key]'
FROM operations o
LEFT JOIN argument_rows container ON container.arguments = o.arguments AND container.key_name = 'map'
LEFT JOIN argument_rows key ON key.arguments = o.arguments AND key.key_name = 'key'
LEFT JOIN datums mapdatum ON mapdatum.oid = container.value_id
LEFT JOIN datums keydatum ON keydatum.oid = key.value_id
LEFT JOIN map_entries m ON m.oid = container.value_id AND m.key_id = key.value_id
WHERE mapdatum.kind IS DISTINCT FROM 'map' OR keydatum.kind IS DISTINCT FROM 'string'
 OR m.value_id IS NULL OR o.value_id IS DISTINCT FROM m.value_id
UNION ALL
SELECT 'empty_dataset', 'dataset', 'roots and objects must be nonempty'
WHERE NOT EXISTS (SELECT 1 FROM roots) OR NOT EXISTS (SELECT 1 FROM objects)
UNION ALL
SELECT 'argument_profile', o.dag, 'operation requires argument-map profile'
FROM operations o LEFT JOIN profiles p ON p.dag = o.arguments
WHERE p.role IS DISTINCT FROM 'builtin-arguments-v1'
UNION ALL
SELECT 'ledger_profile', a.dag, 'arguments require entry ledger'
FROM profiles a LEFT JOIN field_data f ON f.dag = a.dag AND f.name = 'entries'
LEFT JOIN profiles ledger ON ledger.dag = f.target
WHERE a.role = 'builtin-arguments-v1'
 AND ledger.role IS DISTINCT FROM 'builtin-argument-entries-v1'
UNION ALL
SELECT 'entry_profile', a.arguments, a.position
FROM argument_rows a LEFT JOIN profiles p ON p.dag = a.entry
WHERE p.role IS DISTINCT FROM 'builtin-argument-entry-v1'
UNION ALL
SELECT 'trace_target', t.trace, t.position
FROM trace_positions t LEFT JOIN profiles p ON p.dag = t.operation
WHERE p.role IS DISTINCT FROM 'builtin-operation-v1'
UNION ALL
SELECT 'checkpoint_trace_count', r.commit_id, 'positions differ from exerciser plan'
FROM roots r
LEFT JOIN commits c ON c.oid = r.commit_id
LEFT JOIN tree_entries t ON t.oid = c.tree_id AND t.name = 'trace'
LEFT JOIN trace_positions p ON p.trace = t.dag
WHERE r.expected_positions IS NOT NULL
GROUP BY r.checkpoint, r.commit_id, r.expected_positions
HAVING count(p.position) <> r.expected_positions
UNION ALL
SELECT 'trace_positions', trace, 'positions must be contiguous and at most16'
FROM trace_positions GROUP BY trace
HAVING count(*) > 16 OR list(position ORDER BY position) <>
 list_transform(range(count(*)), i -> 'call-' || lpad(CAST(i AS VARCHAR), 2, '0'));
