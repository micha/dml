# Packaging and Distribution Plan

Status: Draft implementation plan.

Authority boundary:

- This document is authoritative for Python package layout and distribution
  strategy.
- For Python API behavior, see `docs/spec/python-bindings.md`.
- For CLI command semantics, see `docs/spec/cli.md`.
- For execution/remotes semantics, see `docs/spec/execution-and-remotes.md`.

## 1. Package Split

The project ships three distribution families:

- `daggerml`
  - Contains Python bindings/API and native extension.
  - Runtime dependencies: none.
  - Includes native code linked statically with `libdml`.
  - Install path: `pip install daggerml`.
- `daggerml-cli`
  - Contains Python CLI app with console script `dml`.
  - Depends on `daggerml`.
  - May include Python-only dependencies (for example `click`, `rich`).
  - Install path: `pipx install daggerml-cli` or `uv tool install daggerml-cli`.
- `daggerml-adapter-<name>`
  - Adapter-specific tool packages.
  - Depend on `daggerml` and optionally `daggerml-cli`.
  - May include service-specific dependencies (for example `boto3`).
  - Install path: `pipx install daggerml-adapter-<name>` or
    `uv tool install daggerml-adapter-<name>`.

## 2. Wheel and sdist Policy

- `daggerml` publishes platform-native wheels and an sdist.
- sdists are allowed, but wheel coverage MUST include the support matrix in
  Section 3 to keep install-from-wheel as the normal path.
- `daggerml-cli` and `daggerml-adapter-*` publish pure-Python wheels
  (`py3-none-any`) and sdists.

## 3. Supported Binary Matrix (`daggerml`)

Required platform wheel targets:

- Linux `x86_64`: `manylinux_*_x86_64`
- Linux `aarch64`: `manylinux_*_aarch64` (native build, no emulation)
- macOS `x86_64`: `macosx_*_x86_64`
- macOS `arm64`: `macosx_*_arm64` (native build)
- Windows `AMD64`: `win_amd64`

Notes:

- Use perennial `manylinux` tags (PEP 600), for example
  `manylinux_2_28_x86_64` and `manylinux_2_28_aarch64`.
- `abi3` wheels are acceptable and recommended if bindings only use Python
  limited API. `abi3` does not change the platform requirement; Linux/macOS
  arm64 wheels remain architecture-native artifacts.

## 4. Repository Layout (Draft)

```text
.
├── src/                              # existing C core + CLI sources
├── include/
├── python/
│   ├── daggerml/
│   │   ├── pyproject.toml
│   │   ├── meson.build
│   │   ├── README.md
│   │   └── daggerml/
│   │       ├── __init__.py
│   │       ├── _core.pyi
│   │       └── py.typed
│   ├── daggerml-cli/
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   └── daggerml_cli/
│   │       ├── __init__.py
│   │       └── main.py
│   └── adapters/
│       └── <name>/
│           ├── pyproject.toml
│           ├── README.md
│           └── daggerml_adapter_<name>/
│               ├── __init__.py
│               └── main.py
└── .github/workflows/
    ├── ci.yml
    └── release-python.yml
```

## 5. `daggerml` Packaging Skeleton

`python/daggerml/pyproject.toml`:

```toml
[build-system]
requires = ["meson-python>=0.17", "meson>=1.4", "ninja>=1.11"]
build-backend = "mesonpy"

[project]
name = "daggerml"
version = "0.1.0"
description = "DaggerML Python API and native bindings"
readme = "README.md"
requires-python = ">=3.8"
license = { text = "MIT" }
authors = [{ name = "DaggerML maintainers" }]
classifiers = [
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3 :: Only",
  "Programming Language :: C",
  "Operating System :: POSIX :: Linux",
  "Operating System :: MacOS",
  "Operating System :: Microsoft :: Windows",
]

[tool.meson-python]
limited-api = true

[tool.meson-python.args]
setup = [
  "--wrap-mode=forcefallback",
  "--force-fallback-for=*",
  "--default-library=static",
]
install = ["--skip-subprojects"]
```

`python/daggerml/meson.build` sketch:

```meson
project('daggerml', 'c', version: '0.1.0', default_options: ['c_std=c11'])

py = import('python').find_installation(pure: false)
py_dep = py.dependency()

dml_core = static_library(
  'dmlcore',
  [
    '../../src/dml.c',
    'src/bindings.c',
  ],
  include_directories: include_directories('../../include', 'include'),
  install: false,
)

py.extension_module(
  '_core',
  [],
  link_with: dml_core,
  dependencies: [py_dep],
  subdir: 'daggerml',
  install: true,
  limited_api: '3.8',
)

py.install_sources('daggerml/__init__.py', subdir: 'daggerml')
```

Guidance:

- Link the core statically into the extension module to avoid runtime shared
  library resolution issues.
- Keep runtime Python deps empty.

## 6. `daggerml-cli` Packaging Skeleton

`python/daggerml-cli/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "daggerml-cli"
version = "0.1.0"
description = "DaggerML command-line interface"
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
  "daggerml>=0.1.0,<0.2.0",
  "click>=8.1",
  "rich>=13.0",
]

[project.scripts]
dml = "daggerml_cli.main:main"
```

Wheel expectation:

- Pure Python wheel: `daggerml_cli-<ver>-py3-none-any.whl`.

## 7. Adapter Packaging Skeleton

`python/adapters/<name>/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "daggerml-adapter-<name>"
version = "0.1.0"
description = "DaggerML adapter: <name>"
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
  "daggerml>=0.1.0,<0.2.0",
  "daggerml-cli>=0.1.0,<0.2.0",
]

[project.scripts]
daggerml-adapter-<name> = "daggerml_adapter_<name>.main:main"

[project.entry-points."daggerml.adapters"]
<name> = "daggerml_adapter_<name>.main:adapter_entrypoint"
```

Wheel expectation:

- Pure Python wheel: `daggerml_adapter_<name>-<ver>-py3-none-any.whl`.

## 8. Build/Release Workflow Matrix (Draft)

Release workflow (`.github/workflows/release-python.yml`) should run on tags
(`v*`) and `workflow_dispatch` with these jobs:

1. Build `daggerml` binary wheels with `cibuildwheel`.
2. Build `daggerml` sdist.
3. Build `daggerml-cli` and adapter pure wheels + sdists.
4. Run smoke installs from built artifacts.
5. Publish with PyPI Trusted Publishing.

Recommended runners for true native builds:

- Linux x86_64 wheels: `ubuntu-24.04`
- Linux aarch64 wheels: `ubuntu-24.04-arm`
- macOS x86_64 wheels: `macos-13`
- macOS arm64 wheels: `macos-14`
- Windows AMD64 wheels: `windows-2022`

Example `cibuildwheel` environment (for `daggerml`):

```text
CIBW_BUILD=cp3*-*
CIBW_ARCHS_LINUX=x86_64 aarch64
CIBW_ARCHS_MACOS=x86_64 arm64
CIBW_ARCHS_WINDOWS=AMD64
CIBW_SKIP=*-musllinux_* pp* *-win32
```

If using native runners per arch, override `CIBW_ARCHS_*` per job to build only
the native arch for that runner.

## 9. Publish Order and Compatibility Rules

- Publish `daggerml` first, then `daggerml-cli`, then adapters.
- Keep dependency ranges narrow and intentional (`>=x,<y`) until compatibility
  policy is established.
- Add a smoke test that installs `daggerml-cli` and at least one adapter from
  built artifacts before publish.

## 10. Operational Notes

- Keep `ci.yml` for PR validation and non-release checks.
- Use `release-python.yml` for package builds/publish only.
- Store build artifacts from release jobs even on failure to debug platform
  packaging regressions.
