"""Owned immutable snapshots, no native import/build/stage activation during preparation."""
import shutil
import subprocess
from pathlib import Path

from incremental.driver import prepare as legacy_prepare, verify_pins as legacy_verify, PYTHON,DUCKDB
from incremental.identity import canonical,digest,file_manifest,manifest_digest,parse,exact

TOOLS='/nix/store/qx9y6qslvc3pw8mblqx77cm1viv2dyzq-python3-3.13.15-env/lib/python3.13/site-packages'
CODE=('__init__.py','pins.py','stages.py','driver.py')
CORE_FAULT='b3f8821144bf64cda49c9ecfaba282e6f88dcdf4517087fab046fa925520febd'


def prepare(worktree,destination):
    worktree,destination=Path(worktree).resolve(),Path(destination).resolve()
    destination.mkdir(parents=True,exist_ok=False)
    legacy=legacy_prepare(worktree,destination/'base')
    payloads={}
    for name in ('A','B','P1','P2','C1','C2'):
        path=destination/name
        shutil.copytree(destination/'base'/('candidate-'+('B' if name=='B' else 'A')),path)
        parent=path/'spikes/relational_invariants'
        for module in ('shared_existing','shared_index'):
            target=parent/module;target.mkdir(parents=True)
            for source in (worktree/'spikes/relational_invariants'/module).iterdir():
                if source.suffix in ('.py','.sql') and not source.name.startswith('test_'):
                    (target/source.name).write_bytes(source.read_bytes())
        (parent/'incremental').mkdir()
        for filename in ('__init__.py','identity.py'):
            (parent/'incremental'/filename).write_bytes((worktree/'spikes/relational_invariants/incremental'/filename).read_bytes())
        for filename in ('normalizer.py','schema.py','engine.py'):
            (parent/filename).write_bytes((worktree/'spikes/relational_invariants'/filename).read_bytes())
        native=path/'build/spike-native';native.mkdir(parents=True)
        artifact=worktree/'build/spike-native/_core_fault.abi3.so'
        if digest(artifact.read_bytes())!=CORE_FAULT:raise ValueError('reviewed eager fault import artifact differs')
        (native/'_core_fault.abi3.so').write_bytes(artifact.read_bytes())
        if name in ('P2','C2'):
            source=parent/'shared_existing'/('project.py' if name=='P2' else 'check.py')
            source.write_bytes(source.read_bytes()+b'\n# Actual owned source-byte invalidation variant.\n')
        payloads[name]=manifest_digest(file_manifest(path))
    controller=destination/'code/indexed_controller';controller.mkdir(parents=True)
    for filename in CODE:(controller/filename).write_bytes((Path(__file__).parent/filename).read_bytes())
    runtime={**legacy['runtime'],'tools':TOOLS}
    runtime['closure']=sorted(set(subprocess.check_output(['nix-store','--query','--requisites',
        *legacy['runtime']['closure'],str(Path(TOOLS).parents[2])]).decode().splitlines()))
    files=file_manifest(destination)
    record_core=manifest_digest(file_manifest(destination/'base/controller/daggerml'))
    control_code=[r for r in file_manifest(controller) if r['path']!='stages.py']
    namespace=digest(canonical({'adapter':control_code,'legacy_controller':legacy['namespace'],
                                'recorder':record_core,'runtime':runtime}))
    pins={'root':str(destination),'namespace':namespace,'payloads':payloads,'runtime':runtime,
          'runtime_digest':digest(canonical(runtime)),'core_sha256':legacy['core_sha256'],
          'wrapper':digest((controller/'stages.py').read_bytes()),'recorder':record_core,'assets':files}
    (destination/'pins.json').write_bytes(canonical(pins))
    for path in destination.rglob('*'):
        if path.is_file():path.chmod(0o444)
    return pins


def verify(path):
    path=Path(path).resolve();pins=exact(parse(path.read_bytes()),{'root','namespace','payloads','runtime',
        'runtime_digest','core_sha256','wrapper','recorder','assets'})
    root=Path(pins['root'])
    if path.parent!=root or [r for r in file_manifest(root) if r['path']!='pins.json']!=pins['assets']:
        # base/pins.json is an asset, not the root receipt.
        actual=[r for r in file_manifest(root) if r['path']!='pins.json']
        if path.parent!=root or actual!=pins['assets']:raise ValueError('frozen asset set/bytes differ')
    legacy=legacy_verify(root/'base/pins.json')
    for filename in CODE:
        if (Path(__file__).parent/filename).read_bytes()!=(root/'code/indexed_controller'/filename).read_bytes():
            raise ValueError('actual adapter code differs from frozen controller')
    payloads={name:manifest_digest(file_manifest(root/name)) for name in ('A','B','P1','P2','C1','C2')}
    control_code=[r for r in file_manifest(root/'code/indexed_controller') if r['path']!='stages.py']
    namespace=digest(canonical({'adapter':control_code,'legacy_controller':legacy['namespace'],
                                'recorder':pins['recorder'],'runtime':pins['runtime']}))
    if (payloads!=pins['payloads'] or namespace!=pins['namespace'] or pins['runtime_digest']!=digest(canonical(pins['runtime']))
            or pins['wrapper']!=digest((root/'code/indexed_controller/stages.py').read_bytes())
            or pins['recorder']!=manifest_digest(file_manifest(root/'base/controller/daggerml'))):
        raise ValueError('pin claims differ from actual inputs')
    return pins
