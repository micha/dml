"""Explicit mandatory local fixture gate; never collected/default-daemon-started by pytest.

Run using current installed host runtime, PYTHONPATH unset. Normal path uses the
installed fixed helper. Private loss substitutions are separately identified.
"""

from dataclasses import replace
import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

import daggerml as d
from daggerml import exchange as ex, local, ssh

ROOT = Path(__file__).resolve().parents[2]
NAME = "dml-iteration9-ssh"
COUNT = 0


def check(value):
    global COUNT
    assert value
    COUNT += 1


def docker(*args, timeout=20):
    return subprocess.check_output(
        ["docker", "--host", "unix:///var/run/docker.sock", *args], timeout=timeout
    ).decode("utf-8")


def control(code, *args):
    return docker("exec", NAME, "/opt/dml/bin/python", "-c", code, *map(str, args))


def tree(tx, oid):
    return dict(tx.get_tree(tx.get_commit(oid).tree))


def scalar(tx, dag, name):
    return tx.get_datum(tx.get_node(tx.lookup_node(dag, name)).datum).value


def typed(path, roots):
    # Independent breadth-first all-types/all-parents/all-packed-bytes oracle.
    result, pending = {}, [("commit", oid) for oid in roots]
    with d.Repository(path) as repo, repo.read() as tx:
        while pending:
            kind, oid = pending.pop(0)
            if (kind, oid) in result:
                continue
            result[kind, oid] = tx.get_record(kind, oid)
            if kind == "commit":
                obj = tx.get_commit(oid)
                pending += [("tree", obj.tree)] + [("commit", p) for p in obj.parents]
            elif kind == "tree":
                pending += [("dag", value) for value in tx.get_tree(oid).values()]
            elif kind == "dag":
                obj = tx.get_dag(oid)
                pending += [("node", obj.root)] + [
                    ("node", n) for n in obj.bindings.values()
                ]
            elif kind == "node":
                obj = tx.get_node(oid)
                pending += (
                    [("datum", obj.datum)]
                    if isinstance(obj, d.LiteralNode)
                    else [("dag", obj.dag)]
                )
            else:
                obj = tx.get_datum(oid)
                if obj.kind in ("list", "set"):
                    pending += [("datum", child) for child in obj.value]
                elif obj.kind == "map":
                    pending += [
                        ("datum", child) for pair in obj.value for child in pair
                    ]
    return result


def packet_rows(packet):
    return {
        (row["kind"], d.ObjectId.from_hex(row["id"])): base64.b64decode(row["record"])
        for row in json.loads((packet / "output.bundle").read_bytes())["objects"]
    }


def stopped_writers():
    output = docker("top", NAME, "-eo", "pid,ppid,args")
    check(
        "daggerml.ssh_worker" not in output
        and "private_loss.py" not in output
        and "entry.py" not in output
    )


def copied_worker(job, destination):
    stopped_writers()
    docker("cp", NAME + ":" + job.workspace + "/worker.dml", str(destination))
    return destination


def barrier_loss(job, phase):
    # Explicit PRIVATE remote command substitution, not normal helper coverage.
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

    ssh._argv = command
    status = None
    try:
        try:
            ssh._invoke(
                job,
                (
                    "stage"
                    if phase == "stage"
                    else "fetch" if phase == "fetch" else "execute"
                ),
                1500,
                (
                    (
                        (
                            job.control.parent
                            / ("input-" + job.expected.token)
                            / "job.json"
                        ).read_bytes(),
                        (
                            job.control.parent
                            / ("input-" + job.expected.token)
                            / "input.bundle"
                        ).read_bytes(),
                    )
                    if phase == "stage"
                    else ()
                ),
            )
        except (subprocess.TimeoutExpired, ssh.SSHError):
            pass
        else:
            raise AssertionError(
                "private response-loss barrier did not interrupt client"
            )
    finally:
        ssh._argv = original
        # On EVERY error path release cooperative gates before any fixture retirement.
        # Failure to release/prove disposition raises and leaves container/history retained.
        status = json.loads(
            control(
                "import json,sys;from pathlib import Path;p=Path(sys.argv[1]);"
                'print(json.dumps((p/"private-barrier").read_text() if (p/"private-barrier").exists() else None))',
                job.workspace,
            )
        )
        control(
            "from pathlib import Path;import sys;p=Path(sys.argv[1]);"
            '(p/"private-release").touch() if p.exists() else None',
            job.workspace,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            output = docker("top", NAME, "-eo", "pid,ppid,args")
            if "private_loss.py" not in output:
                break
            time.sleep(0.05)
        stopped_writers()
    check(status == phase)


def main(fixture, story):
    fixture, story = Path(fixture).resolve(), Path(story).resolve()
    story.mkdir()
    remote = ssh.SSHRemote(**json.loads((fixture / "endpoint.json").read_bytes()))
    inspect = json.loads(docker("inspect", NAME))[0]
    check(inspect["Mounts"] == [])
    check(inspect["HostConfig"]["NetworkMode"] == "host")
    check(inspect["Config"]["Labels"]["dml.fixture"] == "iteration9")
    check("PYTHONPATH" not in os.environ)
    # Independent installed remote module/core and loader identity, no checkout sys.path.
    provenance = json.loads(
        control(
            "import json,sys,daggerml,daggerml._core,daggerml.ssh_worker;"
            "print(json.dumps(dict(python=sys.executable,package=daggerml.__file__,core=daggerml._core.__file__,"
            "worker=daggerml.ssh_worker.__file__,path=sys.path)))"
        )
    )
    check(provenance["python"] == "/opt/dml/bin/python")
    for name in ("package", "core", "worker"):
        check(provenance[name].startswith("/opt/dml/lib/"))
    check(not any("/work/repos/" in p for p in provenance["path"]))
    for module in (
        "__init__.py",
        "local.py",
        "transfer.py",
        "exchange.py",
        "exchange_worker.py",
        "ssh.py",
        "ssh_worker.py",
    ):
        expected = (ROOT / "python/daggerml/daggerml" / module).read_bytes()
        actual = base64.b64decode(
            control(
                "import base64,daggerml,sys;from pathlib import Path;"
                "print(base64.b64encode(Path(daggerml.__file__).with_name(sys.argv[1]).read_bytes()).decode())",
                module,
            )
        )
        check(actual == expected)
    check(
        control(
            'import subprocess,sys;r=subprocess.run([sys.executable,"-m","daggerml_cli.main","--version"],check=True,capture_output=True,text=True);print(r.stdout.strip())'
        ).strip()
        == "0.1.0"
    )
    caller = story / "caller.dml"
    source = (ROOT / "examples/local_add.py").read_bytes()
    remote_source = (
        b"import sys,daggerml; assert sys.executable == '/opt/dml/bin/python'; "
        b"assert daggerml.__file__.startswith('/opt/dml/lib/'); "
        b"assert daggerml._core.__file__.startswith('/opt/dml/lib/'); "
        b"from pathlib import Path; "
        b"Path('/work/exchanges/child-starts').open('ab').write(b'1'); "
        b"print('installed-container-child-ok')\n"
    ) + source
    with d.Repository(caller, create=True) as repo, repo.write() as tx:
        nodes = {
            n: tx.put_literal(tx.put_datum(v)) for n, v in (("left", 4), ("right", 7))
        }
        inputs = tx.put_dag(root=nodes["left"], bindings=nodes)
        binding = local.put_local_binding(
            tx, source=remote_source, interpreter=remote.python, timeout_ms=10000
        )
        failed = local.put_local_binding(
            tx,
            source=remote_source + b"\nraise RuntimeError('after U')",
            interpreter=remote.python,
            timeout_ms=10000,
        )
        launch_failed = local.put_local_binding(
            tx, source=remote_source, interpreter="/absent/python", timeout_ms=1000
        )
        overflow = local.put_local_binding(
            tx,
            source=b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.write() as t:
 n=t.put_literal(t.put_datum(b'x'*(4*1024*1024+1)))
 publish_result(t,c,t.put_dag(root=n))
""",
            interpreter=remote.python,
            timeout_ms=10000,
        )
        warm_binding = local.put_local_binding(
            tx, source=source, interpreter=sys.executable, timeout_ms=10000
        )
        hidden = tx.put_datum("only in composites")
        keep = tx.put_dag(
            root=tx.put_literal(
                tx.put_datum(
                    d.Datum.map(
                        [
                            (
                                tx.put_datum(d.Datum.list([hidden, hidden])),
                                tx.put_datum(d.Datum.set([hidden])),
                            )
                        ]
                    )
                )
            )
        )
        base = tx.put_commit(
            tx.put_tree({"binding": binding, "inputs": inputs, "keep": keep})
        )
        sentinel = tx.put_commit(tx.put_tree({"sentinel": keep}))
        tx.create_ref("main", base)
        tx.create_ref("sentinel", sentinel)
    warm = local.run_step(
        caller,
        head_ref="main",
        intent_uri="urn:example:prior-add",
        binding=warm_binding,
        inputs=inputs,
        scratch_dir=story,
    )
    base = warm.final_commit
    bases = [base, base]
    with d.Repository(caller) as repo, repo.write() as tx:
        for selected in (failed, launch_failed, overflow):
            current = tree(tx, base)
            current["binding"] = selected
            bases.append(tx.put_commit(tx.put_tree(current), parents=(base,)))
    unused = ex.record_exchange_request(
        caller,
        commit=base,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:example:add-i64",
        ref="unstarted",
    )
    old = typed(caller, (base, sentinel, unused.commit))
    jobs, packets, outcomes = [], [], []

    def prepare(selected, label):
        recorded = ex.record_exchange_request(
            caller,
            commit=selected,
            binding_name="binding",
            inputs_name="inputs",
            intent_uri="urn:example:add-i64",
            ref=label,
        )
        temp = story / ("prepare-" + label)
        spec = ex.prepare_exchange(
            caller,
            commit=recorded.commit,
            request=recorded.request,
            binding_name="binding",
            inputs_name="inputs",
            intent_uri=recorded.intent_uri,
            worker_ref="work",
            workspace=temp,
        )
        workspace = story / ("input-" + spec.token)
        temp.rename(workspace)
        ex.save_exchange_handle(
            story / ("expected-" + spec.token + ".json"),
            ex.ExchangeHandle(workspace, spec),
        )
        return workspace, spec

    # Actual fixed installed helper, no fault substitution.
    for index, selected in enumerate(bases):
        workspace, spec = prepare(selected, "submission-" + str(index))
        job = ssh.stage_ssh_exchange(
            remote,
            workspace=workspace,
            expected=spec,
            control=story / ("control-" + spec.token),
            timeout_ms=15000,
        )
        check(
            json.loads(
                control(
                    "from pathlib import Path;import json,sys;print(json.dumps(sorted(p.name for p in Path(sys.argv[1]).iterdir())))",
                    job.workspace,
                )
            )
            == ["input.bundle", "job.json"]
        )
        check((caller / "data.mdb").exists())
        caller.rename(story / "caller.offline")
        workspace.rename(workspace.with_name(workspace.name + ".offline"))
        try:
            try:
                ssh.execute_ssh_exchange(job, timeout_ms=15000)
            except ssh.SSHError:
                check(
                    index == 4
                )  # Real unchanged production post-F >4MiB export failure.
            else:
                check(index != 4)
        finally:
            (story / "caller.offline").rename(caller)
        # Guard rejects before Popen (though it may allocate additional local streams).
        try:
            ssh.execute_ssh_exchange(job, timeout_ms=1000)
        except ssh.SSHError as error:
            check("already dispatched" in str(error))
        else:
            raise AssertionError("repeat execution accepted")
        # Guard rejects before Popen (though it may allocate additional local streams).
        check((job.control / "dispatched").exists())
        starts_before = control(
            'from pathlib import Path;p=Path("/work/exchanges/child-starts");print(p.stat().st_size if p.exists() else 0)'
        ).strip()
        repeated = subprocess.run(
            ssh._argv(job, "execute", 5000),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=5,
        )
        check(repeated.returncode == 1)
        check(
            control(
                'from pathlib import Path;p=Path("/work/exchanges/child-starts");print(p.stat().st_size if p.exists() else 0)'
            ).strip()
            == starts_before
        )
        worker_path = copied_worker(job, story / ("remote-worker-" + str(index)))
        with d.Repository(worker_path) as repo, repo.read() as tx:
            final = tx.get_ref("work")
            ft = tree(tx, final)
            attempt_names = [
                n
                for n in ft
                if n.startswith("attempt-") and n not in tree(tx, spec.commit)
            ]
            check(len(attempt_names) == 1)
            aid = attempt_names[0][8:]
            final_attempt = ft[attempt_names[0]]
            check(scalar(tx, final_attempt, "status") == "done")
            check(
                tx.get_node(tx.lookup_node(final_attempt, "request")).dag
                == spec.request
            )
            qid = tx.get_datum(tx.get_node(tx.get_dag(spec.request).root).datum).value
            check(tx.get_ref("request-" + qid) == spec.commit)
            pre = tx.get_commit(final).parents[0]
            check(tx.get_commit(pre).parents == (spec.commit,))
            check(set(tree(tx, pre)) - set(tree(tx, spec.commit)) == {attempt_names[0]})
        if index == 4:
            try:
                ssh.fetch_ssh_exchange(
                    job, packet=story / "overflow-packet", timeout_ms=5000
                )
            except ssh.SSHError:
                check(not (story / "overflow-packet").exists())
            else:
                raise AssertionError("overflow fabricated completion")
            check(
                json.loads(
                    control(
                        'from pathlib import Path;import sys,json;print(json.dumps((Path(sys.argv[1])/"completion.json").exists()))',
                        job.workspace,
                    )
                )
                is False
            )
            continue
        packet = ssh.fetch_ssh_exchange(
            job, packet=story / ("packet-" + str(index)), timeout_ms=15000
        )
        expected_rows = typed(worker_path, (final,))
        check(packet_rows(packet) == expected_rows)
        # Validate packet in independent public typed store without any computational dispatch.
        validation = story / ("packet-store-" + str(index))
        with d.Repository(validation, create=True):
            pass
        from daggerml.transfer import import_commit

        check(
            import_commit(validation, (packet / "output.bundle").read_bytes()).commit
            == final
        )
        check(typed(validation, (final,)) == expected_rows)
        jobs.append(job)
        packets.append(packet)
        outcomes.append((final, expected_rows))
    # Actual remote POSIX shell quoting: helper path and root contain quotes,
    # spaces, semicolons and command substitution; configured child stays /opt/dml.
    quoted_root = "/work/" + story.name + " space 'quoted'; $(touch /tmp/DML-INJECTED)"
    quoted_python = (
        "/opt/fixture/"
        + story.name
        + " space 'quoted'; $(touch /tmp/DML-INJECTED)/bin/python"
    )
    control(
        "from pathlib import Path;import os,sys;root,python=sys.argv[1:];"
        "Path(root).mkdir(parents=True);os.chown(root,1000,1000);"
        'link=Path(python).parent.parent;link.parent.mkdir(parents=True);os.symlink("/opt/dml",link)',
        quoted_root,
        quoted_python,
    )
    workspace, spec = prepare(base, "quoted-paths")
    quoted = replace(remote, python=quoted_python, workspace_root=quoted_root)
    job = ssh.stage_ssh_exchange(
        quoted,
        workspace=workspace,
        expected=spec,
        control=story / ("control-" + spec.token),
        timeout_ms=15000,
    )
    ssh.execute_ssh_exchange(job, timeout_ms=15000)
    packet = ssh.fetch_ssh_exchange(
        job, packet=story / "quoted-packet", timeout_ms=15000
    )
    check(
        json.loads(
            control(
                'from pathlib import Path;import json;print(json.dumps(Path("/tmp/DML-INJECTED").exists()))'
            )
        )
        is False
    )
    worker_path = copied_worker(job, story / "quoted-worker")
    final = d.ObjectId.from_hex(
        json.loads((packet / "completion.json").read_bytes())["final_commit"]
    )
    expected_rows = typed(worker_path, (final,))
    check(packet_rows(packet) == expected_rows)
    jobs.append(job)
    packets.append(packet)
    outcomes.append((final, expected_rows))
    # Strict actual unknown/changed host keys and wrong key authentication, finite.
    bad_key = story / "wrong-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(bad_key)],
        check=True,
        timeout=10,
    )
    empty_hosts = story / "unknown-hosts"
    empty_hosts.write_text("")
    changed_hosts = story / "changed-hosts"
    fields = bad_key.with_suffix(".pub").read_text().split()
    changed_hosts.write_text(
        "[127.0.0.1]:{} {} {}\n".format(remote.port, fields[0], fields[1])
    )
    for label, config in (
        ("unknown-key", replace(remote, known_hosts_file=empty_hosts)),
        ("changed-key", replace(remote, known_hosts_file=changed_hosts)),
        ("auth", replace(remote, identity_file=bad_key)),
    ):
        workspace, spec = prepare(base, label)
        job = ssh.SSHExchange(config, spec, story / ("control-" + spec.token))
        job.control.mkdir()
        before = (caller / "data.mdb").read_bytes()
        try:
            ssh.execute_ssh_exchange(job, timeout_ms=5000)
        except ssh.SSHError as error:
            check("status 255" in str(error))
        else:
            raise AssertionError("bad endpoint accepted")
        check((job.control / "dispatched").exists())
        check((caller / "data.mdb").read_bytes() == before)
        check(
            json.loads(
                control(
                    "from pathlib import Path;import json,sys;print(json.dumps(Path(sys.argv[1]).exists()))",
                    job.workspace,
                )
            )
            is False
        )
    # Private loss before spawn / after actual child reaping / after closed files / fetch / stage ack.
    docker(
        "cp",
        str(ROOT / "tests/ssh/private_loss.py"),
        NAME + ":/opt/fixture/private_loss.py",
    )
    for phase in ("stage", "pre-child", "reaped-pre-f", "post-files"):
        workspace, spec = prepare(base, "loss-" + phase)
        if phase == "stage":
            job = ssh.SSHExchange(remote, spec, story / ("control-" + spec.token))
            job.control.mkdir()
        else:
            job = ssh.stage_ssh_exchange(
                remote,
                workspace=workspace,
                expected=spec,
                control=story / ("control-" + spec.token),
                timeout_ms=15000,
            )
        barrier_loss(job, phase)
        names = json.loads(
            control(
                "from pathlib import Path;import json,sys;print(json.dumps(sorted(p.name for p in Path(sys.argv[1]).iterdir())))",
                job.workspace,
            )
        )
        if phase == "stage":
            check("worker.dml" not in names and "started" not in names)
            try:
                ssh.stage_ssh_exchange(
                    remote,
                    workspace=workspace,
                    expected=spec,
                    control=story / ("second-stage-" + spec.token),
                    timeout_ms=5000,
                )
            except ssh.SSHError:
                check(True)
            else:
                raise AssertionError("lost stage ack authorized overwrite")
        elif phase == "post-files":
            packet = ssh.fetch_ssh_exchange(
                job, packet=story / "loss-packet", timeout_ms=15000
            )
            check((packet / "completion.json").exists())
            # Fetch interruption is transport-only; release barrier then fresh fixed fetch same files.
            control(
                'from pathlib import Path;import sys;p=Path(sys.argv[1]);(p/"private-release").unlink();(p/"private-barrier").unlink()',
                job.workspace,
            )
            barrier_loss(job, "fetch")
            retry = ssh.fetch_ssh_exchange(
                job, packet=story / "loss-fetch-retry", timeout_ms=15000
            )
            for name in ("job.json", "completion.json", "output.bundle"):
                check((retry / name).read_bytes() == (packet / name).read_bytes())
        else:
            check("worker.dml" in names and "completion.json" not in names)
            copy = copied_worker(job, story / ("unknown-" + phase))
            with d.Repository(copy) as repo, repo.read() as tx:
                head = tx.get_ref("work")
                fresh = set(tree(tx, head)) - set(tree(tx, spec.commit))
                attempt = next(
                    tree(tx, head)[n] for n in fresh if n.startswith("attempt-")
                )
                check("status" not in tx.get_dag(attempt).bindings)
            before = names
            try:
                ssh.fetch_ssh_exchange(
                    job, packet=story / ("unknown-packet-" + phase), timeout_ms=5000
                )
            except ssh.SSHError:
                check(True)
            else:
                raise AssertionError("unknown fetch fabricated outcome")
            check(
                json.loads(
                    control(
                        "from pathlib import Path;import json,sys;print(json.dumps(sorted(p.name for p in Path(sys.argv[1]).iterdir())))",
                        job.workspace,
                    )
                )
                == before
            )
    # Retain B but make endpoint unavailable before fresh installed packet-only reception.
    stopped_writers()
    docker("stop", "--timeout", "5", NAME)
    check(json.loads(docker("inspect", NAME))[0]["State"]["Running"] is False)
    with d.Repository(caller) as repo, repo.write() as tx:
        newer = tx.put_commit(
            tx.put_tree({"later": keep}), parents=(tx.get_ref("main"),)
        )
        tx.update_ref("main", newer)
    received = []
    for index, (job, packet, (final, expected_rows)) in enumerate(
        zip(jobs, packets, outcomes)
    ):
        saved = story / ("expected-" + job.expected.token + ".json")
        code = """import json,sys,daggerml as d
from daggerml.exchange import load_exchange_handle,receive_exchange
path,packet,saved,ref=sys.argv[1:]
assert '/work/repos/micha/dml/python' not in d.__file__
expected=load_exchange_handle(saved).expected
r=receive_exchange(path,workspace=packet,expected=expected,ref=ref)
assert receive_exchange(path,workspace=packet,expected=expected,ref=ref)==r
print(json.dumps(dict(commit=str(r.commit),request=str(r.request),attempt=r.attempt_id,
 outcome=r.outcome,reason=r.reason,cleanup=r.cleanup,result=None if r.result is None else str(r.result),
 evidence=None if r.evidence is None else str(r.evidence))))
"""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                code,
                str(caller),
                str(packet),
                str(saved),
                "received-" + str(index),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        got = json.loads(result.stdout)
        check(
            got["commit"] == str(final) and got["request"] == str(job.expected.request)
        )
        check(typed(caller, (final,)) == expected_rows)
        check(got["cleanup"] == "ok")
        received.append(got)
    check(
        received[0]["result"] == received[1]["result"]
        and received[0]["attempt"] != received[1]["attempt"]
    )
    check(
        received[2]["outcome"] == "failure"
        and received[2]["reason"] == "child-exit"
        and received[2]["evidence"] == received[0]["result"]
    )
    check(received[3]["outcome"] == "failure" and received[3]["reason"] == "launch")
    with d.Repository(caller) as repo, repo.read() as tx:
        check(tx.get_ref("main") == newer and tx.get_ref("sentinel") == sentinel)
        for job in jobs:
            qid = tx.get_datum(
                tx.get_node(tx.get_dag(job.expected.request).root).datum
            ).value
            check(tx.get_ref("request-" + qid) == job.expected.commit)
        for key, value in old.items():
            check(tx.get_record(*key) == value)
        for ref in ("work", "attempt-" + received[0]["attempt"]):
            try:
                tx.get_ref(ref)
            except d.NotFoundError:
                check(True)
            else:
                raise AssertionError("B ref copied to A")
    # Already independently validated Q2 packet with rewritten receipt token/base cannot replace Q1.
    swapped = story / "wrong-q"
    shutil.copytree(packets[1], swapped)
    shutil.copyfile(packets[0] / "job.json", swapped / "job.json")
    receipt = json.loads((swapped / "completion.json").read_bytes())
    receipt.update(token=jobs[0].expected.token, commit=str(jobs[0].expected.commit))
    (swapped / "completion.json").write_text(json.dumps(receipt))
    before = (caller / "data.mdb").read_bytes()
    try:
        ex.receive_exchange(
            caller, workspace=swapped, expected=jobs[0].expected, ref="wrong-q"
        )
    except (ex.ExchangeError, d.DmlError):
        check((caller / "data.mdb").read_bytes() == before)
    else:
        raise AssertionError("wrong Q accepted")
    # Typed-complete expected-Cq P retaining expected Q, but T -> another matching Q.
    # Reject association, not merely missing-base/foreign-Cq. No code/path is executed.
    from daggerml import transfer

    worker_path = story / "remote-worker-0"
    original_receipt = json.loads((packets[0] / "completion.json").read_bytes())
    aid = original_receipt["attempt_id"]
    original_pre = d.ObjectId.from_hex(original_receipt["pre_dispatch"])
    with d.Repository(worker_path) as repo, repo.write() as tx:
        other = local.put_local_request(
            tx,
            request_id="q-" + "e" * 32,
            intent_uri=jobs[0].expected.intent_uri,
            binding=jobs[0].expected.binding,
            inputs=jobs[0].expected.inputs,
        )
        original_tree = tree(tx, original_pre)
        name = "attempt-" + aid
        initial = tx.get_dag(original_tree[name])
        fields = dict(initial.bindings)
        fields["request"] = tx.put_subdag(other)
        original_tree[name] = tx.put_dag(root=initial.root, bindings=fields)
        wrong_pre = tx.put_commit(
            tx.put_tree(original_tree), parents=(jobs[0].expected.commit,)
        )
        preserved_qid = tx.get_datum(
            tx.get_node(tx.get_dag(jobs[0].expected.request).root).datum
        ).value
        check(
            tree(tx, wrong_pre)["request-" + preserved_qid] == jobs[0].expected.request
        )
        original_final_tree = tree(tx, outcomes[0][0])
        publication_name = "publication-" + aid
        original_tree[publication_name] = original_final_tree[publication_name]
        wrong_u = tx.put_commit(tx.put_tree(original_tree), parents=(wrong_pre,))
        final_attempt = tx.get_dag(original_final_tree[name])
        fields = dict(final_attempt.bindings)
        fields["request"] = tx.put_subdag(other)
        original_tree[name] = tx.put_dag(root=final_attempt.root, bindings=fields)
        wrong_f = tx.put_commit(
            tx.put_tree(original_tree), parents=(wrong_pre, wrong_u)
        )
    association = story / "wrong-association"
    association.mkdir()
    shutil.copyfile(packets[0] / "job.json", association / "job.json")
    bundle = transfer.export_commit(worker_path, commit=wrong_f)
    (association / "output.bundle").write_bytes(bundle)
    original_receipt.update(final_commit=str(wrong_f), pre_dispatch=str(wrong_pre))
    (association / "completion.json").write_text(json.dumps(original_receipt))
    validation = story / "association-typed-store"
    with d.Repository(validation, create=True):
        pass
    check(transfer.import_commit(validation, bundle).commit == wrong_f)
    check(typed(validation, (wrong_f,)) == typed(worker_path, (wrong_f,)))
    before = (caller / "data.mdb").read_bytes()
    try:
        ex.receive_exchange(
            caller,
            workspace=association,
            expected=jobs[0].expected,
            ref="wrong-association",
        )
    except ex.ExchangeError as error:
        check("initial attempt association" in str(error))
        check((caller / "data.mdb").read_bytes() == before)
    else:
        raise AssertionError("complete wrong T -> Q association accepted")
    native = Path(d.__file__).with_name("_bin") / "dml"
    log = json.loads(
        subprocess.check_output(
            [
                str(native),
                "--json",
                "--repo",
                str(caller),
                "log",
                "--ref",
                "received-0",
            ],
            timeout=10,
        )
    )
    check(log["start"] == received[0]["commit"])
    (story / "provenance.json").write_text(json.dumps(provenance, indent=2))
    (story / "summary.json").write_text(
        json.dumps(dict(checks=COUNT, received=received), indent=2)
    )
    print("installed SSH fixture checks:", COUNT)
    print("endpoint stopped; B retained; explicit owner removal still required")


if __name__ == "__main__":
    main(*sys.argv[1:])
