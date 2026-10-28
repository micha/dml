"""One pinned step across independent local repositories, through public APIs only.

Caller-owned workspaces are retained. Receive inspects records, never executes code
or follows historical paths. See docs/spec-next/repository-execution.md.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import (
    LiteralNode,
    NotFoundError,
    ObjectId,
    Repository,
    SubDAGNode,
    canonicalize_uri,
)
from . import local, transfer

__all__ = [
    "ExchangeSpec",
    "RecordedRequest",
    "record_exchange_request",
    "ReceivedRun",
    "ExchangeError",
    "prepare_exchange",
    "execute_exchange",
    "receive_exchange",
    "ExchangeHandle",
    "WorkerLaunch",
    "ExchangeObservation",
    "ReceivedObservation",
    "save_exchange_handle",
    "load_exchange_handle",
    "start_exchange",
    "observe_exchange",
    "receive_observation",
]

MAX_DESCRIPTOR_BYTES = 8192
JOB_FORMAT = "daggerml-local-exchange-job-v2"
COMPLETION_FORMAT = "daggerml-local-exchange-completion-v1"
HANDLE_FORMAT = "daggerml-local-exchange-handle-v2"
READY_FORMAT = "daggerml-local-exchange-ready-v1"
OBSERVATION_FORMAT = "daggerml-local-exchange-observation-v1"


class ExchangeError(ValueError):
    """Invalid selection, packet, one-shot state or selected completion."""


def _name(value):
    if type(value) is not str:
        raise TypeError("name requires str")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None:
        raise ExchangeError("invalid name")
    return value


def _hex(value, prefix=""):
    if type(value) is not str or re.fullmatch(prefix + r"[0-9a-f]{32}", value) is None:
        raise ExchangeError("invalid ID or occurrence")
    return value


def _uri(value):
    if type(value) is not str:
        raise TypeError("intent_uri requires str")
    if canonicalize_uri(value) != value:
        raise ExchangeError("intent URI must already be canonical")
    return value


def _path(value):
    value = os.fsdecode(os.fspath(value))
    if not value or "\0" in value:
        raise ExchangeError("path must be nonempty without NUL")
    value.encode("utf-8")
    return Path(os.path.abspath(value))


def _map_size(value):
    if type(value) is not int:
        raise TypeError("map_size requires int")
    if value < 0 or value > sys.maxsize or 0 < value < 1048576:
        raise ExchangeError("invalid map_size")


@dataclass(frozen=True)
class ExchangeSpec:
    token: str
    commit: ObjectId
    binding_name: str
    inputs_name: str
    binding: ObjectId
    inputs: ObjectId
    intent_uri: str
    worker_ref: str
    request: Optional[ObjectId] = None

    def __post_init__(self):
        _hex(self.token)
        for oid in (self.commit, self.binding, self.inputs):
            if not isinstance(oid, ObjectId):
                raise TypeError("selection IDs require ObjectId")
        for name in (self.binding_name, self.inputs_name, self.worker_ref):
            _name(name)
        _uri(self.intent_uri)
        if self.request is not None and not isinstance(self.request, ObjectId):
            raise TypeError("request requires ObjectId or None")


@dataclass(frozen=True)
class RecordedRequest:
    """Owned explicit A publication; no workspace, token, process or live handle."""

    base: ObjectId
    commit: ObjectId
    ref: str
    request: ObjectId
    request_id: str
    binding_name: str
    inputs_name: str
    binding: ObjectId
    inputs: ObjectId
    intent_uri: str


@dataclass(frozen=True)
class ReceivedRun:
    commit: ObjectId
    ref: Optional[str]
    object_count: int
    pre_dispatch: ObjectId
    request_id: str
    attempt_id: str
    request: ObjectId
    initial_attempt: ObjectId
    final_attempt: ObjectId
    outcome: str
    outcome_dag: ObjectId
    exit_code: Optional[int]
    reason: Optional[str]
    detail: Optional[str]
    result: Optional[ObjectId]
    evidence: Optional[ObjectId]
    cleanup: str
    cleanup_dag: ObjectId


def _spec_document(spec):
    return {
        "format": JOB_FORMAT,
        "token": spec.token,
        "commit": str(spec.commit),
        "binding_name": spec.binding_name,
        "inputs_name": spec.inputs_name,
        "binding": str(spec.binding),
        "inputs": str(spec.inputs),
        "intent_uri": spec.intent_uri,
        "worker_ref": spec.worker_ref,
        "request": None if spec.request is None else str(spec.request),
    }


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ExchangeError("duplicate descriptor key")
        result[key] = value
    return result


def _constant(_):
    raise ExchangeError("nonstandard descriptor constant")


def _read(path, limit):
    with open(path, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ExchangeError("file exceeds profile limit")
    return data


def _document(path, keys, format):
    data = _read(path, MAX_DESCRIPTOR_BYTES)
    try:
        document = json.loads(
            data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant
        )
    except (ValueError, RecursionError):
        raise ExchangeError("invalid UTF-8/JSON descriptor") from None
    if type(document) is not dict or set(document) != set(keys) | {"format"}:
        raise ExchangeError("unexpected descriptor fields")
    if document["format"] != format:
        raise ExchangeError("unsupported descriptor format")
    return document


def _job(workspace):
    document = _document(
        workspace / "job.json",
        (
            "token",
            "commit",
            "binding_name",
            "inputs_name",
            "binding",
            "inputs",
            "intent_uri",
            "worker_ref",
            "request",
        ),
        JOB_FORMAT,
    )
    return _spec_values(document)


def _spec_values(document):
    if type(document) is not dict or set(document) != set(_spec_document_keys()):
        raise ExchangeError("unexpected job fields")
    if document["format"] != JOB_FORMAT:
        raise ExchangeError("unsupported job format")
    values = {key: value for key, value in document.items() if key != "format"}
    for name in ("commit", "binding", "inputs"):
        values[name] = ObjectId.from_hex(_hex(values[name]))
    if values["request"] is not None:
        values["request"] = ObjectId.from_hex(_hex(values["request"]))
    return ExchangeSpec(**values)


def _spec_document_keys():
    return (
        "format",
        "token",
        "commit",
        "binding_name",
        "inputs_name",
        "binding",
        "inputs",
        "intent_uri",
        "worker_ref",
        "request",
    )


def _write_document(path, document):
    data = json.dumps(
        document, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    if len(data) > MAX_DESCRIPTOR_BYTES:
        raise ExchangeError("descriptor exceeds profile limit")
    # Caller owns the workspace, including partial temp files after failure.
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=path.name + ".", delete=False
    ) as stream:
        stream.write(data)
        temporary = stream.name
    os.replace(temporary, path)


def _scalar(tx, node, kinds):
    node = tx.get_node(node)
    if not isinstance(node, LiteralNode):
        raise ExchangeError("expected literal field")
    datum = tx.get_datum(node.datum)
    if datum.kind not in kinds:
        raise ExchangeError("wrong scalar field type")
    return datum.value


def _subdag(tx, node):
    node = tx.get_node(node)
    if not isinstance(node, SubDAGNode):
        raise ExchangeError("expected sub-DAG field")
    tx.get_dag(node.dag)
    return node.dag


def _role(tx, oid, role, required, optional=(), occurrence=None):
    dag = tx.get_dag(oid)
    fields = set(dag.bindings)
    if not set(required) <= fields or fields - set(required) - set(optional):
        raise ExchangeError("unexpected selected role fields")
    if _scalar(tx, dag.bindings["role"], ("string",)) != role:
        raise ExchangeError("wrong selected role")
    if occurrence is None:
        if dag.root != dag.bindings["role"]:
            raise ExchangeError("wrong role root")
    elif _scalar(tx, dag.root, ("string",)) != occurrence:
        raise ExchangeError("wrong occurrence root")
    return dag


def _binding(tx, oid):
    dag = _role(
        tx,
        oid,
        "local-python-binding-v1",
        ("role", "source", "adapter", "interpreter", "timeout-ms"),
    )
    source = _scalar(tx, dag.bindings["source"], ("bytes",))
    interpreter = _scalar(tx, dag.bindings["interpreter"], ("string",))
    timeout = _scalar(tx, dag.bindings["timeout-ms"], ("i64",))
    if (
        _scalar(tx, dag.bindings["adapter"], ("uri",)) != local.ADAPTER_URI
        or not 1 <= len(source) <= local.MAX_SOURCE_BYTES
        or not 1 <= timeout <= 3600000
    ):
        raise ExchangeError("invalid binding values")
    _historical_path(interpreter)


def _historical_path(path):
    # Validate recorded spelling only; never stat/open/delete this path.
    if (
        not path
        or not os.path.isabs(path)
        or "\0" in path
        or unicodedata.normalize("NFC", path) != path
    ):
        raise ExchangeError("invalid historical path")
    path.encode("utf-8")


def _tree(tx, commit):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def _selection(tx, spec):
    tree = _tree(tx, spec.commit)
    if (
        tree.get(spec.binding_name) != spec.binding
        or tree.get(spec.inputs_name) != spec.inputs
    ):
        raise ExchangeError("pinned tree selection mismatch")
    _binding(tx, spec.binding)
    tx.get_dag(spec.inputs)
    if spec.request is not None:
        _submission(tx, spec, tree)
    return tree


def _request_selection(tx, spec, request, qid):
    q = _role(
        tx,
        request,
        "local-request-v1",
        ("role", "intent", "binding", "inputs"),
        occurrence=qid,
    )
    if (
        _scalar(tx, q.bindings["intent"], ("uri",)) != spec.intent_uri
        or _subdag(tx, q.bindings["binding"]) != spec.binding
        or _subdag(tx, q.bindings["inputs"]) != spec.inputs
    ):
        raise ExchangeError("request selection mismatch")


def _submission(tx, spec, tree):
    qid = _hex(_scalar(tx, tx.get_dag(spec.request).root, ("string",)), "q-")
    _request_selection(tx, spec, spec.request, qid)
    parents = tx.get_commit(spec.commit).parents
    if len(parents) != 1:
        raise ExchangeError("submission requires one basis parent")
    basis = _tree(tx, parents[0])
    preserved = dict(tree)
    name = "request-" + qid
    if name in basis or preserved.pop(name, None) != spec.request or preserved != basis:
        raise ExchangeError("submission must add only the exact request")
    return qid


def record_exchange_request(
    repository_path,
    *,
    commit: ObjectId,
    binding_name: str,
    inputs_name: str,
    intent_uri: str,
    ref: str,
    map_size: int = 0,
) -> RecordedRequest:
    """Explicitly publish Q/Cq and two create-only A refs atomically; never dispatch."""
    if not isinstance(commit, ObjectId):
        raise TypeError("commit requires ObjectId")
    for name in (binding_name, inputs_name, ref):
        _name(name)
    _uri(intent_uri)
    _map_size(map_size)
    with Repository(repository_path, map_size=map_size) as repo:
        for _ in range(local.COLLISION_TRIES):
            with repo.write() as tx:
                try:
                    tx.get_ref(ref)
                except NotFoundError:
                    pass  # Dangling keys still reject at native create, never repair.
                else:
                    raise ExchangeError("submission ref already exists")
                tree = _tree(tx, commit)
                if binding_name not in tree or inputs_name not in tree:
                    raise ExchangeError("selected tree entry missing")
                _binding(tx, tree[binding_name])
                tx.get_dag(tree[inputs_name])
                qid = "q-" + uuid.uuid4().hex
                qref = "request-" + qid
                if ref == qref:
                    raise ExchangeError("submission and request refs must differ")
                try:
                    tx.get_ref(qref)
                except NotFoundError:
                    collision = qref in tree
                else:
                    collision = True
                if collision:
                    tx.abort()
                    continue
                request = local.put_local_request(
                    tx,
                    request_id=qid,
                    intent_uri=intent_uri,
                    binding=tree[binding_name],
                    inputs=tree[inputs_name],
                )
                tree[qref] = request
                submission = tx.put_commit(tx.put_tree(tree), parents=(commit,))
                tx.create_ref(ref, submission)
                tx.create_ref(qref, submission)
                result = RecordedRequest(
                    commit,
                    submission,
                    ref,
                    request,
                    qid,
                    binding_name,
                    inputs_name,
                    tree[binding_name],
                    tree[inputs_name],
                    intent_uri,
                )
            return result
    raise ExchangeError("request occurrence collision limit exhausted")


def prepare_exchange(
    repository_path,
    *,
    commit: ObjectId,
    binding_name: str,
    inputs_name: str,
    intent_uri: str,
    worker_ref: str,
    workspace,
    request: Optional[ObjectId] = None,
) -> ExchangeSpec:
    """Pin named DAGs and write a new retained workspace; never mutate A."""
    if not isinstance(commit, ObjectId):
        raise TypeError("commit requires ObjectId")
    _name(binding_name)
    _name(inputs_name)
    _name(worker_ref)
    _uri(intent_uri)
    workspace = _path(workspace)
    with Repository(repository_path) as repo, repo.read() as tx:
        tree = _tree(tx, commit)
        if binding_name not in tree or inputs_name not in tree:
            raise ExchangeError("selected tree entry missing")
        spec = ExchangeSpec(
            uuid.uuid4().hex,
            commit,
            binding_name,
            inputs_name,
            tree[binding_name],
            tree[inputs_name],
            intent_uri,
            worker_ref,
            request,
        )
        _selection(tx, spec)
    bundle = transfer.export_commit(repository_path, commit=commit)
    workspace.mkdir()
    with open(workspace / "input.bundle", "xb") as stream:
        stream.write(bundle)
    _write_document(workspace / "job.json", _spec_document(spec))
    return spec


def execute_exchange(workspace, *, map_size: int = 0) -> local.LocalRun:
    """Import into fresh B and call run_step once. Recorded failure is completion."""
    _map_size(map_size)
    workspace = _path(workspace)
    spec = _job(workspace)
    worker = workspace / "worker.dml"
    if any(
        path.exists()
        for path in (
            worker,
            workspace / "output.bundle",
            workspace / "completion.json",
            workspace / "worker-ready.json",
        )
    ):
        raise ExchangeError("worker or output already exists")
    try:
        with open(workspace / "started", "xb"):
            pass
    except FileExistsError:
        raise ExchangeError("exchange already started; use a fresh workspace") from None
    bundle = _read(workspace / "input.bundle", transfer.MAX_BUNDLE_BYTES)
    with Repository(worker, create=True, map_size=map_size):
        pass
    imported = transfer.import_commit(
        worker, bundle, ref=spec.worker_ref, map_size=map_size
    )
    if imported.commit != spec.commit:
        raise ExchangeError("input root mismatch")
    with Repository(worker) as repo, repo.read() as tx:
        _selection(tx, spec)
        if tx.get_ref(spec.worker_ref) != spec.commit:
            raise ExchangeError("worker ref mismatch")
    _write_document(
        workspace / "worker-ready.json",
        {
            "format": READY_FORMAT,
            "token": spec.token,
            "commit": str(spec.commit),
        },
    )
    if spec.request is None:
        run = local.run_step(
            worker,
            head_ref=spec.worker_ref,
            intent_uri=spec.intent_uri,
            binding=spec.binding,
            inputs=spec.inputs,
            scratch_dir=workspace,
        )
    else:
        run = local.run_request(
            worker,
            head_ref=spec.worker_ref,
            request_commit=spec.commit,
            request=spec.request,
            scratch_dir=workspace,
        )
    output = transfer.export_commit(worker, commit=run.final_commit)
    with open(workspace / "output.bundle", "xb") as stream:
        stream.write(output)
    _write_document(
        workspace / "completion.json",
        {
            "format": COMPLETION_FORMAT,
            "token": spec.token,
            "commit": str(spec.commit),
            "final_commit": str(run.final_commit),
            "pre_dispatch": str(run.context.pre_dispatch),
            "request_id": run.request_id,
            "attempt_id": run.attempt_id,
        },
    )
    return run


def _diagnostic(tx, oid):
    dag = tx.get_dag(oid)
    if set(dag.bindings) != {"byte-count", "truncated"}:
        raise ExchangeError("unexpected diagnostic fields")
    data = _scalar(tx, dag.root, ("bytes",))
    count = _scalar(tx, dag.bindings["byte-count"], ("i64",))
    truncated = _scalar(tx, dag.bindings["truncated"], ("bool",))
    if (
        len(data) > local.DIAGNOSTIC_BYTES
        or count < len(data)
        or truncated != (count > len(data))
    ):
        raise ExchangeError("invalid diagnostic values")


def _outcome(tx, oid, publication_result):
    dag = tx.get_dag(oid)
    role = (
        _scalar(tx, dag.bindings["role"], ("string",))
        if "role" in dag.bindings
        else None
    )
    if role not in ("local-success-v1", "local-failure-v1"):
        raise ExchangeError("invalid outcome role")
    success = role == "local-success-v1"
    required = (
        ("role", "exit-code", "result")
        if success
        else ("role", "exit-code", "reason", "detail")
    )
    dag = _role(
        tx,
        oid,
        role,
        required,
        ("stdout", "stderr") if success else ("stdout", "stderr", "evidence"),
    )
    exit_code = _scalar(
        tx, dag.bindings["exit-code"], ("i64",) if success else ("i64", "null")
    )
    reason = detail = result = evidence = None
    if success:
        result = _subdag(tx, dag.bindings["result"])
        if exit_code != 0 or publication_result != result:
            raise ExchangeError("success does not match publication/exit")
    else:
        reason = _scalar(tx, dag.bindings["reason"], ("string",))
        detail = _scalar(tx, dag.bindings["detail"], ("string",))
        if (
            reason
            not in (
                "launch",
                "child-exit",
                "timeout",
                "missing-publication",
                "invalid-publication",
            )
            or len(detail.encode("utf-8")) > local.DIAGNOSTIC_BYTES
            or (reason == "launch" and exit_code is not None)
            or (reason == "child-exit" and exit_code in (None, 0))
            or (
                reason in ("missing-publication", "invalid-publication")
                and exit_code != 0
            )
        ):
            raise ExchangeError("invalid failure values")
        if "evidence" in dag.bindings:
            evidence = _subdag(tx, dag.bindings["evidence"])
        if publication_result != evidence:
            raise ExchangeError("failure evidence does not match publication")
        if (
            reason in ("launch", "missing-publication", "invalid-publication")
            and evidence is not None
        ):
            raise ExchangeError("failure reason cannot retain accepted publication")
    for name in ("stdout", "stderr"):
        if name in dag.bindings:
            _diagnostic(tx, _subdag(tx, dag.bindings[name]))
    return (
        "success" if success else "failure",
        exit_code,
        reason,
        detail,
        result,
        evidence,
    )


def _initial(tx, spec, pre, qid, aid):
    base = _selection(tx, spec)
    qname, aname, pname = "request-" + qid, "attempt-" + aid, "publication-" + aid
    initial_tree = _tree(tx, pre)
    if (
        tx.get_commit(pre).parents != (spec.commit,)
        or (spec.request is None and qname in base)
        or aname in base
        or pname in base
    ):
        raise ExchangeError("invalid pre-dispatch parent or fresh names")
    preserved = dict(initial_tree)
    initial = preserved.pop(aname, None)
    if spec.request is None:
        request = preserved.pop(qname, None)
    else:
        request = preserved.get(qname)
        if request != spec.request:
            raise ExchangeError("pre-dispatch lacks exact pinned request")
    if request is None or initial is None or preserved != base:
        raise ExchangeError("pre-dispatch tree mismatch")
    _request_selection(tx, spec, request, qid)
    required = ("role", "request", "publication-ref", "scratch")
    a = _role(tx, initial, "local-attempt-v1", required, occurrence=aid)
    scratch = _scalar(tx, a.bindings["scratch"], ("string",))
    _historical_path(scratch)
    if (
        _subdag(tx, a.bindings["request"]) != request
        or _scalar(tx, a.bindings["publication-ref"], ("string",)) != aname
    ):
        raise ExchangeError("initial attempt association mismatch")
    return initial_tree, request, initial, a, scratch


def _publication(tx, pre, aid, selected, initial_tree):
    publication_tree = _tree(tx, selected)
    publication = publication_tree.pop("publication-" + aid, None)
    if (
        publication is None
        or publication_tree != initial_tree
        or tx.get_commit(selected).parents != (pre,)
    ):
        raise ExchangeError("publication history mismatch")
    p = _role(
        tx, publication, "local-publication-v1", ("role", "result"), occurrence=aid
    )
    return publication, _subdag(tx, p.bindings["result"])


def _completion(tx, spec, receipt, ref, count):
    pre, final = receipt["pre_dispatch"], receipt["final_commit"]
    qid, aid = receipt["request_id"], receipt["attempt_id"]
    initial_tree, request, initial, a, scratch = _initial(tx, spec, pre, qid, aid)
    aname, pname = "attempt-" + aid, "publication-" + aid
    required = ("role", "request", "publication-ref", "scratch")
    final_tree = _tree(tx, final)
    final_attempt = final_tree.get(aname)
    if final_attempt is None:
        raise ExchangeError("missing final attempt")
    a_final = _role(
        tx,
        final_attempt,
        "local-attempt-v1",
        required + ("status", "outcome", "cleanup"),
        occurrence=aid,
    )
    if (
        any(a_final.bindings[name] != a.bindings[name] for name in required)
        or _scalar(tx, a_final.bindings["status"], ("string",)) != "done"
    ):
        raise ExchangeError("final attempt association/status mismatch")
    parents = tx.get_commit(final).parents
    publication_result = None
    expected_tree = dict(initial_tree)
    expected_tree[aname] = final_attempt
    if len(parents) == 2 and parents[0] == pre:
        publication, publication_result = _publication(
            tx, pre, aid, parents[1], initial_tree
        )
        expected_tree[pname] = publication
    elif parents != (pre,):
        raise ExchangeError("completion parent order mismatch")
    if final_tree != expected_tree:
        raise ExchangeError("completion tree mismatch")
    outcome_dag = _subdag(tx, a_final.bindings["outcome"])
    outcome, exit_code, reason, detail, result, evidence = _outcome(
        tx, outcome_dag, publication_result
    )
    cleanup_dag = _subdag(tx, a_final.bindings["cleanup"])
    cleanup = _role(
        tx,
        cleanup_dag,
        "local-cleanup-v1",
        ("role", "disposition", "detail"),
        ("scratch",),
    )
    disposition = _scalar(tx, cleanup.bindings["disposition"], ("string",))
    cleanup_detail = _scalar(tx, cleanup.bindings["detail"], ("string",))
    if (
        disposition not in ("ok", "failed")
        or len(cleanup_detail.encode("utf-8")) > local.DIAGNOSTIC_BYTES
        or ("scratch" in cleanup.bindings) != (disposition == "failed")
    ):
        raise ExchangeError("invalid cleanup disposition/fields")
    if (
        disposition == "failed"
        and _scalar(tx, cleanup.bindings["scratch"], ("string",)) != scratch
    ):
        raise ExchangeError("cleanup scratch mismatch")
    return ReceivedRun(
        final,
        ref,
        count,
        pre,
        qid,
        aid,
        request,
        initial,
        final_attempt,
        outcome,
        outcome_dag,
        exit_code,
        reason,
        detail,
        result,
        evidence,
        disposition,
        cleanup_dag,
    )


def receive_exchange(
    repository_path, *, workspace, expected: ExchangeSpec, ref: str, map_size: int = 0
) -> ReceivedRun:
    """Validate in disposable storage, then atomically import exact F under ref."""
    if not isinstance(expected, ExchangeSpec):
        raise TypeError("expected requires ExchangeSpec")
    _name(ref)
    _map_size(map_size)
    workspace = _path(workspace)
    if _job(workspace) != expected:
        raise ExchangeError("job differs from caller expected selection")
    receipt = _document(
        workspace / "completion.json",
        ("token", "commit", "final_commit", "pre_dispatch", "request_id", "attempt_id"),
        COMPLETION_FORMAT,
    )
    if _hex(receipt["token"]) != expected.token or _hex(receipt["commit"]) != str(
        expected.commit
    ):
        raise ExchangeError("completion token/base mismatch")
    for name in ("final_commit", "pre_dispatch"):
        receipt[name] = ObjectId.from_hex(_hex(receipt[name]))
    _hex(receipt["request_id"], "q-")
    _hex(receipt["attempt_id"], "a-")
    bundle = _read(workspace / "output.bundle", transfer.MAX_BUNDLE_BYTES)
    scratch = tempfile.mkdtemp(prefix="dml-exchange-validation-")
    try:
        validation = Path(scratch) / "validation.dml"
        with Repository(validation, create=True):
            pass
        imported = transfer.import_commit(validation, bundle)
        if imported.commit != receipt["final_commit"]:
            raise ExchangeError("completion root mismatch")
        with Repository(validation) as repo, repo.read() as tx:
            received = _completion(tx, expected, receipt, ref, imported.object_count)
    finally:
        # Only allocated validation scratch. Cleanup failure prevents any A write.
        shutil.rmtree(scratch)
    transfer.import_commit(repository_path, bundle, ref=ref, map_size=map_size)
    return received


@dataclass(frozen=True)
class ExchangeHandle:
    """Saved observation identity, never live process or recovery authority."""

    workspace: Path
    expected: ExchangeSpec

    def __post_init__(self):
        if not isinstance(self.expected, ExchangeSpec):
            raise TypeError("expected requires ExchangeSpec")
        object.__setattr__(self, "workspace", _path(self.workspace))


class WorkerLaunch:
    """Application-owned direct process. Retain it and explicitly wait/reap it.

    No finalizer, context-manager wait, hidden registry or detached lifetime promise.
    A timed-out wait retains ownership and streams. Process status is not progress.
    """

    def __init__(self, handle, stdout, stderr):
        self.handle = handle
        self.process = None
        self._stdout = stdout
        self._stderr = stderr

    def wait(self, timeout=None):
        code = self.process.wait(timeout=timeout)
        self._stdout.close()
        self._stderr.close()
        return code


def _handle(value):
    if not isinstance(value, ExchangeHandle):
        raise TypeError("handle requires ExchangeHandle")
    if _job(value.workspace) != value.expected:
        raise ExchangeError("job differs from caller expected selection")
    return value.workspace, value.expected


def save_exchange_handle(file, handle: ExchangeHandle) -> None:
    """Write a new caller-owned bounded handle file; never dispatch."""
    if not isinstance(handle, ExchangeHandle):
        raise TypeError("handle requires ExchangeHandle")
    document = {
        "format": HANDLE_FORMAT,
        "workspace": str(handle.workspace),
        "expected": _spec_document(handle.expected),
    }
    data = json.dumps(
        document, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    if len(data) > MAX_DESCRIPTOR_BYTES:
        raise ExchangeError("handle exceeds profile limit")
    with open(_path(file), "xb") as stream:
        stream.write(data)


def load_exchange_handle(file) -> ExchangeHandle:
    """Load identity only. Does not read the workspace, signal a PID or start work."""
    document = _document(_path(file), ("workspace", "expected"), HANDLE_FORMAT)
    if type(document["workspace"]) is not str:
        raise ExchangeError("handle workspace requires str")
    return ExchangeHandle(document["workspace"], _spec_values(document["expected"]))


def start_exchange(handle: ExchangeHandle) -> WorkerLaunch:
    """Spawn the fixed installed worker once, without waiting for computation."""
    workspace, _ = _handle(handle)
    artifacts = (
        "started",
        "worker.dml",
        "output.bundle",
        "completion.json",
        "worker-ready.json",
        "worker.stdout",
        "worker.stderr",
    )
    if any((workspace / name).exists() for name in artifacts):
        raise ExchangeError("worker artifacts already exist")
    try:
        with open(workspace / "launched", "xb"):
            pass
    except FileExistsError:
        raise ExchangeError(
            "exchange already launched; no automatic relaunch"
        ) from None
    # Allocate command, streams and owner before spawn; no postspawn receipt IO.
    command = [sys.executable, "-m", "daggerml.exchange_worker", str(workspace)]
    stdout = open(workspace / "worker.stdout", "xb")
    try:
        stderr = open(workspace / "worker.stderr", "xb")
        try:
            launch = WorkerLaunch(handle, stdout, stderr)
            launch.process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                shell=False,
            )
        except BaseException:
            stderr.close()
            raise
    except BaseException:
        stdout.close()
        raise
    return launch


@dataclass(frozen=True)
class ReceivedObservation:
    lifecycle: str
    phase: str
    commit: ObjectId
    ref: Optional[str]
    object_count: int
    pre_dispatch: ObjectId
    request_id: str
    attempt_id: str
    request: ObjectId
    initial_attempt: ObjectId
    publication: Optional[ObjectId]
    result: Optional[ObjectId]
    completion: Optional[ReceivedRun]


@dataclass(frozen=True)
class ExchangeObservation:
    lifecycle: str
    phase: str
    packet: Optional[Path]
    snapshot: Optional[ReceivedObservation]


def _discover(tx, spec):
    """Read head and its fresh attempt publication ref in this ONE read snapshot."""
    base = _selection(tx, spec)
    head = tx.get_ref(spec.worker_ref)
    if head == spec.commit:
        return None
    selected = _tree(tx, head)
    new_names = set(selected) - set(base)
    if spec.request is None:
        requests = [name for name in new_names if name.startswith("request-q-")]
        if len(requests) != 1:
            raise ExchangeError("worker head lacks exactly one fresh request/attempt")
        qid = requests[0][8:]
    else:
        qid = _submission(tx, spec, base)
    attempts = [name for name in new_names if name.startswith("attempt-a-")]
    if len(attempts) != 1:
        raise ExchangeError("worker head lacks exactly one fresh request/attempt")
    aid = attempts[0][8:]
    _hex(qid, "q-")
    _hex(aid, "a-")
    attempt = tx.get_dag(selected[attempts[0]])
    if "status" in attempt.bindings:
        parents = tx.get_commit(head).parents
        if not parents:
            raise ExchangeError("final head has no pre-dispatch parent")
        pre, phase, root = parents[0], "completion", head
    else:
        pre = head
        initial_tree, _, _, _, _ = _initial(tx, spec, pre, qid, aid)
        target = tx.get_ref("attempt-" + aid)
        if target == pre:
            phase, root = "initial", pre
        else:
            _publication(tx, pre, aid, target, initial_tree)
            phase, root = "publication", target
    receipt = {
        "phase": phase,
        "selected_commit": root,
        "pre_dispatch": pre,
        "request_id": qid,
        "attempt_id": aid,
    }
    _progress(tx, spec, receipt, None, 0)
    return receipt


def _progress(tx, spec, receipt, ref, count):
    pre, selected = receipt["pre_dispatch"], receipt["selected_commit"]
    qid, aid, phase = receipt["request_id"], receipt["attempt_id"], receipt["phase"]
    initial_tree, request, initial, _, _ = _initial(tx, spec, pre, qid, aid)
    publication = result = completion = None
    if phase == "initial":
        if selected != pre:
            raise ExchangeError("initial root differs from pre-dispatch")
    elif phase == "publication":
        publication, result = _publication(tx, pre, aid, selected, initial_tree)
    else:
        completion = _completion(
            tx, spec, dict(receipt, final_commit=selected), ref, count
        )
        result = completion.result
        publication = _tree(tx, selected).get("publication-" + aid)
    return ReceivedObservation(
        "done" if completion is not None else "working",
        phase,
        selected,
        ref,
        count,
        pre,
        qid,
        aid,
        request,
        initial,
        publication,
        result,
        completion,
    )


def _validate_observation(bundle, spec, receipt, ref):
    scratch = tempfile.mkdtemp(prefix="dml-observation-validation-")
    try:
        validation = Path(scratch) / "validation.dml"
        with Repository(validation, create=True):
            pass
        imported = transfer.import_commit(validation, bundle)
        if imported.commit != receipt["selected_commit"]:
            raise ExchangeError("observation root mismatch")
        with Repository(validation) as repo, repo.read() as tx:
            return _progress(tx, spec, receipt, ref, imported.object_count)
    finally:
        shutil.rmtree(scratch)


def observe_exchange(handle: ExchangeHandle, *, packet) -> ExchangeObservation:
    """One coherent discovery and pinned retrieval; no internal polling or execution."""
    workspace, spec = _handle(handle)
    packet = _path(packet)
    ready = workspace / "worker-ready.json"
    if not ready.exists():
        return ExchangeObservation("working", "bootstrap", None, None)
    readiness = _document(ready, ("token", "commit"), READY_FORMAT)
    if _hex(readiness["token"]) != spec.token or _hex(readiness["commit"]) != str(
        spec.commit
    ):
        raise ExchangeError("readiness token/base mismatch")
    worker = workspace / "worker.dml"
    with Repository(worker) as repo, repo.read() as tx:
        receipt = _discover(tx, spec)
    if receipt is None:
        return ExchangeObservation("working", "bootstrap", None, None)
    bundle = transfer.export_commit(worker, commit=receipt["selected_commit"])
    snapshot = _validate_observation(bundle, spec, receipt, None)
    observation = ExchangeObservation(
        snapshot.lifecycle, snapshot.phase, packet, snapshot
    )
    document = {
        "format": OBSERVATION_FORMAT,
        "token": spec.token,
        "commit": str(spec.commit),
    }
    document.update(
        (key, str(value) if isinstance(value, ObjectId) else value)
        for key, value in receipt.items()
    )
    packet.mkdir()
    with open(packet / "snapshot.bundle", "xb") as stream:
        stream.write(bundle)
    _write_document(packet / "job.json", _spec_document(spec))
    _write_document(packet / "observation.json", document)
    return observation


def receive_observation(
    repository_path, *, packet, expected: ExchangeSpec, ref: str, map_size: int = 0
) -> ReceivedObservation:
    """Independently validate immutable P/U/F before atomic explicit-ref A import."""
    if not isinstance(expected, ExchangeSpec):
        raise TypeError("expected requires ExchangeSpec")
    _name(ref)
    _map_size(map_size)
    packet = _path(packet)
    if _job(packet) != expected:
        raise ExchangeError("job differs from caller expected selection")
    receipt = _document(
        packet / "observation.json",
        (
            "token",
            "commit",
            "phase",
            "selected_commit",
            "pre_dispatch",
            "request_id",
            "attempt_id",
        ),
        OBSERVATION_FORMAT,
    )
    if _hex(receipt["token"]) != expected.token or _hex(receipt["commit"]) != str(
        expected.commit
    ):
        raise ExchangeError("observation token/base mismatch")
    if type(receipt["phase"]) is not str or receipt["phase"] not in (
        "initial",
        "publication",
        "completion",
    ):
        raise ExchangeError("invalid observation phase")
    for name in ("selected_commit", "pre_dispatch"):
        receipt[name] = ObjectId.from_hex(_hex(receipt[name]))
    _hex(receipt["request_id"], "q-")
    _hex(receipt["attempt_id"], "a-")
    bundle = _read(packet / "snapshot.bundle", transfer.MAX_BUNDLE_BYTES)
    received = _validate_observation(bundle, expected, receipt, ref)
    transfer.import_commit(repository_path, bundle, ref=ref, map_size=map_size)
    return received
