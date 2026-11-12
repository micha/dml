"""Strict fixed case envelopes; operational grouping never partitions stage identity."""
from incremental.driver import LIMITS
from incremental.identity import FORMAT, canonical, digest, exact, key

PROFILE = 'per-exercise-v1'
LABELS = ('positive-a', 'negative-b', 'positive-c')


def specs(changed=False):
    return [{'label': LABELS[0], 'value': 42, 'fault': False},
            {'label': LABELS[1], 'value': 44 if changed else 42, 'fault': True},
            {'label': LABELS[2], 'value': 43, 'fault': False}]


def validate_spec(spec):
    exact(spec, {'label', 'value', 'fault'})
    if (spec['label'] not in LABELS or type(spec['value']) is not int
            or not -(2**63) <= spec['value'] < 2**63 or type(spec['fault']) is not bool
            or spec['fault'] and spec['value'] == 2**63 - 1):
        raise ValueError('unsupported exact case input')
    return spec


def envelope(pins, stage, spec, *, candidate='A', variant=None, upstream=None):
    validate_spec(spec)
    if candidate not in ('A', 'B'):
        raise ValueError('unknown candidate')
    context = {'profile': PROFILE, **spec}
    dependencies = {'wrapper': pins['wrapper'], 'runtime': pins['runtime_digest']}
    if stage == 'E':
        dependencies.update(candidate=pins['fingerprints']['candidate-' + candidate],
                            exercise=pins['exercise'])
    else:
        if upstream is None or upstream['stage'] != ('E' if stage == 'P' else 'P'):
            raise ValueError('wrong upstream stage')
        if len(upstream['roots']) != 1:
            raise ValueError('one producer publication required')
        context['roots'] = upstream['roots']
        dependencies.update(upstream_key=upstream['key'], upstream_artifact=upstream['digest'])
        if stage == 'P' and variant in ('P1', 'P2'):
            dependencies.update(normalizer=pins['payloads'][variant], decoder=pins['recorder'])
        elif stage == 'C' and variant in ('C1', 'C2'):
            dependencies.update(checker=pins['payloads'][variant])
        else:
            raise ValueError('unknown stage or payload')
    result = {'format': FORMAT, 'namespace': pins['namespace'], 'stage': stage,
              'dependencies': dependencies, 'context': context, 'limits': dict(LIMITS)}
    key(result)
    return result


def material_key(pins, projections):
    if len(projections) != 3:
        raise ValueError('complete three-case pool required')
    if [p['spec']['label'] for p in projections] != list(LABELS):
        raise ValueError('materialization order differs')
    return digest(b'per-exercise-pool-v1\0' + canonical({
        'inputs': [{'scenario': p['spec']['label'], 'key': p['key'], 'artifact': p['digest']}
                   for p in projections], 'schema_materializer': pins['materializer'],
        'runtime': pins['runtime_digest']}))
