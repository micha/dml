#!/usr/bin/env python3
"""Bounded independent downloads of three public pinned sources, never cloud APIs."""
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
(HERE / 'runtime').mkdir(exist_ok=True)
ROOT = Path(tempfile.mkdtemp(prefix='sources-', dir=HERE / 'runtime'))
manifest = json.loads((HERE.parent / 'adversarial/sources.json').read_text())
assert manifest['aws_commit'] == '5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
results = {'revision': manifest['aws_commit'], 'release': manifest['aws_release'], 'files': {}}
for name in ('aws_s3_object.go', 'aws_s3_delete.go', 'aws_s3_object.md'):
    entry = manifest['sources'][name]
    assert entry['url'].startswith('https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/' + manifest['aws_commit'] + '/')
    request = urllib.request.Request(entry['url'], headers={'User-Agent': 'DML-independent-review'})
    with opener.open(request, timeout=30) as response:
        data = response.read(200001)
    assert len(data) <= 200000
    digest = hashlib.sha256(data).hexdigest()
    assert digest == entry['sha256']
    (ROOT / name).write_bytes(data)
    results['files'][name] = {**entry, 'independently_downloaded': True}
(ROOT / 'manifest.json').write_text(json.dumps(results, indent=2) + '\n')
(HERE / 'runtime/latest-sources.json').write_text(json.dumps({'run': str(ROOT)}) + '\n')
print(json.dumps(results, indent=2))
