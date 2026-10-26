#!/usr/bin/env python3
"""Fetch public primary evidence only; bounded requests, no credentials."""
import argparse
import hashlib
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent / 'runtime' / 'sources'
ROOT.mkdir(parents=True, exist_ok=True)

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'DML-feasibility-public-docs'}), timeout=30) as response:
        return response.read()

parser = argparse.ArgumentParser()
parser.add_argument('--aws-commit', help='Pin a known provider commit, skipping release lookup')
parser.add_argument('--aws-release', default='pinned', help='Label for a pinned provider revision')
args = parser.parse_args()
if args.aws_commit:
    tag, sha = args.aws_release, args.aws_commit
else:
    release = json.loads(get('https://api.github.com/repos/hashicorp/terraform-provider-aws/releases/latest'))
    tag = release['tag_name']
    ref = json.loads(get(f'https://api.github.com/repos/hashicorp/terraform-provider-aws/git/ref/tags/{tag}'))['object']
    if ref['type'] == 'tag':
        ref = json.loads(get(ref['url']))['object']
    sha = ref['sha']
urls = {
    'aws_s3_object.md': f'https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/{sha}/website/docs/r/s3_object.html.markdown',
    'aws_s3_object.go': f'https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/{sha}/internal/service/s3/object.go',
    'aws_s3_delete.go': f'https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/{sha}/internal/service/s3/delete.go',
    'tofu-file.html': 'https://opentofu.org/docs/language/functions/file/',
    'tofu-path.html': 'https://opentofu.org/docs/language/expressions/references/',
    'tofu-lock.html': 'https://opentofu.org/docs/language/files/dependency-lock/',
    'tofu-modules.html': 'https://opentofu.org/docs/language/modules/sources/',
    'tofu-provisioners.html': 'https://opentofu.org/docs/language/resources/provisioners/syntax/',
    'tofu-providers.html': 'https://opentofu.org/docs/language/modules/develop/providers/',
    'tofu-lifecycle.html': 'https://opentofu.org/docs/language/meta-arguments/lifecycle/',
    'tofu-sensitive.html': 'https://opentofu.org/docs/language/values/outputs/',
    'aws-delete.html': 'https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObject.html',
    'aws-copy.html': 'https://docs.aws.amazon.com/AmazonS3/latest/API/API_CopyObject.html',
}
manifest = {'aws_release': tag, 'aws_commit': sha, 'sources': {}}
for name, url in urls.items():
    try:
        data = get(url)
        (ROOT / name).write_bytes(data)
        manifest['sources'][name] = {'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        print(name, len(data))
    except Exception as e:
        manifest['sources'][name] = {'url': url, 'error': str(e)}
        print(name, type(e).__name__, str(e))
(ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(tag, sha)
