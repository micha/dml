"""Standalone trusted consumer: actual result sub-DAG times literal I64 factor.

Producer is an opaque immutable occurrence witness, never a dispatch instruction.
Finite declared S3 gates/artifact assertions are example policy, not runtime hooks
or complete environment capture. No imports of uninstalled example/fixture helpers.
"""

import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import quote, urlsplit

import daggerml as d
from daggerml.local import child_context, publish_result


def main():
    context = child_context()
    with d.Repository(context.repository_path) as repository, repository.read() as tx:
        value = tx.get_node(tx.lookup_node(context.inputs, "value"))
        producer = tx.get_node(tx.lookup_node(context.inputs, "producer"))
        if not isinstance(value, d.SubDAGNode) or not isinstance(
            producer, d.SubDAGNode
        ):
            raise ValueError("value/producer must be sub-DAG references")
        tx.get_dag(producer.dag)  # Typed read only; no role codec or historical paths.
        root = tx.get_node(tx.get_dag(value.dag).root)
        if not isinstance(root, d.LiteralNode):
            raise ValueError("value result requires a literal I64 root")
        number = tx.get_datum(root.datum)
        if number.kind != "i64":
            raise ValueError("value result requires a literal I64 root")

        def scalar(name, kind):
            node = tx.get_node(tx.lookup_node(context.inputs, name))
            if not isinstance(node, d.LiteralNode):
                raise ValueError("consumer scalar input must be literal")
            datum = tx.get_datum(node.datum)
            if datum.kind != kind:
                raise ValueError("consumer scalar input has wrong datum kind")
            return datum.value

        factor = scalar("factor", "i64")
        exit_code = scalar("exit-code", "i64")
        endpoint, bucket, gate = (
            scalar(name, "string") for name in ("endpoint", "bucket", "gate")
        )
        artifacts = scalar("artifacts", "bytes")
    remote = urlsplit(endpoint)
    host = remote.hostname
    spelling = "[" + host + "]" if host and ":" in host else host
    if (
        remote.scheme != "http"
        or remote.port is None
        or not 1 <= remote.port <= 65535
        or remote.path
        or remote.query
        or remote.fragment
        or remote.username is not None
        or remote.password is not None
        or not host
        or re.fullmatch(r"[a-z0-9][a-z0-9.:-]*", host) is None
        or endpoint != "http://" + spelling + ":" + str(remote.port)
    ):
        raise ValueError(
            "consumer gate requires canonical explicit local http endpoint"
        )
    if (
        re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket) is None
        or ".." in bucket
    ):
        raise ValueError("consumer bucket outside local profile")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}", gate) is None or any(
        part in ("", ".", "..") for part in gate.split("/")
    ):
        raise ValueError("consumer gate requires normalized bounded key segments")
    inventory = json.loads(artifacts) if artifacts else []
    site = Path(d.__file__).resolve().parent.parent
    for row in inventory:
        if (
            hashlib.sha256((site / row["file"]).read_bytes()).hexdigest()
            != row["sha256"]
        ):
            raise ValueError("declared installed artifact differs")
    prefix = "/" + "/".join(quote(part, safe="") for part in (bucket, *gate.split("/")))

    def call(method, key, data=b""):
        connection = http.client.HTTPConnection(remote.hostname, remote.port, timeout=5)
        response = None
        try:
            connection.request(
                method,
                prefix + "/" + quote(key, safe=""),
                data,
                headers={
                    "Connection": "close",
                    "Authorization": "AWS4-HMAC-SHA256 Credential=test/19700101/us-east-1/s3/aws4_request, SignedHeaders=host, Signature=00",
                    "X-Amz-Date": "19700101T000000Z",
                },
            )
            response = connection.getresponse()
            body = response.read(8193)
            if len(body) > 8192:
                raise ValueError("consumer gate response exceeds example profile")
            return response.status
        finally:
            try:
                if response is not None:
                    response.close()
            finally:
                connection.close()

    def wait(key):
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            status = call("GET", key)
            if status == 200:
                return
            if status != 404:
                raise ValueError("consumer gate response status error")
            time.sleep(0.15)
        raise TimeoutError("finite declared consumer S3 gate expired")

    identity = dict(
        python=sys.executable,
        artifacts=inventory,
        value=str(value.dag),
        producer=str(producer.dag),
        factor=factor,
    )
    if "AWS_BATCH_JOB_ID" in os.environ:
        identity.update(
            job_id=os.environ["AWS_BATCH_JOB_ID"],
            attempt=os.environ["AWS_BATCH_JOB_ATTEMPT"],
        )
        security_fields = {
            "Uid",
            "Gid",
            "CapInh",
            "CapPrm",
            "CapEff",
            "CapBnd",
            "NoNewPrivs",
            "Seccomp",
        }
        identity["security"] = {
            line.split(":", 1)[0]: line.split(":", 1)[1].strip()
            for line in Path("/proc/self/status").read_text().splitlines()
            if line.split(":", 1)[0] in security_fields
        }
    if call("PUT", "started", json.dumps(identity).encode()) != 200:
        raise ValueError("consumer start evidence publication failed")
    wait("gate1")
    with d.Repository(context.repository_path) as repository, repository.write() as tx:
        result = tx.put_literal(tx.put_datum(number.value * factor))
        publish_result(
            tx, context, tx.put_dag(root=result, bindings={"result": result})
        )
    wait("gate2")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
