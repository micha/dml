"""Focused Stage 0 validation. No study execution, source writes or runtime reads."""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import corpus as C
import freeze as F


class CorpusTests(unittest.TestCase):
    def setUp(self):
        runtime = C.HERE / 'runtime'
        runtime.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=runtime)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = self.root / 'package'
        self.package.mkdir()
        self.recipe = C.load(C.HERE, 'allowlist.json')
        self.manifest = C.load(C.HERE, 'manifest.json')
        # Only the enumerated corpus files, not originals or arbitrary directories.
        for rel in ['allowlist.json','manifest.json',*self.manifest['files']]:
            dst = self.package / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(C.read_bytes(C.HERE,rel))

    def change(self, rel, fn):
        value = C.load(self.package,rel)
        fn(value)
        data = C.canonical(value)
        (self.package/rel).write_bytes(data)
        manifest = C.load(self.package,'manifest.json')
        if rel=='allowlist.json':
            manifest['allowlist_sha256']=C.digest(data)
            manifest['supporting_availability']=value['supporting_paths']
        else:
            manifest['files'][rel]=C.digest(data)
        (self.package/'manifest.json').write_bytes(C.canonical(manifest))

    def test_offline_valid(self):
        result=C.check(self.package)
        self.assertEqual((result['source_snapshots'],result['facts'],result['gaps']),(23,17,9))

    def test_sources_byte_reproducible(self):
        self.assertTrue(C.check(self.package,sources=True)['originals_checked'])
        for rel,data in C.reconstruct(self.recipe).items():
            self.assertEqual(data,C.read_bytes(self.package,rel))

    def test_full_refreeze_reproducible(self):
        target=self.root/'refreeze';target.mkdir()
        with patch.object(C,'HERE',target):
            F.freeze()
        for rel in ['allowlist.json','manifest.json',*self.manifest['files']]:
            self.assertEqual(C.read_bytes(target,rel),C.read_bytes(self.package,rel),rel)

    def test_initial_freeze_refuses_overwrite(self):
        with patch.object(C,'HERE',self.package),self.assertRaises(ValueError):
            F.freeze()

    def test_tampered_bytes(self):
        p=self.package/'fixtures/initial-code.json'
        p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'package hash'):
            C.check(self.package)

    def test_missing_fixture(self):
        (self.package/'fixtures/initial-code.json').unlink()
        with self.assertRaises(FileNotFoundError):
            C.check(self.package)

    def test_missing_original_offline_survives(self):
        self.assertEqual(C.check(self.package,root=self.root/'absent')['status'],'valid')
        with self.assertRaises(FileNotFoundError):
            C.check(self.package,sources=True,root=self.root/'absent')

    def test_unavailable_original(self):
        with patch.object(C,'read_bytes',side_effect=PermissionError('restricted')):
            with self.assertRaises(PermissionError):
                C.reconstruct(self.recipe)

    def test_original_tamper_detected(self):
        isolated=self.root/'sources';isolated.mkdir()
        first=self.recipe['sources'][0]
        p=isolated/first['path'];p.parent.mkdir(parents=True);p.write_bytes(b'x'*first['original_bytes'])
        with self.assertRaisesRegex(ValueError,'original hash mismatch'):
            C.reconstruct(self.recipe,isolated)

    def test_citation_pointer_invalid_even_rehashed(self):
        self.change('ground-truth.json',lambda v:v['scenarios'][0]['facts'][0]['citations'][0].update(fixture_pointer='/values/999'))
        with self.assertRaises((IndexError,ValueError)):
            C.check(self.package)

    def test_citation_digest_invalid_even_rehashed(self):
        self.change('ground-truth.json',lambda v:v['scenarios'][0]['facts'][0]['citations'][0].update(value_sha256='0'*64))
        with self.assertRaisesRegex(ValueError,'citation value'):
            C.check(self.package)

    def test_citation_original_invalid_even_rehashed(self):
        self.change('ground-truth.json',lambda v:v['scenarios'][0]['facts'][0]['citations'][0].update(original_sha256='0'*64))
        with self.assertRaisesRegex(ValueError,'citation original'):
            C.check(self.package)

    def test_unknown_source_kind_rejected_in_both_modes(self):
        self.change('allowlist.json',lambda v:v['sources'][2].update(kind='future-format'))
        for sources in [False, True]:
            with self.subTest(sources=sources),self.assertRaisesRegex(ValueError,'source kind'):
                C.check(self.package,sources=sources)

    def test_unknown_gap_schema_rejected_in_both_modes(self):
        self.change('gaps.json',lambda v:v.update(schema='future-gap-v99'))
        for sources in [False, True]:
            with self.subTest(sources=sources),self.assertRaisesRegex(ValueError,'gap schema'):
                C.check(self.package,sources=sources)

    def test_answer_ingestion_must_agree_in_both_modes(self):
        self.change('ground-truth.json',lambda v:v.update(ingestion='live-native'))
        for sources in [False, True]:
            with self.subTest(sources=sources),self.assertRaisesRegex(ValueError,'ingestion'):
                C.check(self.package,sources=sources)

    def test_original_projection_rejects_duplicate_keys_before_selection(self):
        entry={'id':'synthetic','path':'feasibility/synthetic.json','kind':'json',
               'selectors':['/x'],'sha256':'0'*64}
        for raw in [b'{"x":1,"x":2}',b'{"x":1,"unused":{"a":1,"a":2}}']:
            with self.subTest(raw=raw),self.assertRaisesRegex(ValueError,'duplicate JSON key'):
                C.project(raw,entry)

    def test_original_projection_rejects_unselected_nonfinite_values(self):
        entry={'id':'synthetic','path':'feasibility/synthetic.json','kind':'json',
               'selectors':['/x'],'sha256':'0'*64}
        for token in ['NaN','Infinity','-Infinity','1e999','-1e999']:
            raw=('{"x":1,"unused":'+token+'}').encode()
            with self.subTest(token=token),self.assertRaisesRegex(ValueError,'nonfinite JSON'):
                C.project(raw,entry)
            # Package loading and original acquisition share the same decoder.
            (self.root/'bad.json').write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'nonfinite JSON'):
                C.load(self.root,'bad.json')

    def test_each_scenario_requires_nonempty_facts(self):
        for index in range(5):
            truth=C.load(C.HERE,'ground-truth.json')
            truth['scenarios'][index]['facts']=[]
            self.change('ground-truth.json',lambda v:v.update(truth))
            for sources in [False, True]:
                with self.subTest(index=index,sources=sources),self.assertRaisesRegex(ValueError,'nonempty cited facts'):
                    C.check(self.package,sources=sources)

    def test_fact_requires_citations(self):
        self.change('ground-truth.json',lambda v:v['scenarios'][0]['facts'][0].update(citations=[]))
        with self.assertRaisesRegex(ValueError,'fact metadata'):
            C.check(self.package)

    def test_original_byte_count_type_and_range_in_both_modes(self):
        for value in [-1,True,False,'123',1.5,[],C.MAX_BYTES+1]:
            self.change('allowlist.json',lambda v:v['sources'][0].update(original_bytes=value))
            for sources in [False, True]:
                with self.subTest(value=value,sources=sources),self.assertRaisesRegex(ValueError,'original byte count'):
                    C.check(self.package,sources=sources)

    def test_original_byte_count_matches_source(self):
        self.change('allowlist.json',lambda v:v['sources'][0].update(original_bytes=v['sources'][0]['original_bytes']+1))
        # A plausible integer can only be verified against bytes in source mode.
        self.assertEqual(C.check(self.package)['status'],'valid')
        with self.assertRaisesRegex(ValueError,'original byte count mismatch'):
            C.check(self.package,sources=True)
        altered=C.load(self.package,'allowlist.json')
        with self.assertRaisesRegex(ValueError,'original byte count mismatch'):
            C.reconstruct(altered)

    def test_fact_unit_requires_nonblank_string(self):
        for unit in [['made-up-unit'],{'unit':'trials'},1,True,None,'  \t']:
            self.change('ground-truth.json',lambda v:v['scenarios'][0]['facts'][0].update(unit=unit))
            for sources in [False, True]:
                with self.subTest(unit=unit,sources=sources),self.assertRaisesRegex(ValueError,'unit/outcome'):
                    C.check(self.package,sources=sources)

    def test_unit_required(self):
        self.change('ground-truth.json',lambda v:v['scenarios'][0]['facts'][0].update(unit=''))
        with self.assertRaisesRegex(ValueError,'unit/outcome'):
            C.check(self.package)

    def test_evidence_class_required(self):
        self.change('ground-truth.json',lambda v:v['scenarios'][0]['facts'][0].update(evidence_class='tests passed'))
        with self.assertRaisesRegex(ValueError,'fact metadata'):
            C.check(self.package)

    def test_unknown_not_failed_and_harness_not_safety(self):
        truth=C.load(self.package,'ground-truth.json')
        facts={f['id']:f for s in truth['scenarios'] for f in s['facts']}
        self.assertIn('unknown is not a failed',facts['C-unknown']['answer'])
        self.assertIn('unsafe behavior',facts['A-counts']['system_outcome'])
        self.assertEqual(facts['D-reuse']['evidence_class'],'source-inspection')
        self.assertEqual(facts['E-s3']['evidence_class'],'source-inspection')
        self.assertEqual(truth['historical_execution_ids_created'],0)

    def test_historical_binding_rejects_wrong_digest(self):
        self.change('allowlist.json',lambda v:v['historical_bindings'][0].update(digest_pointer='/run_tests.py/sha256'))
        with self.assertRaisesRegex(ValueError,'historical checksum'):
            C.check(self.package)

    def test_no_arbitrary_source_paths(self):
        for path in ['../secret','/etc/passwd','feasibility/gate/runtime/state.json']:
            with self.subTest(path=path):
                altered=copy.deepcopy(self.recipe)
                altered['sources'][0]['path']=path
                with self.assertRaises(ValueError):
                    C.reconstruct(altered,self.root)

    def test_path_traversal(self):
        for path in ['../x','/x','a/../x','a//x','a/./x','a\\x','']:
            with self.subTest(path=path),self.assertRaises(ValueError):
                C.read_bytes(self.root,path)

    def test_leaf_symlink_not_followed(self):
        p=self.root/'link';p.symlink_to(self.package/'ground-truth.json')
        self.assertEqual(C.metadata(self.root,'link'),'symlink-not-followed')
        with self.assertRaises(OSError):
            C.read_bytes(self.root,'link')

    def test_parent_symlink_not_followed(self):
        (self.root/'linked').symlink_to(self.package,target_is_directory=True)
        with self.assertRaises(OSError):
            C.read_bytes(self.root,'linked/ground-truth.json')
        self.assertEqual(C.metadata(self.root,'linked/ground-truth.json'),'unavailable-or-unsafe')

    def test_fixture_symlink_not_followed(self):
        p=self.package/'fixtures/initial-code.json';p.unlink();p.symlink_to(self.package/'ground-truth.json')
        with self.assertRaises(OSError):
            C.check(self.package)

    def test_hardlink_rejected(self):
        os.link(self.package/'ground-truth.json',self.root/'hardlink')
        with self.assertRaisesRegex(ValueError,'single-link'):
            C.read_bytes(self.root,'hardlink')

    def test_nonregular_rejected_without_blocking(self):
        os.mkfifo(self.root/'fifo')
        with self.assertRaisesRegex(ValueError,'regular file'):
            C.read_bytes(self.root,'fifo')

    def test_oversized_rejected(self):
        (self.root/'big').write_bytes(b'x'*(C.MAX_BYTES+1))
        with self.assertRaisesRegex(ValueError,'oversized'):
            C.read_bytes(self.root,'big')

    def test_metadata_never_reads_content(self):
        (self.root/'cited').write_text('not opened')
        with patch.object(C,'read_bytes',side_effect=AssertionError('content read')):
            self.assertEqual(C.metadata(self.root,'cited'),'present-regular')
            self.assertEqual(C.metadata(self.root,'absent'),'missing')

    def test_availability_is_not_historical(self):
        for row in self.manifest['supporting_availability']:
            self.assertFalse(row['contents_read'])
            self.assertIn('not historical availability',row['observation_kind'])
        p=self.package/'allowlist.json'
        self.change('allowlist.json',lambda v:v['supporting_paths'][0].update(contents_read=True))
        with self.assertRaisesRegex(ValueError,'metadata-only'):
            C.check(self.package)

    def test_nonfinite_and_duplicate_json_rejected(self):
        for data in [b'{"x":1,"x":2}',b'{"x":NaN}']:
            (self.root/'bad.json').write_bytes(data)
            with self.assertRaises(ValueError):
                C.load(self.root,'bad.json')

    def test_json_pointer_escaping(self):
        self.assertEqual(C.pointer({'a/b':{'~c':[1]}},'/a~1b/~0c/0'),1)
        for ptr in ['bad','/~2','/01']:
            with self.assertRaises((ValueError,KeyError)):
                C.pointer([1,2],ptr)

    def test_markdown_local_links(self):
        import re
        # Only local document/file links; source line locators are code labels.
        for rel in ['ANSWER-SHEET.md','README.md','REPORT.md']:
            path=C.HERE/rel
            if not path.exists():
                continue
            for target in re.findall(r'\]\(([^)]+)\)',C.read_bytes(C.HERE,rel).decode()):
                if '://' not in target:
                    self.assertTrue((path.parent/target.split('#')[0]).is_file(),target)


if __name__=='__main__':
    unittest.main(verbosity=2)
