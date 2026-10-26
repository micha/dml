#!/usr/bin/env python3
"""Condensed source/number audit. No provider or cloud execution."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sources', type=Path, required=True)
args = p.parse_args()
source = (args.sources / 'aws_s3_object.go').read_text()
delete = (args.sources / 'aws_s3_delete.go').read_text()
update = source.split('func resourceObjectUpdate', 1)[1].split('func resourceObjectDelete', 1)[0]
upload = source.split('func resourceObjectUpload', 1)[1].split('func resourceObjectCustomizeDiff', 1)[0]
changes = source.split('func hasObjectContentChanges', 1)[1].split('func findObjectByBucketAndKey', 1)[0]
assert 'hasObjectContentChanges(d)' in update and 'resourceObjectUpload(ctx, d, meta)' in update
assert '"metadata"' in changes and 'body = bytes.NewReader([]byte{})' in upload
assert 'deleteAllObjectVersions(ctx, conn, bucket, key' in source
assert 'if key != objectKey' in delete and 'if key != deleteMarkerKey' in delete
# Repeat the original generator's exact stopping condition, measuring work rather
# than conflating the configured search domain with the number of hashes tried.
target = hashlib.sha256(b'SYNTHETIC-ONLY-project-0007').hexdigest()
guesses = 0
for i in range(100):
    guesses += 1
    if hashlib.sha256(f'SYNTHETIC-ONLY-project-{i:04}'.encode()).hexdigest() == target:
        break
assert guesses == 8
anchors = {}
for function in ('resourceObjectUpdate', 'resourceObjectDelete', 'resourceObjectUpload', 'hasObjectContentChanges'):
    anchors[function] = next(i for i, line in enumerate(source.splitlines(), 1) if line.startswith('func ' + function + '('))
anchors['version_id_schema'] = next(i for i, line in enumerate(source.splitlines(), 1) if '"version_id": {' in line)
print(json.dumps({'status': 'passed', 'cloud_executed': False,
    'source_claims': ['metadata changes enter upload; absent body selects empty bytes',
                      'versioned deletion enumerates versions and delete markers, filtered to exact key'],
    'low_entropy_search': {'configured_candidate_domain': 100, 'actual_hash_guesses_until_match': guesses,
                          'first_wave_field_100_is_domain_size_not_measured_work': True},
    'object_go_line_anchors': anchors,
    'citation_discrepancy': 'First-wave notes cite version_id schema at 270–273; pinned source has it at 246–249.'}, indent=2))
