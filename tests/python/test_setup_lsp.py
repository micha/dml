"""Editor database generation without requiring Meson or a real compiler."""

import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys

import pytest


@pytest.fixture
def editor_project(tmp_path):
    root = tmp_path / "project"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "setup-lsp.sh"
    shutil.copyfile(Path(__file__).resolve().parents[2] / "scripts/setup-lsp.sh", script)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    headers = tmp_path / "system headers"
    headers.mkdir()

    def executable(name, content):
        path = binaries / name
        path.write_text(f"#!{shutil.which('bash')}\n" + content)
        path.chmod(0o755)
        return path

    if os.name == "nt":
        # Native Windows Python cannot execute a POSIX shebang compiler fixture.
        # A CMD fixture is discoverable through PATHEXT and runs in subprocess.
        compiler = binaries / "cc.cmd"
        compiler.write_text(
            "@echo off\n"
            "echo #include ^<...^> search starts here: 1>&2\n"
            f"echo  {headers} 1>&2\n"
            "echo End of search list. 1>&2\n"
        )
    else:
        compiler = executable(
            "cc", f"echo '#include <...> search starts here:' >&2\n"
            f"echo ' {headers}' >&2\necho 'End of search list.' >&2\n",
        )
    executable("ninja", "exit 0\n")
    executable(
        "meson",
        'if [ "$2" = "--reconfigure" ]; then shift; fi\n'
        'mkdir -p "$2/meson-private"\ntouch "$2/meson-private/coredata.dat"\n',
    )
    (binaries / "python3").symlink_to(sys.executable)
    directory = root / "build" / "editor"
    directory.mkdir(parents=True)
    entries = [
        {"directory": str(directory), "file": "../../src/core.c",
         "command": f"{shlex.quote(str(compiler))} -DCORE=1 -c ../../src/core.c"},
        {"directory": str(directory), "file": "../../python/core.c",
         "arguments": [str(compiler), "-DPYTHON=1", "-c", "../../python/core.c"]},
    ]
    (directory / "compile_commands.json").write_text(json.dumps(entries))
    env = {**os.environ, "PATH": str(binaries) + os.pathsep + os.environ["PATH"]}
    return script, root, compiler, headers, env


def run_setup(script, env, *args):
    return subprocess.run(
        [shutil.which("bash"), str(script), *args], env=env, text=True, capture_output=True,
    )


def test_setup_core_and_binding_discovers_system_headers(editor_project):
    script, root, compiler, headers, env = editor_project
    for _ in range(2):  # Initial setup and reconfiguration both work.
        result = run_setup(script, env)
        assert result.returncode == 0, result.stderr
        commands = json.loads((root / "compile_commands.json").read_text())
        assert len(commands) == 2
        for entry, source, define in zip(
            commands, ("src/core.c", "python/core.c"), ("-DCORE=1", "-DPYTHON=1")
        ):
            assert entry["file"] == str(root / source)
            assert entry["arguments"][:3] == [str(compiler), "-isystem", str(headers)]
            assert define in entry["arguments"]
            assert "command" not in entry
        assert not (root / "compile_commands.json.tmp").exists()


def test_setup_help_and_invalid_arguments(editor_project):
    script, root, _, _, env = editor_project
    assert run_setup(script, env, "--help").returncode == 0
    assert run_setup(script, env, "unexpected").returncode != 0
    assert not (root / "compile_commands.json").exists()


def test_setup_rejects_missing_system_header_search_list(editor_project):
    script, root, compiler, _, env = editor_project
    compiler.write_text("@echo off\nexit /b 0\n" if os.name == "nt"
                        else f"#!{shutil.which('bash')}\nexit 0\n")
    result = run_setup(script, env)
    assert result.returncode != 0
    assert "could not discover C system headers" in result.stderr
    assert not (root / "compile_commands.json").exists()
