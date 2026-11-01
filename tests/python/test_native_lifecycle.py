"""Option A ONLY: deterministic TEST-PRIVATE actual-platform LMDB lifecycles.

Two controls per CI job, ZERO DML requests/attempts/computations/transactions.
Mac uses actual POSIXSEM; Windows actual named mutex; Linux actual default
POSIX mutex. Linux overlapping live environments MUST exercise genuine failed
exclusive/shared success, not wait for an absent semaphore hook or skip a case.
No production hooks/core/module/workflow/threshold/budget edits or B seam.

One private compiler invocation per test session, two actors per control; BOTH
actors start before any environment opens. Original copied native calls execute
once, untouched results and errno/GetLastError restored across instrumentation.
Original sem_unlink/CloseHandle only at their original owned lifecycle sites.
Expected absent namespace lookups acquire no handle; unexpected presence closes
only its borrowed lookup handle and aborts before the interval, never deletes it.
Fresh controller-owned paths; before/after directory/data/lock identity, actor
reaping and retired namespace observations required. No adversarial namespace
isolation claim. Failure/uncertain writers => cooperative abort release + bounded
wait, NO signal/manual resource cleanup/relaunch/fallback/skip/provisioning.

Caps: <=128 x <512-byte native events/actor; <=128KiB combined native traces/case;
<=64KiB compiler/actor stdout/stderr each. No data/record/env-value dumps. Existing
runtime deadlines untouched; NEW fixture barriers15s, controller owner wait20s.
Raw prior CI/UNKNOWN/VP-001 and forced-backend P3 remain distinct and unchanged.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
MDB_SHA256 = "eb8b0fdde8f13bed1139ae899bcc7767e44490f6316ccede59b62392d1c0d717"
ACTUAL_BACKENDS = {"win32": "windows-mutex", "darwin": "mac-posix-sem", "linux": "linux-posix-mutex"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(source: str, old: str, new: str) -> str:
    assert source.count(old) == 1, "copied source seam changed: review, no guessed patch"
    return source.replace(old, new)


def instrument(source: str) -> str:
    """Exact private 0.9.35 seams; every original call/result/branch retained."""
    source = once(source, '#include "midl.h"', '#include "midl.h"\n#include "native_lifecycle_trace.h"')
    source = once(source,
        'mdb_env_excl_lock(MDB_env *env, int *excl)\n{\n\tint rc = 0;',
        'mdb_env_excl_lock(MDB_env *env, int *excl)\n{\n\tint rc = 0;\n'
        '#ifdef _WIN32\n\tNLC_NOTE("compiled-backend-windows-mutex", 0, *excl, env->me_lfd, NULL);\n'
        '#elif defined(MDB_USE_POSIX_SEM)\n\tNLC_NOTE("compiled-backend-posix-sem", 0, *excl, env->me_lfd, NULL);\n'
        '#elif defined(MDB_USE_POSIX_MUTEX)\n\tNLC_NOTE("compiled-backend-posix-mutex", 0, *excl, env->me_lfd, NULL);\n'
        '#else\n\tNLC_NOTE("compiled-backend-unsupported", 0, *excl, env->me_lfd, NULL);\n#endif')
    source = once(source,
        '\t\t\t(rc = ErrCode()) == EINTR) ;\n\tif (!rc) {',
        '\t\t\t(rc = ErrCode()) == EINTR) ;\n\tNLC_NOTE("exclusive-attempt-return", rc, *excl, env->me_lfd, NULL);\n\tif (!rc) {')
    source = once(source, '\t\tlock_info.l_type = F_RDLCK;\n\t\twhile',
        '\t\tlock_info.l_type = F_RDLCK;\n\t\tNLC_SHARED_ATTEMPT_READY();\n\t\twhile')
    source = once(source, '\t\tif (rc == 0)\n\t\t\t*excl = 0;\n\t}',
        '\t\tif (rc == 0)\n\t\t\t*excl = 0;\n\t\tNLC_NOTE("shared-acquisition-return", rc, *excl, env->me_lfd, NULL);\n\t}')
    source = once(source,
        '\t\tsem_unlink(env->me_txns->mti_rmname);\n\t\tsem_unlink(env->me_txns->mti_wmname);',
        '\t\tNLC_NAMESPACE("init", env->me_txns->mti_rmname, env->me_txns->mti_wmname);\n'
        '\t\tNLC_ORIGINAL_UNLINK("init-reader-unlink-return", env->me_txns->mti_rmname);\n'
        '\t\tNLC_ORIGINAL_UNLINK("init-writer-unlink-return", env->me_txns->mti_wmname);')
    for part, short in (("reader", "r"), ("writer", "w")):
        assignment = f'\t\tenv->me_{short}mutex = sem_open(env->me_txns->mti_{short}mname,\n\t\t\tO_CREAT|O_EXCL, mode, 1);'
        source = once(source, assignment, assignment +
            f'\n\t\tNLC_NOTE("{part}-sem-create-return", env->me_{short}mutex == SEM_FAILED ? -1 : 0, *excl, env->me_lfd, env->me_txns->mti_{short}mname);')
        assignment = f'\t\tenv->me_{short}mutex = sem_open(env->me_txns->mti_{short}mname, 0);'
        source = once(source, assignment, assignment +
            f'\n\t\tNLC_NOTE("{part}-sem-open0-return", env->me_{short}mutex == SEM_FAILED ? -1 : 0, *excl, env->me_lfd, env->me_txns->mti_{short}mname);')
    source = once(source,
        '\t\t\tsem_close(env->me_rmutex);\n\t\t\tif (env->me_wmutex != SEM_FAILED)\n\t\t\t\tsem_close(env->me_wmutex);',
        '\t\t\tint nlc_close_rc = sem_close(env->me_rmutex);\n'
        '\t\t\tNLC_NOTE("reader-sem-close-return", nlc_close_rc, excl, env->me_lfd, env->me_txns->mti_rmname);\n'
        '\t\t\tif (env->me_wmutex != SEM_FAILED) {\n'
        '\t\t\t\tnlc_close_rc = sem_close(env->me_wmutex);\n'
        '\t\t\t\tNLC_NOTE("writer-sem-close-return", nlc_close_rc, excl, env->me_lfd, env->me_txns->mti_wmname);\n\t\t\t}')
    source = once(source, '\t\t\tif (excl == 0)\n\t\t\t\tmdb_env_excl_lock(env, &excl);',
        '\t\t\tif (excl == 0) {\n\t\t\t\tnlc_close_rc = mdb_env_excl_lock(env, &excl);\n'
        '\t\t\t\tNLC_NOTE("close-exclusive-return", nlc_close_rc, excl, env->me_lfd, NULL);\n\t\t\t}\n'
        '\t\t\tNLC_CLOSE_EXCLUSIVE(excl);')
    source = once(source,
        '\t\t\t\tsem_unlink(env->me_txns->mti_rmname);\n\t\t\t\tsem_unlink(env->me_txns->mti_wmname);',
        '\t\t\t\tNLC_NAMESPACE("close", env->me_txns->mti_rmname, env->me_txns->mti_wmname);\n'
        '\t\t\t\tNLC_ORIGINAL_UNLINK("close-reader-unlink-return", env->me_txns->mti_rmname);\n'
        '\t\t\t\tNLC_ORIGINAL_UNLINK("close-writer-unlink-return", env->me_txns->mti_wmname);')
    source = once(source, '\t\t(void) close(env->me_lfd);',
        '\t\tNLC_NOTE("lock-descriptor-close-enter", 0, excl, env->me_lfd, NULL);\n'
        '\t\tint nlc_fdclose_rc = close(env->me_lfd);\n'
        '\t\t/* Closed descriptor/path NEVER dereferenced by the logger. */\n'
        '\t\tNLC_NOTE("lock-descriptor-close-return", nlc_fdclose_rc, excl, -1, NULL);')
    return instrument_windows(source)


def instrument_windows(source: str) -> str:
    source = once(source, '\tif (LockFile(env->me_lfd, 0, 0, 1, 0)) {',
        '\tBOOL nlc_exclusive = LockFile(env->me_lfd, 0, 0, 1, 0);\n'
        '\tNLC_NOTE("exclusive-attempt-return", nlc_exclusive ? 0 : -1, *excl, env->me_lfd, NULL);\n'
        '\tif (nlc_exclusive) {')
    source = once(source,
        '\t\tif (LockFileEx(env->me_lfd, 0, 0, 1, 0, &ov)) {\n\t\t\t*excl = 0;\n\t\t} else {\n\t\t\trc = ErrCode();\n\t\t}',
        '\t\tNLC_SHARED_ATTEMPT_READY();\n'
        '\t\tif (LockFileEx(env->me_lfd, 0, 0, 1, 0, &ov)) {\n\t\t\t*excl = 0;\n\t\t} else {\n\t\t\trc = ErrCode();\n\t\t}\n'
        '\t\tNLC_NOTE("shared-acquisition-return", rc, *excl, env->me_lfd, NULL);')
    for part, short in (("reader", "r"), ("writer", "w")):
        assignment = f'\t\tenv->me_{short}mutex = CreateMutexA(&mdb_all_sa, FALSE, env->me_txns->mti_{short}mname);'
        prefix = ('\t\tNLC_NAMESPACE("init", env->me_txns->mti_rmname, env->me_txns->mti_wmname);\n'
                  if short == "r" else "")
        source = once(source, assignment, prefix + assignment +
            f'\n\t\tNLC_NOTE("{part}-mutex-create-return", env->me_{short}mutex ? 0 : -1, *excl, env->me_lfd, env->me_txns->mti_{short}mname);')
        assignment = f'\t\tenv->me_{short}mutex = OpenMutexA(SYNCHRONIZE, FALSE, env->me_txns->mti_{short}mname);'
        source = once(source, assignment, assignment +
            f'\n\t\tNLC_NOTE("{part}-mutex-open-return", env->me_{short}mutex ? 0 : -1, *excl, env->me_lfd, env->me_txns->mti_{short}mname);')
    source = once(source,
        '\t\t\tCloseHandle(env->me_rmutex);\n\t\t\tif (env->me_wmutex) CloseHandle(env->me_wmutex);',
        '\t\t\tNLC_NAMESPACE("close", env->me_txns->mti_rmname, env->me_txns->mti_wmname);\n'
        '\t\t\tBOOL nlc_closed = CloseHandle(env->me_rmutex);\n'
        '\t\t\tNLC_NOTE("reader-mutex-close-return", nlc_closed ? 0 : -1, excl, env->me_lfd, env->me_txns->mti_rmname);\n'
        '\t\t\tif (env->me_wmutex) {\n\t\t\t\tnlc_closed = CloseHandle(env->me_wmutex);\n'
        '\t\t\t\tNLC_NOTE("writer-mutex-close-return", nlc_closed ? 0 : -1, excl, env->me_lfd, env->me_txns->mti_wmname);\n\t\t\t}\n'
        '\t\t\tNLC_WINDOWS_NAMED_CLOSED();')
    comment = ('\t\t\t/* Unlock the lockfile.  Windows would have unlocked it\n'
               '\t\t\t * after closing anyway, but not necessarily at once.\n\t\t\t */\n')
    source = once(source, comment + '\t\t\tUnlockFile(env->me_lfd, 0, 0, 1, 0);',
        comment + '\t\t\tBOOL nlc_unlocked = UnlockFile(env->me_lfd, 0, 0, 1, 0);\n'
        '\t\t\tNLC_NOTE("unlockfile-return", nlc_unlocked ? 0 : -1, excl, env->me_lfd, NULL);')
    return source


def bounded_bytes(path: Path, cap: int = 65536) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(cap + 1)
    assert len(data) <= cap, f"diagnostic cap exceeded; retain original {path}"
    return data


@pytest.fixture(scope="session")
def native_lifecycle_binary(tmp_path_factory, record_testsuite_property):
    """Suite property survives setup failure; no JUnit family/workflow change."""
    work = tmp_path_factory.mktemp("native-lifecycle-build").resolve()
    payload = dict(work=str(work), source_inputs={str(p.relative_to(ROOT)): sha(p) for p in
        (ROOT / "tests/c/native_lifecycle_driver.c", ROOT / "tests/c/native_lifecycle_trace.h", Path(__file__))},
        Q=0, T=0, computations=0, outcome="setup-error", files={})
    try:
        result = compile_native_lifecycle(work)
        payload["outcome"] = "compiled"
        return result
    except BaseException as error:
        payload["exception_type"] = type(error).__name__
        raise
    finally:
        # Known synthetic sources/argv/compiler logs only, bounded BEFORE decode;
        # no environment dump, arbitrary directory scrape or large source dump.
        remaining = 256 * 1024
        for name in ("source-inputs.json", "before-compile.json", "compiled-identity.json",
                     "compile.exit", "compiler.stdout", "compiler.stderr", "compile.stdout", "compile.stderr"):
            path = work / name
            if path.is_file():
                try:
                    raw = bounded_bytes(path, min(65536, remaining))
                    remaining -= len(raw)
                    payload["files"][name] = raw.decode("utf8", "replace")
                except AssertionError:
                    payload["files"][name] = "OVER-CAP: original retained; NOT compiler success"
        record_testsuite_property("native_lifecycle_compile", json.dumps(payload))


def compile_native_lifecycle(work: Path):
    """Compile only these copies; no shared build/config/package mutation."""
    assert sys.platform in ACTUAL_BACKENDS, "unsupported actual platform, NOT a skip"
    dependency = ROOT / "subprojects/lmdb-LMDB_0.9.35/libraries/liblmdb"
    assert sha(dependency / "mdb.c") == MDB_SHA256, "LMDB version/source changed: review"
    driver = ROOT / "tests/c/native_lifecycle_driver.c"
    header = ROOT / "tests/c/native_lifecycle_trace.h"
    sources = {str(p.relative_to(ROOT)): sha(p) for p in
               (driver, header, Path(__file__), ROOT / "subprojects/lmdb.wrap",
                *(dependency / name for name in ("mdb.c", "midl.c", "lmdb.h", "midl.h")))}
    (work / "source-inputs.json").write_text(json.dumps(sources, indent=2))
    for name in ("mdb.c", "midl.c", "lmdb.h", "midl.h"):
        shutil.copyfile(dependency / name, work / name)
    shutil.copyfile(driver, work / driver.name)
    shutil.copyfile(header, work / header.name)
    original = (work / "mdb.c").read_bytes()
    (work / "mdb.original.c").write_bytes(original)
    (work / "mdb.c").write_text(instrument(original.decode("utf8")), encoding="utf8")
    binary_path = Path(os.environ.get("DML_BIN", str(ROOT / "build/check/dml"))).resolve()
    intro_path = binary_path.parent / "meson-info/intro-compilers.json"
    intro = json.loads(intro_path.read_bytes())
    configured = intro["host"]["c"]
    assert configured["id"] in ("gcc", "clang"), "unsupported compiler; no fallback/install"
    command = configured["exelist"]
    compiler = shutil.which(command[0])
    assert compiler is not None, "existing configured compiler missing; no provisioning"
    command = [compiler, *command[1:]]
    version = subprocess.run([*command, "--version"], capture_output=True, check=False)
    (work / "compiler.stdout").write_bytes(version.stdout)
    (work / "compiler.stderr").write_bytes(version.stderr)
    assert version.returncode == 0
    bounded_bytes(work / "compiler.stdout"); bounded_bytes(work / "compiler.stderr")
    binary = work / ("native-lifecycle.exe" if sys.platform == "win32" else "native-lifecycle")
    argv = [*command, "-std=c11", "-O0", "-g", "-Werror=implicit-function-declaration",
            "-I" + str(work), str(work / driver.name), str(work / "mdb.c"),
            str(work / "midl.c"), "-pthread", "-o", str(binary)]
    before = dict(sources=sources, compiler=command, compiler_sha256=sha(Path(compiler)),
                  resolved_compiler_sha256=sha(Path(compiler).resolve()),
                  compiler_version=version.stdout.decode("utf8", "replace"),
                  configured_compiler=configured, configured_compiler_metadata_sha256=sha(intro_path),
                  argv=argv, actual_backend=ACTUAL_BACKENDS[sys.platform], force_backend=False,
                  copied_sources={p.name: sha(p) for p in work.iterdir() if p.suffix in (".c", ".h")},
                  copied_header_sha256=sha(work / header.name), before_compile=True)
    (work / "before-compile.json").write_text(json.dumps(before, indent=2))
    with (work / "compile.stdout").open("wb") as out, (work / "compile.stderr").open("wb") as err:
        compiled = subprocess.run(argv, stdout=out, stderr=err, check=False)
    (work / "compile.exit").write_text(str(compiled.returncode))
    bounded_bytes(work / "compile.stdout"); bounded_bytes(work / "compile.stderr")
    assert compiled.returncode == 0, f"private compiler failed; retain {work}; NO rebuild/fallback"
    before.update(compile_exit=compiled.returncode, binary_sha256=sha(binary))
    (work / "compiled-identity.json").write_text(json.dumps(before, indent=2))
    return binary, before, {"stopped": False}


def file_identities(root: Path) -> list[dict]:
    identities = []
    for relative in ("env", "env/data.mdb", "env/lock.mdb"):
        path = root / relative
        assert not path.is_symlink(), "owned fixture paths only"
        stat = path.stat()
        identities.append(dict(path=relative, dev=stat.st_dev, ino=stat.st_ino,
                               mode=stat.st_mode, size=stat.st_size))
    return identities


def wait_marker(root: Path, name: str, owners) -> None:
    deadline = time.monotonic() + 15
    while not (root / name).exists():
        assert all(owner.poll() is None for owner in owners), "actor exited before barrier; STOP"
        assert time.monotonic() < deadline, "new fixture barrier deadline; STOP"
        time.sleep(0.02)


def actors(binary: Path, provenance: dict, root: Path, case: str):
    """One launch per actor, no retry or signal on uncertainty."""
    assert sha(binary) == provenance["binary_sha256"]
    for relative, expected in provenance["sources"].items():
        assert sha(ROOT / relative) == expected, "source changed after compile: STOP"
    argv = [[str(binary), str(root), role, case] for role in ("A", "B")]
    (root / "before-run.json").write_text(json.dumps(dict(argv=argv, sources=provenance["sources"],
        binary_sha256=sha(binary), controls_in_this_case=1, actors=2, Q=0, T=0, computations=0), indent=2))
    owners, streams, exits = [], [], []
    failure = None
    try:
        for role, command in zip(("A", "B"), argv):
            out = (root / f"{role}.stdout").open("wb")
            err = (root / f"{role}.stderr").open("wb")
            streams.extend((out, err))
            owners.append(subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, close_fds=True))
        (root / "owners.json").write_text(json.dumps(dict(pids=[p.pid for p in owners], argv=argv)))
        wait_marker(root, "A-ready", owners); wait_marker(root, "B-ready", owners)
        (root / "start").touch(exist_ok=False)
        wait_marker(root, "initialized", owners)
        before = file_identities(root)
        (root / "files-before.json").write_text(json.dumps(before, indent=2))
        (root / "begin-close").touch(exist_ok=False)
        for owner in owners:
            exits.append(owner.wait(timeout=20))
        (root / "exits.json").write_text(json.dumps(exits))
        assert exits == [0, 0], "CONTROL/logger/native actor failure; no intended-failure claim"
        after = file_identities(root)
        (root / "files-after.json").write_text(json.dumps(after, indent=2))
        assert [(x["dev"], x["ino"], x["mode"]) for x in before] == [
            (x["dev"], x["ino"], x["mode"]) for x in after], "owned dir/data/lock identity changed"
        return [p.pid for p in owners]
    except BaseException as error:
        failure = error
        # Persist known custody BEFORE additional cooperative waits or reraising
        # the initial timeout; interruption cannot erase that uncertainty record.
        (root / "owner-disposition.json").write_text(json.dumps(dict(
            pids=[p.pid for p in owners], exits=[p.poll() for p in owners],
            reaped=all(p.poll() is not None for p in owners), phase="initial-failure",
            no_signal=True, cooperative_abort_requested=True, namespace_manual_cleanup=False), indent=2))
        raise
    finally:
        if failure is not None:
            # Distinct cooperative abort, NEVER forge opener-done/shared readiness.
            # No new env begins after abort; existing owners finish originals if
            # they can return from native calls. Uncertain writers => no deletion.
            (root / "abort-release").touch()
        for owner in owners:
            if owner.poll() is None:
                try: owner.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    if failure is not None: failure.add_note(f"UNCERTAIN native actor pid={owner.pid}; NO signals/cleanup/retry")
        (root / "owner-disposition.json").write_text(json.dumps(dict(
            pids=[p.pid for p in owners], exits=[p.poll() for p in owners],
            reaped=all(p.poll() is not None for p in owners), no_signal=True,
            cooperative_abort=failure is not None, namespace_manual_cleanup=False), indent=2))
        for stream in streams: stream.close()


def namespace_event(rows: list[dict], label: str) -> tuple[int, dict]:
    matches = [(index, row) for index, row in enumerate(rows) if row["event"] == label]
    assert len(matches) == 1, f"missing/duplicate native namespace operation: {label}"
    return matches[0]


def namespace_epochs(a: list[dict], b: list[dict], *, case: str, platform: str) -> dict:
    """PURE reader: owned epoch membership, never cross-epoch name stability.

    POSIX original sem_close/unlink success proves each epoch's retirement;
    Windows original last-handle closes prove natural retirement under the
    no-other-retained-handles control. A also records its post-close absence
    observation. This reader adds no handles or inferred kernel-blocked events.
    """
    assert case in ("baseline", "interleaved")
    for actor, rows in ((1, a), (2, b)):
        assert rows and all(row["actor"] == actor for row in rows), "foreign actor"
        assert len({row["pid"] for row in rows}) == 1, "foreign actor PID"
    assert a[0]["pid"] != b[0]["pid"], "actors must be distinct owners"
    if platform == "linux":
        assert all(not row["name"] for row in a + b), "unexpected named Linux resource"
        return dict(epochs=[], named_names=[])
    assert platform in ("darwin", "win32")
    sem = platform == "darwin"
    kind = "sem" if sem else "mutex"
    prefix = ("/MDBr", "/MDBw") if sem else ("Global\\MDBr", "Global\\MDBw")
    epochs = []
    union = set()
    active_pair = None
    for actor, rows in ((1, a), (2, b)):
        peer_failure = case == "interleaved" and actor == 2
        if peer_failure:
            assert active_pair is not None
            assert not any(row["event"].endswith("-create-return") for row in rows), "peer must not initialize a new epoch"
            label = "reader-sem-open0-return" if sem else "reader-mutex-open-return"
            _, lookup = namespace_event(rows, label)
            assert lookup["name"] == active_pair[0], "lookup must address exact producing epoch"
            assert lookup["result"] == -1 and lookup["os_error"] == 2, "original reader lookup must fail not-found"
            allowed = {label: active_pair[0]}
            epoch = None
        else:
            ri, reader = namespace_event(rows, f"reader-{kind}-create-return")
            wi, writer = namespace_event(rows, f"writer-{kind}-create-return")
            pair = (reader["name"], writer["name"])
            assert all(name.startswith(p) and len(name) == len(p) + 10 for name, p in zip(pair, prefix)), "invalid native pair"
            assert pair[0][len(prefix[0]):] == pair[1][len(prefix[1]):], "reader/writer must belong to ONE epoch"
            assert reader["result"] == writer["result"] == 0
            rci, rc = namespace_event(rows, f"reader-{kind}-close-return")
            wci, wc = namespace_event(rows, f"writer-{kind}-close-return")
            assert (rc["name"], wc["name"]) == pair, "unmatched original close pair"
            assert rc["result"] == wc["result"] == 0
            oi, opened = namespace_event(rows, "mdb-env-open-return")
            ei, _ = namespace_event(rows, "env-close-enter")
            fi, _ = namespace_event(rows, "env-close-return")
            assert opened["result"] == 0 and ri < wi < oi < ei < rci < wci < fi
            allowed = {f"reader-{kind}-create-return": pair[0], f"writer-{kind}-create-return": pair[1],
                       f"reader-{kind}-close-return": pair[0], f"writer-{kind}-close-return": pair[1]}
            if sem:
                uri, ur = namespace_event(rows, "close-reader-unlink-return")
                uwi, uw = namespace_event(rows, "close-writer-unlink-return")
                assert (ur["name"], uw["name"]) == pair, "unmatched original unlink pair"
                assert ur["result"] == uw["result"] == 0, "missing successful epoch retirement"
                assert wci < uri < uwi < fi
                for part, name in zip(("reader", "writer"), pair):
                    ii, init = namespace_event(rows, f"init-{part}-unlink-return")
                    assert ii < ri and init["name"] == name and init["result"] == -1 and init["os_error"] == 2
                    allowed[f"init-{part}-unlink-return"] = name
                    allowed[f"close-{part}-unlink-return"] = name
                assert sum(row["event"] == "unlink-enter" for row in rows) == 4
            epoch = dict(actor=actor, pid=rows[0]["pid"], created_pair=list(pair), closed_pair=[rc["name"], wc["name"]],
                         retirement="original sem_close+sem_unlink success" if sem else "original last CloseHandle success")
            epochs.append(epoch)
            if actor == 1: active_pair = pair
        for row in rows:
            name = row["name"]
            if not name: continue
            if row["event"] == "namespace-safety-before-originals" and name in ("init", "close"): continue
            if row["event"] == "unlink-enter":
                assert sem and not peer_failure and name in pair, "unexplained unlink target"
            else:
                assert row["event"] in allowed and allowed[row["event"]] == name, "extra unexplained native name"
            union.add(name)
    _, retired = namespace_event(a, "owned-names-retired")
    assert retired["result"] == 0, "missing post-close absence observation"
    assert len(epochs) == (2 if case == "baseline" else 1)
    return dict(epochs=epochs, named_names=sorted(union))


def evidence(root: Path, case: str, pids: list[int]) -> dict:
    rows = []
    for role, pid in zip(("A", "B"), pids):
        trace = [json.loads(line) for line in bounded_bytes(root / f"{role}.jsonl").splitlines()]
        assert 0 < len(trace) <= 128
        assert [x["seq"] for x in trace] == list(range(1, len(trace) + 1))
        assert all(x["pid"] == pid and x["ns"] > 0 for x in trace)
        assert all(x["event"] != "CONTROL-ERROR" for x in trace)
        assert all(x["backend"] == ACTUAL_BACKENDS[sys.platform] for x in trace)
        result = json.loads(bounded_bytes(root / f"{role}.stdout"))
        bounded_bytes(root / f"{role}.stderr")
        assert result["pid"] == pid and result["env_closed"] is True
        rows.append(trace)
    assert sum((root / f"{role}.jsonl").stat().st_size for role in ("A", "B")) <= 128 * 1024
    a, b = rows
    find = lambda items, label: next(x for x in items if x["event"] == label)
    compiled = {"win32": "compiled-backend-windows-mutex", "darwin": "compiled-backend-posix-sem",
                "linux": "compiled-backend-posix-mutex"}[sys.platform]
    for items in rows:
        # Tag originates INSIDE copied mdb.c's actual backend preprocessor branch,
        # NOT the driver's label. Other compiled branches cannot pass this check.
        tags = {x["event"] for x in items if x["event"].startswith("compiled-backend-")}
        assert tags == {compiled}
    native_ids = [x for items in rows for x in items if x["event"] == compiled]
    assert all(x["ino"] > 0 for x in native_ids), "native info failure/zero identity is not proof"
    assert len({(x["dev"], x["ino"]) for x in native_ids}) == 1
    opened_a, opened_b = find(a, "mdb-env-open-return"), find(b, "mdb-env-open-return")
    expected = 2 if case == "interleaved" and sys.platform != "linux" else 0
    assert opened_a["result"] == 0 and opened_b["result"] == expected
    assert find(b, "env-close-return")["result"] == expected
    disposition = json.loads((root / "owner-disposition.json").read_bytes())
    assert disposition["reaped"] and disposition["exits"] == [0, 0]
    timing = {}
    if case == "baseline":
        assert find(a, "env-close-return")["ns"] < opened_b["ns"]
    else:
        failed = find(b, "exclusive-attempt-return")
        shared = find(b, "shared-acquisition-return")
        ready = find(b, "shared-attempt-ready")
        assert failed["result"] != 0
        assert failed["os_error"] in ((33,) if sys.platform == "win32" else (errno.EAGAIN, errno.EACCES))
        assert shared["result"] == 0 and shared["exclusive"] == 0
        assert failed["ns"] < ready["ns"] < shared["ns"] < opened_b["ns"]
        origin = find(a, compiled)
        identity_events = [origin, failed, shared]
        if sys.platform == "darwin":
            close_exclusive = find(a, "close-exclusive-return")
            assert close_exclusive["result"] == 0 and close_exclusive["exclusive"] == 1
            ur, uw = find(a, "close-reader-unlink-return"), find(a, "close-writer-unlink-return")
            enter, done = find(a, "lock-descriptor-close-enter"), find(a, "lock-descriptor-close-return")
            sem = find(b, "reader-sem-open0-return")
            assert sem["result"] == -1 and sem["os_error"] == errno.ENOENT == 2
            assert ur["result"] == uw["result"] == done["result"] == 0
            assert close_exclusive["ns"] < failed["ns"] < ready["ns"] < ur["ns"] <= uw["ns"] < enter["ns"] < shared["ns"] < sem["ns"]
            identity_events.extend((close_exclusive, enter))
            # Release occurs INSIDE original close; its postreturn logger can run
            # after B's shared-return logger. Never demand invented kernel-blocked
            # readiness or strict ordering between those postreturn log writes.
            timing = dict(close_enter_ns=enter["ns"], close_return_logged_ns=done["ns"],
                          shared_return_logged_ns=shared["ns"],
                          postreturn_log_order=done["ns"] <= shared["ns"],
                          release_basis="same positive native identity + actual exclusive/shared fcntl + original close only")
        elif sys.platform == "win32":
            cr, cw = find(a, "reader-mutex-close-return"), find(a, "writer-mutex-close-return")
            lookup = find(b, "reader-mutex-open-return")
            unlock = find(a, "unlockfile-return")
            assert cr["result"] == cw["result"] == unlock["result"] == 0
            assert cr["exclusive"] == cw["exclusive"] == 0
            assert lookup["result"] == -1 and lookup["os_error"] == 2
            assert cr["ns"] <= cw["ns"] < failed["ns"] < shared["ns"] < lookup["ns"] < opened_b["ns"] < unlock["ns"]
            identity_events.extend((cr, cw, unlock))
        else:
            live = find(a, "linux-live-env-overlap")
            assert live["ns"] < failed["ns"] < shared["ns"] < opened_b["ns"] < find(b, "env-close-return")["ns"] < find(a, "env-close-enter")["ns"]
        # 0==0 is NOT native identity proof when fstat/GetFileInformation failed.
        assert all(x["ino"] > 0 for x in identity_events)
        assert len({(x["dev"], x["ino"]) for x in identity_events}) == 1
    namespace = namespace_epochs(a, b, case=case, platform=sys.platform)
    return dict(case=case, actual_compiled_backend=compiled, native_open_rc=opened_b["result"],
                pids=pids, reaped=True, named_names=namespace["named_names"], named_epochs=namespace["epochs"], namespace_retired=True,
                native_identity_positive=True, timing=timing, Q=0, T=0, computations=0,
                historical_hosted_attribution="UNKNOWN", VP001="OPEN UNKNOWN")


def synthetic_sem_epoch(actor: int, suffix: str, *, retired: bool = False) -> list[dict]:
    """Known synthetic parser records only: no fixture/compiler/native calls."""
    reader, writer = "/MDBr" + suffix, "/MDBw" + suffix
    rows = []
    def add(event, name="", result=0, os_error=0):
        rows.append(dict(actor=actor, pid=100 + actor, event=event, name=name, result=result, os_error=os_error))
    add("namespace-safety-before-originals", "init")
    for part, name in (("reader", reader), ("writer", writer)):
        add("unlink-enter", name)
        add("init-" + part + "-unlink-return", name, -1, 2)
    add("reader-sem-create-return", reader); add("writer-sem-create-return", writer)
    add("mdb-env-open-return"); add("env-close-enter")
    add("reader-sem-close-return", reader); add("writer-sem-close-return", writer)
    add("namespace-safety-before-originals", "close")
    for part, name in (("reader", reader), ("writer", writer)):
        add("unlink-enter", name); add("close-" + part + "-unlink-return", name)
    add("env-close-return")
    if retired: add("owned-names-retired")
    return rows


@pytest.mark.parametrize("second_suffix", ("aaaaaaaaaa", "bbbbbbbbbb"))
def test_namespace_epochs_baseline_owns_each_epoch_not_hash_stability(second_suffix):
    a = synthetic_sem_epoch(1, "aaaaaaaaaa", retired=True)
    b = synthetic_sem_epoch(2, second_suffix)
    report = namespace_epochs(a, b, case="baseline", platform="darwin")
    assert len(report["epochs"]) == 2
    assert report["epochs"][0]["created_pair"] == report["epochs"][0]["closed_pair"]
    assert report["epochs"][1]["created_pair"] == report["epochs"][1]["closed_pair"]
    assert len(report["named_names"]) == (2 if second_suffix == "aaaaaaaaaa" else 4)


@pytest.mark.parametrize("mutation", ("unmatched-pair", "missing-retirement", "foreign-actor", "extra-unexplained-name", "missing-B-unlink"))
def test_namespace_epochs_reject_bad_ownership_retirement_and_unexplained_names(mutation):
    a = synthetic_sem_epoch(1, "aaaaaaaaaa", retired=True)
    b = synthetic_sem_epoch(2, "bbbbbbbbbb")
    if mutation == "unmatched-pair":
        next(x for x in b if x["event"] == "writer-sem-close-return")["name"] = "/MDBwcccccccccc"
    elif mutation == "missing-retirement":
        a = [x for x in a if x["event"] != "owned-names-retired"]
    elif mutation == "foreign-actor":
        b[0]["actor"] = 1
    elif mutation == "extra-unexplained-name":
        a.append(dict(actor=1, pid=101, event="unexplained-resource", name="/MDBrcccccccccc", result=0, os_error=0))
    else:
        b = [x for x in b if x["event"] != "close-reader-unlink-return"]
    with pytest.raises(AssertionError):
        namespace_epochs(a, b, case="baseline", platform="darwin")


@pytest.mark.parametrize("foreign_lookup", (False, True))
def test_namespace_epochs_interleaved_requires_exact_producing_pair(foreign_lookup):
    a = synthetic_sem_epoch(1, "aaaaaaaaaa", retired=True)
    b = [dict(actor=2, pid=102, event="reader-sem-open0-return",
              name="/MDBr" + ("bbbbbbbbbb" if foreign_lookup else "aaaaaaaaaa"), result=-1, os_error=2)]
    if foreign_lookup:
        with pytest.raises(AssertionError, match="exact producing epoch"):
            namespace_epochs(a, b, case="interleaved", platform="darwin")
    else:
        report = namespace_epochs(a, b, case="interleaved", platform="darwin")
        assert len(report["epochs"]) == 1 and len(report["named_names"]) == 2


@pytest.mark.parametrize("case", ("baseline", "interleaved"))
def test_actual_native_lifecycle(native_lifecycle_binary, tmp_path, case, record_testsuite_property):
    binary, provenance, session = native_lifecycle_binary
    assert not session["stopped"], "earlier diagnostic failure: STOP, no second control/retry"
    root = (tmp_path / ("native-lifecycle-" + case)).resolve()
    root.mkdir(); (root / "env").mkdir()
    try:
        pids = actors(binary, provenance, root, case)
        report = evidence(root, case, pids)
        (root / "evidence.json").write_text(json.dumps(report, indent=2))
    except BaseException:
        session["stopped"] = True
        raise
    finally:
        # Existing JUnit artifact, no workflow change: carry bounded full native
        # traces/actual stdout/stderr/owner receipts on pass OR failure. Original
        # disk bytes retained; over-cap content is explicitly NOT summarized green.
        payload = dict(root=str(root), provenance=provenance, files={})
        remaining = 512 * 1024
        for path in sorted(root.iterdir()):
            if path.suffix in (".json", ".jsonl", ".stdout", ".stderr") and path.is_file():
                try:
                    raw = bounded_bytes(path, min(65536, remaining))
                    remaining -= len(raw)
                    payload["files"][path.name] = raw.decode("utf8", "replace")
                except AssertionError:
                    payload["files"][path.name] = "OVER-CAP: original retained, NOT a mechanism pass"
        record_testsuite_property("native_lifecycle_" + case, json.dumps(payload))
