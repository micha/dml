"""Immutable artifact admission; partial/tampered files never become cache misses."""

from pathlib import Path

from .identity import FORMAT, canonical, digest, exact, file_manifest, manifest_digest, parse, sha

MAX_DATA = 32 * 1024 * 1024
MAX_LOGS = 1024 * 1024
FIELDS = {'format', 'stage', 'key', 'producer', 'dependencies', 'status', 'exit', 'files'}


def describe(directory, *, stage, key, producer, dependencies, status, exit_code):
    directory = Path(directory)
    if (directory / 'manifest.json').exists():
        raise ValueError('artifact manifest already exists')
    files = file_manifest(directory)
    logs = sum(row['size'] for row in files if row['path'] in ('stdout.log', 'stderr.log'))
    data = sum(row['size'] for row in files) - logs
    if data > MAX_DATA or logs > MAX_LOGS:
        raise ValueError('artifact admission size bound exceeded')
    manifest_digest(files)
    document = {'format': FORMAT, 'stage': stage, 'key': key, 'producer': producer,
                'dependencies': dependencies, 'status': status, 'exit': exit_code, 'files': files}
    validate(document)
    return document


def validate(document):
    exact(document, FIELDS)
    if document['format'] != FORMAT or document['stage'] not in ('E', 'P', 'C'):
        raise ValueError('unsupported artifact profile')
    sha(document['key'])
    if type(document['producer']) is not str or not document['producer']:
        raise ValueError('missing producer occurrence')
    if type(document['dependencies']) is not dict:
        raise ValueError('artifact dependencies require object')
    for value in document['dependencies'].values():
        sha(value)
    if type(document['exit']) is not int or document['status'] not in ('success', 'rejected', 'error'):
        raise ValueError('invalid terminal artifact outcome')
    if (document['status'] == 'success') != (document['exit'] == 0):
        raise ValueError('success and actual exit disagree')
    manifest_digest(document['files'])
    return document


def finalize(partial, destination, document):
    partial, destination = Path(partial), Path(destination)
    if not partial.name.endswith('.partial') or partial.parent != destination.parent:
        raise ValueError('finalize requires sibling owned partial directory')
    if destination.exists() or destination.is_symlink():
        raise ValueError('artifact destination already exists')
    validate(document)
    if file_manifest(partial) != document['files']:
        raise ValueError('artifact changed before publication')
    (partial / 'manifest.json').write_bytes(canonical(document))
    partial.rename(destination)
    return digest(canonical(document))


def admit(root, name, *, expected_digest=None):
    """Only owned direct-child finalized directories. No historical arbitrary path following."""
    from .identity import safe_name
    safe_name(name)
    if '/' in name or name.endswith('.partial'):
        raise ValueError('not a finalized artifact child')
    root = Path(root)
    directory = root / name
    if root.is_symlink() or directory.is_symlink() or not directory.is_dir():
        raise ValueError('artifact directory unavailable/unsafe')
    manifest_path = directory / 'manifest.json'
    if manifest_path.is_symlink():
        raise ValueError('symlink artifact manifest')
    raw = manifest_path.read_bytes()
    document = validate(parse(raw))
    if raw != canonical(document):
        raise ValueError('noncanonical artifact manifest')
    if expected_digest is not None and digest(raw) != sha(expected_digest):
        raise ValueError('artifact manifest digest differs')
    actual = file_manifest(directory)
    actual = [row for row in actual if row['path'] != 'manifest.json']
    if actual != document['files']:
        raise ValueError('artifact file set/digests differ')
    logs = sum(row['size'] for row in actual if row['path'] in ('stdout.log', 'stderr.log'))
    if sum(row['size'] for row in actual) - logs > MAX_DATA or logs > MAX_LOGS:
        raise ValueError('artifact admission size bound exceeded')
    return document
