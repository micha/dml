"""Explicit Floci-only stage/one-shot submit/fresh bounded history observation.

Unsigned local prototype, not an AWS SDK adapter. Service status is diagnostic;
exchange owns exact-Q/history inspection and explicit-ref atomic reception.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import tempfile

from . import exchange
from . import floci_http as http
from .floci_http import FlociError

__all__ = [
    "FlociError",
    "FlociRemote",
    "StagedFlociExchange",
    "FlociJob",
    "FlociObservation",
    "stage_floci_exchange",
    "submit_floci_exchange",
    "save_floci_job",
    "load_floci_job",
    "observe_floci_job",
]

INPUT_FORMAT = "daggerml-floci-input-v1"
PHASE_FORMAT = "daggerml-floci-phase-v1"
SAVED_FORMAT = "daggerml-floci-job-v1"
STAGED_FORMAT = "daggerml-floci-staged-v1"


def _path(value):
    value = http.text(os.fsdecode(os.fspath(value)))
    return Path(os.path.abspath(value))


@dataclass(frozen=True)
class FlociRemote:
    endpoint: str
    bucket: str
    prefix: str
    queue: str
    job_definition: str
    image: str
    python: str

    def __post_init__(self):
        http.endpoint(self.endpoint)
        http.match(self.bucket, r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]")
        if ".." in self.bucket:
            raise FlociError("bucket spelling contains empty component")
        http.match(self.prefix, r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}")
        if any(part in ("", ".", "..") for part in self.prefix.split("/")):
            raise FlociError("prefix requires normalized nonempty segments")
        http.match(self.queue, r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
        http.match(
            self.job_definition, r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}:[1-9][0-9]{0,8}"
        )
        http.match(self.image, r"sha256:[0-9a-f]{64}")
        http.posix_path(self.python)


@dataclass(frozen=True)
class StagedFlociExchange:
    remote: FlociRemote
    expected: exchange.ExchangeSpec
    control: Path

    def __post_init__(self):
        if not isinstance(self.remote, FlociRemote):
            raise TypeError("remote requires FlociRemote")
        http.expected(self.expected)
        object.__setattr__(self, "control", _path(self.control))


@dataclass(frozen=True)
class FlociJob(StagedFlociExchange):
    job_id: str

    def __post_init__(self):
        super().__post_init__()
        http.job_id(self.job_id)


@dataclass(frozen=True)
class FlociObservation:
    observation: exchange.ExchangeObservation
    job_id: str
    service_status: str

    @property
    def lifecycle(self):
        return self.observation.lifecycle

    @property
    def phase(self):
        return self.observation.phase

    @property
    def packet(self):
        return self.observation.packet

    @property
    def snapshot(self):
        return self.observation.snapshot


def _remote_document(remote):
    return {name: getattr(remote, name) for name in http.REMOTE_FIELDS}


def _remote(value):
    if type(value) is not dict or set(value) != set(http.REMOTE_FIELDS):
        raise FlociError("unexpected Floci operational fields")
    return FlociRemote(**value)


def _metadata(job, label):
    value = {"format": label, "remote": _remote_document(job.remote)}
    if isinstance(job, FlociJob):
        value["job_id"] = job.job_id
    return http.encoded(value)


def _save(directory, job, label):
    data = _metadata(job, label)
    directory.mkdir()
    exchange.save_exchange_handle(
        directory / "expected.json", exchange.ExchangeHandle(job.control, job.expected)
    )
    with open(directory / "floci.json", "xb") as stream:
        stream.write(data)


def _load(directory, label):
    handle = exchange.load_exchange_handle(directory / "expected.json")
    value = http.document(
        http.read_file(directory / "floci.json", http.DESCRIPTOR_BYTES)
    )
    keys = ("remote", "job_id") if label == SAVED_FORMAT else ("remote",)
    http.fields(value, keys, label)
    remote = _remote(value["remote"])
    if label == SAVED_FORMAT:
        return FlociJob(remote, handle.expected, handle.workspace, value["job_id"])
    return StagedFlociExchange(remote, handle.expected, handle.workspace)


def save_floci_job(directory, job: FlociJob) -> None:
    """Exclusive saved identity only; no endpoint/input/control/B/A/process access."""
    if not isinstance(job, FlociJob):
        raise TypeError("job requires acknowledged FlociJob")
    _save(_path(directory), job, SAVED_FORMAT)


def load_floci_job(directory) -> FlociJob:
    """Load inert independent expected+acknowledged ID; never dispatch/signal."""
    return _load(_path(directory), SAVED_FORMAT)


def _input_manifest(expected, files):
    return http.encoded(
        dict(
            format=INPUT_FORMAT,
            token=expected.token,
            commit=str(expected.commit),
            request=str(expected.request),
            files=http.file_rows(files),
        )
    )


def _read_input_manifest(data, token, commit, request=None):
    value = http.fields(
        http.document(data), ("token", "commit", "request", "files"), INPUT_FORMAT
    )
    if http.hex_id(value["token"]) != token or http.hex_id(value["commit"]) != commit:
        raise FlociError("input manifest selection mismatch")
    if request is not None and value["request"] != request:
        raise FlociError("input manifest exact Q mismatch")
    http.hex_id(value["request"])
    http.validate_rows(value["files"], http.INPUT_FILES)
    return value


def stage_floci_exchange(
    remote: FlociRemote, *, workspace, expected, control, timeout_ms: int
) -> StagedFlociExchange:
    """Stage exact closed caller-Q bytes, manifest last; no submit/Q/T/A writes."""
    budget = http.Budget(timeout_ms, 3)
    staged = StagedFlociExchange(remote, expected, control)
    workspace = _path(workspace)
    files = tuple(
        (name, http.read_file(workspace / name, http.limit(name)))
        for name in http.INPUT_FILES
    )
    if http.owned_spec(files[0][1]) != expected:
        raise FlociError("staged job differs from independent expected")
    manifest = _input_manifest(expected, files)
    staged.control.mkdir()
    _save(staged.control / "identity", staged, STAGED_FORMAT)
    for name, data in files:
        http.put_object(remote, budget, expected.token, "input/" + name, data)
    http.put_object(remote, budget, expected.token, "input/manifest.json", manifest)
    with open(staged.control / "staged.json", "xb") as stream:
        stream.write(manifest)
    return staged


def _command(remote, token, commit):
    return [
        remote.python,
        "-m",
        "daggerml.floci_worker",
        http.encoded(_remote_document(remote)).decode("utf-8"),
        token,
        commit,
    ]


def _preflight(remote, budget):
    value = http.batch(
        remote,
        budget,
        "DescribeJobDefinitions",
        {"jobDefinitions": [remote.job_definition]},
    )
    if (
        type(value) is not dict
        or set(value) != {"jobDefinitions"}
        or type(value["jobDefinitions"]) is not list
        or len(value["jobDefinitions"]) != 1
    ):
        raise FlociError("exact job-definition revision unavailable")
    definition = value["jobDefinitions"][0]
    name, revision = remote.job_definition.split(":")
    if type(definition) is not dict:
        raise FlociError("invalid job-definition description")
    container = definition.get("containerProperties")
    retry = definition.get("retryStrategy")
    if (
        definition.get("jobDefinitionName") != name
        or type(definition.get("revision")) is not int
        or definition["revision"] != int(revision)
        or definition.get("status") != "ACTIVE"
        or definition.get("type") != "container"
        or definition.get("nodeProperties") is not None
        or definition.get("parameters")
        or definition.get("timeout") is not None
        or type(container) is not dict
        or container.get("image") != remote.image
        or container.get("command") != [remote.python, "-m", "daggerml.floci_worker"]
        or container.get("environment") not in (None, [])
        or type(retry) is not dict
        or type(retry.get("attempts")) is not int
        or retry["attempts"] != 1
    ):
        raise FlociError(
            "job definition differs from fixed installed single-attempt profile"
        )


def _resource(value, family, selected):
    if type(value) is not str:
        raise FlociError("Batch resource association requires str")
    if value != selected:
        http.match(
            value,
            r"arn:aws:batch:[a-z0-9-]+:[0-9]{12}:" + family + "/" + re.escape(selected),
        )
    return value


def submit_floci_exchange(staged: StagedFlociExchange, *, timeout_ms: int) -> FlociJob:
    """Acquire local guard BEFORE any API; submit once, never repair lost ack."""
    if type(staged) is not StagedFlociExchange:
        raise TypeError("submit requires StagedFlociExchange, not acknowledged job")
    budget = http.Budget(timeout_ms, 2)
    if _load(staged.control / "identity", STAGED_FORMAT) != staged:
        raise FlociError("local staged identity mismatch")
    _read_input_manifest(
        http.read_file(staged.control / "staged.json", http.DESCRIPTOR_BYTES),
        staged.expected.token,
        str(staged.expected.commit),
        str(staged.expected.request),
    )
    body = dict(
        jobName="dml-" + staged.expected.token,
        jobQueue=staged.remote.queue,
        jobDefinition=staged.remote.job_definition,
        retryStrategy={"attempts": 1},
        containerOverrides={
            "command": _command(
                staged.remote, staged.expected.token, str(staged.expected.commit)
            )
        },
    )
    http.encoded(body)
    try:
        with open(staged.control / "dispatched", "xb"):
            pass
    except FileExistsError:
        raise FlociError(
            "Floci exchange already dispatched; no automatic resubmit"
        ) from None
    _preflight(staged.remote, budget)
    response = http.batch(staged.remote, budget, "SubmitJob", body)
    # Extract any validated acknowledged ID before checking other response claims.
    acknowledged = None
    if type(response) is dict and "jobId" in response:
        acknowledged = http.job_id(response["jobId"])
    try:
        if (
            type(response) is not dict
            or set(response) != {"jobId", "jobName", "jobArn"}
            or response["jobName"] != body["jobName"]
        ):
            raise FlociError("invalid submission acknowledgement")
        _resource(response["jobArn"], "job", acknowledged)
        if response["jobArn"] == acknowledged:
            raise FlociError("submission jobArn requires associated ARN")
        job = FlociJob(staged.remote, staged.expected, staged.control, acknowledged)
        receipt = http.encoded(
            dict(
                format="daggerml-floci-submission-v1",
                job_id=acknowledged,
                token=staged.expected.token,
                commit=str(staged.expected.commit),
            )
        )
        with open(staged.control / "submitted.json", "xb") as stream:
            stream.write(receipt)
    except BaseException as error:
        raise FlociError(
            "submission acknowledgement/receipt failed; do not resubmit",
            job_id=acknowledged,
        ) from error
    return job


def _status(job, budget):
    value = http.batch(job.remote, budget, "DescribeJobs", {"jobs": [job.job_id]})
    if (
        type(value) is not dict
        or set(value) != {"jobs"}
        or type(value["jobs"]) is not list
        or len(value["jobs"]) != 1
    ):
        raise FlociError("acknowledged job unavailable")
    row = value["jobs"][0]
    if type(row) is not dict:
        raise FlociError("invalid job diagnostic description")
    retry, attempts = row.get("retryStrategy"), row.get("attempts")
    container = row.get("container")
    status = row.get("status")
    _resource(row.get("jobDefinition"), "job-definition", job.remote.job_definition)
    _resource(row.get("jobQueue"), "job-queue", job.remote.queue)
    if (
        row.get("jobId") != job.job_id
        or row.get("jobName") != "dml-" + job.expected.token
        or type(retry) is not dict
        or type(retry.get("attempts")) is not int
        or retry["attempts"] != 1
        or type(attempts) is not list
        or len(attempts) > 1
        or row.get("nodeProperties") is not None
        or row.get("arrayProperties") is not None
        or type(container) is not dict
        or container.get("image") != job.remote.image
        or container.get("command")
        != _command(job.remote, job.expected.token, str(job.expected.commit))
        or type(status) is not str
        or status
        not in (
            "SUBMITTED",
            "PENDING",
            "RUNNABLE",
            "STARTING",
            "RUNNING",
            "SUCCEEDED",
            "FAILED",
        )
    ):
        raise FlociError("job diagnostic identity/attempt/profile mismatch")
    return status


def _phase_manifest(job, phase, snapshot, files):
    return http.encoded(
        dict(
            format=PHASE_FORMAT,
            token=job.expected.token,
            commit=str(job.expected.commit),
            request=str(job.expected.request),
            job_id=job.job_id,
            attempt=1,
            phase=phase,
            selected_commit=str(snapshot.commit),
            files=http.file_rows(files),
        )
    )


def _read_phase(data, job, phase):
    value = http.fields(
        http.document(data),
        (
            "token",
            "commit",
            "request",
            "job_id",
            "attempt",
            "phase",
            "selected_commit",
            "files",
        ),
        PHASE_FORMAT,
    )
    if (
        http.hex_id(value["token"]) != job.expected.token
        or http.hex_id(value["commit"]) != str(job.expected.commit)
        or http.hex_id(value["request"]) != str(job.expected.request)
        or http.job_id(value["job_id"]) != job.job_id
        or type(value["attempt"]) is not int
        or value["attempt"] != 1
        or value["phase"] != phase
    ):
        raise FlociError("immutable phase association mismatch")
    http.hex_id(value["selected_commit"])
    http.validate_rows(value["files"], http.PACKET_FILES)
    return value


def _inspect(files, expected):
    with tempfile.TemporaryDirectory(prefix="dml-floci-inspection-") as temporary:
        scratch = Path(temporary)
        for name, data in files:
            (scratch / name).write_bytes(data)
        snapshot = exchange.read_observation(scratch, expected=expected)
    return snapshot


def observe_floci_job(job: FlociJob, *, packet, timeout_ms: int) -> FlociObservation:
    """At most seven fixed HTTP calls; pin one manifest, validate BEFORE packet IO."""
    if not isinstance(job, FlociJob):
        raise TypeError("observe requires acknowledged FlociJob")
    budget = http.Budget(timeout_ms, 7)
    packet = _path(packet)
    status = _status(job, budget)
    for phase in http.PHASES:
        manifest = http.get_object(
            job.remote,
            budget,
            job.expected.token,
            "phases/" + phase + ".json",
            http.DESCRIPTOR_BYTES,
        )
        if manifest is not None:
            break
    else:
        return FlociObservation(
            exchange.ExchangeObservation("working", "bootstrap", None, None),
            job.job_id,
            status,
        )
    selected = _read_phase(manifest, job, phase)
    files = http.fetch_files(
        job.remote,
        budget,
        job.expected.token,
        "snapshots/" + selected["selected_commit"],
        selected["files"],
    )
    snapshot = _inspect(files, job.expected)
    if snapshot.phase != phase or str(snapshot.commit) != selected["selected_commit"]:
        raise FlociError("manifest phase/root differs from authoritative history")
    result = FlociObservation(
        exchange.ExchangeObservation(
            snapshot.lifecycle, snapshot.phase, packet, snapshot
        ),
        job.job_id,
        status,
    )
    packet.mkdir()
    # Retain operational association separately; observation receipt stays LAST.
    by_name = dict(files)
    for name, data in (
        ("snapshot.bundle", by_name["snapshot.bundle"]),
        ("job.json", by_name["job.json"]),
        ("floci-manifest.json", manifest),
        ("observation.json", by_name["observation.json"]),
    ):
        with open(packet / name, "xb") as stream:
            stream.write(data)
    return result
