"""Fixed three-case sequential stage requests, verified assemblies and saved continuation."""
from pathlib import Path
import argparse
import os
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    legacy = Path(__file__).resolve().parents[2] / 'base/controller/code'
    common = Path(__file__).resolve().parents[2] / 'common'
    if legacy.is_dir():
        sys.path[:0] = [str(legacy), str(common)]
    __package__ = 'per_exercise'

from incremental.artifacts import describe, finalize
from incremental.driver import PYTHON, environment
from incremental.identity import canonical, digest, key, parse
from incremental.records import Store
from incremental.stages import load_dml
from .pins import prepare, verify
from .profiles import envelope, material_key, specs
from . import capsules, batch


class Controller:
    def __init__(self, pins_path, directory, *, namespace='ACCEPTANCE/per-exercise-v1', create=False):
        if not namespace.startswith(('ACCEPTANCE/', 'CONTROL/')):
            raise ValueError('actual namespace must be explicit')
        self.pins_path = Path(pins_path).resolve()
        self.pins = verify(self.pins_path)
        self.directory = Path(directory).resolve()
        self.artifacts = self.directory / 'artifacts'
        self.evidence, self.decoder = self.directory / 'evidence.dml', self.directory / 'decoder.dml'
        root = Path(self.pins['root'])
        sys.path.insert(0, str(root / 'common'))
        dml = load_dml(root / 'base/controller/daggerml')
        if create:
            self.directory.mkdir(parents=True, exist_ok=False)
            self.artifacts.mkdir()
            for path in (self.evidence, self.decoder):
                with dml.Repository(path, create=True):
                    pass
        self.store = Store(dml, self.directory / 'controller.dml', self.artifacts, namespace, create=create)

    def result(self, terminal, request, fresh, satisfaction=None):
        attempt, produced, outcome, reference, artifact = self.store.terminal(terminal)
        spec = {name: parse(produced['inputs'])['context'][name] for name in ('label', 'value', 'fault')}
        directory = self.artifacts / reference['name']
        roots = []
        if outcome['status'] == 'success' and artifact['stage'] in ('E', 'P'):
            roots = parse((directory / ('evidence.json' if artifact['stage'] == 'E' else 'roots.json')).read_bytes())['roots']
        return {'request': str(request), 'terminal': str(terminal), 'outcome': str(attempt['outcome']),
                'satisfaction': None if satisfaction is None else str(satisfaction), 'fresh': fresh,
                'name': reference['name'], 'digest': reference['sha256'], 'key': produced['key'],
                'stage': artifact['stage'], 'status': outcome['status'], 'roots': roots, 'spec': spec}

    def stage(self, stage, spec, *, candidate='A', variant=None, upstream=None, pool=None, fresh=False):
        verify(self.pins_path)
        if upstream is not None:
            batch.authority(self.store, upstream, spec)
            actual = self.result(self.store.dml.ObjectId.from_hex(upstream['terminal']),
                                 upstream['request'], upstream['fresh'])
            if actual['roots'] != upstream['roots']:
                raise ValueError('upstream roots differ')
        if stage == 'C':
            if pool is None:
                raise ValueError('admitted pool required')
            self.validate_pool(pool, upstream)
        inputs = envelope(self.pins, stage, spec, candidate=candidate, variant=variant, upstream=upstream)
        request, _ = self.store.request(inputs, 'fresh' if fresh else 'reuse')
        reused = None if fresh else self.store.reuse(request)
        if reused is not None:
            return self.result(reused[0], request, False, reused[1])
        initial, producer, _ = self.store.begin(request)
        name = 'attempt-' + producer.rsplit('-', 1)[-1]
        partial = self.artifacts / (name + '.partial')
        partial.mkdir()
        job = {'pin_root': self.pins['root'], 'stage': stage, 'spec': spec, 'candidate': candidate,
               'variant': variant, 'key': key(inputs), 'producer': producer, 'output': str(partial),
               'repository': str(self.evidence if stage == 'E' else self.decoder),
               'upstream': None if upstream is None else str(self.artifacts / upstream['name']), 'pool': pool}
        job_path = self.directory / (name + '.job.json')
        job_path.write_bytes(canonical(job))
        command = [PYTHON, '-I', '-B', str(Path(self.pins['root']) / 'code/per_exercise/stages.py'), str(job_path)]
        with (partial / 'stdout.log').open('wb') as stdout, (partial / 'stderr.log').open('wb') as stderr:
            process = subprocess.Popen(command, env=environment(self.pins, self.directory), cwd=self.directory,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            owner = {'pid': process.pid, 'group': process.pid, 'command': command, 'producer': producer}
            owner_path = self.directory / (name + '.owner.json')
            owner_path.write_bytes(canonical(owner))
            code = process.wait()
        owner['wait_exit'] = code
        owner_path.write_bytes(canonical(owner))
        status = 'success' if code == 0 else ('rejected' if stage == 'C' and code == 1
                  and (partial / 'verdict.json').exists() else 'error')
        if status != 'error':
            receipt = parse((partial / 'receipt.json').read_bytes())
            root = Path(self.pins['root'])
            source = (root / 'code/per_exercise/evidence.py' if stage == 'E' else
                      root / 'payloads' / variant / ('project.py' if stage == 'P' else 'predicate.py'))
            package = (root / 'base' / ('candidate-' + candidate) / 'python/daggerml/daggerml'
                       if stage == 'E' else root / 'base/controller/daggerml')
            if (receipt['stage'] != stage or receipt['spec'] != spec or receipt['key'] != key(inputs)
                    or receipt['producer'] != producer or receipt['source'] != digest(source.read_bytes())
                    or receipt['package'] != str(package / '__init__.py')
                    or receipt['core'] != self.pins['core_sha256'] or receipt['python'] != PYTHON
                    or receipt['runtime'] != self.pins['runtime_digest']
                    or receipt['process'] != {'pid': process.pid, 'parent': os.getpid(), 'group': process.pid}
                    or len(receipt['children']) != (1 if stage == 'C' else 0)
                    or any(c['wait_exit'] != 0 or c['command'][0] != self.pins['runtime']['duckdb']
                           for c in receipt['children'])):
                raise ValueError('actual stage source/import/ownership/receipt differs; STOP')
        manifest = describe(partial, stage=stage, key=key(inputs), producer=producer,
                            dependencies=inputs['dependencies'], status=status, exit_code=code)
        fingerprint = finalize(partial, self.artifacts / name, manifest)
        terminal, _ = self.store.finish(initial, name, fingerprint)
        result = self.result(terminal, request, True)
        if status != 'success':
            raise RuntimeError('stage non-success; preserve actual artifact/STOP: ' + name)
        return result

    def validate_pool(self, pool, upstream=None):
        path = Path(pool['directory'])
        inputs = pool['inputs']
        if (inputs['materializer'] != self.pins['materializer'] or inputs['runtime'] != self.pins['runtime_digest']
                or len(inputs['projections']) != 3):
            raise ValueError('pool dependency identity differs')
        expected = digest(b'per-exercise-pool-v1\0' + canonical({
            'inputs': inputs['projections'], 'schema_materializer': inputs['materializer'],
            'runtime': inputs['runtime']}))
        if expected != pool['identity']:
            raise ValueError('pool computational key differs')
        if upstream is not None:
            wanted = {'scenario': upstream['spec']['label'], 'key': upstream['key'], 'artifact': upstream['digest']}
            if sum(row == wanted for row in inputs['projections']) != 1:
                raise ValueError('THIS case capsule not in admitted pool')
        if path.parent != self.directory / 'materializations' or path.name != pool['identity']:
            raise ValueError('pool custody path differs')
        capsules.admit(path, pool['identity'], inputs, pool['digest'])

    def pool(self, projections):
        for p in projections:
            batch.authority(self.store, p, p['spec'])
        identity = material_key(self.pins, projections)
        inputs = {'projections': [{'scenario': p['spec']['label'], 'key': p['key'], 'artifact': p['digest']}
                                  for p in projections], 'materializer': self.pins['materializer'],
                  'runtime': self.pins['runtime_digest']}
        directory = self.directory / 'materializations' / identity
        facts = [capsules.read(self.artifacts / p['name'] / 'capsule.json') for p in projections]
        if directory.exists():
            capsules.admit(directory, identity, inputs)
            fingerprint = digest((directory / 'manifest.json').read_bytes())
            fresh = False
        else:
            fingerprint = capsules.materialize(facts, directory, identity, inputs, self.pins['runtime']['duckdb'])
            fresh = True
        return {'identity': identity, 'inputs': inputs, 'directory': str(directory),
                'digest': fingerprint, 'fresh': fresh}

    def round(self, cases, number, candidate, projection, checker, fresh_label=None):
        rows = []
        for spec in cases:
            e = self.stage('E', spec, candidate=candidate, fresh=spec['label'] == fresh_label)
            p = self.stage('P', spec, variant=projection, upstream=e, fresh=spec['label'] == fresh_label)
            rows.append({'spec': spec, 'E': e, 'P': p})
        pool = self.pool([row['P'] for row in rows])
        for row in rows:
            row['C'] = self.stage('C', row['spec'], variant=checker, upstream=row['P'], pool=pool,
                                  fresh=row['spec']['label'] == fresh_label)
        group = batch.publish(self, rows, pool, number)
        return {'cases': rows, 'group': {'publication': group['publication'], 'occurrence': group['occurrence'],
                                      'bundle_sha256': group['bundle_sha256']}, 'pool': pool}


def story(pins_path, directory):
    controller = Controller(pins_path, directory, create=True)
    configurations = [(False, 'A', 'P1', 'C1'), (False, 'A', 'P1', 'C1'),
                      (True, 'A', 'P1', 'C1'), (True, 'A', 'P1', 'C2'),
                      (True, 'A', 'P2', 'C2'), (True, 'B', 'P1', 'C2'), (True, 'A', 'P1', 'C2')]
    rows = []
    for number, (changed, candidate, p, c) in enumerate(configurations, 1):
        if number == 2:
            command = [PYTHON, '-I', '-B', str(Path(controller.pins['root']) / 'code/per_exercise/driver.py'),
                       'continue', str(controller.pins_path), str(controller.directory)]
            with (controller.directory / 'continuation.stdout').open('wb') as stdout, (controller.directory / 'continuation.stderr').open('wb') as stderr:
                child = subprocess.Popen(command, env=environment(controller.pins, controller.directory),
                                         stdout=stdout, stderr=stderr)
                owner = {'pid': child.pid, 'command': command}
                (controller.directory / 'continuation.owner.json').write_bytes(canonical(owner))
                owner['wait_exit'] = child.wait()
                (controller.directory / 'continuation.owner.json').write_bytes(canonical(owner))
            if owner['wait_exit'] != 0:
                raise ValueError('actual continuation failed; STOP')
            row = parse((controller.directory / 'continuation.json').read_bytes())
        else:
            row = controller.round(specs(changed), number, candidate, p, c,
                                   'negative-b' if number == 7 else None)
        rows.append(row)
        (controller.directory / 'observed-rounds.json').write_bytes(canonical(rows))
        if number in (1, 3, 4):
            for case in row['cases']:
                for stage in ('E', 'P', 'C'):
                    if case[stage]['fresh']:
                        controller.store.adopt(controller.store.dml.ObjectId.from_hex(case[stage]['terminal']))
    expected = [(3, 3, 3), (0, 0, 0), (1, 1, 1), (0, 0, 3), (0, 3, 3), (3, 3, 3), (1, 1, 1)]
    actual = [tuple(sum(case[s]['fresh'] for case in row['cases']) for s in ('E', 'P', 'C')) for row in rows]
    if actual != expected or [r['pool']['fresh'] for r in rows] != [True, False, True, False, True, True, True]:
        raise ValueError('actual stage/assembly matrix differs')
    old = rows[2]['cases'][1]['E']
    new = rows[6]['cases'][1]['E']
    e_input = envelope(controller.pins, 'E', specs(True)[1])
    if old['key'] != new['key'] or str(controller.store.selected(e_input)) != old['terminal']:
        raise ValueError('fresh auto-adopted or E computation changed')
    basis = controller.store.head()
    controller.store.fork('explicit-new-E', basis)
    controller.store.adopt(controller.store.dml.ObjectId.from_hex(new['terminal']), branch='explicit-new-E', expected=basis)
    result = {'rounds': rows, 'fresh': {'E': 8, 'P': 11, 'C': 14}, 'requests': 63, 'reused': 30,
              'known_story_actors': 53, 'scope': 'isolated three-case profile, not maintained suite/coverage'}
    (controller.directory / 'result.json').write_bytes(canonical(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'story', 'continue'))
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.mode == 'prepare':
        record = prepare(args.source, args.destination)
        print(canonical({'namespace': record['namespace'], 'assets': len(record['assets'])}).decode())
    elif args.mode == 'story':
        print(canonical(story(args.source, args.destination)).decode())
    else:
        controller = Controller(args.source, args.destination)
        row = controller.round(specs(), 2, 'A', 'P1', 'C1')
        if row['pool']['fresh'] or any(case[s]['fresh'] for case in row['cases'] for s in ('E', 'P', 'C')):
            raise ValueError('continuation unexpectedly activated work')
        (controller.directory / 'continuation.json').write_bytes(canonical(row))
        print(canonical(row).decode())
