#!/usr/bin/env python3
"""Stage 0 only: bounded acquisition and offline integrity, never study execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat

HERE = Path(__file__).absolute().parent
ROOT = HERE.parent.parent
MAX_BYTES = 256 * 1024
CLASSES = {'actual-recorded-effects', 'simulation', 'source-inspection', 'authored-claim'}


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parts(rel):
    if not isinstance(rel, str) or not rel or '\\' in rel:
        raise ValueError('unsafe path')
    p = PurePosixPath(rel)
    if p.is_absolute() or any(x in ('', '.', '..') for x in rel.split('/')):
        raise ValueError('unsafe path')
    return p.parts


def parent_fd(root, rel):
    # Every component opened relative to its pinned parent; never follow symlinks.
    names = parts(rel)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in names[:-1]:
            nxt = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd, names[-1]
    except BaseException:
        os.close(fd)
        raise


def read_bytes(root, rel):
    fd, name = parent_fd(root, rel)
    try:
        child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(child, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('not a single-link regular file')
            data = stream.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError('oversized input')
            return data
    finally:
        os.close(fd)


def metadata(root, rel):
    """Bounded lstat of one explicitly cited path, no content or symlink traversal."""
    try:
        fd, name = parent_fd(root, rel)
        try:
            mode = os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
        finally:
            os.close(fd)
        return 'symlink-not-followed' if stat.S_ISLNK(mode) else ('present-regular' if stat.S_ISREG(mode) else 'present-directory' if stat.S_ISDIR(mode) else 'present-other')
    except FileNotFoundError:
        return 'missing'
    except (OSError, ValueError):
        return 'unavailable-or-unsafe'


def decode_json(data):
    """Reject ambiguity/nonfinite values anywhere, before selection or hashing."""
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError('duplicate JSON key')
            result[k] = v
        return result
    def finite_float(text):
        import math
        value = float(text)
        if not math.isfinite(value):
            raise ValueError('nonfinite JSON')
        return value
    return json.loads(data, object_pairs_hook=unique, parse_float=finite_float,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def load(root, rel):
    return decode_json(read_bytes(root, rel))


def validate_source_format(entry):
    if entry['kind'] not in {'json', 'text'}:
        raise ValueError('invalid source kind')
    if type(entry['original_bytes']) is not int or not 0 <= entry['original_bytes'] <= MAX_BYTES:
        raise ValueError('invalid original byte count')


def pointer(value, path):
    if path == '':
        return value
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('invalid JSON pointer')
    for token in path[1:].split('/'):
        import re
        if re.search(r'~(?![01])', token):
            raise ValueError('invalid JSON pointer escape')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith('0')):
                raise ValueError('invalid array index')
            value = value[int(token)]
        else:
            value = value[token]
    return value


def project(data, entry):
    if entry['kind'] == 'json':
        value = decode_json(data)
        values = [{'locator': p, 'value': pointer(value, p)} for p in entry['selectors']]
    elif entry['kind'] == 'text':
        lines = data.decode('utf-8').splitlines(keepends=True)
        values = []
        for start, end in entry['selectors']:
            if not 1 <= start <= end <= len(lines):
                raise ValueError('invalid line span')
            values.append({'locator': f'lines:{start}-{end}', 'value': ''.join(lines[start-1:end])})
    else:
        raise ValueError('invalid source kind')
    for row in values:
        row['value_sha256'] = digest(canonical(row['value']))
    return {'source_id': entry['id'], 'source_path': entry['path'],
            'original_sha256': entry['sha256'], 'acquisition': 'retrospective-selected-copy',
            'values': values}


def reconstruct(recipe, root=ROOT):
    outputs = {}
    for entry in recipe['sources']:
        validate_source_format(entry)
        if not entry['path'].startswith('feasibility/') or '/runtime/' in entry['path']:
            raise ValueError('not a permitted source path')
        data = read_bytes(root, entry['path'])
        if len(data) != entry['original_bytes']:
            raise ValueError('original byte count mismatch: ' + entry['path'])
        if digest(data) != entry['sha256']:
            raise ValueError('original hash mismatch: ' + entry['path'])
        outputs['fixtures/' + entry['id'] + '.json'] = canonical(project(data, entry))
    return outputs


def check(corpus=HERE, sources=False, root=ROOT):
    recipe = load(corpus, 'allowlist.json')
    manifest = load(corpus, 'manifest.json')
    if manifest['schema'] != 'stage0-corpus-v1' or manifest['ingestion'] != 'retrospective':
        raise ValueError('unsupported corpus version or ingestion')
    if digest(read_bytes(corpus, 'allowlist.json')) != manifest['allowlist_sha256']:
        raise ValueError('allowlist integrity')
    if recipe['schema'] != 'stage0-allowlist-v1':
        raise ValueError('unsupported allowlist version')
    by_id = {}
    import re
    for entry in recipe['sources']:
        validate_source_format(entry)
        if not re.fullmatch(r'[a-z0-9-]+', entry['id']) or entry['id'] in by_id or entry['evidence_class'] not in CLASSES:
            raise ValueError('invalid source classification/duplicate')
        parts(entry['path'])
        if not entry['path'].startswith('feasibility/') or '/runtime/' in entry['path']:
            raise ValueError('not a permitted source path')
        if not re.fullmatch(r'[0-9a-f]{64}', entry['sha256']):
            raise ValueError('invalid original digest')
        by_id[entry['id']] = entry
    if manifest['supporting_availability'] != recipe['supporting_paths']:
        raise ValueError('availability snapshot mismatch')
    if set(manifest['files']) != {'fixtures/' + x + '.json' for x in by_id} | {'ground-truth.json', 'gaps.json', 'ANSWER-SHEET.md'}:
        raise ValueError('unexpected/missing package member')
    for rel, sha in manifest['files'].items():
        if digest(read_bytes(corpus, rel)) != sha:
            raise ValueError('package hash mismatch: ' + rel)
    snapshots = {}
    for sid, entry in by_id.items():
        snap = load(corpus, 'fixtures/' + sid + '.json')
        if (snap['source_id'], snap['source_path'], snap['original_sha256'], snap['acquisition']) != (sid, entry['path'], entry['sha256'], 'retrospective-selected-copy'):
            raise ValueError('snapshot identity')
        expected = entry['selectors'] if entry['kind'] == 'json' else [f'lines:{a}-{b}' for a,b in entry['selectors']]
        if [r['locator'] for r in snap['values']] != expected:
            raise ValueError('snapshot selection')
        for row in snap['values']:
            if digest(canonical(row['value'])) != row['value_sha256']:
                raise ValueError('value digest')
        snapshots[sid] = snap
    truth = load(corpus, 'ground-truth.json')
    if (truth['schema'] != 'stage0-answer-v1' or truth['historical_execution_ids_created'] != 0
            or truth['ingestion'] != manifest['ingestion']):
        raise ValueError('answer identity boundary or ingestion')
    if {s['id'] for s in truth['scenarios']} != set('ABCDE') or len(truth['scenarios']) != 5:
        raise ValueError('scenario coverage')
    claims = 0
    def citation(c):
        entry = by_id[c['source_id']]
        snap = snapshots[c['source_id']]
        row = pointer(snap, c['fixture_pointer'])
        if row != {'locator': c['original_locator'], 'value': row['value'], 'value_sha256': c['value_sha256']}:
            raise ValueError('citation value/locator mismatch')
        if c['source_path'] != entry['path'] or c['original_sha256'] != entry['sha256']:
            raise ValueError('citation original mismatch')
    for support in recipe['supporting_paths']:
        parts(support['path'])
        if not support['path'].startswith('feasibility/') or '/runtime/' not in support['path'] or support['contents_read'] is not False:
            raise ValueError('invalid metadata-only path')
        if support['observation'] not in {'missing', 'unavailable-or-unsafe', 'symlink-not-followed', 'present-regular', 'present-directory', 'present-other'}:
            raise ValueError('invalid availability classification')
        citation(support['citation'])
    ids = set()
    for scenario in truth['scenarios']:
        if not isinstance(scenario['facts'], list) or not scenario['facts']:
            raise ValueError('scenario requires nonempty cited facts')
        for fact in scenario['facts']:
            if fact['id'] in ids or fact['evidence_class'] not in CLASSES or not fact['citations'] or not fact['limitations']:
                raise ValueError('invalid fact metadata')
            ids.add(fact['id'])
            if fact['origin'] != 'curator-authored-interpretation-of-cited-evidence':
                raise ValueError('claim/proof boundary')
            if (not isinstance(fact['unit'], str) or not fact['unit'].strip()
                    or not fact['harness_result'] or not fact['system_outcome']):
                raise ValueError('missing unit/outcome boundary')
            for c in fact['citations']:
                citation(c)
            claims += 1
    gaps = load(corpus, 'gaps.json')
    if gaps['schema'] != 'stage0-gaps-v1':
        raise ValueError('unsupported gap schema')
    if len({g['id'] for g in gaps['items']}) != len(gaps['items']):
        raise ValueError('duplicate gap')
    for gap in gaps['items']:
        if not gap['citations'] or not gap['impact']:
            raise ValueError('uncited gap')
        for c in gap['citations']:
            citation(c)
    for binding in recipe['historical_bindings']:
        actual = by_id[binding['target_id']]['sha256']
        row = snapshots[binding['manifest_id']]['values'][binding['selection_index']]['value']
        expected = pointer(row, binding['digest_pointer'])
        if actual != expected:
            raise ValueError('historical checksum binding mismatch')
    if sources:
        rebuilt = reconstruct(recipe, root)
        for rel, data in rebuilt.items():
            if read_bytes(corpus, rel) != data:
                raise ValueError('regeneration mismatch: ' + rel)
    return {'status': 'valid', 'source_snapshots': len(by_id), 'facts': claims,
            'scenarios': 5, 'gaps': len(gaps['items']), 'historical_hash_bindings': len(recipe['historical_bindings']),
            'fixture_bytes': sum(len(read_bytes(corpus, 'fixtures/' + sid + '.json')) for sid in by_id),
            'originals_checked': sources,
            'meaning': 'integrity and citation consistency, not authenticity or scientific safety'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', action='store_true', help='check only frozen allowlisted originals and byte-reproducible projections')
    parser.add_argument('--availability', action='store_true', help='lstat only explicitly cited supporting paths; never read them')
    args = parser.parse_args()
    result = check(sources=args.sources)
    if args.availability:
        recipe = load(HERE, 'allowlist.json')
        result['current_availability'] = [{'path': r['path'], 'status': metadata(ROOT, r['path'])} for r in recipe['supporting_paths']]
    print(canonical(result).decode(), end='')


if __name__ == '__main__':
    main()
