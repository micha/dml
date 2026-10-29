"""Mandatory actual installed DML-in-Batch story; explicit owned fixture only.

Normal installed worker evidence here is separate from private owner/loss wrappers.
Run with current bare installed Python and PYTHONPATH unset, after fixture preflight.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import daggerml as d
from daggerml import exchange as ex, floci as f, local, transfer
from fixture import Fixture

CHILD = r"""
import hashlib,http.client,json,os,sys,time
from pathlib import Path
import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.read() as t:
 def scalar(name):return t.get_datum(t.get_node(t.lookup_node(c.inputs,name)).datum).value
 left,right=scalar('left'),scalar('right')
 endpoint,bucket,gate=scalar('endpoint'),scalar('bucket'),scalar('gate')
 artifacts=json.loads(scalar('artifacts'))
assert endpoint=='http://floci:4566', 'captured fixture endpoint must match actual fixed transport'
assert sys.executable=='/opt/dml/bin/python'
site=Path(d.__file__).resolve().parent.parent
assert '/python/daggerml/' not in str(site)
for row in artifacts:
 assert hashlib.sha256((site/row['file']).read_bytes()).hexdigest()==row['sha256']
def call(method,key,data=b''):
 conn=http.client.HTTPConnection('floci',4566,timeout=5)
 try:
  conn.request(method,'/'+bucket+'/'+gate+'/'+key,data,headers={'Connection':'close','Authorization':'AWS4-HMAC-SHA256 Credential=test/19700101/us-east-1/s3/aws4_request, SignedHeaders=host, Signature=00','X-Amz-Date':'19700101T000000Z'})
  response=conn.getresponse();body=response.read(8193);assert len(body)<=8192
  return response.status,body
 finally:conn.close()
def wait(key):
 deadline=time.monotonic()+120
 while time.monotonic()<deadline:
  status,_=call('GET',key)
  if status==200:return
  assert status==404
  time.sleep(.15)
 raise TimeoutError('finite declared S3 gate expired')
security={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if line.split(':',1)[0] in ('Uid','Gid','CapInh','CapPrm','CapEff','CapBnd','NoNewPrivs','Seccomp')}
identity=dict(job_id=os.environ['AWS_BATCH_JOB_ID'],attempt=os.environ['AWS_BATCH_JOB_ATTEMPT'],pid=os.getpid(),python=sys.executable,artifacts=artifacts,security=security)
assert call('PUT','started',json.dumps(identity).encode())[0]==200
wait('gate1')
with d.Repository(c.repository_path) as r,r.write() as t:
 result=t.put_literal(t.put_datum(left+right))
 publish_result(t,c,t.put_dag(root=result,bindings={'result':result}))
wait('gate2')
print(json.dumps(identity))
sys.exit(EXIT_CODE)
"""
CLIENT_SUBMIT = r"""
import json,sys
from pathlib import Path
from daggerml import exchange as ex,floci as f
remote=f.FlociRemote(**json.loads(sys.argv[1]))
expected=ex.read_exchange_spec('/work/input')
staged=f.stage_floci_exchange(remote,workspace='/work/input',expected=expected,control='/tmp/control',timeout_ms=30000)
job=f.submit_floci_exchange(staged,timeout_ms=10000)
f.save_floci_job('/tmp/saved',job)
try:f.submit_floci_exchange(staged,timeout_ms=10000)
except f.FlociError:pass
else:raise AssertionError('repeat submit permitted')
print(json.dumps(dict(job_id=job.job_id,token=job.expected.token,commit=str(job.expected.commit),request=str(job.expected.request))))
"""
CLIENT_OBSERVE = r"""
import json
from daggerml import floci as f
job=f.load_floci_job('/work/saved')
got=f.observe_floci_job(job,packet='/tmp/packet',timeout_ms=10000)
print(json.dumps(dict(phase=got.phase,lifecycle=got.lifecycle,job_id=got.job_id,status=got.service_status,packet=got.packet is not None)))
"""


def typed(path, root):
    found, pending = {}, [("commit", root)]
    with d.Repository(path) as repository, repository.read() as tx:
        while pending:
            kind, oid = pending.pop(0)
            if (kind, oid) in found:
                continue
            found[kind, oid] = tx.get_record(kind, oid)
            if kind == "commit":
                value = tx.get_commit(oid)
                pending += [("tree", value.tree)] + [
                    ("commit", p) for p in value.parents
                ]
            elif kind == "tree":
                pending += [("dag", v) for v in tx.get_tree(oid).values()]
            elif kind == "dag":
                value = tx.get_dag(oid)
                pending += [("node", value.root)] + [
                    ("node", n) for n in value.bindings.values()
                ]
            elif kind == "node":
                value = tx.get_node(oid)
                pending += (
                    [("datum", value.datum)]
                    if isinstance(value, d.LiteralNode)
                    else [("dag", value.dag)]
                )
            else:
                value = tx.get_datum(oid)
                if value.kind in ("list", "set"):
                    pending += [("datum", n) for n in value.value]
                elif value.kind == "map":
                    pending += [("datum", n) for pair in value.value for n in pair]
    return found


def native_rows(records):
    return {
        (row["kind"], d.ObjectId.from_hex(row["id"])): base64.b64decode(
            row["record"], validate=True
        )
        for row in records
    }


def oracle_script():
    # Same independent public BFS algorithm, not transfer's private traversal/codec.
    import inspect

    return (
        "import base64,json,sys\nfrom pathlib import Path\nimport daggerml as d\nfrom daggerml import exchange as ex\n"
        + inspect.getsource(typed)
        + r"""
paths=[path.parent for path in Path('/tmp').glob('dml-floci-execution-*/job.json') if ex.read_exchange_spec(path.parent).token==sys.argv[1]]
assert len(paths)==1
found=typed(paths[0]/'worker.dml',d.ObjectId.from_hex(sys.argv[2]))
print(json.dumps({'workspace':str(paths[0]),'objects':[dict(kind=kind,id=str(oid),record=base64.b64encode(data).decode()) for (kind,oid),data in found.items()]}))
"""
    )


def basis(story, artifacts, gate):
    caller = story / "A.dml"
    with d.Repository(caller, create=True) as repository, repository.write() as tx:

        def literal(value):
            return tx.put_literal(tx.put_datum(value))

        left, right = literal(13), literal(29)
        fields = dict(
            left=left,
            right=right,
            endpoint=literal("http://floci:4566"),
            bucket=literal("dml-local"),
            gate=literal(gate),
            artifacts=literal(json.dumps(artifacts).encode()),
        )
        inputs = tx.put_dag(root=left, bindings=fields)
        prior_source = b"import daggerml as d\nfrom daggerml.local import child_context,publish_result\nc=child_context()\nwith d.Repository(c.repository_path) as r,r.write() as t:\n n=t.put_literal(t.put_datum('genuine prior result'));publish_result(t,c,t.put_dag(root=n))\n"
        prior = local.put_local_binding(
            tx, source=prior_source, interpreter=sys.executable, timeout_ms=10000
        )
        binding = local.put_local_binding(
            tx,
            source=CHILD.replace("EXIT_CODE", "0").encode(),
            interpreter="/opt/dml/bin/python",
            timeout_ms=360000,
        )
        failing = local.put_local_binding(
            tx,
            source=CHILD.replace("EXIT_CODE", "23").encode(),
            interpreter="/opt/dml/bin/python",
            timeout_ms=360000,
        )
        key, value = tx.put_datum("composite-only-key"), tx.put_datum(
            b"composite-only-child"
        )
        composite = tx.put_datum(d.Datum.map([(key, value)]))
        nested = tx.put_datum(d.Datum.list([composite]))
        tree = tx.put_tree(
            dict(
                binding=binding,
                failing=failing,
                prior=prior,
                inputs=inputs,
                composite=tx.put_dag(root=tx.put_literal(nested)),
            )
        )
        commit = tx.put_commit(tree)
        sentinel = tx.put_commit(
            tx.put_tree(dict(sentinel=tx.put_dag(root=literal("independent branch"))))
        )
        tx.create_ref("main", commit)
        tx.create_ref("sentinel", sentinel)
    previous = local.run_step(
        caller,
        head_ref="main",
        intent_uri="urn:example:prior",
        binding=prior,
        inputs=inputs,
    )
    return caller, previous.final_commit, sentinel


def run(root, story):
    fixture = Fixture(root)
    assert (
        fixture.state["conditional_put_verified"] and fixture.state["profile"]["no9169"]
    )
    assert not fixture.children()
    story = Path(story).resolve()
    story.mkdir()
    artifacts = json.loads((fixture.root / "artifacts.json").read_bytes())
    site = Path(d.__file__).resolve().parent.parent
    for row in artifacts:
        assert (
            hashlib.sha256((site / row["file"]).read_bytes()).hexdigest()
            == row["sha256"]
        )
    gate = "gates/" + fixture.state["owner"]
    caller, commit, sentinel = basis(story, artifacts, gate)
    old = typed(caller, commit)
    old.update(typed(caller, sentinel))
    fixed_refs = dict(main=commit, sentinel=sentinel)
    never = ex.record_exchange_request(
        caller,
        commit=commit,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:example:add",
        ref="never-started",
    )
    fixed_refs.update(
        {never.ref: never.commit, "request-" + never.request_id: never.commit}
    )
    remote = f.FlociRemote(
        "http://floci:4566",
        "dml-local",
        "iteration11/scope",
        "local",
        "installed:1",
        fixture.state["image"],
        "/opt/dml/bin/python",
    )
    results = []
    try:
        for trial in range(3):
            assert not fixture.children()
            for key in ("gate1", "gate2", "started"):
                assert fixture.api("DELETE", "/dml-local/" + gate + "/" + key)[0] in (
                    200,
                    204,
                )
            recorded = ex.record_exchange_request(
                caller,
                commit=commit,
                binding_name="failing" if trial == 2 else "binding",
                inputs_name="inputs",
                intent_uri="urn:example:add",
                ref="submission-" + str(trial),
            )
            fixed_refs.update(
                {
                    recorded.ref: recorded.commit,
                    "request-" + recorded.request_id: recorded.commit,
                }
            )
            expected = ex.prepare_exchange(
                caller,
                commit=recorded.commit,
                request=recorded.request,
                binding_name=recorded.binding_name,
                inputs_name="inputs",
                intent_uri=recorded.intent_uri,
                worker_ref="work",
                workspace=story / ("input-" + str(trial)),
            )
            caller.rename(story / "A.offline")
            intent = fixture.job_intent(
                expected.token, label="normal-installed", trial=trial
            )
            submitted = json.loads(
                fixture.client(
                    CLIENT_SUBMIT,
                    arguments=(json.dumps(f._remote_document(remote)),),
                    copies=((story / ("input-" + str(trial)), "/work/input"),),
                    outputs=(
                        ("/tmp/saved", story / ("saved-" + str(trial))),
                        ("/tmp/control", story / ("control-" + str(trial))),
                    ),
                )
            )
            job = f.load_floci_job(story / ("saved-" + str(trial)))
            assert job.expected == expected and job.job_id == submitted["job_id"]
            intent["id"] = job.job_id
            fixture.save()
            (story / ("input-" + str(trial))).rename(
                story / ("input-" + str(trial) + ".offline")
            )
            # Submitter has exited and been inspected stopped BEFORE declared gate1 release.
            fixture.clients_stopped()
            packets = []
            child_id = None
            for phase in ("initial", "publication", "completion"):
                deadline = time.monotonic() + 60
                for poll in range(50):
                    destination = story / (str(trial) + "-" + phase + "-" + str(poll))
                    code = CLIENT_OBSERVE.replace(
                        "print(json.dumps", "print(json.dumps"
                    )
                    raw = json.loads(
                        fixture.client(
                            code,
                            copies=((story / ("saved-" + str(trial)), "/work/saved"),),
                        )
                    )
                    last_client = fixture.state["clients"][-1]["id"]
                    if raw["packet"]:
                        fixture.docker("cp", last_client + ":/tmp/packet", destination)
                    if raw["phase"] == phase:
                        break
                    assert (
                        time.monotonic() < deadline
                    ), "bounded external driver wait expired"
                    time.sleep(0.15)
                else:
                    raise AssertionError("phase not retrieved")
                inspected = ex.read_observation(destination, expected=expected)
                assert (
                    inspected.phase == phase and inspected.request == expected.request
                )
                validation = story / (destination.name + "-validation")
                with d.Repository(validation, create=True):
                    pass
                transfer.import_commit(
                    validation, (destination / "snapshot.bundle").read_bytes()
                )
                records = typed(validation, inspected.commit)
                rows = {
                    (row["kind"], d.ObjectId.from_hex(row["id"])): base64.b64decode(
                        row["record"], validate=True
                    )
                    for row in json.loads(
                        (destination / "snapshot.bundle").read_bytes()
                    )["objects"]
                }
                assert records == rows
                if phase != "completion":
                    children = fixture.children()
                    assert len(children) == 1
                    child = children[0]
                    assert (
                        child["Config"]["Labels"]["io.floci.resource-id"] == job.job_id
                    )
                    assert (
                        child["State"]["Running"]
                        and not child["Mounts"]
                        and not child["HostConfig"]["PortBindings"]
                        and not child["HostConfig"]["Privileged"]
                    )
                    assert (
                        child["Image"] == fixture.state["image"]
                        and child["Config"]["User"] == "1000:1000"
                    )
                    assert child["HostConfig"]["Memory"] == 512 * 1024**2
                    if child_id is not None:
                        assert child["Id"] == child_id
                    child_id = child["Id"]
                    oracle = json.loads(
                        fixture.docker(
                            "exec",
                            child_id,
                            "/opt/dml/bin/python",
                            "-c",
                            oracle_script(),
                            expected.token,
                            str(inspected.commit),
                        )
                    )
                    assert native_rows(oracle["objects"]) == records
                    (story / (destination.name + "-actual-B.json")).write_text(
                        json.dumps(oracle)
                    )
                    (story / (destination.name + "-container.json")).write_text(
                        json.dumps(child, indent=2)
                    )
                    assert raw["status"] == "RUNNING"
                packets.append(
                    dict(
                        phase=phase,
                        packet=str(destination),
                        commit=str(inspected.commit),
                        request_id=inspected.request_id,
                        attempt_id=inspected.attempt_id,
                        objects=len(records),
                    )
                )
                if phase == "initial":
                    assert inspected.lifecycle == "working"
                    assert (
                        fixture.api("PUT", "/dml-local/" + gate + "/gate1", "released")[
                            0
                        ]
                        == 200
                    )
                elif phase == "publication":
                    assert (
                        inspected.lifecycle == "working"
                        and inspected.result is not None
                    )
                    assert (
                        fixture.api("PUT", "/dml-local/" + gate + "/gate2", "released")[
                            0
                        ]
                        == 200
                    )
                else:
                    assert (
                        inspected.lifecycle == "done"
                        and inspected.completion.cleanup == "ok"
                    )
                    assert inspected.completion.outcome == (
                        "failure" if trial == 2 else "success"
                    )
                    assert inspected.completion.exit_code == (23 if trial == 2 else 0)
                    assert (
                        inspected.completion.evidence is not None
                        if trial == 2
                        else inspected.result is not None
                    )
            deadline = time.monotonic() + 60
            while fixture.children() and time.monotonic() < deadline:
                time.sleep(0.2)
            assert (
                not fixture.children()
            ), "terminal status is not writer disposition proof"
            final = fixture.batch("DescribeJobs", {"jobs": [job.job_id]})["jobs"][0]
            assert final["status"] == "SUCCEEDED" and len(final["attempts"]) == 1
            # Recorded computational failure23 still has normally successful adapter publication.
            identity_status, identity_raw = fixture.api(
                "GET", "/dml-local/" + gate + "/started"
            )
            assert identity_status == 200
            identity = json.loads(identity_raw)
            assert (
                identity["job_id"] == job.job_id
                and identity["attempt"] == "1"
                and identity["artifacts"] == artifacts
            )
            results.append(
                dict(
                    trial=trial,
                    job_id=job.job_id,
                    container_id=child_id,
                    packets=packets,
                    child_provenance=identity,
                    service_final=final,
                )
            )
            (story / "A.offline").rename(caller)
    finally:
        # Try every declared finite gate release; never kill/cancel a computational child.
        errors = []
        for key in ("gate1", "gate2"):
            try:
                assert (
                    fixture.api(
                        "PUT", "/dml-local/" + gate + "/" + key, "finally release"
                    )[0]
                    == 200
                )
            except BaseException as error:
                errors.append(error)
        if (story / "A.offline").exists():
            (story / "A.offline").rename(caller)
        deadline = time.monotonic() + 300
        while fixture.children() and time.monotonic() < deadline:
            time.sleep(1)
        fixture.clients_stopped()
        assert not fixture.children(), "unknown owned writer; retain fixture"
        if errors:
            raise RuntimeError(
                "gate release errors retained; fixture not stopped"
            ) from errors[0]
    assert results[0]["job_id"] != results[1]["job_id"]
    assert (
        results[0]["packets"][0]["request_id"] != results[1]["packets"][0]["request_id"]
    )
    assert (
        results[0]["packets"][0]["attempt_id"] != results[1]["packets"][0]["attempt_id"]
    )
    fixture.stop()
    with d.Repository(caller) as repository, repository.write() as tx:
        advanced = tx.put_commit(
            tx.put_tree(
                dict(
                    later=tx.put_dag(
                        root=tx.put_literal(tx.put_datum("independently advanced"))
                    )
                )
            ),
            parents=(commit,),
        )
        tx.update_ref("main", advanced)
    fixed_refs["main"] = advanced
    for result in results:
        job = f.load_floci_job(story / ("saved-" + str(result["trial"])))
        for row in result["packets"]:
            packet = Path(row["packet"])
            before = {
                name: (packet / name).read_bytes()
                for name in ("job.json", "snapshot.bundle", "observation.json")
            }
            ref = "return-" + str(result["trial"]) + "-" + row["phase"]
            got = ex.receive_observation(
                caller, packet=packet, expected=job.expected, ref=ref
            )
            assert (
                ex.receive_observation(
                    caller, packet=packet, expected=job.expected, ref=ref
                )
                == got
            )
            assert typed(caller, got.commit) == typed(
                story / (packet.name + "-validation"), got.commit
            )
            assert all(
                (packet / name).read_bytes() == data for name, data in before.items()
            )
            with d.Repository(caller) as repository, repository.read() as tx:
                assert all(
                    tx.get_ref(name) == target for name, target in fixed_refs.items()
                )
                assert all(
                    tx.get_record(kind, oid) == data
                    for (kind, oid), data in old.items()
                )
                for name in ("work", "attempt-" + got.attempt_id):
                    try:
                        tx.get_ref(name)
                    except d.NotFoundError:
                        pass
                    else:
                        raise AssertionError("copied B operational ref")
    success0 = ex.read_observation(
        results[0]["packets"][-1]["packet"],
        expected=f.load_floci_job(story / "saved-0").expected,
    )
    success1 = ex.read_observation(
        results[1]["packets"][-1]["packet"],
        expected=f.load_floci_job(story / "saved-1").expected,
    )
    assert success0.result == success1.result
    (story / "summary.json").write_text(
        json.dumps(
            dict(
                normal_installed=True,
                trials=results,
                image=fixture.state["image"],
                artifact_count=len(artifacts),
                never_started=str(never.request),
                endpoint_stopped=True,
            ),
            indent=2,
        )
    )
    print(
        json.dumps(
            dict(
                normal_installed=True,
                trials=len(results),
                phase_packets=9,
                artifact_count=len(artifacts),
                story=str(story),
            )
        )
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]))
