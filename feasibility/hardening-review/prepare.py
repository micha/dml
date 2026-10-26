#!/usr/bin/env python3
"""Copy candidate sources into fresh owned paths; never edit upstream workers."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    runtime = HERE / 'runtime'
    runtime.mkdir(exist_ok=True)
    base = next((runtime / str(i) for i in range(1, 9) if not (runtime / str(i)).exists()), None)
    assert base, 'eight runs retained; no automatic pruning'
    base.mkdir()
    records = []
    for worker, names in {'journal':['journal.py','test_journal.py','test_followup.py'], 'gate':['gate.py','run_tests.py','journal_adapter.py'],
                          'artifact':['test_provider.py','main.go','ready.json']}.items():
        target = base / worker
        target.mkdir()
        (target / 'runtime').mkdir()
        for name in names:
            source = HERE.parent / worker / name
            dest = target / name
            shutil.copyfile(source, dest)
            assert sha(source) == sha(dest)
            record = {'source':str(source), 'copy':str(dest), 'sha256':sha(source)}
            if name == 'test_provider.py':
                old = "temp = runtime / 't'"
                new = f"temp = Path({str(HERE / 'runtime' / 't')!r})"
                text = dest.read_text()
                assert text.count(old) == 1
                dest.write_text(text.replace(old, new))
                record.update(adaptation='TMPDIR shortened within review-owned runtime to avoid Unix socket length limit', adapted_sha256=sha(dest))
            records.append(record)
    (base / 'tools').symlink_to(HERE.parent / 'tools', target_is_directory=True)
    (base / 'source-manifest.json').write_text(json.dumps(records, indent=2)+'\n')
    (runtime / 'latest.json').write_text(json.dumps({'base':str(base)})+'\n')
    print(base)

if __name__ == '__main__':
    main()
