"""Finite original16 body demonstration in one indexed repository."""
import argparse
import json
from pathlib import Path
import sys

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]));__package__='shared_existing'
    from run import bootstrap
    bootstrap()

import daggerml as d
from daggerml import transfer
from incremental.identity import canonical
from shared_index.check import pool
from .exercise import exercise
from .project import normalize
from .check import check_case,assert_agreement


def demonstrate(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    handle=exercise(directory/'exercise',namespace=directory.name+'/actual-original16')
    root=d.ObjectId.from_hex(handle['publication'])
    bundle=transfer.export_commit(handle['repository'],commit=root)
    (directory/'publication.bundle').write_bytes(bundle)
    imported_path=directory/'imported-validation'
    with d.Repository(imported_path,create=True):pass
    imported=transfer.import_commit(imported_path,bundle)
    if imported.commit!=root:raise ValueError('import root differs')
    rows,catalog,stats=normalize(imported_path,str(root),directory/'normalized')
    database=pool(rows,directory/'pool');results=[]
    for number,case in enumerate(catalog['cases'],1):
        result=check_case(database,rows,case,directory/'checks'/f'case-{number:03d}')
        results.append(result);(directory/'observed-results.json').write_bytes(canonical(results))
        assert_agreement(case,result)
    summary={'handle':handle,'original_assertion_instances':len(catalog['cases']),
             'native_recorded_calls':sum(len(case['calls']) for case in catalog['cases']),
             'unique_native_reads':stats['unique_record_reads'],
             'case_memberships':sum(len(case['membership']) for case in catalog['cases']),
             'bundle_bytes':len(bundle),'bundle_objects':imported.object_count,'results':results,
             'qualification':'unchanged assertions/shared fixture seam/independent partial SQL; no process/ref/full-suite assurance'}
    (directory/'result.json').write_bytes(canonical(summary))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    print(canonical(demonstrate(parser.parse_args().directory)).decode())
