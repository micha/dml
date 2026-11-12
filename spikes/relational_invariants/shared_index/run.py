"""Bounded shared-index demonstration; complete portable retention and per-case queries."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    __package__ = 'shared_index'
    from run import bootstrap
    bootstrap()

import daggerml as dml
from daggerml.transfer import export_commit, import_commit
from incremental.identity import canonical
from .exercise import exercise
from .project import normalize
from .check import assert_expected, check_case, pool


def demonstrate(directory):
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    handle = exercise(directory/'exercise',namespace=directory.name+'/actual-run-1')
    publication = dml.ObjectId.from_hex(handle['publication'])
    data = Path(handle['repository'])/'data.mdb'
    before = hashlib.sha256(data.read_bytes()).hexdigest()
    bundle = export_commit(handle['repository'],commit=publication)
    (directory/'publication.bundle').write_bytes(bundle)
    # Import complete parent closure with NO destination ref. No database/lock copying.
    imported_path = directory/'imported-repository'
    with dml.Repository(imported_path,create=True):
        pass
    imported = import_commit(imported_path,bundle)
    if imported.commit != publication or export_commit(imported_path,commit=publication) != bundle:
        raise ValueError('portable indexed history identity differs')
    rows,catalog,stats = normalize(imported_path,str(publication),directory/'normalized')
    database = pool(rows,directory/'pool')
    verdicts = []
    for case in catalog['cases']:
        result = check_case(database,rows,case)
        verdicts.append(result)
        (directory/'observed-verdicts.json').write_bytes(canonical(verdicts))
        assert_expected(case,result)
    if hashlib.sha256(data.read_bytes()).hexdigest() != before:
        raise ValueError('read/transfer changed original shared repository')
    result = {'repository':handle['repository'],'publication':str(publication),'publications':handle['publication_chain'],
              'exercise_repositories':1,'cases':catalog['completed_cases'],'builtin_calls':sum(c['calls'] for c in catalog['cases']),
              'case_memberships':sum(len(c['membership']) for c in catalog['cases']),
              'unique_native_reads':stats['unique_record_reads'],'bundle_bytes':len(bundle),'bundle_objects':imported.object_count,
              'verdicts':verdicts,'first_parent_chain':catalog['first_parent_chain'],
              'shared_data_sha256':before,'native_original_unchanged':True,
              'qualification':'fixed local builtin cases, not generic suite/security/codec/installed/platform assurance'}
    (directory/'result.json').write_bytes(canonical(result))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    args=parser.parse_args()
    result=demonstrate(args.directory)
    print(canonical(result).decode())


if __name__=='__main__':
    main()
