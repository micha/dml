"""Actual-job/S3 loss and pin gates with EXPLICIT private response substitutions.

Not physical network/host-loss assurance or normal installed branch coverage.
No resubmit, cancellation, live-child kill or unknown-writer endpoint stop.
"""

import json
from pathlib import Path
import shutil
import sys
import time

import daggerml as d
from daggerml import exchange as ex, floci as f
from fixture import Fixture, PROVENANCE
import integration as normal
from retained_integration import prove_profile, wait_object, wait_phase, observe

LOST_ACK = r"""
import json,sys
from pathlib import Path
from daggerml import exchange as ex,floci as f,floci_http as h
remote=f.FlociRemote(**json.loads(sys.argv[1]));expected=ex.read_exchange_spec('/work/input')
staged=f.stage_floci_exchange(remote,workspace='/work/input',expected=expected,control='/tmp/control',timeout_ms=30000)
original=h.batch;count=0
def lost(remote,budget,action,body):
 global count
 value=original(remote,budget,action,body)
 if action=='SubmitJob':
  count+=1
  raise h.FlociError('private accepted-call acknowledgement suppression')
 return value
h.batch=lost
try:f.submit_floci_exchange(staged,timeout_ms=10000)
except h.FlociError as error:assert error.job_id is None
else:raise AssertionError('private lost acknowledgement not reported')
try:f.submit_floci_exchange(staged,timeout_ms=10000)
except h.FlociError:pass
else:raise AssertionError('repeat dispatch permitted')
assert count==1 and Path('/tmp/control/dispatched').exists() and not Path('/tmp/control/submitted.json').exists()
print(json.dumps({'lost_ack':True,'api_calls':count,'token':expected.token}))
"""
LOST_INPUT_BODY = r"""
import json,sys
from pathlib import Path
from daggerml import exchange as ex,floci as f,floci_http as h
remote=f.FlociRemote(**json.loads(sys.argv[1]));expected=ex.read_exchange_spec('/work/input')
original=h.request
def lost(*args,**kwargs):
 result=original(*args,**kwargs)
 if args[2]=='PUT' and args[3].endswith('/input/input.bundle') and result[0]==200:
  raise h.FlociError('private committed-input-body response suppression')
 return result
h.request=lost
try:f.stage_floci_exchange(remote,workspace='/work/input',expected=expected,control='/tmp/control',timeout_ms=30000)
except h.FlociError:pass
else:raise AssertionError('stage body loss not reported')
assert not Path('/tmp/control/staged.json').exists() and not Path('/tmp/control/dispatched').exists()
print(json.dumps({'body_before_manifest':True,'token':expected.token}))
"""
TRUNCATED_OBSERVE = r"""
import http.client,json
from pathlib import Path
from daggerml import floci as f
Original=http.client.HTTPConnection
class DroppedBody:
 def __init__(self,stream):self.stream=stream;self.sent=False
 def read1(self,n):
  if self.sent:return b''
  self.sent=True;return self.stream.read1(min(n,32))
 def flush(self):self.stream.flush()
 def close(self):self.stream.close()
class Connection(Original):
 def request(self,method,path,*a,**k):self.selected=path.endswith('/snapshot.bundle');return super().request(method,path,*a,**k)
 def getresponse(self):
  response=super().getresponse()
  if self.selected:response.fp.stream=DroppedBody(response.fp.stream)
  return response
http.client.HTTPConnection=Connection
job=f.load_floci_job('/work/saved')
try:f.observe_floci_job(job,packet='/tmp/packet',timeout_ms=10000)
except f.FlociError:pass
else:raise AssertionError('truncated actual S3 body accepted')
assert not Path('/tmp/packet').exists()
print(json.dumps({'private_body_suppression':True,'no_packet':True}))
"""
PIN_U = r"""
import json,time
from daggerml import floci as f,floci_http as h
job=f.load_floci_job('/work/saved');original=h.get_object;selected=False
def pin(remote,budget,token,key,bound):
 global selected
 data=original(remote,budget,token,key,bound)
 if key=='phases/publication.json' and data is not None and not selected:
  selected=True;h.put_object(remote,h.Budget(5000,1),token,'fixture/u-selected',b'selected')
  deadline=time.monotonic()+30
  while time.monotonic()<deadline:
   if original(remote,h.Budget(5000,1),token,'fixture/resume-observe',8192) is not None:break
   time.sleep(.1)
  else:raise TimeoutError('finite private observer selection barrier')
 return data
h.get_object=pin
got=f.observe_floci_job(job,packet='/tmp/packet',timeout_ms=30000)
assert selected and got.phase=='publication' and got.lifecycle=='working'
print(json.dumps({'pinned_phase':got.phase,'commit':str(got.snapshot.commit)}))
"""


def prepare(fixture, case, remote, gate):
    case.mkdir()
    artifacts = json.loads((fixture.root / "artifacts.json").read_bytes())
    caller, commit, sentinel = normal.basis(case, artifacts, gate)
    recorded = ex.record_exchange_request(
        caller,
        commit=commit,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:example:add",
        ref="submission",
    )
    expected = ex.prepare_exchange(
        caller,
        commit=recorded.commit,
        request=recorded.request,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri=recorded.intent_uri,
        worker_ref="work",
        workspace=case / "input",
    )
    return expected


def final_disposition(fixture, job):
    deadline = time.monotonic() + 60
    while fixture.children() and time.monotonic() < deadline:
        time.sleep(0.2)
    assert not fixture.children()
    row = fixture.batch("DescribeJobs", {"jobs": [job.job_id]})["jobs"][0]
    assert row["jobId"] == job.job_id and row["jobName"] == "dml-" + job.expected.token
    assert row["status"] in ("SUCCEEDED", "FAILED") and len(row["attempts"]) == 1
    return row


def loss_image(fixture):
    context = fixture.root / "loss-context"
    context.mkdir()
    for name in ("retain.py", "lost_manifest.py"):
        shutil.copyfile(Path(__file__).with_name(name), context / name)
    shutil.copyfile(
        Path(__file__).with_name("LostManifest.Dockerfile"), context / "Dockerfile"
    )
    base = "dml-floci-installed:" + fixture.root.name
    assert (
        json.loads(fixture.docker("image", "inspect", base))[0]["Id"]
        == fixture.state["image"]
    )
    tag = "dml-floci-manifest-loss:" + fixture.root.name
    fixture.docker(
        "build",
        "--network",
        "none",
        "--pull=false",
        "--build-arg",
        "BASE=" + base,
        "-t",
        tag,
        context,
        timeout=90,
    )
    image = json.loads(fixture.docker("image", "inspect", tag))[0]["Id"]
    (fixture.root / "loss-image.txt").write_text(image + "\n")
    provenance = fixture.client(
        PROVENANCE,
        copies=((fixture.root / "artifacts.json", "/work/artifacts.json"),),
        image=image,
    )
    (fixture.root / "loss-image-provenance.json").write_bytes(provenance)
    fixture.batch(
        "RegisterJobDefinition",
        dict(
            jobDefinitionName="loss",
            type="container",
            containerProperties=dict(
                image=image,
                command=["/opt/dml/bin/python", "-m", "daggerml.floci_worker"],
                resourceRequirements=[dict(type="MEMORY", value="512")],
            ),
            retryStrategy={"attempts": 1},
        ),
    )
    return image


def run(root, story):
    fixture = Fixture(root)
    assert fixture.state["stopped"]
    fixture.resume()
    prove_profile(fixture)
    story = Path(story).resolve()
    story.mkdir()
    remote = f.FlociRemote(
        "http://floci:4566",
        "dml-local",
        "iteration11/scope",
        "local",
        "installed:1",
        fixture.state["image"],
        "/opt/dml/bin/python",
    )
    gate = "loss-gates/" + fixture.state["owner"]
    rows = []
    current = None
    reader = None
    original_source = normal.CHILD
    normal.CHILD = normal.CHILD.replace(
        "wait('gate2')",
        "assert call('PUT','published',b'publication committed')[0]==200\nwait('gate2')",
    )
    try:
        # Real input bodies commit; private response loss leaves manifest absent/no job.
        expected = prepare(fixture, story / "body-before-manifest", remote, gate)
        result = json.loads(
            fixture.client(
                LOST_INPUT_BODY,
                arguments=(json.dumps(f._remote_document(remote)),),
                copies=((story / "body-before-manifest/input", "/work/input"),),
                outputs=(("/tmp/control", story / "body-before-manifest/control"),),
            )
        )
        assert (
            result["body_before_manifest"]
            and fixture.api(
                "GET",
                "/dml-local/"
                + remote.prefix
                + "/"
                + expected.token
                + "/input/manifest.json",
            )[0]
            == 404
        )
        assert (
            fixture.api(
                "GET",
                "/dml-local/"
                + remote.prefix
                + "/"
                + expected.token
                + "/input/input.bundle",
            )[0]
            == 200
        )
        assert not fixture.children()
        rows.append(dict(mode="input-body-before-manifest", token=expected.token))
        for mode in ("accepted-lost-ack", "committed-manifest-lost-response"):
            for key in ("gate1", "gate2", "started", "published"):
                assert fixture.api("DELETE", "/dml-local/" + gate + "/" + key)[0] in (
                    200,
                    204,
                )
            configured = remote
            if mode == "committed-manifest-lost-response":
                configured = f.FlociRemote(
                    remote.endpoint,
                    remote.bucket,
                    remote.prefix,
                    remote.queue,
                    "loss:1",
                    loss_image(fixture),
                    remote.python,
                )
            case = story / mode
            expected = prepare(fixture, case, configured, gate)
            intent = fixture.job_intent(
                expected.token, label="private-response-loss", mode=mode
            )
            code = LOST_ACK if mode == "accepted-lost-ack" else normal.CLIENT_SUBMIT
            outputs = (("/tmp/control", case / "control"),) + (
                () if mode == "accepted-lost-ack" else (("/tmp/saved", case / "saved"),)
            )
            result = json.loads(
                fixture.client(
                    code,
                    arguments=(json.dumps(f._remote_document(configured)),),
                    copies=((case / "input", "/work/input"),),
                    outputs=outputs,
                )
            )
            raw = wait_object(
                fixture,
                "/dml-local/"
                + configured.prefix
                + "/"
                + expected.token
                + "/phases/initial.json",
            )
            manifest = json.loads(raw)
            if mode == "accepted-lost-ack":
                assert result["lost_ack"] and result["api_calls"] == 1
                # Explicit OUT-OF-BAND investigation, not runtime ListJobs repair.
                children = fixture.children()
                assert len(children) == 1
                identifier = children[0]["Config"]["Labels"]["io.floci.resource-id"]
                assert identifier == manifest["job_id"]
                diagnostic = fixture.batch("DescribeJobs", {"jobs": [identifier]})[
                    "jobs"
                ][0]
                assert (
                    diagnostic["jobName"] == "dml-" + expected.token
                    and diagnostic["retryStrategy"]["attempts"] == 1
                )
                current = f.FlociJob(
                    configured, expected, Path("/tmp/control"), identifier
                )
                f.save_floci_job(case / "saved", current)
            else:
                current = f.load_floci_job(case / "saved")
                assert current.expected == expected
            intent["id"] = current.job_id
            fixture.save()
            p, pstatus = wait_phase(
                fixture, case / "saved", case / "initial", "initial"
            )
            assert pstatus["lifecycle"] == "working"
            assert (
                fixture.api("PUT", "/dml-local/" + gate + "/gate1", "released")[0]
                == 200
            )
            wait_object(fixture, "/dml-local/" + gate + "/published")
            if mode == "accepted-lost-ack":
                u, _ = wait_phase(
                    fixture, case / "saved", case / "publication", "publication"
                )
                # Actual S3 GET, privately cut body, no new packet/dispatch/B changes.
                truncated = json.loads(
                    fixture.client(
                        TRUNCATED_OBSERVE, copies=((case / "saved", "/work/saved"),)
                    )
                )
                assert truncated["no_packet"]
                fresh, _ = wait_phase(
                    fixture, case / "saved", case / "fresh-u", "publication"
                )
                assert (fresh / "snapshot.bundle").read_bytes() == (
                    u / "snapshot.bundle"
                ).read_bytes()
                reader = fixture.client(
                    PIN_U, copies=((case / "saved", "/work/saved"),), background=True
                )
                wait_object(
                    fixture,
                    "/dml-local/"
                    + configured.prefix
                    + "/"
                    + expected.token
                    + "/fixture/u-selected",
                )
            assert (
                fixture.api("PUT", "/dml-local/" + gate + "/gate2", "released")[0]
                == 200
            )
            final, fstatus = wait_phase(
                fixture, case / "saved", case / "completion", "completion"
            )
            assert fstatus["lifecycle"] == "done"
            if mode == "accepted-lost-ack":
                assert (
                    fixture.api(
                        "PUT",
                        "/dml-local/"
                        + configured.prefix
                        + "/"
                        + expected.token
                        + "/fixture/resume-observe",
                        "released",
                    )[0]
                    == 200
                )
                pinned = case / "pinned-u"
                pin = json.loads(
                    fixture.finish_client(reader, outputs=(("/tmp/packet", pinned),))
                )
                reader = None
                assert pin["pinned_phase"] == "publication"
                assert all(
                    (pinned / name).read_bytes() == (u / name).read_bytes()
                    for name in ("job.json", "observation.json", "snapshot.bundle")
                )
            else:
                marker = json.loads(
                    wait_object(
                        fixture,
                        "/dml-local/"
                        + configured.prefix
                        + "/"
                        + expected.token
                        + "/fixture/after-reap.json",
                    )
                )
                assert marker["worker_exit"] == 1 and marker["private_after_reap"]
                child = fixture.children()
                assert len(child) == 1
                fixture.docker(
                    "cp",
                    child[0]["Id"] + ":" + marker["workspace"] + "/worker.dml",
                    case / "actual-B",
                )
                got = ex.read_observation(final, expected=expected)
                validation = case / "validation"
                with d.Repository(validation, create=True):
                    pass
                transfer = __import__("daggerml.transfer", fromlist=["import_commit"])
                transfer.import_commit(
                    validation, (final / "snapshot.bundle").read_bytes()
                )
                assert normal.typed(validation, got.commit) == normal.typed(
                    case / "actual-B", got.commit
                )
                assert fstatus["status"] == "RUNNING"
                assert (
                    fixture.api(
                        "PUT",
                        "/dml-local/"
                        + configured.prefix
                        + "/"
                        + expected.token
                        + "/fixture/release",
                        "released",
                    )[0]
                    == 200
                )
            terminal = final_disposition(fixture, current)
            assert terminal["status"] == (
                "SUCCEEDED" if mode == "accepted-lost-ack" else "FAILED"
            )
            rows.append(
                dict(
                    mode=mode,
                    job_id=current.job_id,
                    token=expected.token,
                    p=str(p),
                    f=str(final),
                    terminal=terminal,
                )
            )
            current = None
    finally:
        normal.CHILD = original_source
        errors = []
        paths = ["/dml-local/" + gate + "/gate1", "/dml-local/" + gate + "/gate2"]
        if current is not None:
            paths += [
                "/dml-local/"
                + current.remote.prefix
                + "/"
                + current.expected.token
                + "/fixture/"
                + key
                for key in ("resume-observe", "release")
            ]
        for path in paths:
            try:
                assert fixture.api("PUT", path, "finally release")[0] == 200
            except BaseException as error:
                errors.append(error)
        if reader is not None:
            try:
                fixture.finish_client(reader)
            except BaseException as error:
                errors.append(error)
        deadline = time.monotonic() + 300
        while fixture.children() and time.monotonic() < deadline:
            time.sleep(1)
        fixture.clients_stopped()
        assert not fixture.children()
        if errors:
            raise RuntimeError(
                "private loss cleanup blocker; retain fixture"
            ) from errors[0]
    fixture.stop()
    (story / "summary.json").write_text(
        json.dumps(
            dict(
                actual_jobs=2,
                private_response_substitutions=True,
                rows=rows,
                endpoint_stopped=True,
            ),
            indent=2,
        )
    )
    print(
        json.dumps(dict(actual_jobs=2, loss_and_pin_gates=True, endpoint_stopped=True))
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]))
