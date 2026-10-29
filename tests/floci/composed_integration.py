"""Actual current-installed two-step chain, explicit owned cached fixture ONLY.

Uses existing fixture ownership/profiles, public authoring/inspection, finite S3
inputs and fresh installed clients. Never default-collected or packaged.
"""

from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import daggerml as d
from daggerml import exchange as ex, floci as f, local, transfer
from fixture import Fixture, PROVENANCE
import integration as normal
from retained_integration import prove_profile, wait_object
from loss_integration import final_disposition

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "composed_app", ROOT / "examples/composed_execution.py"
)
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)


def setup(story, artifacts, gate):
    caller, prior, sentinel = normal.basis(story, artifacts, gate)
    with d.Repository(caller) as repo, repo.write() as tx:
        entries = dict(tx.get_tree(tx.get_commit(prior).tree))
        entries["add-binding"] = entries.pop("binding")
        entries["add-inputs"] = entries.pop("inputs")
        entries["failing-add-binding"] = entries.pop("failing")
        entries["double-binding"] = local.put_local_binding(
            tx,
            source=(ROOT / "examples/floci_double.py").read_bytes(),
            interpreter="/opt/dml/bin/python",
            timeout_ms=360000,
        )
        base = tx.put_commit(tx.put_tree(entries), parents=(prior,))
        tx.update_ref("main", base)
    return caller, base, sentinel


def request(caller, base, story, label, binding, inputs):
    recorded = ex.record_exchange_request(
        caller,
        commit=base,
        binding_name=binding,
        inputs_name=inputs,
        intent_uri=(
            "urn:example:double" if inputs == "double-inputs" else "urn:example:add"
        ),
        ref="submission-" + label,
    )
    expected = ex.prepare_exchange(
        caller,
        commit=recorded.commit,
        request=recorded.request,
        binding_name=binding,
        inputs_name=inputs,
        intent_uri=recorded.intent_uri,
        worker_ref="work",
        workspace=story / (label + "-input"),
    )
    return expected, recorded


def reset(fixture, gate):
    assert not fixture.children()
    fixture.jobs_terminal()
    fixture.clients_stopped()
    prove_profile(fixture)
    for key in ("gate1", "gate2", "started"):
        assert fixture.api("DELETE", "/dml-local/" + gate + "/" + key)[0] in (200, 204)


def computational_cmdlines(cmdlines):
    """Actual /proc NUL-delimited argv, never literal backslash escape matching."""
    return [
        row
        for row in cmdlines
        if "daggerml.exchange_worker" in row.split("\0")
        or any(arg.endswith("/entry.py") for arg in row.split("\0"))
    ]


def run_step(
    fixture, caller, story, label, expected, remote, gate, artifacts, *, retained=False
):
    reset(fixture, gate)
    input_path = story / (label + "-input")
    saved = story / (label + "-saved")
    offline = caller.with_name(caller.name + ".offline")
    caller.rename(offline)
    intent = fixture.job_intent(
        expected.token, label="iteration12-composed", step=label
    )
    packets = []
    child_id = None
    try:
        response = json.loads(
            fixture.client(
                normal.CLIENT_SUBMIT,
                arguments=(json.dumps(asdict(remote)),),
                copies=((input_path, "/work/input"),),
                outputs=(
                    ("/tmp/saved", saved),
                    ("/tmp/control", story / (label + "-control")),
                ),
            )
        )
        job = f.load_floci_job(saved)
        assert job.expected == expected and job.job_id == response["job_id"]
        intent["id"] = job.job_id
        fixture.save()
        input_path.rename(input_path.with_name(input_path.name + ".offline"))
        fixture.clients_stopped()  # Submitter EXITED before initial gate release.
        for phase in ("initial", "publication", "completion"):
            for poll in range(50):
                destination = story / (label + "-" + phase + "-" + str(poll))
                observed = json.loads(
                    fixture.client(
                        normal.CLIENT_OBSERVE, copies=((saved, "/work/saved"),)
                    )
                )
                if observed["packet"]:
                    fixture.docker(
                        "cp",
                        fixture.state["clients"][-1]["id"] + ":/tmp/packet",
                        destination,
                    )
                if observed["phase"] == phase:
                    break
                time.sleep(0.15)
            else:
                raise AssertionError("finite composed phase wait expired")
            got = ex.read_observation(destination, expected=expected)
            assert got.phase == phase and got.request == expected.request
            validation = story / (destination.name + "-validation")
            with d.Repository(validation, create=True):
                pass
            transfer.import_commit(
                validation, (destination / "snapshot.bundle").read_bytes()
            )
            records = normal.typed(validation, got.commit)
            assert records == normal.native_rows(
                json.loads((destination / "snapshot.bundle").read_bytes())["objects"]
            )
            if phase != "completion":
                children = fixture.children()
                assert len(children) == 1
                child = children[0]
                assert child["Config"]["Labels"]["io.floci.resource-id"] == job.job_id
                assert child["State"]["Running"] and child["Image"] == remote.image
                assert (
                    child["Config"]["User"] == "1000:1000"
                    and not child["Mounts"]
                    and not child["HostConfig"]["PortBindings"]
                )
                assert (
                    not child["HostConfig"]["Privileged"]
                    and child["HostConfig"]["Memory"] == 512 * 1024**2
                )
                if child_id:
                    assert child_id == child["Id"]
                child_id = child["Id"]
                oracle = json.loads(
                    fixture.docker(
                        "exec",
                        child_id,
                        "/opt/dml/bin/python",
                        "-c",
                        normal.oracle_script(),
                        expected.token,
                        str(got.commit),
                    )
                )
                assert normal.native_rows(oracle["objects"]) == records
                (story / (destination.name + "-actual-B.json")).write_text(
                    json.dumps(oracle)
                )
                (story / (destination.name + "-container.json")).write_text(
                    json.dumps(child)
                )
                # Public eligibility guard BEFORE any A open/authoring/Q/submit.
                if expected.inputs_name == "add-inputs":
                    jobs = len(fixture.state["jobs"])
                    before = (offline / "data.mdb").read_bytes()
                    try:
                        app.consumer_basis(
                            caller,
                            producer_packet=destination,
                            producer_expected=expected,
                            remote=remote,
                            gate="gates/not-launched",
                        )
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("P/U authorized consumer")
                    assert (offline / "data.mdb").read_bytes() == before and len(
                        fixture.state["jobs"]
                    ) == jobs
            if phase == "publication":
                assert got.lifecycle == "working" and got.result is not None
                with d.Repository(validation) as repo, repo.read() as tx:
                    assert app.i64_root(tx, got.result) == (
                        84 if expected.inputs_name == "double-inputs" else 42
                    )
            packets.append(
                dict(
                    phase=phase,
                    packet=str(destination),
                    commit=str(got.commit),
                    objects=len(records),
                    validation=str(validation),
                )
            )
            if phase != "completion":
                assert (
                    fixture.api(
                        "PUT",
                        "/dml-local/"
                        + gate
                        + "/"
                        + ("gate1" if phase == "initial" else "gate2"),
                        "released",
                    )[0]
                    == 200
                )
        if retained:
            marker = json.loads(
                wait_object(
                    fixture,
                    "/dml-local/"
                    + remote.prefix
                    + "/"
                    + expected.token
                    + "/fixture/after-reap.json",
                )
            )
            assert (
                marker["private_after_reap"]
                and marker["job_id"] == job.job_id
                and marker["worker_exit"] == 0
            )
            children = fixture.children()
            assert len(children) == 1 and children[0]["Id"] == child_id
            process_code = "import json,os;from pathlib import Path;print(json.dumps([p.read_bytes().decode(errors='replace') for p in Path('/proc').glob('[0-9]*/cmdline') if p.parent.name not in ('1',str(os.getpid()))]))"
            processes = json.loads(
                fixture.docker(
                    "exec", child_id, "/opt/dml/bin/python", "-c", process_code
                )
            )
            assert not computational_cmdlines(processes)
            final = got.commit
            oracle = json.loads(
                fixture.docker(
                    "exec",
                    child_id,
                    "/opt/dml/bin/python",
                    "-c",
                    normal.oracle_script(),
                    expected.token,
                    str(final),
                )
            )
            actual_b = story / (label + "-actual-final-B")
            fixture.docker(
                "cp", child_id + ":" + marker["workspace"] + "/worker.dml", actual_b
            )
            assert (
                normal.native_rows(oracle["objects"])
                == normal.typed(actual_b, final)
                == records
            )
            (story / (label + "-after-reap.json")).write_text(
                json.dumps(
                    dict(marker=marker, processes=processes, objects=oracle["objects"])
                )
            )
            assert (
                fixture.api(
                    "PUT",
                    "/dml-local/"
                    + remote.prefix
                    + "/"
                    + expected.token
                    + "/fixture/release",
                    "released",
                )[0]
                == 200
            )
        terminal = final_disposition(fixture, job)
        assert (
            terminal["status"] == ("FAILED" if retained else "SUCCEEDED")
            and terminal["retryStrategy"]["attempts"] == 1
        )
        if retained:
            assert terminal["container"]["exitCode"] == 75
        status, raw = fixture.api("GET", "/dml-local/" + gate + "/started")
        assert status == 200
        identity = json.loads(raw)
        assert (
            identity["job_id"] == job.job_id
            and identity["attempt"] == "1"
            and identity["artifacts"] == artifacts
        )
        if offline.exists():
            offline.rename(caller)
        for row in packets:
            got = ex.receive_observation(
                caller,
                packet=row["packet"],
                expected=expected,
                ref=label + "-" + row["phase"],
            )
            assert normal.typed(caller, got.commit) == normal.typed(
                Path(row["validation"]), got.commit
            )
        result = dict(
            label=label,
            job_id=job.job_id,
            container_id=child_id,
            packets=packets,
            identity=identity,
            terminal=terminal,
            saved=str(saved),
        )
        (story / (label + "-evidence.json")).write_text(json.dumps(result, indent=2))
        return result
    finally:
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
        if retained:
            try:
                assert (
                    fixture.api(
                        "PUT",
                        "/dml-local/"
                        + remote.prefix
                        + "/"
                        + expected.token
                        + "/fixture/release",
                        "finally release",
                    )[0]
                    == 200
                )
            except BaseException as error:
                errors.append(error)
        if offline.exists():
            offline.rename(caller)
        deadline = time.monotonic() + 300
        while fixture.children() and time.monotonic() < deadline:
            time.sleep(1)
        fixture.clients_stopped()
        assert not fixture.children(), "unknown writers; retain fixture"
        if errors:
            raise RuntimeError("composed gate disposition blocker") from errors[0]


def run(root, story):
    fixture = Fixture(root)
    assert not fixture.state["stopped"] and not fixture.children()
    story = Path(story).resolve()
    story.mkdir()
    artifacts = json.loads((fixture.root / "artifacts.json").read_bytes())
    site = Path(d.__file__).resolve().parent.parent
    for row in artifacts:
        assert (
            hashlib.sha256((site / row["file"]).read_bytes()).hexdigest()
            == row["sha256"]
        )
    remote = f.FlociRemote(
        "http://floci:4566",
        "dml-local",
        "iteration12/scope",
        "local",
        "installed:1",
        fixture.state["image"],
        "/opt/dml/bin/python",
    )
    gate = "composed-add/" + fixture.state["owner"]
    caller, base, sentinel = setup(story, artifacts, gate)
    old = normal.typed(caller, base)
    old.update(normal.typed(caller, sentinel))
    never = ex.record_exchange_request(
        caller,
        commit=base,
        binding_name="add-binding",
        inputs_name="add-inputs",
        intent_uri="urn:example:add",
        ref="never-started",
    )
    fixed = dict(
        main=base,
        sentinel=sentinel,
        **{never.ref: never.commit, "request-" + never.request_id: never.commit},
    )
    results = []
    for label in ("add-a", "add-b"):
        expected, recorded = request(
            caller, base, story, label, "add-binding", "add-inputs"
        )
        fixed.update(
            {
                recorded.ref: recorded.commit,
                "request-" + recorded.request_id: recorded.commit,
            }
        )
        results.append(
            run_step(fixture, caller, story, label, expected, remote, gate, artifacts)
        )
    jobs = [f.load_floci_job(row["saved"]) for row in results]
    assert (
        jobs[0].expected.intent_uri == jobs[1].expected.intent_uri == "urn:example:add"
    )
    assert (
        jobs[0].expected.binding == jobs[1].expected.binding
        and jobs[0].expected.inputs == jobs[1].expected.inputs
    )
    with d.Repository(caller) as repo, repo.read() as tx:
        assert (
            tx.get_commit(jobs[0].expected.commit).parents
            == tx.get_commit(jobs[1].expected.commit).parents
            == (base,)
        )
    assert (
        jobs[0].job_id != jobs[1].job_id
        and jobs[0].expected.request != jobs[1].expected.request
    )
    packets = [row["packets"][-1]["packet"] for row in results]
    first = [
        ex.read_observation(packet, expected=job.expected)
        for packet, job in zip(packets, jobs)
    ]
    assert (
        first[0].result == first[1].result
        and first[0].completion.final_attempt != first[1].completion.final_attempt
    )
    assert first[0].attempt_id != first[1].attempt_id
    with d.Repository(caller) as repo, repo.write() as tx:
        tx.create_ref("latest", first[1].commit)
    fixed["latest"] = first[1].commit
    double_gate = "composed-double/" + fixture.state["owner"]
    basis = app.consumer_basis(
        caller,
        producer_packet=packets[0],
        producer_expected=jobs[0].expected,
        remote=remote,
        gate=double_gate,
        artifacts=json.dumps(artifacts).encode(),
    )
    with d.Repository(caller) as repo, repo.write() as tx:
        fields = dict(tx.get_dag(basis.dag).bindings)
        fields["producer"] = tx.put_subdag(first[1].completion.final_attempt)
        alternate = tx.put_dag(root=fields["value"], bindings=fields)
        assert alternate != basis.dag
    expected, recorded = request(
        caller, basis.commit, story, "double", "double-binding", "double-inputs"
    )
    fixed.update(
        {
            recorded.ref: recorded.commit,
            "request-" + recorded.request_id: recorded.commit,
            "double-basis": basis.commit,
        }
    )
    # Cached PRIVATE wrapper only: current installed package unchanged, exact
    # wrapper bytes asserted BEFORE job definition/submit. No image build/pull.
    cached = ROOT / "build/iteration11-image2"
    private_image = (cached / "private-image.txt").read_text().strip()
    assert (cached / "private-context/retain.py").read_bytes() == Path(
        __file__
    ).with_name("retain.py").read_bytes()
    private_config = json.loads(fixture.docker("image", "inspect", private_image))[0]
    assert private_config["Config"]["Entrypoint"] == [
        "/opt/dml/bin/python",
        "/opt/fixture/retain.py",
    ]
    source_hash = hashlib.sha256(
        Path(__file__).with_name("retain.py").read_bytes()
    ).hexdigest()
    provenance = (
        PROVENANCE
        + "\nassert __import__('hashlib').sha256(Path('/opt/fixture/retain.py').read_bytes()).hexdigest()=="
        + repr(source_hash)
    )
    (fixture.root / "private-current-provenance.json").write_bytes(
        fixture.client(
            provenance,
            copies=((fixture.root / "artifacts.json", "/work/artifacts.json"),),
            image=private_image,
        )
    )
    revision = fixture.batch(
        "RegisterJobDefinition",
        dict(
            jobDefinitionName="retained",
            type="container",
            containerProperties=dict(
                image=private_image,
                command=["/opt/dml/bin/python", "-m", "daggerml.floci_worker"],
                resourceRequirements=[dict(type="MEMORY", value="512")],
            ),
            retryStrategy=dict(attempts=1),
        ),
    )["revision"]
    consumer_remote = f.FlociRemote(
        remote.endpoint,
        remote.bucket,
        remote.prefix,
        remote.queue,
        "retained:" + str(revision),
        private_image,
        remote.python,
    )
    results.append(
        run_step(
            fixture,
            caller,
            story,
            "double",
            expected,
            consumer_remote,
            double_gate,
            artifacts,
            retained=True,
        )
    )
    second_packet = results[-1]["packets"][-1]["packet"]
    second = ex.read_observation(second_packet, expected=expected)
    assert second.completion.outcome == "success"
    with d.Repository(caller) as repo, repo.read() as tx:
        app.input_association(tx, expected.inputs, first[0])
        assert app.i64_root(tx, second.result) == 84
    # Actual consumer failure after U84, separate A explicit branch on SAME Fa.
    failure_case = story / "consumer-failure"
    failure_case.mkdir()
    failure_a = failure_case / "A.dml"
    with d.Repository(failure_a, create=True):
        pass
    ex.receive_observation(
        failure_a, packet=packets[0], expected=jobs[0].expected, ref="add-completion"
    )
    failed_gate = "composed-failed-double/" + fixture.state["owner"]
    failed_basis = app.consumer_basis(
        failure_a,
        producer_packet=packets[0],
        producer_expected=jobs[0].expected,
        remote=remote,
        gate=failed_gate,
        exit_code=23,
        artifacts=json.dumps(artifacts).encode(),
    )
    failed_expected, _ = request(
        failure_a,
        failed_basis.commit,
        failure_case,
        "double-failure",
        "double-binding",
        "double-inputs",
    )
    failed_result = run_step(
        fixture,
        failure_a,
        failure_case,
        "double-failure",
        failed_expected,
        remote,
        failed_gate,
        artifacts,
    )
    failed_packet = failed_result["packets"][-1]["packet"]
    failed = ex.read_observation(failed_packet, expected=failed_expected)
    assert (
        failed.completion.outcome == "failure"
        and failed.completion.exit_code == 23
        and failed.completion.evidence is not None
    )
    try:
        app.experiment_summary(
            failure_a,
            producer_packet=packets[0],
            producer_expected=jobs[0].expected,
            consumer_packet=failed_packet,
            consumer_expected=failed_expected,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("consumer failure produced successful summary")
    producer_case = story / "producer-failure"
    producer_case.mkdir()
    producer_a, pbase, _ = setup(producer_case, artifacts, gate)
    failing_expected, _ = request(
        producer_a,
        pbase,
        producer_case,
        "add-failure",
        "failing-add-binding",
        "add-inputs",
    )
    failing_result = run_step(
        fixture,
        producer_a,
        producer_case,
        "add-failure",
        failing_expected,
        remote,
        gate,
        artifacts,
    )
    failing_packet = failing_result["packets"][-1]["packet"]
    failing = ex.read_observation(failing_packet, expected=failing_expected)
    assert (
        failing.completion.outcome == "failure"
        and failing.completion.exit_code == 23
        and failing.completion.evidence is not None
    )
    before = (producer_a / "data.mdb").read_bytes()
    job_count = len(fixture.state["jobs"])
    try:
        app.consumer_basis(
            producer_a,
            producer_packet=failing_packet,
            producer_expected=failing_expected,
            remote=remote,
            gate="gates/not-launched",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("failed producer authorized consumer")
    assert (producer_a / "data.mdb").read_bytes() == before and len(
        fixture.state["jobs"]
    ) == job_count
    fixture.stop()  # Full terminal-job/client/namespace proof + fresh service archive.
    # Endpoint/input unavailable; same-process installed receive never executes.
    # Fresh-process proof is the separate composed_offline.py gate.
    for row in results:
        job = f.load_floci_job(row["saved"])
        for phase in row["packets"]:
            got = ex.receive_observation(
                caller,
                packet=phase["packet"],
                expected=job.expected,
                ref=row["label"] + "-" + phase["phase"],
            )
            assert normal.typed(caller, got.commit) == normal.typed(
                Path(phase["validation"]), got.commit
            )
    authored = app.experiment_summary(
        caller,
        producer_packet=packets[0],
        producer_expected=jobs[0].expected,
        consumer_packet=second_packet,
        consumer_expected=expected,
    )
    with d.Repository(caller) as repo, repo.read() as tx:
        assert all(tx.get_ref(name) == oid for name, oid in fixed.items())
        assert all(tx.get_record(*key) == raw for key, raw in old.items())
        for row in results:
            got = ex.read_observation(
                row["packets"][-1]["packet"],
                expected=f.load_floci_job(row["saved"]).expected,
            )
            for name in ("work", "attempt-" + got.attempt_id):
                try:
                    tx.get_ref(name)
                except d.NotFoundError:
                    pass
                else:
                    raise AssertionError("copied operational ref")
    report = dict(
        actual_installed_chain=True,
        selected_producer=first[0].attempt_id,
        matching_result=str(first[0].result),
        distinct_witnesses=[str(v.completion.final_attempt) for v in first],
        consumer_inputs=str(expected.inputs),
        summary=str(authored.commit),
        trials=results,
        producer_failure=failing_result,
        consumer_failure=failed_result,
        endpoint_stopped=True,
    )
    (story / "summary.json").write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            dict(
                actual_installed_chain=True,
                jobs=5,
                packets=15,
                selected=first[0].attempt_id,
                summary=str(authored.commit),
            )
        )
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]))
