"""Disposable Linux probe; not used for timed samples."""
import hashlib
import json
from pathlib import Path
import sys

import daggerml as dml
from daggerml import transfer
import native_export

mode, path, root, expected = sys.argv[1:]
commit = dml.ObjectId.from_hex(root)
phases = {}


def checkpoint(phase):
    lines = Path('/proc/self/status').read_text().splitlines()
    phases[phase] = {key: int(value.split()[0]) for line in lines
                     for key, _, value in (line.partition(':'),)
                     if key in ('VmHWM', 'VmRSS')}
    # Reset the high-water mark to current RSS to distinguish the next phase's peak.
    Path('/proc/self/clear_refs').write_text('5\n')


original_dumps = transfer.json.dumps
original_acquire = native_export.read_packed_rows
original_bind = dml._core._export_rows


def bind(*args):
    rows = original_bind(*args)
    checkpoint('walk_and_bind_txn_open')
    return rows


def acquire(*args):
    rows = original_acquire(*args)
    checkpoint('txn_closed')
    return rows


def dumps(*args, **kwargs):
    checkpoint('pre_json')
    return original_dumps(*args, **kwargs)


transfer.json.dumps = dumps
if mode == 'native':
    dml._core._export_rows = bind
    native_export.read_packed_rows = acquire
    export = native_export.export_commit_native
else:
    assert mode == 'python'
    export = transfer.export_commit

checkpoint('before_export')
bundle = export(path, commit=commit)
checkpoint('bundle_returned')
assert hashlib.sha256(bundle).hexdigest() == expected
print(original_dumps(phases, indent=2))
