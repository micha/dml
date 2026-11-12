"""Independent byte/UTF8/JSON projection of stored V headers; no DML validators."""

import json

SCHEMA = {'dag': 'VARCHAR', 'field': 'VARCHAR', 'datum': 'VARCHAR',
          'byte_count': 'INTEGER', 'parse_error': 'VARCHAR', 'document': 'JSON'}


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def reject_nonfinite(value):
    raise ValueError('nonfinite JSON')


def project(rows):
    nodes = {row['oid']: row for row in rows['nodes']}
    datums = {row['oid']: row for row in rows['datums']}
    fields = {}
    for row in rows['fields']:
        fields.setdefault(row['dag'], {})[row['name']] = row['node']
    targets = set()
    for slots in fields.values():
        node = nodes.get(slots.get('validation'))
        if node is not None and node['kind'] == 'subdag':
            targets.add(node['target'])
    result = []
    for dag in sorted(targets):
        for name in ('expected', 'job', 'observation'):
            node = nodes.get(fields.get(dag, {}).get(name))
            datum = datums.get(node['target']) if node and node['kind'] == 'literal' else None
            row = {'dag': dag, 'field': name, 'datum': datum['oid'] if datum else None,
                   'byte_count': None, 'parse_error': None, 'document': None}
            try:
                if datum is None or datum['kind'] != 'bytes':
                    raise ValueError('header is not a BYTES literal')
                raw = bytes.fromhex(datum['scalar'])
                row['byte_count'] = len(raw)
                if len(raw) > 8192:
                    raise ValueError('header exceeds8192 bytes')
                document = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_keys,
                                      parse_constant=reject_nonfinite)
                if type(document) is not dict:
                    raise ValueError('header must be a JSON object')
                row['document'] = json.dumps(document, sort_keys=True, separators=(',', ':'))
            except (ValueError, UnicodeError) as error:
                row['parse_error'] = str(error)
            result.append(row)
    return result
