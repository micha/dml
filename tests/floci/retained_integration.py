"""PRIVATE post-reap lifetime/evidence gate, distinct from normal installed jobs.

Fixture image ENTRYPOINT calls unchanged installed worker, then holds AFTER its return
for exact B copy/oracle/F-before-outer-status evidence. No live-child sacrifice/signals.
"""

import json
from pathlib import Path
import shutil
import sys
import time

import daggerml as d
from daggerml import exchange as ex, floci as f, local, transfer
from fixture import Fixture, PROVENANCE
import integration as normal


def prove_profile(fixture):
    old = fixture.state["profile"]["service"]
    current = fixture.inspect(fixture.state["service_id"])
    assert (
        current["Config"] == old["Config"]
        and current["HostConfig"] == old["HostConfig"]
    )
    network = json.loads(
        fixture.docker("network", "inspect", fixture.state["network"])
    )[0]
    assert network["Internal"] and not current["HostConfig"]["PortBindings"]
    logs = fixture.docker("logs", current["Id"]).decode()
    import re

    enabled = re.findall(r"Enabled services: \[([^\]]*)\]", logs)
    assert set(enabled[-1].split(", ")) == {"batch", "s3", "cloudwatchlogs", "iam"}
    bindings = fixture.docker(
        "exec",
        current["Id"],
        "cat",
        "/proc/net/tcp",
        "/proc/net/tcp6",
        "/proc/net/udp",
        "/proc/net/udp6",
    ).decode()
    assert not any(
        len(line.split()) > 3
        and ":" in line.split()[1]
        and line.split()[1].split(":")[-1] == "23D1"
        for line in bindings.splitlines()
    )
    assert len(fixture.state["profile"]["released_service_keys"]) == 128
    (fixture.root / "private-pre-submit-profile.json").write_text(
        json.dumps(
            dict(service=current, network=network, enabled=enabled[-1], no9169=True),
            indent=2,
        )
    )


def wait_object(fixture, path):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        status, body = fixture.api("GET", path)
        if status == 200:
            return body
        assert status == 404
        time.sleep(0.15)
    raise AssertionError("bounded private object wait expired")


def observe(fixture, saved, destination):
    result = json.loads(
        fixture.client(normal.CLIENT_OBSERVE, copies=((saved, "/work/saved"),))
    )
    if result["packet"]:
        client = fixture.state["clients"][-1]["id"]
        fixture.docker("cp", client + ":/tmp/packet", destination)
    return result


def wait_phase(fixture, saved, prefix, phase):
    for number in range(40):
        target = prefix.with_name(prefix.name + "-" + str(number))
        response = observe(fixture, saved, target)
        if response["phase"] == phase:
            return target, response
        time.sleep(0.15)
    raise AssertionError("bounded private phase wait expired")


def variant(fixture):
    context = fixture.root / "private-context"
    if context.exists():
        assert (context / "retain.py").read_bytes() == Path(__file__).with_name(
            "retain.py"
        ).read_bytes()
        image = (fixture.root / "private-image.txt").read_text().strip()
        fixture.docker("image", "inspect", image)
        return image
    context.mkdir()
    shutil.copyfile(Path(__file__).with_name("retain.py"), context / "retain.py")
    shutil.copyfile(
        Path(__file__).with_name("Retain.Dockerfile"), context / "Dockerfile"
    )
    base = "dml-floci-installed:" + fixture.root.name
    assert (
        json.loads(fixture.docker("image", "inspect", base))[0]["Id"]
        == fixture.state["image"]
    )
    tag = "dml-floci-retain:" + fixture.root.name
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
    (fixture.root / "private-image.txt").write_text(image + "\n")
    provenance = fixture.client(
        PROVENANCE,
        copies=((fixture.root / "artifacts.json", "/work/artifacts.json"),),
        image=image,
    )
    (fixture.root / "private-image-installed-provenance.json").write_bytes(provenance)
    return image


def run(root, story):
    fixture = Fixture(root)
    assert fixture.state["stopped"]
    fixture.resume()
    prove_profile(fixture)
    image = variant(fixture)
    revision = fixture.batch(
        "RegisterJobDefinition",
        dict(
            jobDefinitionName="installed",
            type="container",
            containerProperties=dict(
                image=image,
                command=["/opt/dml/bin/python", "-m", "daggerml.floci_worker"],
                resourceRequirements=[dict(type="MEMORY", value="512")],
            ),
            retryStrategy={"attempts": 1},
        ),
    )["revision"]
    assert type(revision) is int and revision >= 2
    remote = f.FlociRemote(
        "http://floci:4566",
        "dml-local",
        "iteration11/scope",
        "local",
        "installed:" + str(revision),
        image,
        "/opt/dml/bin/python",
    )
    story = Path(story).resolve()
    story.mkdir()
    artifacts = json.loads((fixture.root / "artifacts.json").read_bytes())
    original_source = normal.CHILD
    rows = []
    current_job = None
    gate = "private-gates/" + fixture.state["owner"]
    try:
        for mode in ("final-held", "cleanup-failed", "overflow"):
            assert not fixture.children()
            for key in ("gate1", "gate2", "started", "published"):
                assert fixture.api("DELETE", "/dml-local/" + gate + "/" + key)[0] in (
                    200,
                    204,
                )
            case = story / mode
            case.mkdir()
            source = original_source.replace(
                "wait('gate2')",
                "assert call('PUT','published',b'actual publication committed')[0]==200\nwait('gate2')",
            )
            if mode == "cleanup-failed":
                source = source.replace(
                    "print(json.dumps(identity))",
                    "locked=Path(c.scratch)/'locked'\nlocked.mkdir();(locked/'data').write_bytes(b'owned cleanup failure probe');locked.chmod(0)\nprint(json.dumps(identity))",
                )
            elif mode == "overflow":
                source = source.replace(
                    "t.put_dag(root=result,bindings={'result':result})",
                    "t.put_dag(root=result,bindings={'result':result,'large':t.put_literal(t.put_datum(b'x'*(4*1024*1024+1)))})",
                )
            normal.CHILD = source
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
            intent = fixture.job_intent(
                expected.token, label="private-after-reap-entrypoint", mode=mode
            )
            response = json.loads(
                fixture.client(
                    normal.CLIENT_SUBMIT,
                    arguments=(json.dumps(f._remote_document(remote)),),
                    copies=((case / "input", "/work/input"),),
                    outputs=(
                        ("/tmp/saved", case / "saved"),
                        ("/tmp/control", case / "control"),
                    ),
                )
            )
            current_job = f.load_floci_job(case / "saved")
            assert response["job_id"] == current_job.job_id
            intent["id"] = current_job.job_id
            fixture.save()
            initial, _ = wait_phase(
                fixture, case / "saved", case / "initial", "initial"
            )
            assert (
                fixture.api("PUT", "/dml-local/" + gate + "/gate1", "released")[0]
                == 200
            )
            wait_object(fixture, "/dml-local/" + gate + "/published")
            publication = None
            if mode != "overflow":
                publication, _ = wait_phase(
                    fixture, case / "saved", case / "publication", "publication"
                )
            assert (
                fixture.api("PUT", "/dml-local/" + gate + "/gate2", "released")[0]
                == 200
            )
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
                marker["job_id"] == current_job.job_id
                and marker["token"] == expected.token
                and marker["commit"] == str(expected.commit)
                and marker["private_after_reap"]
            )
            assert marker["worker_exit"] == (1 if mode == "overflow" else 0)
            children = fixture.children()
            assert (
                len(children) == 1
                and children[0]["Config"]["Labels"]["io.floci.resource-id"]
                == current_job.job_id
            )
            child = children[0]
            assert child["State"]["Running"] and child["Image"] == image
            assert (
                not child["Mounts"]
                and not child["HostConfig"]["PortBindings"]
                and not child["HostConfig"]["Privileged"]
            )
            assert child["HostConfig"]["Memory"] == 512 * 1024**2
            assert child["HostConfig"]["NanoCpus"] == 0 and child["HostConfig"][
                "PidsLimit"
            ] in (None, 0)
            assert (
                not child["HostConfig"]["CapDrop"]
                and not child["HostConfig"]["SecurityOpt"]
            )
            processes = json.loads(
                fixture.docker(
                    "exec",
                    child["Id"],
                    "/opt/dml/bin/python",
                    "-c",
                    "import json;from pathlib import Path;print(json.dumps([p.read_bytes().split(b'\\0')[1:-1][0:3] and p.read_bytes().decode(errors='replace') for p in Path('/proc').glob('[0-9]*/cmdline') if p.parent.name not in ('1',str(__import__('os').getpid()))]))",
                )
            )
            assert not any(
                "\x00daggerml.exchange_worker\x00" in row or "/entry.py\x00" in row
                for row in processes
                if isinstance(row, str)
            )
            final_packet = None
            if mode == "overflow":
                selected, status = wait_phase(
                    fixture, case / "saved", case / "unreturnable", "initial"
                )
                assert (
                    status["lifecycle"] == "working" and status["status"] == "RUNNING"
                )
                read_head = "import daggerml as d,sys;from pathlib import Path\nwith d.Repository(Path(sys.argv[1])/'worker.dml') as r,r.read() as t:print(str(t.get_ref('work')))"
                final = d.ObjectId.from_hex(
                    fixture.docker(
                        "exec",
                        child["Id"],
                        "/opt/dml/bin/python",
                        "-c",
                        read_head,
                        marker["workspace"],
                    )
                    .decode()
                    .strip()
                )
            else:
                final_packet, status = wait_phase(
                    fixture, case / "saved", case / "completion", "completion"
                )
                got = ex.read_observation(final_packet, expected=expected)
                assert got.lifecycle == "done" and status["status"] == "RUNNING"
                assert (
                    got.completion.outcome == "success"
                    and got.completion.cleanup
                    == ("failed" if mode == "cleanup-failed" else "ok")
                )
                final = got.commit
            raw_oracle = fixture.docker(
                "exec",
                child["Id"],
                "/opt/dml/bin/python",
                "-c",
                normal.oracle_script(),
                expected.token,
                str(final),
            )
            assert len(raw_oracle) <= 32 * 1024**2
            oracle = json.loads(raw_oracle)
            assert oracle["workspace"] == marker["workspace"]
            assert marker["workspace"].startswith("/tmp/dml-floci-execution-")
            # Copy ONLY exact known immutable repository after real reap. A
            # deliberate locked scratch/cleanup failure must not be permission-
            # edited or silently relabelled as a successful whole-workspace archive.
            fixture.docker(
                "cp",
                child["Id"] + ":" + marker["workspace"] + "/worker.dml",
                case / "actual-B-repository",
            )
            actual_b = case / "actual-B-repository"
            assert normal.typed(actual_b, final) == normal.native_rows(
                oracle["objects"]
            )
            if final_packet is not None:
                validation = case / "validation"
                with d.Repository(validation, create=True):
                    pass
                transfer.import_commit(
                    validation, (final_packet / "snapshot.bundle").read_bytes()
                )
                assert normal.typed(validation, final) == normal.typed(actual_b, final)
            else:
                with pytest_export_error():
                    transfer.export_commit(actual_b, commit=final)
                with d.Repository(actual_b) as repository, repository.read() as tx:
                    tree = tx.get_tree(tx.get_commit(final).tree)
                    attempt = tx.get_dag(
                        tree[
                            "attempt-"
                            + ex.read_observation(initial, expected=expected).attempt_id
                        ]
                    )
                    value = tx.get_datum(
                        tx.get_node(attempt.bindings["status"]).datum
                    ).value
                    assert (
                        value == "done"
                    ), "genuine recorded F precedes original production profile failure"
            (case / "after-reap.json").write_text(
                json.dumps(
                    dict(
                        marker=marker,
                        container=child,
                        stopped_computational_processes=processes,
                        objects=len(oracle["objects"]),
                        final_commit=str(final),
                    ),
                    indent=2,
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
            deadline = time.monotonic() + 60
            while fixture.children() and time.monotonic() < deadline:
                time.sleep(0.2)
            assert not fixture.children()
            terminal = fixture.batch("DescribeJobs", {"jobs": [current_job.job_id]})[
                "jobs"
            ][0]
            assert (
                terminal["status"] == "FAILED"
                and terminal["container"]["exitCode"] == 75
                and len(terminal["attempts"]) == 1
            )
            latest = case / "after-outer-failure"
            later = observe(fixture, case / "saved", latest)
            assert later["status"] == "FAILED" and later["lifecycle"] == (
                "working" if mode == "overflow" else "done"
            )
            rows.append(
                dict(
                    mode=mode,
                    job_id=current_job.job_id,
                    initial=str(initial),
                    publication=str(publication) if publication else None,
                    final_packet=str(final_packet) if final_packet else None,
                    final_commit=str(final),
                    actual_b=str(actual_b),
                    terminal=terminal,
                )
            )
            current_job = None
    finally:
        normal.CHILD = original_source
        errors = []
        for path in [
            "/dml-local/" + gate + "/gate1",
            "/dml-local/" + gate + "/gate2",
        ] + (
            [
                "/dml-local/"
                + remote.prefix
                + "/"
                + current_job.expected.token
                + "/fixture/release"
            ]
            if current_job is not None
            else []
        ):
            try:
                assert fixture.api("PUT", path, "finally release")[0] == 200
            except BaseException as error:
                errors.append(error)
        deadline = time.monotonic() + 300
        while fixture.children() and time.monotonic() < deadline:
            time.sleep(1)
        fixture.clients_stopped()
        assert not fixture.children(), "unknown writer; retain fixture"
        if errors:
            raise RuntimeError(
                "private gate cleanup blocker; retain fixture"
            ) from errors[0]
    fixture.stop()
    for row in rows:
        if row["final_packet"] is None:
            continue
        case = story / row["mode"]
        job = f.load_floci_job(case / "saved")
        for phase, packet in [
            ("initial", row["initial"]),
            ("publication", row["publication"]),
            ("completion", row["final_packet"]),
        ]:
            got = ex.receive_observation(
                case / "A.dml",
                packet=packet,
                expected=job.expected,
                ref="received-" + phase,
            )
            assert normal.typed(case / "A.dml", got.commit) == normal.typed(
                Path(row["actual_b"]), got.commit
            )
    (story / "summary.json").write_text(
        json.dumps(
            dict(
                private_after_reap=True,
                installed_package_bytes_unchanged=True,
                base_image=fixture.state["image"],
                private_image=image,
                rows=rows,
                endpoint_stopped=True,
            ),
            indent=2,
        )
    )
    print(
        json.dumps(
            dict(private_after_reap=True, cases=len(rows), endpoint_stopped=True)
        )
    )


class pytest_export_error:
    # Small standalone oracle, no pytest dependency in installed fixture clients.
    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        assert isinstance(error, transfer.TransferError) and "profile" in str(error)
        return True


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]))
