#!/usr/bin/env python3
"""Bounded marker wait and read-only source snapshots in this worker's sandbox."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

HERE=Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    marker=HERE.parent/'gate/followup-done.json'
    start=time.monotonic()
    snapshot_now='--snapshot-now' in sys.argv
    while not snapshot_now and not marker.exists() and time.monotonic()-start<600:
        time.sleep(min(15,600-(time.monotonic()-start)))
    completion=json.loads(marker.read_text()) if marker.exists() else {'status':'marker-unavailable','report':str(HERE.parent/'gate/report.md')}
    assert completion['status'] in ('completed','marker-unavailable') and Path(completion['report']).is_file()
    root=HERE/'runtime/followup'
    root.mkdir(exist_ok=True)
    base=next((root/str(i) for i in range(1,9) if not (root/str(i)).exists()),None)
    assert base, 'eight retained runs; never auto-prune'
    base.mkdir()
    sources=[]
    workers={'gate':[p.name for p in (HERE.parent/'gate').glob('*.py') if '-initial' not in p.name],
             'journal':['journal.py'], 'artifact':['ready.json','main.go']}
    for worker,names in workers.items():
        target=base/worker
        target.mkdir();(target/'runtime').mkdir()
        for name in names:
            source=HERE.parent/worker/name
            before=sha(source)
            dest=target/name
            shutil.copyfile(source,dest)
            assert before==sha(source)==sha(dest), 'source changed during snapshot'
            sources.append({'source':str(source),'copy':str(dest),'sha256':before})
    for name in ('followup-done.json','report.md','summary.json'):
        source=HERE.parent/'gate'/name
        if not source.exists():
            continue
        dest=base/'gate'/name
        shutil.copyfile(source,dest)
        sources.append({'source':str(source),'copy':str(dest),'sha256':sha(dest)})
    (base/'tools').symlink_to(HERE.parent/'tools',target_is_directory=True)
    shutil.copyfile(HERE/'checks.py',base/'initial-checks.py')
    sources.append({'source':str(HERE/'checks.py'),'copy':str(base/'initial-checks.py'),'sha256':sha(HERE/'checks.py')})
    (base/'source-manifest.json').write_text(json.dumps({'sources':sources,'marker':completion,'waited_seconds':round(time.monotonic()-start,2),
                                                       'snapshot_now':snapshot_now,'prior_wait_log':str(HERE/'runtime/followup-prepare.log')},indent=2)+'\n')
    (root/'latest.json').write_text(json.dumps({'base':str(base)})+'\n')
    print(base)

if __name__=='__main__':main()
