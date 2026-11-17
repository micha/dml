"""Stdlib-only immutable source preparation, using unchanged as-built native pins."""
from pathlib import Path
import shutil

from incremental.driver import prepare as base_prepare, verify_pins as base_verify
from incremental.identity import canonical, digest, exact, file_manifest, manifest_digest, parse

CODE = ('__init__.py', 'pins.py', 'profiles.py', 'evidence.py', 'capsules.py',
        'batch.py', 'stages.py', 'driver.py')


def claims(root, base):
    common = manifest_digest(file_manifest(root / 'common'))
    materializer = digest(canonical({'capsules': digest((root / 'code/per_exercise/capsules.py').read_bytes()),
                                    'common': common}))
    recorder = manifest_digest(file_manifest(root / 'base/controller/daggerml'))
    runtime = base['runtime']
    code = file_manifest(root / 'code/per_exercise')
    return {'namespace': digest(canonical({'code': code, 'base': base['namespace'],
                                          'recorder': recorder, 'runtime': runtime})),
            'fingerprints': {name: manifest_digest(file_manifest(root / 'base' / name))
                             for name in ('candidate-A', 'candidate-B')},
            'exercise': digest(canonical({'common': common, 'evidence': code})),
            'payloads': {name: digest(canonical({'files': file_manifest(root / 'payloads' / name),
                                               'common': common, 'materializer': materializer}))
                         for name in ('P1', 'P2', 'C1', 'C2')},
            'recorder': recorder, 'materializer': materializer,
            'wrapper': manifest_digest(code), 'runtime': runtime,
            'runtime_digest': digest(canonical(runtime)), 'core_sha256': base['core_sha256']}


def prepare(worktree, destination, *, review_path=None):
    worktree, root = Path(worktree).resolve(), Path(destination).resolve()
    if review_path is None:
        raise ValueError('explicit review_path required')
    if root.exists():
        raise ValueError('pin directory already exists')
    base = base_prepare(worktree, root / 'base', review_path=review_path)
    source = root / 'base/candidate-A/spikes/relational_invariants'
    own = source / 'per_exercise'
    code = root / 'code/per_exercise'
    code.mkdir(parents=True)
    for name in CODE:
        (code / name).write_bytes((own / name).read_bytes())
    common = root / 'common'
    common.mkdir()
    for name in ('normalizer.py', 'schema.py', 'engine.py', 'checks.sql'):
        (common / name).write_bytes((source / name).read_bytes())
    (common / 'shared_index').mkdir()
    for name in ('__init__.py', 'exercise.py', 'project.py', 'check.py'):
        (common / 'shared_index' / name).write_bytes((source / 'shared_index' / name).read_bytes())
    for variant, filename in [('P1', 'project.py'), ('P2', 'project.py'),
                              ('C1', 'predicate.py'), ('C2', 'predicate.py')]:
        path = root / 'payloads' / variant
        path.mkdir(parents=True)
        raw = (own / filename).read_bytes()
        if variant.endswith('2'):
            raw += b'\n# Owned actual byte-change variant, not an identity label only.\n'
        (path / filename).write_bytes(raw)
    pins = {'root': str(root), **claims(root, base), 'assets': file_manifest(root)}
    (root / 'pins.json').write_bytes(canonical(pins))
    for path in root.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
    return verify(root / 'pins.json')


def verify(path):
    path = Path(path)
    pins = exact(parse(path.read_bytes()), {'root', 'namespace', 'fingerprints', 'exercise',
        'payloads', 'recorder', 'materializer', 'wrapper', 'runtime', 'runtime_digest', 'core_sha256', 'assets'})
    root = Path(pins['root'])
    if path.is_symlink() or path.parent.resolve() != root:
        raise ValueError('pin location differs')
    if [r for r in file_manifest(root) if r['path'] != 'pins.json'] != pins['assets']:
        raise ValueError('pin asset bytes differ')
    base = base_verify(root / 'base/pins.json')
    for name in CODE:
        if (Path(__file__).parent / name).read_bytes() != (root / 'code/per_exercise' / name).read_bytes():
            raise ValueError('actual trusted code differs')
    expected = claims(root, base)
    if any(pins[name] != value for name, value in expected.items()):
        raise ValueError('pin claims differ')
    return pins
