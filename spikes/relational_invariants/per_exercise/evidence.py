"""One producer publication in the shared evidence store; unchanged fixed helpers."""
from pathlib import Path

from incremental.identity import canonical, digest
from .profiles import validate_spec


def produce(dml, repository, spec, producer, directory):
    from shared_index.exercise import (RUN, CONTEXT, OBSERVATIONS, DESCRIPTION, LIMITS,
        captures, fixture, make_case, publication, index, role_dag, literal, id_list)
    from daggerml import transfer
    validate_spec(spec)
    captured = captures()
    with dml.Repository(repository) as repo:
        with repo.write() as tx:
            run = role_dag(tx, RUN, {'namespace': literal(tx, producer),
                'scenarios': literal(tx, canonical([spec])), 'captures': literal(tx, canonical(captured)),
                'limits': literal(tx, canonical(LIMITS))})
            previous = tx.put_commit(tx.put_tree({'exercise-index': index(tx, {}), 'exercise-run': run}))
            base, entries, sources, bindings = fixture(tx, [spec])
            context = role_dag(tx, CONTEXT, {'scenario': literal(tx, 'builtin-map-get'),
                'parameters': literal(tx, canonical({'value': spec['value']})),
                'captures': literal(tx, canonical(captured)), 'limits': literal(tx, canonical(LIMITS)),
                'expectations': literal(tx, canonical({'positions': [None, 3, 3],
                    'outcome': 'reject' if spec['fault'] else 'accept',
                    'invariant': 'map_get_value' if spec['fault'] else None})),
                'fixture': literal(tx, base.bytes), 'sources': id_list(tx, sources[spec['value']])})
        occurrence = producer + '/exercise-1'
        target, roots, returns, bad = make_case(repo, base, entries, sources[spec['value']],
                                               bindings, context, occurrence, spec)
        with repo.write() as tx:
            observations = role_dag(tx, OBSERVATIONS, {'calls': literal(tx, len(returns)),
                'returns': literal(tx, canonical(returns)), 'errors': literal(tx, canonical([])),
                'bad-operation': literal(tx, None if bad is None else bad.bytes)})
            description = role_dag(tx, DESCRIPTION, {'label': literal(tx, spec['label']),
                'occurrence': literal(tx, occurrence), 'target': literal(tx, target.bytes),
                'roots': id_list(tx, roots), 'context': tx.put_subdag(context),
                'observations': tx.put_subdag(observations)})
            published = publication(tx, previous, target, run, {'case-001': description})
    bundle = transfer.export_commit(repository, commit=published)
    directory = Path(directory)
    (directory / 'publication.bundle').write_bytes(bundle)
    evidence = {'publication': str(published), 'roots': [str(published)], 'producer_run': str(run),
                'description': str(description), 'target': str(target), 'spec': spec,
                'occurrence': occurrence, 'calls': len(returns), 'producer': producer,
                'bundle_sha256': digest(bundle)}
    (directory / 'evidence.json').write_bytes(canonical(evidence))
    return evidence
