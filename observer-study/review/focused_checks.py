#!/usr/bin/env python3
"""Independent Stage 0 checks; no producer imports, dispatch or runtime contents.

Mutations use enumerated copies in reviewer-owned ignored runtime. Exit 1 means
one or more reject-required probes were accepted, not that research was rerun.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'observer-study/corpus'
RUNTIME = ROOT / 'observer-study/runtime/stage0'
spec = importlib.util.spec_from_file_location('stage0_checker_under_review', PACKAGE / 'corpus.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)  # Only the corpus checker, never feasibility modules.


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode()


def strict(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def pointer(value, path):
    assert path == '' or path.startswith('/')
    if not path:
        return value
    for part in path[1:].split('/'):
        assert not re.search(r'~(?![01])', part)
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            assert re.fullmatch('0|[1-9][0-9]*', part)
            value = value[int(part)]
        else:
            value = value[part]
    return value


def independent():
    recipe = strict(C.read_bytes(PACKAGE, 'allowlist.json'))
    manifest = strict(C.read_bytes(PACKAGE, 'manifest.json'))
    assert manifest['allowlist_sha256'] == sha(C.read_bytes(PACKAGE, 'allowlist.json'))
    for name, digest in manifest['files'].items():
        assert sha(C.read_bytes(PACKAGE, name)) == digest, name
    snapshots = {}
    selected_rows = 0
    for entry in recipe['sources']:
        # Audited bounded no-follow reader; independent decoding, selection and hashing.
        assert entry['path'].startswith('feasibility/') and '/runtime/' not in entry['path']
        raw = C.read_bytes(ROOT, entry['path'])
        assert len(raw) == entry['original_bytes']
        assert sha(raw) == entry['sha256']
        if entry['kind'] == 'json':
            original = strict(raw)
            rows = [{'locator': loc, 'value': pointer(original, loc)} for loc in entry['selectors']]
        else:
            assert entry['kind'] == 'text'
            lines = raw.decode().splitlines(keepends=True)
            rows = []
            for start, end in entry['selectors']:
                assert 1 <= start <= end <= len(lines)
                rows.append({'locator': f'lines:{start}-{end}', 'value': ''.join(lines[start-1:end])})
        for row in rows:
            row['value_sha256'] = sha(canonical(row['value']))
        expected = {'source_id': entry['id'], 'source_path': entry['path'],
                    'original_sha256': entry['sha256'], 'acquisition': 'retrospective-selected-copy',
                    'values': rows}
        assert canonical(expected) == C.read_bytes(PACKAGE, 'fixtures/' + entry['id'] + '.json')
        snapshots[entry['id']] = expected
        selected_rows += len(rows)
    truth = strict(C.read_bytes(PACKAGE, 'ground-truth.json'))
    gaps = strict(C.read_bytes(PACKAGE, 'gaps.json'))
    citations = [c for s in truth['scenarios'] for f in s['facts'] for c in f['citations']]
    citations += [c for g in gaps['items'] for c in g['citations']]
    citations += [s['citation'] for s in recipe['supporting_paths']]
    for c in citations:
        snap = snapshots[c['source_id']]
        row = pointer(snap, c['fixture_pointer'])
        assert row['locator'] == c['original_locator']
        assert row['value_sha256'] == c['value_sha256']
        assert snap['source_path'] == c['source_path']
        assert snap['original_sha256'] == c['original_sha256']
    by_id = {e['id']: e for e in recipe['sources']}
    for b in recipe['historical_bindings']:
        value = snapshots[b['manifest_id']]['values'][b['selection_index']]['value']
        assert by_id[b['target_id']]['sha256'] == pointer(value, b['digest_pointer'])
    marker = strict(C.read_bytes(ROOT, 'observer-study/runtime/stage0/curator-done.json'))
    for key, rel in [('manifest', 'observer-study/corpus/manifest.json'),
                     ('report', marker['report']), ('summary', marker['summary'])]:
        assert sha(C.read_bytes(ROOT, rel)) == marker[key + '_sha256']
    return {'sources': len(snapshots), 'selected_rows': selected_rows,
            'curator_completion_hashes_verified': 3,
            'manifest_sha256': sha(C.read_bytes(PACKAGE, 'manifest.json')),
            'citations': len(citations), 'historical_bindings': len(recipe['historical_bindings']),
            'original_bytes': sum(e['original_bytes'] for e in recipe['sources']),
            'fixture_bytes': sum(len(C.read_bytes(PACKAGE, 'fixtures/' + e['id'] + '.json')) for e in recipe['sources'])}


def probe(name, mutate, sources=False):
    manifest = strict(C.read_bytes(PACKAGE, 'manifest.json'))
    with tempfile.TemporaryDirectory(prefix='reviewer-probe-', dir=RUNTIME) as temp:
        target = Path(temp)
        for rel in ['allowlist.json', 'manifest.json', *manifest['files']]:
            path = target / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(C.read_bytes(PACKAGE, rel))
        def change(rel, fn):
            value = strict(C.read_bytes(target, rel))
            fn(value)
            raw = canonical(value)
            (target / rel).write_bytes(raw)
            index = strict(C.read_bytes(target, 'manifest.json'))
            if rel == 'allowlist.json':
                index['allowlist_sha256'] = sha(raw)
                index['supporting_availability'] = value['supporting_paths']
            else:
                index['files'][rel] = sha(raw)
            (target / 'manifest.json').write_bytes(canonical(index))
        mutate(target, change)
        try:
            result = C.check(target, sources=sources)
        except Exception as exc:
            return {'probe': name, 'expected': 'reject', 'observed': 'rejected',
                    'exception': type(exc).__name__, 'detail': str(exc)}
        return {'probe': name, 'expected': 'reject', 'observed': 'ACCEPTED', 'result': result}


def main():
    RUNTIME.mkdir(exist_ok=True)
    measured = independent()
    probes = []
    def mutation(name, rel, fn, sources=False):
        probes.append(probe(name, lambda t, change: change(rel, fn), sources))
    mutation('unknown-source-evidence-class', 'allowlist.json',
             lambda v: v['sources'][0].update(evidence_class='cloud-tested'))
    mutation('unknown-fact-evidence-class', 'ground-truth.json',
             lambda v: v['scenarios'][0]['facts'][0].update(evidence_class='unknown'))
    mutation('unknown-source-kind-offline', 'allowlist.json',
             lambda v: next(e for e in v['sources'] if e['id'] == 'initial-code').update(kind='future-format'))
    mutation('unknown-source-kind-with-sources', 'allowlist.json',
             lambda v: next(e for e in v['sources'] if e['id'] == 'initial-code').update(kind='future-format'), True)
    mutation('unknown-gap-schema', 'gaps.json', lambda v: v.update(schema='future-gap-v99'))
    mutation('contradictory-answer-ingestion', 'ground-truth.json', lambda v: v.update(ingestion='live-native'))
    mutation('negative-original-byte-count-with-sources', 'allowlist.json',
             lambda v: v['sources'][0].update(original_bytes=-1), True)
    mutation('empty-scenario-facts', 'ground-truth.json', lambda v: v['scenarios'][0].update(facts=[]))
    mutation('non-string-unit', 'ground-truth.json', lambda v: v['scenarios'][0]['facts'][0].update(unit=['made-up-unit']))
    mutation('historical-occurrence-created', 'ground-truth.json', lambda v: v.update(historical_execution_ids_created=1))
    mutation('broken-original-locator', 'ground-truth.json',
             lambda v: v['scenarios'][0]['facts'][0]['citations'][0].update(original_locator='/not/the/original'))
    mutation('supporting-path-traversal', 'allowlist.json',
             lambda v: v['supporting_paths'][0].update(path='feasibility/runtime/../../outside'))
    probes.append(probe('unexpected-manifest-member', lambda t, change:
                        (t / 'manifest.json').write_bytes(canonical({**strict(C.read_bytes(t, 'manifest.json')),
                         'files': {**strict(C.read_bytes(t, 'manifest.json'))['files'], '../outside': '0'*64}}))))
    probes.append(probe('leaf-symlink-fixture', lambda t, change:
                        ((t / 'fixtures/initial-code.json').unlink(),
                         (t / 'fixtures/initial-code.json').symlink_to(t / 'ground-truth.json'))))
    # Direct acquisition boundary with synthetic original bytes; no producer reads.
    for name, raw in [('duplicate-original-json-keys', b'{"x":1,"x":2}'),
                      ('nonfinite-unselected-original-value', b'{"x":1,"other":NaN}')]:
        entry = {'id': 'synthetic', 'path': 'feasibility/synthetic.json', 'kind': 'json',
                 'selectors': ['/x'], 'sha256': sha(raw)}
        try:
            C.project(raw, entry)
        except Exception as exc:
            probes.append({'probe': name, 'expected': 'reject', 'observed': 'rejected', 'exception': type(exc).__name__})
        else:
            probes.append({'probe': name, 'expected': 'reject', 'observed': 'ACCEPTED'})
    accepted = sum(p['observed'] == 'ACCEPTED' for p in probes)
    output = {'independent_integrity': measured, 'probes': probes,
              'reject_required_probes': len(probes), 'correct_rejections': len(probes)-accepted,
              'unexpected_acceptances': accepted,
              'meaning': 'Rejected/accepted validator probes, not research trials. Rehashed copies do not demonstrate bypass of frozen original hashes.'}
    print(json.dumps(output, sort_keys=True, indent=2))
    return bool(accepted)


if __name__ == '__main__':
    raise SystemExit(main())
