"""Actual bootstrap loss: explicit owned input corruption BEFORE computational launch.

Stage succeeds, controller deletes only this fresh token's input body, then submit
once. Installed worker refuses missing staged bytes; service FAILED is still unknown/
working bootstrap, never an invented computational attempt/outcome. No live-child kill.
"""

import json
from pathlib import Path
import sys
import time

from daggerml import floci as f
from fixture import Fixture
import integration as normal
from loss_integration import prepare, final_disposition
from retained_integration import prove_profile, wait_object, observe

CLIENT = r"""
import json,sys,time
from daggerml import exchange as ex,floci as f,floci_http as h
r=f.FlociRemote(**json.loads(sys.argv[1]));expected=ex.read_exchange_spec('/work/input')
staged=f.stage_floci_exchange(r,workspace='/work/input',expected=expected,control='/tmp/control',timeout_ms=30000)
h.put_object(r,h.Budget(5000,1),expected.token,'fixture/staged',b'closed input staged')
deadline=time.monotonic()+30
while time.monotonic()<deadline:
 if h.get_object(r,h.Budget(5000,1),expected.token,'fixture/submit',8192) is not None:break
 time.sleep(.1)
else:raise TimeoutError('finite private stage-before-submit barrier')
job=f.submit_floci_exchange(staged,timeout_ms=10000);f.save_floci_job('/tmp/saved',job)
print(json.dumps({'job_id':job.job_id,'token':expected.token}))
"""


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
    case = story / "bootstrap"
    gate = "bootstrap-gates/" + fixture.state["owner"]
    expected = prepare(fixture, case, remote, gate)
    intent = fixture.job_intent(
        expected.token, label="private-before-launch-input-loss"
    )
    reader = fixture.client(
        CLIENT,
        arguments=(json.dumps(f._remote_document(remote)),),
        copies=((case / "input", "/work/input"),),
        background=True,
    )
    prefix = "/dml-local/" + remote.prefix + "/" + expected.token + "/"
    try:
        wait_object(fixture, prefix + "fixture/staged")
        assert not fixture.children()  # Stage has not submitted/created any T.
        assert fixture.api("DELETE", prefix + "input/input.bundle")[0] in (200, 204)
        assert fixture.api("PUT", prefix + "fixture/submit", "released")[0] == 200
        result = json.loads(
            fixture.finish_client(
                reader,
                outputs=(
                    ("/tmp/saved", case / "saved"),
                    ("/tmp/control", case / "control"),
                ),
            )
        )
        reader = None
        job = f.load_floci_job(case / "saved")
        assert job.expected == expected and result["job_id"] == job.job_id
        intent["id"] = job.job_id
        fixture.save()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            detail = fixture.batch("DescribeJobs", {"jobs": [job.job_id]})["jobs"][0]
            if detail["status"] == "FAILED":
                break
            time.sleep(0.2)
        assert final_disposition(fixture, job)["status"] == "FAILED"
        response = observe(fixture, case / "saved", case / "no-packet")
        assert (
            response["status"] == "FAILED"
            and response["lifecycle"] == "working"
            and response["phase"] == "bootstrap"
            and not response["packet"]
        )
        assert not (case / "no-packet").exists()
        assert fixture.api("GET", "/dml-local/" + gate + "/started")[0] == 404
    finally:
        if reader is not None:
            assert (
                fixture.api("PUT", prefix + "fixture/submit", "finally release")[0]
                == 200
            )
            fixture.finish_client(reader)
        fixture.clients_stopped()
        assert not fixture.children()
    fixture.stop()
    (story / "summary.json").write_text(
        json.dumps(
            dict(
                actual_bootstrap_loss=True,
                job_id=job.job_id,
                request=str(expected.request),
                response=response,
                terminal=detail,
                endpoint_stopped=True,
            ),
            indent=2,
        )
    )
    print(
        json.dumps(
            dict(
                actual_bootstrap_loss=True,
                service_failed_not_done=True,
                endpoint_stopped=True,
            )
        )
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]))
