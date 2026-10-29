#!/usr/bin/env bash
# Explicit offline current-source wheel/bare-runtime image; no pull or bootstrap.
set -euo pipefail
repo="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
root="$(realpath -m "${1:?new owned build root required}")"
packaging="${2:?explicit cached packaging Python required}"
runtime="${3:?explicit bare runtime Python required}"
case "$root" in "$repo"/build/*) ;; *) exit 1;; esac
case "$root" in "$repo"/build/check*|"$repo"/build/coverage*) exit 1;; esac
mkdir "$root"
touch "$root/.dml-floci-fixture"
python="$(readlink -f "$runtime")"
store="$(dirname "$(dirname "$python")")"
case "$store" in /nix/store/*-env) echo 'requires bare runtime, not dev env' >&2; exit 1;; esac
test -x "$python" && test -x "$packaging"
mkdir -p "$root/context/rootfs" "$root/dist"
nix-store -qR "$store" > "$root/closure.txt"
while IFS= read -r path; do
  test -d "$path"
  mkdir -p "$root/context/rootfs$(dirname "$path")"
  cp -a "$path" "$root/context/rootfs$path"
done < "$root/closure.txt"
fs="$root/context/rootfs"
mkdir -p "$fs"/{etc,opt,tmp,work,home/dml}
printf 'root:x:0:0:root:/root:/bin/false\ndml:x:1000:1000:dml:/home/dml:/bin/false\n' > "$fs/etc/passwd"
printf 'root:x:0:\ndml:x:1000:\n' > "$fs/etc/group"
printf 'hosts: files dns\n' > "$fs/etc/nsswitch.conf"
chmod 1777 "$fs/tmp"
chmod 777 "$fs/work" "$fs/home/dml"
(cd "$repo"
  "$packaging" -m build --wheel --no-isolation --outdir "$root/dist" .
  "$packaging" -m build --wheel --no-isolation --outdir "$root/dist" python/daggerml-cli)
"$python" -m venv --without-pip "$fs/opt/dml"
"$packaging" -m pip --python "$fs/opt/dml/bin/python" install --no-index --no-deps "$root"/dist/*.whl
cp "$repo/tests/floci/Dockerfile" "$root/context/Dockerfile"
image="dml-floci-installed:$(basename "$root")"
docker --host unix:///var/run/docker.sock build --network none --pull=false -t "$image" "$root/context"
docker --host unix:///var/run/docker.sock image inspect "$image" --format '{{.Id}}' > "$root/image.txt"
sha256sum "$root"/dist/*.whl > "$root/wheels.sha256"
"$fs/opt/dml/bin/python" - "$root" "$repo" <<'PY'
import hashlib,json,sys,zipfile
from pathlib import Path
import daggerml
root,repo=map(Path,sys.argv[1:])
site=Path(daggerml.__file__).resolve().parent.parent
artifacts=[]
for wheel in (root/'dist').glob('*.whl'):
 with zipfile.ZipFile(wheel) as archive:
  for name in archive.namelist():
   if name.startswith(('daggerml/','daggerml_cli/')) and not name.endswith('/'):
    data=archive.read(name)
    assert (site/name).read_bytes()==data
    if name.endswith('.py'):
     source=repo/'python'/('daggerml-cli' if name.startswith('daggerml_cli/') else 'daggerml')/name
     assert source.read_bytes()==data
    artifacts.append(dict(file=name,sha256=hashlib.sha256(data).hexdigest()))
assert not any('test' in row['file'] or 'fixture' in row['file'] for row in artifacts)
(root/'artifacts.json').write_text(json.dumps(artifacts,indent=2))
PY
