"""Finite endpoint-driven prepare/submit/fresh observe/offline receive modes.

Provisioning/declared S3 gate release is external application/fixture policy.
No Docker import, service polling loop, automatic resubmit or live caller owner.
"""

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path

import daggerml as d
from daggerml import exchange as ex, floci as f, local


def configuration(file):
    with open(file, "rb") as stream:
        data = stream.read(8193)
    if len(data) > 8192:
        raise ValueError("example operational configuration exceeds profile")
    return f.FlociRemote(**json.loads(data.decode("utf-8")))


def prepare(root, remote, *, source, gate, left=13, right=29, exit_code=0):
    gate = replace(remote, prefix=gate).prefix  # Same narrow normalized key profile.
    root = Path(root).resolve()
    root.mkdir()
    repository_path = root / "caller.dml"
    with d.Repository(
        repository_path, create=True
    ) as repository, repository.write() as tx:
        fields = {
            name: tx.put_literal(tx.put_datum(value))
            for name, value in dict(
                left=left,
                right=right,
                endpoint=remote.endpoint,
                bucket=remote.bucket,
                gate=gate,
                **{"exit-code": exit_code},
            ).items()
        }
        inputs = tx.put_dag(root=fields["left"], bindings=fields)
        binding = local.put_local_binding(
            tx,
            source=Path(source).read_bytes(),
            interpreter=remote.python,
            timeout_ms=360000,
        )
        commit = tx.put_commit(tx.put_tree({"binding": binding, "inputs": inputs}))
        tx.create_ref("main", commit)
        tx.create_ref("sentinel", commit)
    recorded = ex.record_exchange_request(
        repository_path,
        commit=commit,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:example:add-i64",
        ref="submission",
    )
    expected = ex.prepare_exchange(
        repository_path,
        commit=recorded.commit,
        request=recorded.request,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri=recorded.intent_uri,
        worker_ref="work",
        workspace=root / "input",
    )
    (root / "remote.json").write_text(json.dumps(asdict(remote)), encoding="utf-8")
    return expected


def submit(root, *, timeout_ms=30000):
    root = Path(root)
    remote = configuration(root / "remote.json")
    expected = ex.read_exchange_spec(root / "input")
    staged = f.stage_floci_exchange(
        remote,
        workspace=root / "input",
        expected=expected,
        control=root / "control",
        timeout_ms=timeout_ms,
    )
    job = f.submit_floci_exchange(staged, timeout_ms=timeout_ms)
    f.save_floci_job(root / "saved", job)
    return job


def observe(saved, packet, *, timeout_ms=10000):
    return f.observe_floci_job(
        f.load_floci_job(saved), packet=packet, timeout_ms=timeout_ms
    )


def receive(repository_path, saved, packet, ref):
    # Loading saved identity does not consult the offline endpoint/control/input/B.
    return ex.receive_observation(
        repository_path,
        packet=packet,
        expected=f.load_floci_job(saved).expected,
        ref=ref,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    prepared = commands.add_parser("prepare")
    prepared.add_argument("root", type=Path)
    prepared.add_argument("config", type=Path)
    prepared.add_argument("source", type=Path)
    prepared.add_argument("gate", help="declared S3 key prefix controlled out of band")
    prepared.add_argument("--exit-code", type=int, default=0)
    submitted = commands.add_parser("submit")
    submitted.add_argument("root", type=Path)
    observed = commands.add_parser("observe")
    observed.add_argument("saved", type=Path)
    observed.add_argument("packet", type=Path)
    received = commands.add_parser("receive")
    for name in ("repository", "saved", "packet"):
        received.add_argument(name, type=Path)
    received.add_argument("ref")
    args = parser.parse_args(argv)
    if args.mode == "prepare":
        expected = prepare(
            args.root,
            configuration(args.config),
            source=args.source,
            gate=args.gate,
            exit_code=args.exit_code,
        )
        report = dict(
            token=expected.token,
            commit=str(expected.commit),
            request=str(expected.request),
        )
    elif args.mode == "submit":
        job = submit(args.root)
        report = dict(job_id=job.job_id)
    elif args.mode == "observe":
        got = observe(args.saved, args.packet)
        report = dict(
            job_id=got.job_id,
            phase=got.phase,
            lifecycle=got.lifecycle,
            service_status=got.service_status,
        )
    else:
        got = receive(args.repository, args.saved, args.packet, args.ref)
        report = dict(
            commit=str(got.commit),
            ref=got.ref,
            phase=got.phase,
            lifecycle=got.lifecycle,
        )
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
