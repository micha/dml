"""One synchronous, trusted local Python step over the public repository API.

See docs/spec-next/local-execution.md for the cooperative publication contract.
Inspection never executes source. This module is not a sandbox or recovery service.
"""

from __future__ import annotations

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
from typing import Optional, Sequence, Tuple

from . import Datum, DmlError, LiteralNode, NotFoundError, ObjectId, Repository, SubDAGNode, Transaction

__all__ = [
    "put_local_binding",
    "put_local_request",
    "run_request",
    "run_step",
    "retry_step",
    "child_context",
    "publish_result",
    "LocalContext",
    "LocalRun",
    "LocalExecutionError",
    "ProtocolError",
    "ConflictError",
]

ADAPTER_URI = "urn:daggerml:local-python-v1"
MAX_SOURCE_BYTES = 1024 * 1024
DIAGNOSTIC_BYTES = 4096
SHUTDOWN_SECONDS = 5
COLLISION_TRIES = 3


class ProtocolError(ValueError):
    """Malformed local role or pinned publication association."""


class ConflictError(RuntimeError):
    """A coordination head or publication ref moved unexpectedly."""


class LocalExecutionError(RuntimeError):
    """Caller-visible error; occurrence is inspectable, but has no claimed done status."""

    def __init__(self, detail: str, occurrence: Optional[LocalContext] = None) -> None:
        self.occurrence = occurrence
        super().__init__(detail)


@dataclass(frozen=True)
class LocalContext:
    repository_path: str
    pre_dispatch: ObjectId
    request_id: str
    attempt_id: str
    request: ObjectId
    attempt: ObjectId
    publication_ref: str
    binding: ObjectId
    inputs: ObjectId
    scratch: str


@dataclass(frozen=True)
class LocalRun:
    context: LocalContext
    final_commit: ObjectId
    final_attempt: ObjectId
    outcome: str
    result: Optional[ObjectId]
    evidence: Optional[ObjectId]
    cleanup: str

    @property
    def request_id(self) -> str:
        return self.context.request_id

    @property
    def attempt_id(self) -> str:
        return self.context.attempt_id


def _literal(tx: Transaction, value) -> ObjectId:
    return tx.put_literal(tx.put_datum(value))


def _record(tx: Transaction, root, fields, subdags=()) -> ObjectId:
    nodes = {name: _literal(tx, value) for name, value in fields.items()}
    nodes.update((name, tx.put_subdag(dag)) for name, dag in subdags)
    return tx.put_dag(root=_literal(tx, root), bindings=nodes)


def _scalar(tx: Transaction, node: ObjectId, kind: str):
    description = tx.get_node(node)
    if not isinstance(description, LiteralNode):
        raise ProtocolError("expected literal node")
    datum = tx.get_datum(description.datum)
    if datum.kind != kind:
        raise ProtocolError("expected " + kind + " datum")
    return datum.value


def _fields(tx: Transaction, dag: ObjectId, required, role: str):
    description = tx.get_dag(dag)
    if set(description.bindings) != set(required):
        raise ProtocolError("unexpected fields for " + role)
    if _scalar(tx, description.bindings["role"], "string") != role:
        raise ProtocolError("unexpected record role")
    return description


def _subdag(tx: Transaction, node: ObjectId) -> ObjectId:
    description = tx.get_node(node)
    if not isinstance(description, SubDAGNode):
        raise ProtocolError("expected sub-DAG node")
    tx.get_dag(description.dag)
    return description.dag


def _occurrence(value: str, prefix: str) -> str:
    if type(value) is not str or re.fullmatch(prefix + r"-[0-9a-f]{32}", value) is None:
        raise ProtocolError("invalid " + prefix + " occurrence identifier")
    return value


def _path(value) -> str:
    value = os.fsdecode(os.fspath(value))
    if not value or "\0" in value:
        raise ValueError("path must be nonempty without NUL")
    value.encode("utf-8")
    return os.path.abspath(value)


def _recorded_path(value: str) -> None:
    # Native STRING datums normalize NFC. Never silently retarget a filesystem path.
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError("recorded interpreter/scratch paths must be NFC")


def _binding_values(source: bytes, interpreter: str, timeout_ms: int) -> None:
    if type(source) is not bytes or type(interpreter) is not str or type(timeout_ms) is not int:
        raise TypeError("source/interpreter/timeout_ms require bytes/str/int")
    if not 1 <= len(source) <= MAX_SOURCE_BYTES:
        raise ValueError("source must contain 1..1048576 bytes")
    if not interpreter or "\0" in interpreter or not os.path.isabs(interpreter):
        raise ValueError("interpreter must be an absolute executable path without NUL")
    interpreter.encode("utf-8")
    _recorded_path(interpreter)
    if not 1 <= timeout_ms <= 3600000:
        raise ValueError("timeout_ms must be in 1..3600000")


def put_local_binding(tx: Transaction, *, source: bytes, interpreter: str,
                      timeout_ms: int) -> ObjectId:
    """Capture one entry script, not its imports, interpreter binary or environment."""
    _binding_values(source, interpreter, timeout_ms)
    role = "local-python-binding-v1"
    return _record(tx, role, {"role": role, "source": source,
                            "adapter": Datum.uri(ADAPTER_URI), "interpreter": interpreter,
                            "timeout-ms": timeout_ms})


def _binding(tx: Transaction, binding: ObjectId) -> Tuple[bytes, str, int]:
    role = "local-python-binding-v1"
    dag = _fields(tx, binding, ("role", "source", "adapter", "interpreter", "timeout-ms"), role)
    if dag.root != dag.bindings["role"] or _scalar(tx, dag.bindings["adapter"], "uri") != ADAPTER_URI:
        raise ProtocolError("invalid binding root or adapter")
    values = (_scalar(tx, dag.bindings["source"], "bytes"),
              _scalar(tx, dag.bindings["interpreter"], "string"),
              _scalar(tx, dag.bindings["timeout-ms"], "i64"))
    _binding_values(*values)
    return values


def _request(tx: Transaction, request: ObjectId):
    dag = _fields(tx, request, ("role", "intent", "binding", "inputs"), "local-request-v1")
    occurrence = _occurrence(_scalar(tx, dag.root, "string"), "q")
    _scalar(tx, dag.bindings["intent"], "uri")
    binding = _subdag(tx, dag.bindings["binding"])
    _binding(tx, binding)
    inputs = _subdag(tx, dag.bindings["inputs"])
    return occurrence, binding, inputs


def put_local_request(
    tx: Transaction,
    *,
    request_id: str,
    intent_uri: str,
    binding: ObjectId,
    inputs: ObjectId,
) -> ObjectId:
    """Build ordinary Q only; caller owns uniqueness, refs and transaction commit."""
    _occurrence(request_id, "q")
    if type(intent_uri) is not str:
        raise TypeError("intent_uri requires str")
    if not isinstance(binding, ObjectId) or not isinstance(inputs, ObjectId):
        raise TypeError("binding and inputs require ObjectId")
    _binding(tx, binding)
    tx.get_dag(inputs)
    return _record(
        tx,
        request_id,
        {"role": "local-request-v1", "intent": Datum.uri(intent_uri)},
        (("binding", binding), ("inputs", inputs)),
    )


def _submission(tx: Transaction, commit: ObjectId, request: ObjectId):
    request_id, binding, inputs = _request(tx, request)
    parents = tx.get_commit(commit).parents
    if len(parents) != 1:
        raise ProtocolError("submission requires one basis parent")
    basis = _tree(tx, parents[0])
    tree = _tree(tx, commit)
    name = "request-" + request_id
    if name in basis or tree.pop(name, None) != request or tree != basis:
        raise ProtocolError("submission must add only the exact request")
    if binding not in basis.values() or inputs not in basis.values():
        raise ProtocolError("submission basis lacks binding or inputs")
    return request_id, binding, inputs


def _tree(tx: Transaction, commit: ObjectId):
    return dict(tx.get_tree(tx.get_commit(commit).tree))


def _context(tx: Transaction, repository_path: str, pre_dispatch: ObjectId,
             attempt_id: str, publication_ref: str) -> LocalContext:
    _occurrence(attempt_id, "a")
    if publication_ref != "attempt-" + attempt_id:
        raise ProtocolError("publication ref does not match attempt")
    tree = _tree(tx, pre_dispatch)
    attempt = tree.get("attempt-" + attempt_id)
    if attempt is None:
        raise ProtocolError("pinned snapshot lacks attempt")
    dag = _fields(tx, attempt, ("role", "request", "publication-ref", "scratch"), "local-attempt-v1")
    if _scalar(tx, dag.root, "string") != attempt_id:
        raise ProtocolError("attempt root does not match occurrence")
    if _scalar(tx, dag.bindings["publication-ref"], "string") != publication_ref:
        raise ProtocolError("attempt publication ref mismatch")
    scratch = _scalar(tx, dag.bindings["scratch"], "string")
    if not os.path.isabs(scratch) or "\0" in scratch:
        raise ProtocolError("invalid recorded scratch path")
    request = _subdag(tx, dag.bindings["request"])
    request_id, binding, inputs = _request(tx, request)
    if tree.get("request-" + request_id) != request:
        raise ProtocolError("pinned snapshot lacks exact request")
    reservation = _tree(tx, tx.get_ref("request-" + request_id))
    if reservation.get("request-" + request_id) != request:
        raise ProtocolError("request reservation mismatch")
    return LocalContext(repository_path, pre_dispatch, request_id, attempt_id, request, attempt,
                        publication_ref, binding, inputs, scratch)


def child_context(argv: Optional[Sequence[str]] = None) -> LocalContext:
    """Read the four positional contract arguments from the pinned snapshot."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 4:
        raise ProtocolError("expected repository path, pre-dispatch commit, attempt ID, publication ref")
    path, commit, attempt, ref = args
    path = _path(path)
    with Repository(path) as repo, repo.read() as tx:
        return _context(tx, path, ObjectId.from_hex(commit), attempt, ref)


def publish_result(tx: Transaction, context: LocalContext, result: ObjectId) -> ObjectId:
    """Publish in the child's existing write transaction; caller commits the batch."""
    pinned = _context(tx, context.repository_path, context.pre_dispatch,
                      context.attempt_id, context.publication_ref)
    if pinned != context:
        raise ProtocolError("context differs from pinned attempt")
    if tx.get_ref(context.publication_ref) != context.pre_dispatch:
        raise ConflictError("publication ref moved before publication")
    tx.get_dag(result)
    tree = _tree(tx, context.pre_dispatch)
    name = "publication-" + context.attempt_id
    if name in tree:
        raise ConflictError("publication entry already exists")
    tree[name] = _record(tx, context.attempt_id, {"role": "local-publication-v1"}, (("result", result),))
    commit = tx.put_commit(tx.put_tree(tree), parents=(context.pre_dispatch,))
    tx.update_ref(context.publication_ref, commit)
    return commit


def _new_id(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex


def _exists(tx: Transaction, ref: str) -> bool:
    try:
        tx.get_ref(ref)
    except NotFoundError:
        return False
    return True


def _prepare(
    path: str,
    head_ref: str,
    scratch: str,
    *,
    intent_uri=None,
    binding=None,
    inputs=None,
    request=None,
    request_commit=None,
) -> LocalContext:
    with Repository(path) as repo:
        for _ in range(COLLISION_TRIES):
            with repo.write() as tx:
                base = tx.get_ref(head_ref)
                tree = _tree(tx, base)
                if request is None:
                    _binding(tx, binding)
                    tx.get_dag(inputs)
                    request_id = _new_id("q")
                    selected_request = None
                elif request_commit is not None:
                    if base != request_commit:
                        raise ConflictError("head differs from pinned submission")
                    request_id, binding, inputs = _submission(
                        tx, request_commit, request
                    )
                    if _exists(tx, "request-" + request_id):
                        raise ConflictError("request already registered locally")
                    selected_request = request
                else:
                    request_id, binding, inputs = _request(tx, request)
                    reserved = _tree(tx, tx.get_ref("request-" + request_id))
                    if reserved.get("request-" + request_id) != request:
                        raise ProtocolError("retry request reservation mismatch")
                    selected_request = request
                    if tree.get("request-" + request_id) not in (None, request):
                        raise ConflictError("head contains another request description")
                attempt_id = _new_id("a")
                qref, aref = "request-" + request_id, "attempt-" + attempt_id
                if (
                    (request is None and (_exists(tx, qref) or qref in tree))
                    or _exists(tx, aref)
                    or aref in tree
                    or "publication-" + attempt_id in tree
                ):
                    tx.abort()
                    continue
                if selected_request is None:
                    selected_request = put_local_request(
                        tx,
                        request_id=request_id,
                        intent_uri=intent_uri,
                        binding=binding,
                        inputs=inputs,
                    )
                attempt = _record(
                    tx,
                    attempt_id,
                    {
                        "role": "local-attempt-v1",
                        "publication-ref": aref,
                        "scratch": scratch,
                    },
                    (("request", selected_request),),
                )
                tree[qref], tree[aref] = selected_request, attempt
                commit = tx.put_commit(tx.put_tree(tree), parents=(base,))
                tx.update_ref(head_ref, commit)
                if request is None or request_commit is not None:
                    tx.create_ref(
                        qref, commit if request_commit is None else request_commit
                    )
                tx.create_ref(aref, commit)
            return LocalContext(
                path,
                commit,
                request_id,
                attempt_id,
                selected_request,
                attempt,
                aref,
                binding,
                inputs,
                scratch,
            )
    raise ConflictError("occurrence collision limit exhausted")


@dataclass(frozen=True)
class _Observation:
    exit_code: Optional[int]
    reason: Optional[str]
    detail: str
    stdout: Optional[Tuple[bytes, int]]
    stderr: Optional[Tuple[bytes, int]]


def _diagnostic(stream) -> Tuple[bytes, int]:
    stream.flush()
    stream.seek(0, os.SEEK_END)
    count = stream.tell()
    stream.seek(0)
    return stream.read(DIAGNOSTIC_BYTES), count


def _shutdown(process) -> None:
    process.terminate()
    try:
        process.wait(timeout=SHUTDOWN_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=SHUTDOWN_SECONDS)


def _execute(context: LocalContext, source: bytes, interpreter: str, timeout_ms: int) -> _Observation:
    entry = Path(context.scratch) / "entry.py"
    process = None
    try:
        entry.write_bytes(source)
        with open(Path(context.scratch) / "stdout", "w+b") as stdout, \
                open(Path(context.scratch) / "stderr", "w+b") as stderr:
            try:
                process = subprocess.Popen([interpreter, str(entry), context.repository_path,
                                            str(context.pre_dispatch), context.attempt_id,
                                            context.publication_ref], cwd=context.scratch,
                                           stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                           shell=False)
            except OSError as error:
                return _Observation(None, "launch", _detail(error), None, None)
            reason, detail = None, ""
            try:
                try:
                    process.wait(timeout=timeout_ms / 1000)
                except subprocess.TimeoutExpired:
                    reason, detail = "timeout", "execution timeout expired"
                    _shutdown(process)
            except BaseException:
                # A failure to reap is an unknown outcome, never a recorded done response.
                if reason != "timeout" and process.poll() is None:
                    _shutdown(process)
                raise
            if reason is None and process.returncode != 0:
                reason, detail = "child-exit", "child exited nonzero"
            return _Observation(process.returncode, reason, detail, _diagnostic(stdout), _diagnostic(stderr))
    except OSError as error:
        if process is not None:
            raise  # Post-launch IO/reaping failure is unknown, not a launch failure.
        return _Observation(None, "launch", _detail(error), None, None)


def _detail(error) -> str:
    # Bound UTF-8 bytes, not merely code points. Do not dump environment/tracebacks.
    return str(error).encode("utf-8", "replace")[:DIAGNOSTIC_BYTES].decode("utf-8", "ignore")


def _cleanup(scratch: str) -> Tuple[str, str]:
    try:
        shutil.rmtree(scratch)
    except OSError as error:
        return "failed", _detail(error)
    return "ok", ""


def _publication(tx: Transaction, context: LocalContext, target: ObjectId) -> ObjectId:
    commit = tx.get_commit(target)
    if commit.parents != (context.pre_dispatch,):
        raise ProtocolError("publication parents mismatch")
    base = _tree(tx, context.pre_dispatch)
    actual = dict(tx.get_tree(commit.tree))
    name = "publication-" + context.attempt_id
    publication = actual.pop(name, None)
    if publication is None or actual != base:
        raise ProtocolError("publication tree does not preserve pinned entries exactly")
    dag = _fields(tx, publication, ("role", "result"), "local-publication-v1")
    if _scalar(tx, dag.root, "string") != context.attempt_id:
        raise ProtocolError("publication attempt mismatch")
    return _subdag(tx, dag.bindings["result"])


def _put_diagnostic(tx: Transaction, observation: Tuple[bytes, int]) -> ObjectId:
    data, count = observation
    return _record(tx, data, {"byte-count": count, "truncated": count > len(data)})


def _finalize(context: LocalContext, head_ref: str, observation: _Observation,
              cleanup: Tuple[str, str]) -> LocalRun:
    with Repository(context.repository_path) as repo, repo.write() as tx:
        if tx.get_ref(head_ref) != context.pre_dispatch:
            raise ConflictError("coordination head moved before completion")
        pinned = _context(tx, context.repository_path, context.pre_dispatch,
                          context.attempt_id, context.publication_ref)
        if pinned != context:
            raise ProtocolError("completion context differs from pinned attempt")
        target = tx.get_ref(context.publication_ref)
        result, reason, detail = None, observation.reason, observation.detail
        parents = (context.pre_dispatch,)
        tree = _tree(tx, context.pre_dispatch)
        if target == context.pre_dispatch:
            if reason is None:
                reason, detail = "missing-publication", "child did not publish a result"
        else:
            try:
                result = _publication(tx, context, target)
            except (ProtocolError, DmlError) as error:
                if reason is None:
                    reason, detail = "invalid-publication", _detail(error)
            else:
                parents += (target,)
                tree["publication-" + context.attempt_id] = _tree(tx, target)["publication-" + context.attempt_id]
        kind = "success" if reason is None else "failure"
        fields = {"role": "local-" + kind + "-v1", "exit-code": observation.exit_code}
        subdags = []
        if reason is not None:
            fields.update(reason=reason, detail=detail)
        if result is not None:
            subdags.append(("result" if kind == "success" else "evidence", result))
        for name, diagnostic in (("stdout", observation.stdout), ("stderr", observation.stderr)):
            if diagnostic is not None:
                subdags.append((name, _put_diagnostic(tx, diagnostic)))
        outcome = _record(tx, fields["role"], fields, subdags)
        disposition, cleanup_detail = cleanup
        cleanup_fields = {"role": "local-cleanup-v1", "disposition": disposition, "detail": cleanup_detail}
        if disposition == "failed":
            cleanup_fields["scratch"] = context.scratch
        cleanup_dag = _record(tx, "local-cleanup-v1", cleanup_fields)
        final_attempt = _record(tx, context.attempt_id,
                                {"role": "local-attempt-v1", "publication-ref": context.publication_ref,
                                 "scratch": context.scratch, "status": "done"},
                                (("request", context.request), ("outcome", outcome), ("cleanup", cleanup_dag)))
        tree["attempt-" + context.attempt_id] = final_attempt
        commit = tx.put_commit(tx.put_tree(tree), parents=parents)
        tx.update_ref(head_ref, commit)
    return LocalRun(context, commit, final_attempt, kind, result if kind == "success" else None,
                    result if kind == "failure" else None, disposition)


def _run(repository_path, head_ref: str, scratch_dir, **request_args) -> LocalRun:
    path = _path(repository_path)
    scratch_parent = None if scratch_dir is None else _path(scratch_dir)
    scratch = os.path.abspath(tempfile.mkdtemp(prefix="dml-local-", dir=scratch_parent))
    context = None
    try:
        _recorded_path(scratch)
        context = _prepare(path, head_ref, scratch, **request_args)
        with Repository(path) as repo, repo.read() as tx:
            source, interpreter, timeout_ms = _binding(tx, context.binding)
        observation = _execute(context, source, interpreter, timeout_ms)
    except Exception as error:
        disposition, detail = _cleanup(scratch)
        raise LocalExecutionError(_detail(error) + ("; cleanup failed: " + detail if disposition == "failed" else ""),
                                  context) from error
    except BaseException:
        _cleanup(scratch)
        raise
    cleanup = _cleanup(scratch)
    try:
        return _finalize(context, head_ref, observation, cleanup)
    except Exception as error:
        raise LocalExecutionError(_detail(error), context) from error


def run_step(repository_path, *, head_ref: str, intent_uri: str, binding: ObjectId,
             inputs: ObjectId, scratch_dir=None) -> LocalRun:
    """Create a fresh request/attempt and execute once; no implicit reuse or retry."""
    if type(intent_uri) is not str:
        raise TypeError("intent_uri requires str")
    if not isinstance(binding, ObjectId) or not isinstance(inputs, ObjectId):
        raise TypeError("binding and inputs require ObjectId")
    return _run(repository_path, head_ref, scratch_dir, intent_uri=intent_uri, binding=binding, inputs=inputs)


def run_request(
    repository_path,
    *,
    head_ref: str,
    request_commit: ObjectId,
    request: ObjectId,
    scratch_dir=None,
) -> LocalRun:
    """Register an imported unreserved submission and create only T before dispatch.

    Exact head/submission/Q and absent local reservation are checked atomically.
    This local first-registration guard is not global exactly-once execution.
    """
    if not isinstance(request_commit, ObjectId) or not isinstance(request, ObjectId):
        raise TypeError("request_commit and request require ObjectId")
    return _run(
        repository_path,
        head_ref,
        scratch_dir,
        request=request,
        request_commit=request_commit,
    )


def retry_step(repository_path, *, head_ref: str, request: ObjectId, scratch_dir=None) -> LocalRun:
    """New attempt for the exact reserved request, without replacing old attempts."""
    if not isinstance(request, ObjectId):
        raise TypeError("request requires ObjectId")
    return _run(repository_path, head_ref, scratch_dir, request=request)
