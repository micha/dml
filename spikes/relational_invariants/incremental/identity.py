"""Strict canonical descriptions and dependency-complete, path-neutral stage keys."""

import hashlib
import json
import re
from pathlib import PurePosixPath

FORMAT = 'spike-incremental-v1'
REQUIRED = {
    'E': {'candidate', 'exercise', 'wrapper', 'runtime'},
    'P': {'upstream_key', 'upstream_artifact', 'normalizer', 'decoder', 'wrapper', 'runtime'},
    'C': {'upstream_key', 'upstream_artifact', 'checker', 'wrapper', 'runtime'},
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('expected exact lowercase SHA256')
    return value


def safe_name(value):
    if type(value) is not str or not value or '\\' in value or '\x00' in value:
        raise ValueError('unsafe artifact name')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('', '.', '..') for part in value.split('/')):
        raise ValueError('unsafe artifact name')
    return value


def validate(value):
    if value is None or type(value) in (bool, str):
        return
    if type(value) is int and -(2**63) <= value < 2**63:
        return
    if type(value) is list:
        for item in value:
            validate(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            validate(item)
        return
    raise ValueError('description requires null/bool/I64/string/list/string-key object')


def canonical(value):
    validate(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate description field')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('nonstandard JSON constant')


def parse(data):
    if type(data) is not bytes:
        raise TypeError('description requires bytes')
    value = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
    validate(value)
    return value


def exact(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError('description field set differs')
    return value


def key(envelope):
    exact(envelope, {'format', 'namespace', 'stage', 'dependencies', 'context', 'limits'})
    if envelope['format'] != FORMAT or envelope['stage'] not in REQUIRED:
        raise ValueError('unsupported stage envelope')
    sha(envelope['namespace'])
    dependencies = exact(envelope['dependencies'], REQUIRED[envelope['stage']])
    for value in dependencies.values():
        sha(value)
    if type(envelope['context']) is not dict or type(envelope['limits']) is not dict:
        raise ValueError('context and limits require objects')
    return digest(b'incremental-v1/' + envelope['stage'].encode('ascii') + b'\x00' + canonical(envelope))


def file_manifest(root):
    """Every regular file, no followed symlinks or implicit executable additions."""
    root = root.resolve()
    rows = []
    for path in sorted(root.rglob('*'), key=lambda path: path.relative_to(root).as_posix()):
        if path.is_symlink():
            raise ValueError('symlink in snapshot/artifact')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError('nonregular snapshot/artifact')
        name = safe_name(path.relative_to(root).as_posix())
        data = path.read_bytes()
        rows.append({'path': name, 'size': len(data), 'sha256': digest(data)})
    return rows


def manifest_digest(rows):
    names = set()
    for row in rows:
        exact(row, {'path', 'size', 'sha256'})
        safe_name(row['path'])
        sha(row['sha256'])
        if type(row['size']) is not int or row['size'] < 0 or row['path'] in names:
            raise ValueError('invalid or conflicting file manifest')
        names.add(row['path'])
    if rows != sorted(rows, key=lambda row: row['path']):
        raise ValueError('manifest order differs')
    return digest(canonical(rows))
