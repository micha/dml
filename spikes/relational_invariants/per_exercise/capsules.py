"""Strict per-case facts and immutable, independently scoped pool materialization."""
from pathlib import Path
import subprocess

from incremental.identity import canonical, digest, exact, file_manifest, parse
from schema import SCHEMA, KEYS


def ordered(rows):
    exact(rows, set(SCHEMA))
    result = {}
    for table, columns in SCHEMA.items():
        index = {}
        for row in rows[table]:
            exact(row, set(columns))
            for column, kind in columns.items():
                value = row[column]
                nullable = (table == 'datums' and column == 'scalar' or
                            table == 'roots' and column == 'expected_positions')
                if value is None and nullable:
                    continue
                if (kind == 'INTEGER' and type(value) is not int or
                        kind == 'VARCHAR' and type(value) is not str):
                    raise ValueError('typed fact column differs')
            identity = tuple(row[k] for k in KEYS[table])
            if identity in index:
                raise ValueError('duplicate capsule row identity')
            index[identity] = row
        result[table] = sorted(index.values(), key=canonical)
    if len(result['objects']) > 10000:
        raise ValueError('case object bound exceeded')
    return result


def validate(capsule):
    from shared_index.project import catalog, Facts
    exact(capsule, {'rows', 'case', 'publication', 'producer_run'})
    rows = ordered(capsule['rows'])
    if rows != capsule['rows']:
        raise ValueError('noncanonical fact order')
    actual = catalog(rows, capsule['publication'])
    if len(actual['cases']) != 1 or actual['cases'][0] != capsule['case']:
        raise ValueError('case catalog authority differs')
    facts = Facts(rows)
    if facts.index(capsule['publication'])[0] != capsule['producer_run']:
        raise ValueError('producer run differs')
    scope = capsule['case']
    roots = [{'checkpoint': i, 'commit_id': root, 'expected_positions': positions}
             for i, (root, positions) in enumerate(zip(scope['roots'], scope['expectations']['positions']))]
    if rows['roots'] != sorted(roots, key=canonical):
        raise ValueError('case root rows differ')
    # Detect dangling foreign records even outside the semantic target closure.
    facts.reached(capsule['publication'])
    return capsule


def merge(capsules):
    if len(capsules) != 3:
        raise ValueError('pool requires three capsules')
    merged = {table: {} for table in SCHEMA}
    for capsule in capsules:
        validate(capsule)
        for table, rows in capsule['rows'].items():
            if table == 'roots':
                continue
            for row in rows:
                identity = tuple(row[k] for k in KEYS[table])
                previous = merged[table].get(identity)
                if previous is not None and previous != row:
                    raise ValueError('conflicting shared row identity')
                merged[table][identity] = row
    if len(merged['objects']) > 10000:
        raise ValueError('pooled object bound exceeded')
    return {name: sorted(index.values(), key=canonical) for name, index in merged.items()}


def read(path):
    return validate(parse(Path(path).read_bytes()))


def seal(directory, identity, inputs, receipt):
    directory = Path(directory)
    files = file_manifest(directory)
    size = sum(row['size'] for row in files)
    logs = sum(row['size'] for row in files if row['path'] in ('stdout.log', 'stderr.log'))
    if size - logs > 32 * 1024 * 1024 or logs > 1024 * 1024:
        raise ValueError('assembly artifact cap exceeded')
    manifest = {'identity': identity, 'inputs': inputs, 'receipt': receipt, 'files': files}
    (directory / 'manifest.json').write_bytes(canonical(manifest))
    return digest(canonical(manifest))


def admit(directory, identity, inputs, expected_digest=None):
    directory = Path(directory)
    if (directory.is_symlink() or not directory.is_dir()
            or (directory / 'manifest.json').is_symlink()):
        raise ValueError('pool directory unavailable/unsafe')
    raw = (directory / 'manifest.json').read_bytes()
    record = exact(parse(raw), {'identity', 'inputs', 'receipt', 'files'})
    if (raw != canonical(record) or record['identity'] != identity or record['inputs'] != inputs
            or expected_digest is not None and digest(raw) != expected_digest):
        raise ValueError('pool manifest authority differs')
    files = [row for row in file_manifest(directory) if row['path'] != 'manifest.json']
    size = sum(row['size'] for row in files)
    logs = sum(row['size'] for row in files if row['path'] in ('stdout.log', 'stderr.log'))
    if files != record['files'] or size - logs > 32 * 1024 * 1024 or logs > 1024 * 1024:
        raise ValueError('pool file set/digests/cap differs')
    return record


def materialize(capsules, directory, identity, inputs, duckdb):
    from engine import quote
    directory = Path(directory)
    if directory.exists():
        raise ValueError('fresh pool destination exists')
    partial = directory.with_name(directory.name + '.partial')
    partial.mkdir(parents=True, exist_ok=False)
    rows = merge(capsules)
    database = partial / 'pool.duckdb'
    sql = ['BEGIN TRANSACTION;']
    for table, columns in SCHEMA.items():
        definition = ', '.join(f'"{key}" {kind}' for key, kind in columns.items())
        sql.append(f'CREATE TABLE pool_{table} ({definition});')
        path = partial / (table + '.jsonl')
        path.write_bytes(b''.join(canonical(row) + b'\n' for row in rows[table]))
        if rows[table]:
            types = ', '.join(f'{quote(k)}: {quote(v)}' for k, v in columns.items())
            sql.append(f'INSERT INTO pool_{table} SELECT * FROM read_json({quote(path.resolve())}, '
                       f"format='newline_delimited', columns={{{types}}});")
    sql.extend(['CREATE UNIQUE INDEX object_identity ON pool_objects(kind,oid);', 'COMMIT;'])
    query = '\n'.join(sql)
    (partial / 'load.sql').write_text(query + '\n')
    command = [duckdb, '-batch', '-bail', str(database)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate(query)
    receipt = {'pid': process.pid, 'wait_exit': process.returncode, 'command': command,
               'typed_objects': len(rows['objects'])}
    (partial / 'stdout.log').write_text(stdout)
    (partial / 'stderr.log').write_text(stderr)
    (partial / 'owner.json').write_bytes(canonical(receipt))
    if process.returncode != 0:
        raise RuntimeError('pool loader failed; retain partial/STOP')
    fingerprint = seal(partial, identity, inputs, receipt)
    partial.rename(directory)
    admit(directory, identity, inputs, fingerprint)
    return fingerprint
