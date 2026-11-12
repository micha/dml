-- Independent selected builtin profiles, not Inspector verdict predicates.
CREATE TEMP VIEW fd AS
SELECT f.dag,f.name,f.node,n.kind AS node_kind,n.target,d.kind AS datum_kind,d.scalar
FROM fields f LEFT JOIN nodes n ON n.oid=f.node LEFT JOIN datums d ON n.kind='literal' AND d.oid=n.target;
CREATE TEMP VIEW roles AS SELECT dag,scalar AS role FROM fd WHERE name='role' AND node_kind='literal' AND datum_kind='string';
CREATE TEMP VIEW expected AS SELECT * FROM (VALUES
 ('builtin-binding-v1','role','literal','string'),('builtin-binding-v1','adapter','literal','null'),
 ('builtin-binding-v1','interpreter','literal','null'),('builtin-binding-v1','timeout-ms','literal','null'),('builtin-binding-v1','source','literal','uri'),
 ('builtin-literal-v1','role','literal','string'),('builtin-literal-v1','value','literal','*'),
 ('builtin-literal-source-v1','role','literal','string'),('builtin-literal-source-v1','value','literal','*'),
 ('builtin-literal-source-v1','source','subdag','*'),('builtin-literal-source-v1','name','literal','string'),('builtin-literal-source-v1','node','literal','bytes'),
 ('builtin-arguments-v1','role','literal','string'),('builtin-arguments-v1','value','literal','map'),('builtin-arguments-v1','entries','subdag','*'),
 ('builtin-argument-entry-v1','role','literal','string'),('builtin-argument-entry-v1','key','literal','string'),('builtin-argument-entry-v1','source','subdag','*'),
 ('builtin-operation-v1','role','literal','string'),('builtin-operation-v1','value','literal','*'),
 ('builtin-operation-v1','func','literal','uri'),('builtin-operation-v1','binding','subdag','*'),('builtin-operation-v1','arguments','subdag','*')
) AS t(role,name,node_kind,datum_kind);
CREATE TEMP VIEW args AS
SELECT p.dag AS arguments,slot.name AS position,slot.target AS entry,k.target AS key_id,k.scalar AS key_name,s.target AS source,v.target AS value_id
FROM roles p JOIN fd ledger ON ledger.dag=p.dag AND ledger.name='entries'
JOIN fd slot ON slot.dag=ledger.target AND slot.name<>'role'
LEFT JOIN fd k ON k.dag=slot.target AND k.name='key'
LEFT JOIN fd s ON s.dag=slot.target AND s.name='source'
LEFT JOIN fd v ON v.dag=s.target AND v.name='value' WHERE p.role='builtin-arguments-v1';
CREATE TEMP VIEW wanted_args AS
SELECT p.dag AS arguments,m.key_id,m.value_id FROM roles p JOIN fd v ON v.dag=p.dag AND v.name='value'
JOIN map_entries m ON m.oid=v.target WHERE p.role='builtin-arguments-v1';
CREATE TEMP VIEW ops AS
SELECT p.dag,f.scalar AS func,b.target AS binding,a.target AS arguments,v.target AS value_id
FROM roles p LEFT JOIN fd f ON f.dag=p.dag AND f.name='func' LEFT JOIN fd b ON b.dag=p.dag AND b.name='binding'
LEFT JOIN fd a ON a.dag=p.dag AND a.name='arguments' LEFT JOIN fd v ON v.dag=p.dag AND v.name='value'
WHERE p.role='builtin-operation-v1';
CREATE TEMP VIEW signatures AS SELECT * FROM (VALUES
 ('dml://builtin/map/empty','dml://source/builtin/map/empty/v1',[]::VARCHAR[]),
 ('dml://builtin/map/insert','dml://source/builtin/map/insert/v1',['key','map','value']),
 ('dml://builtin/map/get','dml://source/builtin/map/get/v1',['key','map']),
 ('dml://builtin/map/get','dml://source/builtin/map/get/v2',['key','map']),
 ('dml://builtin/list/get','dml://source/builtin/list/get/v1',['index','list'])
) AS t(func,source,names);
CREATE TEMP VIEW operands AS
SELECT o.*,m.value_id AS map_id,k.value_id AS key_id,v.value_id AS inserted_id,l.value_id AS list_id,i.value_id AS index_id
FROM ops o LEFT JOIN args m ON m.arguments=o.arguments AND m.key_name='map'
LEFT JOIN args k ON k.arguments=o.arguments AND k.key_name='key' LEFT JOIN args v ON v.arguments=o.arguments AND v.key_name='value'
LEFT JOIN args l ON l.arguments=o.arguments AND l.key_name='list' LEFT JOIN args i ON i.arguments=o.arguments AND i.key_name='index';
CREATE TEMP VIEW faults AS
SELECT 'missing_object' AS invariant,e.src AS subject,e.label AS detail FROM edges e LEFT JOIN objects x ON x.kind=e.dst_kind AND x.oid=e.dst WHERE x.oid IS NULL
UNION ALL SELECT 'subject_role',s.subject,'unsupported selected semantic role/method' FROM subject s LEFT JOIN roles r ON r.dag=s.subject
 WHERE r.role IS NULL OR (s.method='trace' AND r.role<>'builtin-trace-v1') OR (s.method='arguments' AND r.role<>'builtin-arguments-v1')
 OR (s.method='node' AND r.role NOT IN ('builtin-literal-v1','builtin-literal-source-v1','builtin-arguments-v1','builtin-operation-v1'))
UNION ALL SELECT 'profile_fields',p.dag,x.name FROM roles p JOIN expected x ON x.role=p.role LEFT JOIN fd f ON f.dag=p.dag AND f.name=x.name
 WHERE f.node IS NULL OR f.node_kind IS DISTINCT FROM x.node_kind OR (x.datum_kind<>'*' AND f.datum_kind IS DISTINCT FROM x.datum_kind)
UNION ALL SELECT 'extra_field',p.dag,f.name FROM roles p JOIN fd f ON f.dag=p.dag LEFT JOIN expected e ON e.role=p.role AND e.name=f.name
 WHERE p.role IN(SELECT DISTINCT role FROM expected) AND e.name IS NULL
UNION ALL SELECT 'profile_root',p.dag,'designated field differs' FROM roles p JOIN dags d ON d.oid=p.dag LEFT JOIN fields f ON f.dag=p.dag
 AND f.name=CASE WHEN p.role IN('builtin-literal-v1','builtin-literal-source-v1','builtin-arguments-v1','builtin-operation-v1') THEN 'value' ELSE 'role' END
 WHERE p.role IN(SELECT DISTINCT role FROM expected) OR p.role IN('builtin-argument-entries-v1','builtin-trace-v1')
 GROUP BY p.dag,d.root,f.node HAVING d.root IS DISTINCT FROM f.node
UNION ALL SELECT 'source_association',p.dag,'source/name/node/value differ' FROM roles p
 LEFT JOIN fd src ON src.dag=p.dag AND src.name='source' LEFT JOIN fd name ON name.dag=p.dag AND name.name='name'
 LEFT JOIN fd n ON n.dag=p.dag AND n.name='node' LEFT JOIN fd v ON v.dag=p.dag AND v.name='value'
 LEFT JOIN fields selected ON selected.dag=src.target AND selected.name=name.scalar LEFT JOIN nodes actual ON actual.oid=selected.node
 WHERE p.role='builtin-literal-source-v1' AND (selected.node IS NULL OR n.scalar IS DISTINCT FROM selected.node OR actual.kind IS DISTINCT FROM 'literal' OR actual.target IS DISTINCT FROM v.target)
UNION ALL SELECT 'argument_sources',coalesce(a.arguments,w.arguments),coalesce(a.key_id,w.key_id) FROM args a FULL OUTER JOIN wanted_args w ON a.arguments=w.arguments AND a.key_id=w.key_id
 WHERE a.arguments IS NULL OR w.arguments IS NULL OR a.value_id IS DISTINCT FROM w.value_id
UNION ALL SELECT 'argument_key_duplicate',arguments,key_id FROM args GROUP BY arguments,key_id HAVING count(*)<>1
UNION ALL SELECT 'ledger_profile',p.dag,'entry ledger/type/name differs' FROM roles p
 LEFT JOIN fd e ON e.dag=p.dag AND e.name='entries' LEFT JOIN roles r ON r.dag=e.target
 WHERE p.role='builtin-arguments-v1' AND r.role IS DISTINCT FROM 'builtin-argument-entries-v1'
UNION ALL SELECT 'ledger_entry',p.dag,f.name FROM roles p JOIN fd f ON f.dag=p.dag AND f.name<>'role' LEFT JOIN roles r ON r.dag=f.target
 WHERE p.role='builtin-argument-entries-v1' AND (f.node_kind<>'subdag' OR r.role IS DISTINCT FROM 'builtin-argument-entry-v1' OR NOT regexp_matches(f.name,'^arg-[0-9]{2}$'))
UNION ALL SELECT 'trace_target',p.dag,f.name FROM roles p JOIN fd f ON f.dag=p.dag AND f.name<>'role' LEFT JOIN roles r ON r.dag=f.target
 WHERE p.role='builtin-trace-v1' AND (f.node_kind<>'subdag' OR r.role IS DISTINCT FROM 'builtin-operation-v1' OR NOT regexp_matches(f.name,'^call-[0-9]{2}$'))
UNION ALL SELECT 'binding_signature',o.dag,'func/captured source pair unsupported' FROM ops o LEFT JOIN fd s ON s.dag=o.binding AND s.name='source'
 LEFT JOIN signatures wanted ON wanted.func=o.func AND wanted.source=s.scalar WHERE wanted.func IS NULL
UNION ALL SELECT 'argument_signature',o.dag,'exact argument names differ' FROM ops o LEFT JOIN fd s ON s.dag=o.binding AND s.name='source'
 JOIN signatures wanted ON wanted.func=o.func AND wanted.source=s.scalar LEFT JOIN args a ON a.arguments=o.arguments
 GROUP BY o.dag,wanted.names HAVING coalesce(list_sort(list(a.key_name) FILTER(WHERE a.key_name IS NOT NULL)),[]::VARCHAR[])<>wanted.names
UNION ALL SELECT 'operation_arguments',o.dag,'argument-map role missing' FROM ops o LEFT JOIN roles r ON r.dag=o.arguments WHERE r.role IS DISTINCT FROM 'builtin-arguments-v1'
UNION ALL SELECT 'map_empty_value',o.dag,'empty MAP required' FROM ops o LEFT JOIN datums d ON d.oid=o.value_id
 WHERE o.func='dml://builtin/map/empty' AND (d.kind IS DISTINCT FROM 'map' OR EXISTS(SELECT 1 FROM map_entries m WHERE m.oid=o.value_id))
UNION ALL SELECT 'map_get_value',o.dag,'map[key] result differs' FROM operands o LEFT JOIN datums m ON m.oid=o.map_id LEFT JOIN datums k ON k.oid=o.key_id
 LEFT JOIN map_entries item ON item.oid=o.map_id AND item.key_id=o.key_id
 WHERE o.func='dml://builtin/map/get' AND (m.kind IS DISTINCT FROM 'map' OR k.kind IS DISTINCT FROM 'string' OR item.value_id IS NULL OR item.value_id IS DISTINCT FROM o.value_id)
UNION ALL SELECT 'list_get_value',o.dag,'list[index] result differs' FROM operands o LEFT JOIN datums l ON l.oid=o.list_id LEFT JOIN datums i ON i.oid=o.index_id
 LEFT JOIN edges item ON item.src_kind='datum' AND item.src=o.list_id AND item.label='item-'||i.scalar
 WHERE o.func='dml://builtin/list/get' AND (l.kind IS DISTINCT FROM 'list' OR i.kind IS DISTINCT FROM 'i64' OR try_cast(i.scalar AS BIGINT)<0 OR item.dst IS NULL OR item.dst IS DISTINCT FROM o.value_id)
UNION ALL SELECT 'map_insert_value',o.dag,'immutable insertion differs' FROM operands o LEFT JOIN datums m ON m.oid=o.map_id LEFT JOIN datums k ON k.oid=o.key_id LEFT JOIN datums v ON v.oid=o.value_id
 WHERE o.func='dml://builtin/map/insert' AND (m.kind IS DISTINCT FROM 'map' OR k.kind IS DISTINCT FROM 'string' OR v.kind IS DISTINCT FROM 'map'
 OR EXISTS(SELECT 1 FROM map_entries old WHERE old.oid=o.map_id AND old.key_id=o.key_id)
 OR NOT EXISTS(SELECT 1 FROM map_entries added WHERE added.oid=o.value_id AND added.key_id=o.key_id AND added.value_id=o.inserted_id)
 OR EXISTS(SELECT 1 FROM map_entries old WHERE old.oid=o.map_id AND NOT EXISTS(SELECT 1 FROM map_entries new WHERE new.oid=o.value_id AND new.key_id=old.key_id AND new.value_id=old.value_id))
 OR EXISTS(SELECT 1 FROM map_entries new WHERE new.oid=o.value_id AND new.key_id<>o.key_id AND NOT EXISTS(SELECT 1 FROM map_entries old WHERE old.oid=o.map_id AND old.key_id=new.key_id AND old.value_id=new.value_id)));
