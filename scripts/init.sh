
#!/usr/bin/env bash

prog=$0

warn() { [ $# -gt 0 ] && echo $prog: "$@" 1>&2; }
abort() { warn "$@"; exit 1; }

usage() {
  warn "$@"
  cat <<EOT
USAGE: $(basename $prog) [-h]

Installs system packages required for building the project and running the tests.

OPTIONS:
  -h              Print this and exit.
EOT
  exit;
}

while getopts "h" o; do
  case "${o}" in
    h) usage ;;
    ?) abort ;;
  esac
done
shift $((OPTIND-1))

apt_packages=$(cat <<EOT
build-essential
clang-format
clangd
git-hub
golang
lcov
make
meson
mull-19
ninja-build
python3
python3-coverage
python3-hypothesis
python3-pip
python3-pytest
python3-setuptools
python3-wheel
ripgrep
tree
valgrind
EOT
)

git_hooks=$(cat <<EOT
scripts/commit-msg-hook.sh
EOT
)

echo
echo "Packages to install:"
echo "$apt_packages" |sed 's@^@- @'

echo
echo "Git hooks to install:"
echo "$git_hooks" |sed 's@^@- @'

echo
read -p "Proceed? [y/N] " -n 1 -r
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 1 || echo

export DEBIAN_FRONTEND=noninteractive
echo sudo apt-get -y update
echo sudo apt-get install -y $apt_packages

for hook in $git_hooks; do
  echo cp $hook .git/hooks/$(echo $hook |sed -e 's@^.*/@@' -e 's@-hook\.sh@@')
done
