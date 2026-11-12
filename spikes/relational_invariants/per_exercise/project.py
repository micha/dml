"""Replaceable fixed projection payload: public import/unique extraction, no SQL."""
from pathlib import Path

from incremental.identity import canonical, digest, parse
from per_exercise.capsules import ordered, validate


def canonical_rows(raw):
    """Convert the native extractor's mapping without dropping fields or relaxing validation."""
    return ordered(dict(raw))


def project(dml, upstream, repository, directory, spec):
    from daggerml import transfer
    from normalizer import extract
    from shared_index.project import catalog
    upstream, directory = Path(upstream), Path(directory)
    evidence = parse((upstream / 'evidence.json').read_bytes())
    bundle = (upstream / 'publication.bundle').read_bytes()
    if digest(bundle) != evidence['bundle_sha256'] or evidence['spec'] != spec:
        raise ValueError('producer evidence/input differs')
    imported = transfer.import_commit(repository, bundle)
    if str(imported.commit) != evidence['publication']:
        raise ValueError('imported root differs')
    rows, stats = extract({'repository': str(repository), 'roots': [evidence['publication']]})
    case_catalog = catalog(rows, evidence['publication'])
    if len(case_catalog['cases']) != 1:
        raise ValueError('producer batch not one case')
    case = case_catalog['cases'][0]
    if (case['label'] != spec['label'] or case['parameters'] != {'value': spec['value']}
            or (case['expectations']['outcome'] == 'reject') != spec['fault']
            or case['description'] != evidence['description'] or case['target'] != evidence['target']
            or case['occurrence'] != evidence['producer'] + '/exercise-1'):
        raise ValueError('producer case authority differs')
    rows['roots'] = [{'checkpoint': i, 'commit_id': root, 'expected_positions': positions}
                     for i, (root, positions) in enumerate(zip(case['roots'], case['expectations']['positions']))]
    capsule = validate({'rows': canonical_rows(rows), 'case': case, 'publication': evidence['publication'],
                        'producer_run': evidence['producer_run']})
    (directory / 'capsule.json').write_bytes(canonical(capsule))
    (directory / 'roots.json').write_bytes(canonical({'roots': evidence['roots'], 'spec': spec}))
    (directory / 'stats.json').write_bytes(canonical({'unique_record_reads': stats['unique_record_reads'],
                                                     'reference_edges': stats['reference_edges']}))
    return capsule
