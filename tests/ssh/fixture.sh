#!/usr/bin/env bash
# Explicit local-only fixture ownership. Invoke in the existing project tools shell.
set -euo pipefail
repo="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
action="${1:?build/start/stop/remove required}"
root="${2:?fixture root under build/ required}"
root="$(realpath -m "$root")"
case "$root" in "$repo"/build/*) ;; *) echo 'fixture root must be inside checkout build/' >&2; exit 1;; esac
case "$root" in "$repo"/build/check|"$repo"/build/check/*|"$repo"/build/coverage|"$repo"/build/coverage/*) exit 1;; esac
name=dml-iteration10-ssh
label=dml.fixture=iteration10
image=dml-ssh-fixture:local
docker_local() { docker --host unix:///var/run/docker.sock "$@"; }
owned_container() {
  test "$(docker_local inspect "$name" --format '{{index .Config.Labels "dml.fixture"}}')" = iteration10
}
case "$action" in
  build)
    packaging="${3:?explicit existing packaging Python required}"
    runtime="${4:?explicit bare cached runtime Python required}"
    if [ ! -d "$root" ]; then mkdir "$root"; touch "$root/.dml-ssh-fixture"; fi
    test -f "$root/.dml-ssh-fixture"
    test -x "$packaging"
    test -x "$runtime"
    # Query only already-present store paths; no Nix realisation or package bootstrap.
    python="$(readlink -f "$runtime")"
    shell="$(readlink -f "$(command -v bash)")"
    ssh="$(readlink -f "$(command -v ssh)")"
    sshd="$(dirname "$ssh")/sshd"
    test -x "$sshd"
    # Runtime Python is explicitly selected, not inferred from the development env
    # (which would unnecessarily copy pytest/Hypothesis/coverage dependencies).
    case "$(dirname "$(dirname "$python")")" in /nix/store/*-env) echo 'select bare runtime Python, not tools env' >&2; exit 1;; esac
    mkdir -p "$root/context/rootfs" "$root/context/exchanges" "$root/dist"
    nix-store -qR "$(dirname "$(dirname "$python")")" "$(dirname "$(dirname "$shell")")" \
      "$(dirname "$(dirname "$sshd")")" > "$root/closure.txt"
    while IFS= read -r store; do
      test -d "$store"
      mkdir -p "$root/context/rootfs$(dirname "$store")"
      if [ ! -d "$root/context/rootfs$store" ]; then cp -a "$store" "$root/context/rootfs$store"; fi
    done < "$root/closure.txt"
    fs="$root/context/rootfs"
    mkdir -p "$fs"/{bin,etc,opt/fixture,run/sshd,var/empty,tmp,work}
    ln -sfn "$shell" "$fs/bin/sh"
    ln -sfn "$sshd" "$fs/opt/fixture/sshd"
    printf 'root:x:0:0:fixture:/root:/bin/sh\nsshd:x:74:74:sshd:/var/empty:/bin/sh\ndml:x:1000:1000:fixture:/work:/bin/sh\n' > "$fs/etc/passwd"
    printf 'root:x:0:\nsshd:x:74:\ndml:x:1000:\n' > "$fs/etc/group"
    printf 'root:*:19000:0:99999:7:::\nsshd:*:19000:0:99999:7:::\ndml:x:19000:0:99999:7:::\n' > "$fs/etc/shadow"
    chmod 1777 "$fs/tmp"
    (cd "$repo"; "$packaging" -m build --wheel --no-isolation --outdir "$root/dist" .
      "$packaging" -m build --wheel --no-isolation --outdir "$root/dist" python/daggerml-cli)
    "$python" -m venv --clear --without-pip "$fs/opt/dml"
    "$packaging" -m pip --python "$fs/opt/dml/bin/python" install --no-index --no-deps "$root"/dist/*.whl
    cp "$repo/tests/ssh/Dockerfile" "$root/context/Dockerfile"
    docker_local build --network none --pull=false -t "$image" "$root/context"
    docker_local image inspect "$image" --format '{{.Id}}' > "$root/image.txt"
    sha256sum "$root"/dist/*.whl > "$root/wheels.sha256"
    ;;
  start)
    test -f "$root/.dml-ssh-fixture"
    port="${3:?explicit free high loopback port required}"
    python3 - "$port" <<'PY'
import socket, sys
port = int(sys.argv[1])
assert 1024 <= port <= 65535
with socket.socket() as s:
    s.bind(('127.0.0.1', port))
PY
    mkdir "$root/credentials"
    chmod 700 "$root/credentials"
    ssh-keygen -q -t ed25519 -N '' -f "$root/credentials/client"
    ssh-keygen -q -t ed25519 -N '' -f "$root/credentials/host"
    printf 'Port %s\nListenAddress 127.0.0.1\nHostKey /etc/dml_host_key\nAuthorizedKeysFile /etc/dml_authorized_keys\nAllowUsers dml\nPubkeyAuthentication yes\nPasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\nUsePAM no\nStrictModes yes\nAllowAgentForwarding no\nAllowTcpForwarding no\nX11Forwarding no\nPermitTunnel no\nPrintMotd no\nPrintLastLog no\nLogLevel ERROR\n' "$port" > "$root/sshd_config"
    # Approved deviation: host network, server strictly on loopback. No namespace-isolation claim.
    docker_local create --pull never --network host --name "$name" --label "$label" \
      "$(< "$root/image.txt")" -D -e -f /etc/dml_sshd_config
    docker_local cp "$root/credentials/host" "$name:/etc/dml_host_key"
    docker_local cp "$root/credentials/client.pub" "$name:/etc/dml_authorized_keys"
    docker_local cp "$root/sshd_config" "$name:/etc/dml_sshd_config"
    docker_local start "$name"
    python3 - "$root" "$port" <<'PY'
from pathlib import Path
import json, sys
root, port = Path(sys.argv[1]), int(sys.argv[2])
key = (root/'credentials/host.pub').read_text().split()
(root/'credentials/known_hosts').write_text('[127.0.0.1]:{} {} {}\n'.format(port, key[0], key[1]))
(root/'endpoint.json').write_text(json.dumps(dict(host='127.0.0.1', port=port, user='dml',
    identity_file=str(root/'credentials/client'), known_hosts_file=str(root/'credentials/known_hosts'),
    python='/opt/dml/bin/python', workspace_root='/work/exchanges')))
PY
    docker_local inspect "$name" --format '{{json .Mounts}} {{json .HostConfig.NetworkMode}}'
    ss -ltn "( sport = :$port )"
    ;;
  stop)
    test -f "$root/.dml-ssh-fixture"
    owned_container
    # Caller must first prove no live computation/unknown writer; stopping alone is NOT that proof.
    docker_local stop --timeout 5 "$name"
    test "$(docker_local inspect "$name" --format '{{.State.Running}}')" = false
    ;;
  remove)
    test -f "$root/.dml-ssh-fixture"
    owned_container
    test "$(docker_local inspect "$name" --format '{{.State.Running}}')" = false
    # Explicit evidence/history disposal policy; not an automatic transport-error action.
    docker_local rm "$name"
    rm -f "$root/credentials/client" "$root/credentials/client.pub" \
      "$root/credentials/host" "$root/credentials/host.pub"
    ;;
  *) echo 'unsupported fixture action' >&2; exit 1;;
esac
