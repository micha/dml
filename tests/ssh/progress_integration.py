"""Mandatory installed foreground SSH progression, fresh clients and offline receive.

Explicit driver only, never pytest/default Docker startup. Remote gates are
controlled out of band; private safe-loss substitutions are labelled separately.
"""

from dataclasses import replace
import base64
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

import daggerml as d
from daggerml import exchange as ex, local, ssh, transfer

from integration import (
    NAME,
    ROOT,
    control,
    docker,
    typed,
    tree,
    scalar,
    stopped_writers,
)

COUNT = 0


def check(value):
    global COUNT
    assert value
    COUNT += 1


def fresh(script, *args):
    result = subprocess.run(
        [sys.executable, str(script), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=35,
        check=True,
    )
    return json.loads(result.stdout)


def gates(directory, reset=False):
    # Explicit fixture-owner Docker control, never runtime arbitrary commands/mounts.
    control(
        "from pathlib import Path;import os,sys;p=Path(sys.argv[1]);p.mkdir(exist_ok=True);os.chown(p,1000,1000);"
        "[(p/n).unlink(missing_ok=True) for n in ('initial-release','publication-release')] if sys.argv[2]=='reset' else None",
        directory,
        "reset" if reset else "keep",
    )


def release(directory, phase):
    control(
        "from pathlib import Path;import sys;(Path(sys.argv[1])/(sys.argv[2]+'-release')).touch()",
        directory,
        phase,
    )


def poll(script, saved, directory, phase):
    deadline = time.monotonic() + 30
    index = 0
    while time.monotonic() < deadline:
        packet = directory / (phase + "-" + str(index))
        got = fresh(script, "observe", saved, packet)
        if got["phase"] == phase:
            return packet, got
        if got["phase"] == "completion" and phase != "completion":
            # Retain actual selected diagnostic/history evidence; never guess gate expiry.
            raise RuntimeError("expected phase missed: " + json.dumps(got))
        index += 1
        time.sleep(0.05)
    raise RuntimeError("bounded progress observation exhausted")


def remote_typed(job, root):
    # Independent breadth-first public typed oracle in actual current remote runtime.
    code = (
        "import json,base64,sys,daggerml as d\n"
        + inspect.getsource(typed)
        + "\nrows=typed(sys.argv[1],(d.ObjectId.from_hex(sys.argv[2]),))\nprint(json.dumps([[k,str(o),base64.b64encode(v).decode()] for (k,o),v in rows.items()]))"
    )
    return {
        (k, d.ObjectId.from_hex(o)): base64.b64decode(v)
        for k, o, v in json.loads(control(code, job.workspace + "/worker.dml", root))
    }


def owned_packet(packet, expected, directory):
    received = ex.read_observation(packet, expected=expected)
    directory.mkdir()
    store = directory / "validation.dml"
    with d.Repository(store, create=True):
        pass
    bundle = (packet / "snapshot.bundle").read_bytes()
    imported = transfer.import_commit(store, bundle)
    check(imported.commit == received.commit)
    rows = {
        (row["kind"], d.ObjectId.from_hex(row["id"])): base64.b64decode(row["record"])
        for row in json.loads(bundle)["objects"]
    }
    check(typed(store, (received.commit,)) == rows)
    with d.Repository(store) as repo, repo.read() as tx:
        initial = tree(tx, received.pre_dispatch)
        base = tree(tx, expected.commit)
        check(tx.get_commit(received.pre_dispatch).parents == (expected.commit,))
        check(set(initial) - set(base) == {"attempt-" + received.attempt_id})
        check(all(initial[name] == value for name, value in base.items()))
        check(initial["request-" + received.request_id] == expected.request)
        check(
            tx.get_node(tx.lookup_node(received.initial_attempt, "request")).dag
            == expected.request
        )
        parents = tx.get_commit(received.commit).parents
        if received.phase == "initial":
            check(received.commit == received.pre_dispatch)
            check("status" not in tx.get_dag(received.initial_attempt).bindings)
        elif received.phase == "publication":
            check(parents == (received.pre_dispatch,))
            check(
                tree(tx, received.commit)["attempt-" + received.attempt_id]
                == received.initial_attempt
            )
        else:
            check(len(parents) == 2 and parents[0] == received.pre_dispatch)
            check(tx.get_commit(parents[1]).parents == (received.pre_dispatch,))
            initial_fields = tx.get_dag(received.initial_attempt).bindings
            final_fields = tx.get_dag(received.completion.final_attempt).bindings
            check(
                all(
                    final_fields[name] == value
                    for name, value in initial_fields.items()
                )
            )
    return received, rows


def wait_remote_private(job, phase):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        got = json.loads(
            control(
                "import json,sys;from pathlib import Path;p=Path(sys.argv[1])/'private-barrier';print(json.dumps(p.read_text() if p.exists() else None))",
                job.workspace,
            )
        )
        if got == phase:
            return
        time.sleep(0.05)
    raise RuntimeError("private safe barrier absent")


def private_launch(job, phase):
    original = ssh._argv

    def command(selected, action, budget):
        argv = original(selected, action, budget)
        argv[-1] = " ".join(
            shlex.quote(s)
            for s in (
                selected.remote.python,
                "/opt/fixture/private_loss.py",
                phase,
                selected.workspace,
            )
        )
        return argv

    try:
        ssh._argv = command
        return ssh.start_ssh_exchange(job, connect_timeout_ms=5000)
    finally:
        ssh._argv = original


def lost_observation(job, launch, packet):
    """PRIVATE truncated observe reply; never disconnect the execution connection."""
    original = ssh._argv

    def command(selected, action, budget):
        argv = original(selected, action, budget)
        argv[-1] = " ".join(
            shlex.quote(s)
            for s in (
                selected.remote.python,
                "/opt/fixture/private_loss.py",
                "observe",
                selected.workspace,
            )
        )
        return argv

    try:
        ssh._argv = command
        try:
            ssh.observe_ssh_exchange(job, packet=packet, timeout_ms=1500)
        except (ssh.SSHError, subprocess.TimeoutExpired):
            check(not packet.exists())
        else:
            raise AssertionError("truncated observation returned successfully")
    finally:
        ssh._argv = original
        try:
            control(
                "from pathlib import Path;import sys;(Path(sys.argv[1])/'private-release').touch()",
                job.workspace,
            )
        finally:
            deadline = time.monotonic() + 10
            while "private_loss.py" in docker("top", NAME, "-eo", "pid,ppid,args"):
                if time.monotonic() > deadline:
                    raise RuntimeError(
                        "private observe disposition blocker; fixture retained"
                    )
                time.sleep(0.05)
    check(launch.process.poll() is None and not launch._stdout.closed)


def finish_execution(launch, gate, offline, caller, original_error):
    """Try every owned cleanup independently; never kill a computational child."""
    errors = []
    for phase in ("initial", "publication"):
        try:
            release(gate, phase)
        except BaseException as error:
            errors.append(error)
    if launch is not None:
        try:
            launch.wait(timeout=180)  # unconditional, including already exited clients
        except ssh.SSHError as error:
            if original_error is not None and launch.process.poll() is not None:
                original_error.transport_cleanup_error = error
            else:
                errors.append(error)
        except BaseException as error:
            errors.append(error)
    try:
        offline.rename(caller)
    except BaseException as error:
        errors.append(error)
    try:
        stopped_writers()
    except BaseException as error:
        errors.append(error)
    if errors:
        blocker = RuntimeError(
            "fixture cleanup/disposition blocker; fixture/B/evidence retained"
        )
        blocker.launch = launch
        blocker.original_error = original_error
        blocker.cleanup_errors = tuple(errors)
        raise blocker from errors[0]


def parallel_readers(script, saved, trial, commit):
    readers = []
    try:
        for number in range(2):
            readers.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        str(script),
                        "observe",
                        str(saved),
                        str(trial / ("parallel-" + str(number))),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            )
        for reader in readers:
            out, err = reader.communicate(timeout=30)
            check(reader.returncode == 0 and json.loads(out)["commit"] == str(commit))
    finally:
        errors = []
        for reader in readers:
            try:
                # Every acquired observation client is communicated/reaped, even
                # after another client's check/communicate or later spawn failed.
                reader.communicate(timeout=35)
            except BaseException as error:
                errors.append(error)
        if errors:
            blocker = RuntimeError(
                "observation-client disposition blocker; evidence retained"
            )
            blocker.processes = tuple(readers)
            blocker.original_error = sys.exc_info()[1]
            raise blocker from errors[0]


def negative_history(caller, story, saved_jobs, packets, snapshots):
    """Full typed valid Q2 and expected-Cq/wrong-T->Q negative histories."""
    expected = ssh.load_ssh_exchange(saved_jobs[0]).expected
    before = (caller / "data.mdb").read_bytes()
    for offset, phase in enumerate(("initial", "publication", "completion")):
        swapped = story / ("wrong-q-" + phase)
        shutil.copytree(packets[3 + offset], swapped)
        other_expected = ssh.load_ssh_exchange(saved_jobs[3 + offset]).expected
        check(
            ex.read_observation(swapped, expected=other_expected)
            == snapshots[3 + offset]
        )
        shutil.copyfile(packets[offset] / "job.json", swapped / "job.json")
        receipt = json.loads((swapped / "observation.json").read_bytes())
        receipt.update(token=expected.token, commit=str(expected.commit))
        (swapped / "observation.json").write_text(json.dumps(receipt))
        for inspect_only in (True, False):
            try:
                if inspect_only:
                    ex.read_observation(swapped, expected=expected)
                else:
                    ex.receive_observation(
                        caller, packet=swapped, expected=expected, ref="wrong-q"
                    )
            except (ex.ExchangeError, d.DmlError):
                check((caller / "data.mdb").read_bytes() == before)
            else:
                raise AssertionError("other matching Q accepted")
    source = story / "wrong-association-source"
    with d.Repository(source, create=True):
        pass
    transfer.import_commit(source, (packets[2] / "snapshot.bundle").read_bytes())
    first = snapshots[2]
    with d.Repository(source) as repo, repo.write() as tx:
        other = local.put_local_request(
            tx,
            request_id="q-" + "e" * 32,
            intent_uri=expected.intent_uri,
            binding=expected.binding,
            inputs=expected.inputs,
        )
        initial = tx.get_dag(first.initial_attempt)
        fields = dict(initial.bindings)
        fields["request"] = tx.put_subdag(other)
        wrong_initial = tx.put_dag(root=initial.root, bindings=fields)
        entries = tree(tx, first.pre_dispatch)
        name = "attempt-" + first.attempt_id
        entries[name] = wrong_initial
        wrong_pre = tx.put_commit(tx.put_tree(entries), parents=(expected.commit,))
        check(entries["request-" + first.request_id] == expected.request)
        publication_name = "publication-" + first.attempt_id
        entries[publication_name] = tree(tx, first.commit)[publication_name]
        wrong_u = tx.put_commit(tx.put_tree(entries), parents=(wrong_pre,))
        final = tx.get_dag(first.completion.final_attempt)
        fields = dict(final.bindings)
        fields["request"] = tx.put_subdag(other)
        entries[name] = tx.put_dag(root=final.root, bindings=fields)
        wrong_f = tx.put_commit(tx.put_tree(entries), parents=(wrong_pre, wrong_u))
    for offset, (phase, root) in enumerate(
        zip(("initial", "publication", "completion"), (wrong_pre, wrong_u, wrong_f))
    ):
        packet = story / ("association-" + phase)
        shutil.copytree(packets[offset], packet)
        bundle = transfer.export_commit(source, commit=root)
        (packet / "snapshot.bundle").write_bytes(bundle)
        receipt = json.loads((packet / "observation.json").read_bytes())
        receipt.update(selected_commit=str(root), pre_dispatch=str(wrong_pre))
        (packet / "observation.json").write_text(json.dumps(receipt))
        validation = story / ("typed-association-" + phase)
        with d.Repository(validation, create=True):
            pass
        check(transfer.import_commit(validation, bundle).commit == root)
        check(typed(validation, (root,)) == typed(source, (root,)))
        for inspect_only in (True, False):
            try:
                if inspect_only:
                    ex.read_observation(packet, expected=expected)
                else:
                    ex.receive_observation(
                        caller,
                        packet=packet,
                        expected=expected,
                        ref="wrong-association",
                    )
            except ex.ExchangeError as error:
                check("initial attempt association" in str(error))
                check((caller / "data.mdb").read_bytes() == before)
            else:
                raise AssertionError("typed complete wrong T -> matching Q accepted")


def write_changed_hosts(path, port, public_key):
    """Fixture-only valid changed key, independently parsed/fingerprinted before SSH."""
    fields = Path(public_key).read_text().split()
    # Explicit UTF-8/LF bytes keep the fixture oracle independent of host text newline conversion.
    path.write_bytes(
        "[127.0.0.1]:{} {} {}\n".format(port, fields[0], fields[1]).encode("utf-8")
    )
    fingerprints = []
    for file in (public_key, path):
        output = subprocess.check_output(
            ["ssh-keygen", "-l", "-E", "sha256", "-f", str(file)], timeout=10
        ).decode("utf-8")
        fingerprints.append(output.split()[1])
    assert (
        fingerprints[0] == fingerprints[1]
    ), "changed known-host key fingerprint mismatch"
    return fingerprints[0]


def main(fixture, story):
    fixture, story = Path(fixture).resolve(), Path(story).resolve()
    story.mkdir()
    endpoint = ssh.SSHRemote(**json.loads((fixture / "endpoint.json").read_bytes()))
    check("PYTHONPATH" not in os.environ)
    meta = json.loads(docker("inspect", NAME))[0]
    check(meta["Mounts"] == [] and meta["HostConfig"]["NetworkMode"] == "host")
    check(meta["Config"]["Labels"]["dml.fixture"] == "iteration10")
    check(str(d.__file__).startswith(str(fixture / "context/rootfs/opt/dml/lib")))
    check(control("import sys;print(sys.executable)").strip() == endpoint.python)
    # Current installed source + native/executable provenance, not stale image names.
    package = Path(d.__file__).parent
    for name in (
        "__init__.py",
        "local.py",
        "transfer.py",
        "exchange.py",
        "exchange_worker.py",
        "ssh.py",
        "ssh_worker.py",
        "_core.pyi",
        "py.typed",
        "_bin/dml",
        Path(d._core.__file__).name,
    ):
        actual = base64.b64decode(
            control(
                "import base64,sys,daggerml;from pathlib import Path;print(base64.b64encode((Path(daggerml.__file__).parent/sys.argv[1]).read_bytes()).decode())",
                name,
            )
        )
        check(actual == (package / name).read_bytes())
        if name.endswith(".py"):
            check(actual == (ROOT / "python/daggerml/daggerml" / name).read_bytes())
    script = story / "ssh_progress.py"
    shutil.copyfile(ROOT / "examples/ssh_progress.py", script)
    shutil.copyfile(ROOT / "examples/local_add.py", story / "local_add.py")
    spec_module = importlib.util.spec_from_file_location("progress_example", script)
    example = importlib.util.module_from_spec(spec_module)
    spec_module.loader.exec_module(example)
    gate = "/work/gates-" + story.name
    gates(gate, reset=True)
    prepared = example.prepare(story / "application", endpoint, gate)
    application = story / "application"
    caller = application / "caller.dml"
    first_job = ssh.load_ssh_exchange(application / "saved")
    base = d.ObjectId.from_hex(prepared["base"])
    saved_jobs, packets, expected_rows, snapshots = [], [], [], []
    with d.Repository(caller) as repo, repo.read() as tx:
        sentinel = tx.get_ref("sentinel")
        unstarted = tx.get_ref("unstarted")
    old = typed(caller, (base, sentinel, unstarted))

    def prepare(selected, label):
        record = ex.record_exchange_request(
            caller,
            commit=selected,
            binding_name="binding",
            inputs_name="inputs",
            intent_uri="urn:example:add-i64",
            ref=label,
        )
        workspace = application / ("input-" + label)
        expected = ex.prepare_exchange(
            caller,
            commit=record.commit,
            request=record.request,
            binding_name="binding",
            inputs_name="inputs",
            intent_uri=record.intent_uri,
            worker_ref="work",
            workspace=workspace,
        )
        job = ssh.stage_ssh_exchange(
            endpoint,
            workspace=workspace,
            expected=expected,
            control=application / ("control-" + label),
            timeout_ms=20000,
        )
        saved = application / ("saved-" + label)
        ssh.save_ssh_exchange(saved, job)
        return job, saved, workspace

    # Three normal actual fixed installed execute/observe streams. Same C for first two.
    with d.Repository(caller) as repo, repo.write() as tx:
        selected = tree(tx, base)
        inputs = tx.get_dag(selected["inputs"])
        fields = dict(inputs.bindings)
        fields["fail"] = tx.put_literal(tx.put_datum(True))
        selected["inputs"] = tx.put_dag(root=inputs.root, bindings=fields)
        fail_base = tx.put_commit(tx.put_tree(selected), parents=(base,))
    normal = [
        (first_job, application / "saved", application / "input"),
        prepare(base, "submission-2"),
        prepare(fail_base, "submission-failure"),
    ]
    # A fresh bootstrap client exits before any execution/attempt exists.
    check(
        fresh(script, "observe", normal[0][1], story / "bootstrap")["phase"]
        == "bootstrap"
    )
    check(not (story / "bootstrap").exists())
    docker(
        "cp",
        str(ROOT / "tests/ssh/private_loss.py"),
        NAME + ":/opt/fixture/private_loss.py",
    )
    for index, (job, saved, workspace) in enumerate(normal):
        gates(gate, reset=True)
        trial = story / ("trial-" + str(index))
        trial.mkdir()
        check(
            json.loads(
                control(
                    "import sys,json;from pathlib import Path;print(json.dumps(sorted(p.name for p in Path(sys.argv[1]).iterdir())))",
                    job.workspace,
                )
            )
            == ["input.bundle", "job.json"]
        )
        caller.rename(application / "caller.offline")
        workspace.rename(workspace.with_name(workspace.name + ".offline"))
        launch = None
        try:
            launch = ssh.start_ssh_exchange(job, connect_timeout_ms=10000)
            for operation, kwargs in (
                (ssh.start_ssh_exchange, {"connect_timeout_ms": 1}),
                (ssh.execute_ssh_exchange, {"timeout_ms": 1}),
            ):
                try:
                    operation(job, **kwargs)
                except ssh.SSHError as error:
                    check("already dispatched" in str(error))
                else:
                    raise AssertionError("repeat dispatch accepted")
            previous = None
            for phase in ("initial", "publication", "completion"):
                if phase != "initial":
                    release(
                        gate, "initial" if phase == "publication" else "publication"
                    )
                packet, report = poll(script, saved, trial, phase)
                got, rows = owned_packet(packet, job.expected, trial / phase)
                check(rows == remote_typed(job, str(got.commit)))
                check(got.request == job.expected.request)
                check(got.lifecycle == ("done" if phase == "completion" else "working"))
                if previous is not None:
                    check(
                        (got.request_id, got.attempt_id, got.initial_attempt)
                        == (
                            previous.request_id,
                            previous.attempt_id,
                            previous.initial_attempt,
                        )
                    )
                if phase == "initial":
                    with pytest_timeout():
                        launch.wait(timeout=0.05)
                    check(launch.process.poll() is None and not launch._stdout.closed)
                    # Concurrent fresh clients use distinct packet paths, same gated P.
                    parallel_readers(script, saved, trial, got.commit)
                    if index == 0:
                        lost_observation(job, launch, trial / "lost-observation")
                        retried = ssh.observe_ssh_exchange(
                            job, packet=trial / "retried-observation", timeout_ms=20000
                        )
                        check(retried.snapshot == got)
                        control(
                            "from pathlib import Path;import sys;p=Path(sys.argv[1]);(p/'private-release').unlink();(p/'private-barrier').unlink()",
                            job.workspace,
                        )
                if phase == "publication":
                    check(
                        got.completion is None
                        and got.result is not None
                        and launch.process.poll() is None
                    )
                if phase == "completion":
                    check(got.completion.cleanup == "ok")
                    check(
                        got.completion.outcome
                        == ("failure" if index == 2 else "success")
                    )
                    if index == 2:
                        check(
                            got.completion.reason == "child-exit"
                            and got.completion.evidence is not None
                        )
                saved_jobs.append(saved)
                packets.append(packet)
                expected_rows.append(rows)
                snapshots.append(got)
                previous = got
            check(launch.wait(timeout=30) == 0)
            stopped_writers()
            # Read-only F discovery independent of original synchronous receipts/exports.
            control(
                "from pathlib import Path;import sys;p=Path(sys.argv[1]);(p/'completion.json').unlink();(p/'output.bundle').unlink()",
                job.workspace,
            )
            alternate = trial / "receiptless"
            check(
                fresh(script, "observe", saved, alternate)["commit"]
                == str(previous.commit)
            )
            for earlier in packets[-3:-1]:
                frozen = snapshots[-3] if earlier == packets[-3] else snapshots[-2]
                check(ex.read_observation(earlier, expected=job.expected) == frozen)
            # Actual independent remote one-shot execute guard; no local-marker dependence.
            repeated = subprocess.run(
                ssh._argv(job, "execute", 5000),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=10,
            )
            check(repeated.returncode == 1)
            check(remote_typed(job, str(previous.commit)) == expected_rows[-1])
        finally:
            finish_execution(
                launch, gate, application / "caller.offline", caller, sys.exc_info()[1]
            )
    check(snapshots[2].result == snapshots[5].result)
    check(
        snapshots[2].request_id != snapshots[5].request_id
        and snapshots[2].attempt_id != snapshots[5].attempt_id
    )

    # PRIVATE safe execution loss: before child spawn, after actual reaping/pre-F,
    # and after recorded F/files while foreground SSH owner is still held.
    docker(
        "cp",
        str(ROOT / "tests/ssh/private_loss.py"),
        NAME + ":/opt/fixture/private_loss.py",
    )
    for phase in ("pre-ready", "pre-child", "reaped-pre-f", "post-files"):
        job, saved, _ = prepare(base, "private-" + phase)
        gates(gate, reset=True)
        release(gate, "initial")
        release(gate, "publication")
        launch = private_launch(job, phase)
        try:
            wait_remote_private(job, phase)
            got_packet = story / ("safe-" + phase)
            got = ssh.observe_ssh_exchange(job, packet=got_packet, timeout_ms=20000)
            check(
                got.phase
                == (
                    "bootstrap"
                    if phase == "pre-ready"
                    else (
                        "initial"
                        if phase == "pre-child"
                        else "publication" if phase == "reaped-pre-f" else "completion"
                    )
                )
            )
            check(got.lifecycle == ("done" if phase == "post-files" else "working"))
            check(launch.process.poll() is None)
            with pytest_timeout():
                launch.wait(timeout=0.05)
        finally:
            try:
                control(
                    "from pathlib import Path;import sys;(Path(sys.argv[1])/'private-release').touch()",
                    job.workspace,
                )
            finally:
                try:
                    launch.wait(timeout=30)
                except ssh.SSHError as error:
                    check("status 75" in str(error))
                finally:
                    stopped_writers()
        retry = ssh.observe_ssh_exchange(
            job, packet=story / ("safe-retry-" + phase), timeout_ms=20000
        )
        check(retry.snapshot == got.snapshot)

    # Genuine unchanged production 4MiB+1 result; B records F, observe cannot claim done.
    with d.Repository(caller) as repo, repo.write() as tx:
        selected = tree(tx, base)
        selected["binding"] = local.put_local_binding(
            tx,
            source=b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.write() as t:
 n=t.put_literal(t.put_datum(b'x'*(4*1024*1024+1)))
 publish_result(t,c,t.put_dag(root=n))
""",
            interpreter=endpoint.python,
            timeout_ms=10000,
        )
        overflow_base = tx.put_commit(tx.put_tree(selected), parents=(base,))
    job, _, _ = prepare(overflow_base, "overflow")
    owner = ssh.start_ssh_exchange(job, connect_timeout_ms=10000)
    try:
        owner.wait(timeout=30)
    except ssh.SSHError:
        check(owner.process.poll() == 1)
    else:
        raise AssertionError("overflow execution export accepted")
    stopped_writers()
    check(
        control(
            "import sys,daggerml as d;from pathlib import Path;p=Path(sys.argv[1])/'worker.dml'\nwith d.Repository(p) as r,r.read() as t:\n c=t.get_ref('work');tree=t.get_tree(t.get_commit(c).tree);a=next(v for k,v in tree.items() if k.startswith('attempt-') and 'status' in t.get_dag(v).bindings);print(t.get_datum(t.get_node(t.lookup_node(a,'status')).datum).value)",
            job.workspace,
        ).strip()
        == "done"
    )
    try:
        ssh.observe_ssh_exchange(
            job, packet=story / "overflow-packet", timeout_ms=10000
        )
    except ssh.SSHError:
        check(not (story / "overflow-packet").exists())
    else:
        raise AssertionError("overflow observation returned done")

    # Actual asynchronous authentication/host-key rejection before computational dispatch.
    wrong_key = story / "wrong-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(wrong_key)],
        check=True,
        timeout=10,
    )
    unknown_hosts, changed_hosts = story / "unknown-hosts", story / "changed-hosts"
    unknown_hosts.write_text("")
    changed_fingerprint = write_changed_hosts(
        changed_hosts, endpoint.port, wrong_key.with_suffix(".pub")
    )
    for label, config in (
        ("unknown-key", replace(endpoint, known_hosts_file=unknown_hosts)),
        ("changed-key", replace(endpoint, known_hosts_file=changed_hosts)),
        ("wrong-auth", replace(endpoint, identity_file=wrong_key)),
    ):
        job, _, _ = prepare(base, label)
        selected = replace(job, remote=config)
        before = (caller / "data.mdb").read_bytes()
        owner = ssh.start_ssh_exchange(selected, connect_timeout_ms=5000)
        try:
            owner.wait(timeout=15)
        except ssh.SSHError as error:
            check("status 255" in str(error) and owner.process.poll() == 255)
            check(owner._stdout.closed)
            if label == "changed-key":
                diagnostic = next(job.control.glob("execute.stderr.*")).read_text()
                check("REMOTE HOST IDENTIFICATION HAS CHANGED" in diagnostic)
                check("Offending ED25519 key" in diagnostic)
                check(
                    changed_fingerprint
                    != subprocess.check_output(
                        [
                            "ssh-keygen",
                            "-l",
                            "-E",
                            "sha256",
                            "-f",
                            str(fixture / "credentials/host.pub"),
                        ],
                        timeout=10,
                    )
                    .decode("utf-8")
                    .split()[1]
                )
                print(
                    "genuine asynchronous changed-host-key rejection verified (parsed changed fingerprint/dedicated diagnostic)"
                )
        else:
            raise AssertionError("bad SSH identity accepted")
        check((job.control / "dispatched").exists())
        check((caller / "data.mdb").read_bytes() == before)
        check(
            control(
                "from pathlib import Path;import sys;print((Path(sys.argv[1])/'worker.dml').exists())",
                job.workspace,
            ).strip()
            == "False"
        )
    # Stop endpoint only with proven writers absent; retained B, then fresh installed receive.
    stopped_writers()
    docker("stop", "--timeout", "5", NAME)
    check(not json.loads(docker("inspect", NAME))[0]["State"]["Running"])
    with d.Repository(caller) as repo, repo.write() as tx:
        newer = tx.put_commit(
            tx.put_tree({"later": next(iter(tree(tx, base).values()))}),
            parents=(tx.get_ref("main"),),
        )
        tx.update_ref("main", newer)
    for index, (saved, packet, rows, snapshot) in enumerate(
        zip(saved_jobs, packets, expected_rows, snapshots)
    ):
        got = fresh(script, "receive", caller, saved, packet, "received-" + str(index))
        check(got["commit"] == str(snapshot.commit))
        check(typed(caller, (snapshot.commit,)) == rows)
        check(
            fresh(script, "receive", caller, saved, packet, "received-" + str(index))
            == got
        )
    with d.Repository(caller) as repo, repo.read() as tx:
        check(tx.get_ref("main") == newer and tx.get_ref("sentinel") == sentinel)
        check(tx.get_ref("unstarted") == unstarted)
        for saved in set(saved_jobs):
            expected = ssh.load_ssh_exchange(saved).expected
            qid = tx.get_datum(
                tx.get_node(tx.get_dag(expected.request).root).datum
            ).value
            check(tx.get_ref("request-" + qid) == expected.commit)
        for key, value in old.items():
            check(tx.get_record(*key) == value)
        for name in ("work", "attempt-" + snapshots[0].attempt_id):
            try:
                tx.get_ref(name)
            except d.NotFoundError:
                check(True)
            else:
                raise AssertionError("B ref copied")
    before = (caller / "data.mdb").read_bytes()
    try:
        ex.receive_observation(
            caller,
            packet=packets[2],
            expected=ssh.load_ssh_exchange(saved_jobs[0]).expected,
            ref="received-0",
        )
    except transfer.RefConflictError:
        check((caller / "data.mdb").read_bytes() == before)
    else:
        raise AssertionError("P ref implicitly advanced to F")
    negative_history(caller, story, saved_jobs, packets, snapshots)
    (story / "summary.json").write_text(
        json.dumps(
            {"checks": COUNT, "snapshots": [str(s.commit) for s in snapshots]}, indent=2
        )
    )
    print("installed asynchronous SSH checks:", COUNT)
    print("endpoint stopped/B retained; explicit owner retirement still required")


class pytest_timeout:
    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        if kind is not None and issubclass(kind, subprocess.TimeoutExpired):
            return True
        if kind is None:
            raise AssertionError("gated execution wait unexpectedly completed")


if __name__ == "__main__":
    main(*sys.argv[1:])
