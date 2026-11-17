"""Explicit snapshot preparation and fixed sequential stage orchestration, no discovery."""

import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = 'incremental'

from .artifacts import admit, describe, finalize
from .identity import FORMAT, canonical, digest, exact, file_manifest, key, manifest_digest, parse
from .records import Store
from .runtime import read_review, source_manifest, verify_runtime

SOURCE = ('identity.py', 'artifacts.py', 'records.py', 'stages.py', 'driver.py', 'runtime.py', '__init__.py')
LIMITS = {'bundle_bytes': 33554432, 'record_bytes': 4194304, 'packed_bytes': 16777216,
          'bundle_objects': 100000, 'extraction_objects': 10000, 'roots': 4,
          'arguments': 16, 'positions': 16, 'builtin_reached': 64,
          'stage_data_bytes': 33554432, 'stage_log_bytes': 1048576}


def prepare(worktree, destination, *, review_path=None):
    """Copies executable/source bytes ONLY. Never opens any database/imports native code."""
    worktree, destination = Path(worktree).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError('pin directory already exists')
    if review_path is None:
        raise ValueError('explicit review_path required; generate and inspect a runtime review first')
    reviewed = read_review(review_path)
    rows = source_manifest(worktree)
    if rows != reviewed['sources']:
        raise ValueError('reviewed candidate source inventory differs')
    core = Path(reviewed['core'])
    if digest(core.read_bytes()) != reviewed['core_sha256']:
        raise ValueError('reviewed native artifact differs')
    destination.mkdir(parents=True)
    for variant in ('A', 'B'):
        candidate = destination / ('candidate-' + variant)
        for row in rows:
            target = candidate / row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            source = worktree if variant == 'A' else destination / 'candidate-A'
            target.write_bytes((source / row['path']).read_bytes())
        package = candidate / 'python/daggerml/daggerml'
        (package / '_core.abi3.so').write_bytes(core.read_bytes())
        if variant == 'B':
            target = package / 'builtin.py'
            target.write_bytes(target.read_bytes() + b'\n# Owned candidate B: equal behavior, distinct build bytes.\n')
    controller = destination / 'controller/daggerml'
    controller.mkdir(parents=True)
    for row in rows:
        if row['path'].startswith('python/daggerml/daggerml/'):
            (controller / Path(row['path']).name).write_bytes(
                (destination / 'candidate-A' / row['path']).read_bytes())
    (controller / '_core.abi3.so').write_bytes(core.read_bytes())
    new_code = destination / 'controller/code/incremental'
    new_code.mkdir(parents=True)
    old = destination / 'candidate-A/spikes/relational_invariants'
    for name in SOURCE:
        (new_code / name).write_bytes((old / 'incremental' / name).read_bytes())
    for variant, names in {'exercise': ['exerciser.py'],
                           'P1': ['normalizer.py', 'engine.py', 'schema.py'],
                           'P2': ['normalizer.py', 'engine.py', 'schema.py'],
                           'C1': ['checker.py', 'checks.sql', 'engine.py'],
                           'C2': ['checker.py', 'checks.sql', 'engine.py'],
                           'C-disabled': ['checker.py', 'checks.sql', 'engine.py']}.items():
        directory = destination / variant
        directory.mkdir()
        for name in names:
            (directory / name).write_bytes((old / name).read_bytes())
        if variant in ('P2', 'C2'):
            target = directory / ('normalizer.py' if variant == 'P2' else 'checker.py')
            target.write_bytes(target.read_bytes() + b'\n# Owned byte-change invalidation variant.\n')
    weak = destination / 'C-disabled/checks.sql'
    sql = weak.read_text()
    start = "UNION ALL\nSELECT 'map_get_value', o.dag"
    end = "UNION ALL\nSELECT 'empty_dataset', 'dataset'"
    before, following = sql.split(start, 1)
    _, after = following.split(end, 1)
    weak.write_text(before + end + after)
    runtime = reviewed['runtime']
    files = file_manifest(destination)
    fingerprints = {name: manifest_digest(file_manifest(destination / name))
                    for name in ('candidate-A', 'candidate-B', 'controller/daggerml',
                                 'exercise', 'P1', 'P2', 'C1', 'C2', 'C-disabled')}
    control_files = file_manifest(new_code)
    control_files = [row for row in control_files if row['path'] != 'stages.py']
    namespace = digest(canonical({'code': control_files, 'recorder': fingerprints['controller/daggerml'],
                                 'runtime': digest(canonical(runtime)), 'format': FORMAT}))
    pins = {'root': str(destination), 'namespace': namespace, 'runtime': runtime,
            'runtime_digest': digest(canonical(runtime)), 'fingerprints': fingerprints,
            'core_sha256': reviewed['core_sha256'], 'review': reviewed,
            'tracked_source_manifest': rows, 'assets': files,
            'wrapper': digest((new_code / 'stages.py').read_bytes())}
    (destination / 'pins.json').write_bytes(canonical(pins))
    for path in destination.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
    return verify_pins(destination / 'pins.json')


def verify_pins(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('symlink pin receipt')
    pins = exact(parse(path.read_bytes()), {'root', 'namespace', 'runtime', 'runtime_digest', 'fingerprints',
                                          'core_sha256', 'review', 'tracked_source_manifest', 'assets', 'wrapper'})
    verify_runtime(pins['runtime'])
    root = Path(pins['root'])
    if root != path.parent.resolve():
        raise ValueError('pin location differs')
    rows = [row for row in file_manifest(root) if row['path'] != 'pins.json']
    if rows != pins['assets']:
        raise ValueError('pinned executable asset set/digests differ')
    for name in SOURCE:
        if (Path(__file__).parent / name).read_bytes() != (root / 'controller/code/incremental' / name).read_bytes():
            raise ValueError('executing controller source differs from frozen namespace')
    fingerprints = {name: manifest_digest(file_manifest(root / name)) for name in pins['fingerprints']}
    code = [row for row in file_manifest(root / 'controller/code/incremental') if row['path'] != 'stages.py']
    namespace = digest(canonical({'code': code, 'recorder': fingerprints['controller/daggerml'],
                                 'runtime': digest(canonical(pins['runtime'])), 'format': FORMAT}))
    if (fingerprints != pins['fingerprints'] or namespace != pins['namespace']
            or pins['runtime_digest'] != digest(canonical(pins['runtime']))
            or pins['wrapper'] != digest((root / 'controller/code/incremental/stages.py').read_bytes())
            or pins['core_sha256'] != pins['review']['core_sha256']
            or pins['runtime'] != pins['review']['runtime']
            or pins['tracked_source_manifest'] != pins['review']['sources']):
        raise ValueError('pin claims/namespace disagree with actual frozen inputs')
    for row in pins['tracked_source_manifest']:
        raw = (root / 'candidate-A' / row['path']).read_bytes()
        if digest(raw) != row['sha256'] or len(raw) != row['size']:
            raise ValueError('frozen candidate differs from reviewed source')
    for package in ('candidate-A/python/daggerml/daggerml',
                    'candidate-B/python/daggerml/daggerml', 'controller/daggerml'):
        if digest((root / package / '_core.abi3.so').read_bytes()) != pins['core_sha256']:
            raise ValueError('frozen native artifact differs from review')
    return pins


def environment(pins, directory):
    directory = Path(directory)
    home, temporary = directory / 'home', directory / 'tmp'
    home.mkdir(parents=True, exist_ok=True)
    temporary.mkdir(parents=True, exist_ok=True)
    return {'PATH': str(Path(pins['runtime']['duckdb']).parent), 'HOME': str(home),
            'TMPDIR': str(temporary), 'LC_ALL': 'C.UTF-8', 'PYTHONHASHSEED': '0',
            'LD_LIBRARY_PATH': pins['runtime']['library_path']}


def envelope(pins, stage, *, candidate='A', scenario='normal', variant=None, upstream=None, profile='ACCEPTANCE'):
    fingerprints = pins['fingerprints']
    if profile not in ('ACCEPTANCE', 'CONTROL') or variant == 'C-disabled' and profile != 'CONTROL':
        raise ValueError('sensitivity payload requires explicit CONTROL profile')
    if candidate not in ('A', 'B') or scenario not in ('normal', 'wrong'):
        raise ValueError('unsupported candidate/scenario context')
    dependencies = {'wrapper': pins['wrapper'], 'runtime': pins['runtime_digest']}
    context = {'scenario': scenario, 'checkpoints': 2, 'expected_positions': 3, 'profile': profile}
    if stage == 'E':
        dependencies.update(candidate=fingerprints['candidate-' + candidate], exercise=fingerprints['exercise'])
    else:
        if upstream is None:
            raise ValueError('upstream evidence authority required')
        dependencies.update(upstream_key=upstream['key'], upstream_artifact=upstream['digest'])
        context['roots'] = upstream['roots']
        if stage == 'P' and variant in ('P1', 'P2'):
            dependencies.update(normalizer=fingerprints[variant], decoder=fingerprints['controller/daggerml'])
        elif stage == 'C' and variant in ('C1', 'C2', 'C-disabled'):
            dependencies.update(checker=fingerprints[variant])
        else:
            raise ValueError('unsupported payload variant')
    result = {'format': FORMAT, 'namespace': pins['namespace'], 'stage': stage,
              'dependencies': dependencies, 'context': context, 'limits': dict(LIMITS)}
    key(result)
    return result


class Controller:
    def __init__(self, pins_path, directory, *, store_namespace, profile='ACCEPTANCE', create=False):
        if profile not in ('ACCEPTANCE', 'CONTROL') or not store_namespace.startswith(profile + '/'):
            raise ValueError('explicit profile-qualified actual store namespace required')
        self.profile = profile
        self.pins_path = Path(pins_path).resolve()
        self.pins = verify_pins(self.pins_path)
        self.directory = Path(directory).resolve()
        if create:
            self.directory.mkdir(parents=True, exist_ok=False)
            (self.directory / 'artifacts').mkdir()
        from .stages import load_dml
        dml = load_dml(Path(self.pins['root']) / 'controller/daggerml', name='incremental_controller_dml')
        self.store = Store(dml, self.directory / 'controller.dml', self.directory / 'artifacts',
                           store_namespace, create=create)

    def stage(self, stage_envelope, *, candidate='A', variant='normal', upstream=None,
              fresh=False, branch='main'):
        verify_pins(self.pins_path)
        # Caller must ask for the exact declared fixed profile, not invented hash labels.
        scenario = stage_envelope['context']['scenario']
        if stage_envelope['stage'] == 'E' and variant != scenario:
            raise ValueError('actual exercise variant differs from computation key')
        if upstream is not None:
            upstream_terminal = self.store.dml.ObjectId.from_hex(upstream['terminal'])
            _, produced, _, reference, artifact = self.store.terminal(upstream_terminal)
            wanted_stage = 'E' if stage_envelope['stage'] == 'P' else 'P'
            if (artifact['stage'] != wanted_stage or produced['key'] != upstream['key']
                    or reference != {'name': upstream['name'], 'sha256': upstream['digest']}):
                raise ValueError('upstream producer/evidence authority differs')
            actual_upstream = self._result(upstream_terminal, upstream_terminal, False)
            if actual_upstream['roots'] != upstream['roots']:
                raise ValueError('upstream root context differs')
        expected = envelope(self.pins, stage_envelope['stage'], candidate=candidate, scenario=scenario,
                            variant=variant, upstream=upstream, profile=self.profile)
        if stage_envelope != expected:
            raise ValueError('requested fixed stage profile differs')
        request, _ = self.store.request(stage_envelope, 'fresh' if fresh else 'reuse', branch=branch)
        reused = None if fresh else self.store.reuse(request, branch=branch)
        if reused is not None:
            return self._result(reused[0], request, False)
        initial, producer, _ = self.store.begin(request, branch=branch)
        serial = producer.rsplit('-', 1)[-1]
        name = 'attempt-' + serial
        root = self.directory / 'artifacts'
        partial, destination = root / (name + '.partial'), root / name
        partial.mkdir()
        job = {'pins': str(self.pins_path), 'stage': stage_envelope['stage'], 'candidate': candidate,
               'variant': variant, 'producer': producer, 'key': key(stage_envelope),
               'output': str(partial), 'upstream': None if upstream is None else str(root / upstream['name'])}
        job_path = self.directory / (name + '.job.json')
        job_path.write_bytes(canonical(job))
        command = [self.pins['runtime']['python'], '-I', '-B',
                   str(Path(self.pins['root']) / 'controller/code/incremental/stages.py'), str(job_path)]
        with (partial / 'stdout.log').open('wb') as stdout, (partial / 'stderr.log').open('wb') as stderr:
            process = subprocess.Popen(command, cwd=self.directory, env=environment(self.pins, self.directory),
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            owner = {'pid': process.pid, 'group': process.pid, 'command': command, 'producer': producer}
            (self.directory / (name + '.owner.json')).write_bytes(canonical(owner))
            actual_exit = process.wait()
        owner['wait_exit'] = actual_exit
        (self.directory / (name + '.owner.json')).write_bytes(canonical(owner))
        status = 'success' if actual_exit == 0 else 'rejected' if (actual_exit == 1 and
                 stage_envelope['stage'] == 'C' and (partial / 'verdict.json').is_file()) else 'error'
        if status != 'error':
            receipt = parse((partial / 'receipt.json').read_bytes())
            loaded = receipt['loaded']
            if (receipt['stage'] != job['stage'] or receipt['key'] != job['key']
                    or receipt['producer'] != producer or receipt['variant'] != variant
                    or receipt['process'] != {'pid': process.pid, 'parent': os.getpid(), 'group': process.pid}
                    or loaded['runtime'] != self.pins['runtime_digest'] or loaded['python'] != self.pins['runtime']['python']):
                raise ValueError('actual stage receipt disagrees with requested activation')
            stage = job['stage']
            payload = ('exercise/exerciser.py' if stage == 'E' else
                       variant + ('/normalizer.py' if stage == 'P' else '/checker.py'))
            if receipt['source'] != digest((Path(self.pins['root']) / payload).read_bytes()):
                raise ValueError('actual payload source differs')
            if stage != 'C':
                expected_package = (Path(self.pins['root']) / ('candidate-' + candidate) /
                                    'python/daggerml/daggerml' if stage == 'E' else
                                    Path(self.pins['root']) / 'controller/daggerml')
                if loaded['package'] != str(expected_package / '__init__.py') or loaded['core'] != self.pins['core_sha256']:
                    raise ValueError('actual candidate/decoder import differs')
            if len(receipt['children']) != {'E': 0, 'P': 1, 'C': 3}[stage]:
                raise ValueError('actual CLI invocation allowance differs')
            for child in receipt['children']:
                if child['wait_exit'] != 0 or child['command'][0] != self.pins['runtime']['duckdb']:
                    raise ValueError('stage CLI exit/pin differs')
        document = describe(partial, stage=stage_envelope['stage'], key=key(stage_envelope), producer=producer,
                            dependencies=stage_envelope['dependencies'], status=status, exit_code=actual_exit)
        artifact_digest = finalize(partial, destination, document)
        terminal, _ = self.store.finish(initial, name, artifact_digest, branch=branch)
        result = self._result(terminal, request, True)
        if status == 'error':
            raise RuntimeError('stage activation failed; retain evidence and STOP: ' + name)
        return result

    def _result(self, terminal, request, fresh):
        _, produced, outcome, reference, artifact = self.store.terminal(terminal)
        directory = self.directory / 'artifacts' / reference['name']
        stage = artifact['stage']
        roots = (parse((directory / 'evidence.json').read_bytes())['roots'] if stage == 'E' else
                 parse((directory / 'roots.json').read_bytes())['roots'] if stage == 'P' else [])
        return {'request': str(request), 'terminal': str(terminal), 'fresh': fresh, 'key': produced['key'],
                'name': reference['name'], 'digest': reference['sha256'], 'stage': stage,
                'status': outcome['status'], 'roots': roots}


def story(pins_path, directory):
    """SOLE acceptance activation; caller must obtain separate readiness approval first."""
    controller = Controller(pins_path, directory, store_namespace='ACCEPTANCE/incremental-v1-story', create=True)
    rounds = [('A', 'P1', 'C1', False, 'normal'), ('A', 'P1', 'C1', False, 'normal'),
              ('A', 'P1', 'C2', False, 'normal'), ('A', 'P2', 'C2', False, 'normal'),
              ('B', 'P2', 'C2', False, 'normal'), ('B', 'P2', 'C2', True, 'normal'),
              ('B', 'P2', 'C2', False, 'wrong')]
    rows = []
    old_e = None
    for number, (candidate, projection, checking, fresh, scenario) in enumerate(rounds, 1):
        e = controller.stage(envelope(controller.pins, 'E', candidate=candidate, scenario=scenario),
                             candidate=candidate, variant=scenario, fresh=fresh)
        p = controller.stage(envelope(controller.pins, 'P', scenario=scenario, variant=projection, upstream=e),
                             variant=projection, upstream=e, fresh=fresh)
        c = controller.stage(envelope(controller.pins, 'C', scenario=scenario, variant=checking, upstream=p),
                             variant=checking, upstream=p, fresh=fresh)
        rows.append({'round': number, 'E': e, 'P': p, 'C': c})
        (controller.directory / 'observed-rounds.json').write_bytes(canonical(rows))
        if scenario == 'wrong':
            evidence = parse((controller.directory / 'artifacts' / e['name'] / 'evidence.json').read_bytes())
            verdict = parse((controller.directory / 'artifacts' / c['name'] / 'verdict.json').read_bytes())
            bad = {row['subject'] for row in verdict['violations'] if row['invariant'] == 'map_get_value'}
            if c['status'] != 'rejected' or bad != {evidence['bad_subject']}:
                raise ValueError('specific native wrong-result counterexample missing; STOP')
        elif c['status'] != 'success':
            raise ValueError('unexpected rejection in positive round; STOP')
        elif number != 6:
            for result in (e, p, c):
                if result['fresh']:
                    controller.store.adopt(controller.store.dml.ObjectId.from_hex(result['terminal']))
        if number == 5:
            old_e = e
        if number == 6:
            actual = controller.store.selected(envelope(controller.pins, 'E', candidate='B'))
            if str(actual) != old_e['terminal']:
                raise ValueError('fresh completion automatically moved E selection; STOP')
            basis = controller.store.head()
            controller.store.fork('fresh-E-choice', basis)
            controller.store.adopt(controller.store.dml.ObjectId.from_hex(e['terminal']),
                                   branch='fresh-E-choice', expected=basis)
            if str(controller.store.selected(envelope(controller.pins, 'E', candidate='B'))) != old_e['terminal']:
                raise ValueError('sibling adoption moved main selection; STOP')
    counts = {stage: sum(row[stage]['fresh'] for row in rows) for stage in ('E', 'P', 'C')}
    if counts != {'E': 4, 'P': 5, 'C': 6} or len({row[s]['request'] for row in rows for s in counts}) != 21:
        raise ValueError('actual activation/request counts differ; STOP')
    (controller.directory / 'result.json').write_bytes(canonical({'rounds': rows, 'fresh': counts,
        'requests': 21, 'reused': 6, 'note': 'actual isolated stage proof, NOT full-suite/platform/coverage pass'}))
    return controller.directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'story'])
    parser.add_argument('source', type=Path, help='worktree for prepare; frozen pins.json for approved story')
    parser.add_argument('destination', type=Path)
    parser.add_argument('--review', help='explicit reviewed source/native/runtime manifest for prepare')
    args = parser.parse_args()
    if args.command == 'prepare':
        pins = prepare(args.source, args.destination, review_path=args.review)
        print(canonical({'namespace': pins['namespace'], 'assets': len(pins['assets']),
                         'pins': str(args.destination / 'pins.json')}).decode())
    else:
        print(story(args.source, args.destination))


if __name__ == '__main__':
    main()
