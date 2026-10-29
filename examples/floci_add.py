"""Trusted captured addition with explicitly declared local S3 gates.

Imports/runtime/service contents are not captured by this entry script. Gate waits
are finite example policy, not adapter polling. No Docker/test/fault hooks.
"""

import http.client
import re
import sys
import time
from urllib.parse import quote, urlsplit

import daggerml as d
from daggerml.local import child_context, publish_result


def main():
    context = child_context()
    with d.Repository(context.repository_path) as repository, repository.read() as tx:

        def scalar(name):
            return tx.get_datum(
                tx.get_node(tx.lookup_node(context.inputs, name)).datum
            ).value

        left, right = scalar("left"), scalar("right")
        endpoint, bucket, gate = scalar("endpoint"), scalar("bucket"), scalar("gate")
        exit_code = scalar("exit-code")
    if type(left) is not int or type(right) is not int or type(exit_code) is not int:
        raise TypeError("addition inputs/exit-code require int")
    if type(endpoint) is not str or type(bucket) is not str or type(gate) is not str:
        raise TypeError("gate endpoint/bucket/key require str")
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
        raise ValueError("example gate requires canonical explicit local http endpoint")
    if (
        re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket) is None
        or ".." in bucket
    ):
        raise ValueError("example bucket outside local profile")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}", gate) is None or any(
        part in ("", ".", "..") for part in gate.split("/")
    ):
        raise ValueError("example gate requires normalized bounded key segments")
    prefix = "/" + "/".join(quote(part, safe="") for part in (bucket, *gate.split("/")))

    def wait(key):
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            connection = http.client.HTTPConnection(
                remote.hostname, remote.port, timeout=5
            )
            response = None
            try:
                connection.request(
                    "GET",
                    prefix + "/" + quote(key, safe=""),
                    headers={
                        "Connection": "close",
                        "Authorization": "AWS4-HMAC-SHA256 Credential=test/19700101/us-east-1/s3/aws4_request, SignedHeaders=host, Signature=00",
                        "X-Amz-Date": "19700101T000000Z",
                    },
                )
                response = connection.getresponse()
                data = response.read(8193)
                if len(data) > 8192:
                    raise ValueError("gate response exceeds example profile")
                if response.status == 200:
                    return
                if response.status != 404:
                    raise ValueError("gate response status error")
            finally:
                try:
                    if response is not None:
                        response.close()
                finally:
                    connection.close()
            time.sleep(0.15)
        raise TimeoutError("finite declared S3 gate expired")

    wait("gate1")
    with d.Repository(context.repository_path) as repository, repository.write() as tx:
        result = tx.put_literal(tx.put_datum(left + right))
        publish_result(
            tx, context, tx.put_dag(root=result, bindings={"result": result})
        )
    wait("gate2")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
