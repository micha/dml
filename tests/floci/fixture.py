"""Explicit owned cached local fixture control, NEVER collected/default-started.

Trusted socket grants daemon-root-equivalent authority. No pull/prune/global changes.
Stop requires correlated writer absence; retains evidence/resources on uncertainty.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ["docker", "--host", "unix:///var/run/docker.sock"]
FLOCI = "docker.io/floci/floci@sha256:09b72c45f333019adecb302e79c6b746e290135f528016c8514618bc7ab02344"
REVISION = "ee15f502bfc017861b67b076b82e1ccd032c7129"
APPLICATION_SHA = "99f54d4c62c72bfe7a7282d1e37c2613d6486f02730686cad1417eb4c81bc70a"

API = r"""
import http.client,json,sys
query=json.loads(sys.argv[1]);connection=http.client.HTTPConnection('floci',4566,timeout=5)
try:
 connection.request(query['method'],query['path'],query['body'].encode(),headers={'Content-Type':'application/json','Connection':'close','Authorization':'AWS4-HMAC-SHA256 Credential=test/19700101/us-east-1/'+query['service']+'/aws4_request, SignedHeaders=host, Signature=00','X-Amz-Date':'19700101T000000Z',**query.get('headers',{})})
 response=connection.getresponse();body=response.read(1048577)
 assert len(body)<=1048576
 print(json.dumps({'status':response.status,'body':body.decode()}))
finally:
 connection.close()
"""
PROVENANCE = r"""
import hashlib,json,sys
from pathlib import Path
import daggerml
site=Path(daggerml.__file__).resolve().parent.parent
expected=json.loads(Path('/work/artifacts.json').read_bytes())
for row in expected:
 assert hashlib.sha256((site/row['file']).read_bytes()).hexdigest()==row['sha256']
assert sys.executable=='/opt/dml/bin/python'
assert '/python/daggerml/' not in str(site)
print(json.dumps({'python':sys.executable,'package':str(site),'artifacts':expected}))
"""


def service_keys(app):
    current, found = None, []
    for line in app.split("\n  services:\n", 1)[1].splitlines():
        key = re.fullmatch(r"    ([a-z0-9-]+):(?:\s*#.*)?", line)
        if key:
            current = key.group(1)
        elif re.match(r"      enabled:\s*(true|false)(?:\s*#.*)?$", line):
            assert current is not None and current not in found
            found.append(current)
        elif line and not line.startswith("    ") and not line.lstrip().startswith("#"):
            current = None
    assert len(found) == 128 and {"batch", "s3", "cloudwatchlogs", "iam", "ec2"} <= set(
        found
    )
    return found


class Fixture:
    def __init__(self, root):
        self.root = Path(root).resolve()
        assert self.root.is_relative_to(ROOT / "build")
        assert self.root not in (ROOT / "build/check", ROOT / "build/coverage")
        assert (self.root / ".dml-floci-fixture").is_file()
        self.state_path = self.root / "fixture.json"
        self.state = (
            json.loads(self.state_path.read_bytes()) if self.state_path.exists() else {}
        )
        self.calls_path = self.root / "commands.json"
        self.calls = (
            json.loads(self.calls_path.read_bytes()) if self.calls_path.exists() else []
        )

    def save(self):
        self.state_path.write_text(json.dumps(self.state, indent=2))

    def docker(self, *args, timeout=40):
        command = DOCKER + list(map(str, args))
        try:
            result = subprocess.run(command, capture_output=True, timeout=timeout)
        except BaseException:
            self.calls.append(dict(command=command, exit=None, disposition="unknown"))
            self.calls_path.write_text(json.dumps(self.calls, indent=2))
            raise
        self.calls.append(
            dict(
                command=command,
                exit=result.returncode,
                stdout=result.stdout.decode(errors="replace"),
                stderr=result.stderr.decode(errors="replace"),
            )
        )
        self.calls_path.write_text(json.dumps(self.calls, indent=2))
        if result.returncode:
            raise RuntimeError("owned Docker operation failed; retained evidence")
        return (
            result.stdout + result.stderr
            if args and args[0] == "logs"
            else result.stdout
        )

    def inspect(self, name):
        return json.loads(self.docker("inspect", name))[0]

    def clients_stopped(self):
        expected = {self.state["service_id"]}
        for client in self.state.get("clients", []):
            assert (
                client["id"] is not None
            ), "client create acknowledgement uncertain; retain fixture"
            value = self.inspect(client["id"])
            assert value["Id"] == client["id"] and value["Name"] == "/" + client["name"]
            assert value["Config"]["Labels"]["dml.owner"] == self.state["owner"]
            assert not value["State"][
                "Running"
            ], "API client disposition unknown; retain fixture"
            expected.add(client["id"])
        census = set(
            self.docker(
                "ps",
                "-aq",
                "--no-trunc",
                "--filter",
                "label=dml.owner=" + self.state["owner"],
            )
            .decode()
            .split()
        )
        assert census == expected, "untracked owned client/resource; retain fixture"

    def job_intent(self, token, **description):
        assert not any(row["token"] == token for row in self.state["jobs"])
        row = dict(id=None, token=token, **description)
        self.state["jobs"].append(row)
        self.save()
        return row

    def jobs_terminal(self):
        for row in self.state.get("jobs", []):
            assert (
                row["id"] is not None
            ), "submission acknowledgement unknown; exact out-of-band correlation required"
            result = self.batch("DescribeJobs", {"jobs": [row["id"]]})
            assert len(result["jobs"]) == 1
            job = result["jobs"][0]
            assert job["jobId"] == row["id"] and job["jobName"] == "dml-" + row["token"]
            assert job["status"] in (
                "SUCCEEDED",
                "FAILED",
            ), "queued/starting/running job remains an owned writer"
            assert job["retryStrategy"]["attempts"] == 1 and len(job["attempts"]) == 1
            row["terminal_proof"] = job
        self.save()

    def _child_ids(self):
        return (
            self.docker(
                "ps", "-aq", "--filter", "label=floci_namespace=" + self.state["owner"]
            )
            .decode()
            .split()
        )

    def children(self):
        ids = self._child_ids()
        if not ids:
            return []
        try:
            inspected = self.docker("inspect", *ids)
        except RuntimeError:
            # One bounded fresh census can prove naturally retired exact IDs.
            # A still-present OR newly-present child remains uncertain: propagate
            # original inspect failure, never retry-until-pass or swallow it.
            if not self._child_ids():
                return []
            raise
        return json.loads(inspected)

    def client(
        self,
        code,
        *,
        arguments=(),
        copies=(),
        outputs=(),
        timeout=40,
        image=None,
        background=False,
    ):
        number = len(self.state.setdefault("clients", []))
        name = self.state["name"] + "-client-" + str(number)
        row = dict(name=name, id=None, create_intent=True)
        self.state["clients"].append(row)
        self.save()
        identifier = (
            self.docker(
                "create",
                "--pull=never",
                "--name",
                name,
                "--label",
                "dml.owner=" + self.state["owner"],
                "--label",
                "dml.fixture=iteration11",
                "--network",
                self.state["network"],
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--memory",
                "512m",
                "--cpus",
                ".5",
                "--pids-limit",
                "64",
                "--no-healthcheck",
                "--entrypoint",
                "/opt/dml/bin/python",
                image or self.state["image"],
                "-c",
                code,
                *arguments,
            )
            .decode()
            .strip()
        )
        row["id"] = identifier
        self.save()
        for source, target in copies:
            self.docker("cp", source, identifier + ":" + target)
        if background:
            self.docker("start", identifier)
            return identifier
        stdout = self.docker("start", "-a", identifier, timeout=timeout)
        value = self.inspect(identifier)
        assert (
            not value["State"]["Running"] and value["State"]["ExitCode"] == 0
        ), "client error retained"
        assert value["Config"]["Labels"]["dml.owner"] == self.state["owner"]
        for source, target in outputs:
            self.docker("cp", identifier + ":" + source, target)
        return stdout

    def finish_client(self, identifier, *, outputs=(), timeout=40):
        assert any(row["id"] == identifier for row in self.state["clients"])
        self.docker("wait", identifier, timeout=timeout)
        value = self.inspect(identifier)
        assert not value["State"]["Running"] and value["State"]["ExitCode"] == 0
        assert (
            value["Id"] == identifier
            and value["Config"]["Labels"]["dml.owner"] == self.state["owner"]
        )
        for source, target in outputs:
            self.docker("cp", identifier + ":" + source, target)
        return self.docker("logs", identifier)

    def api(self, method, path, body="", service="s3", headers=None):
        query = json.dumps(
            dict(
                method=method,
                path=path,
                body=body,
                service=service,
                headers=headers or {},
            )
        )
        result = json.loads(self.client(API, arguments=(query,)))
        return result["status"], result["body"]

    def batch(self, action, body):
        status, raw = self.api(
            "POST", "/v1/" + action.lower(), json.dumps(body), "batch"
        )
        assert status == 200, "fixture Batch API failed"
        return json.loads(raw)

    def start(self, application):
        assert not self.state, "fixture already allocated"
        owner = uuid.uuid4().hex
        name = "dml-iteration11-" + owner
        image = (self.root / "image.txt").read_text().strip()
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", image)
        self.docker("image", "inspect", image)
        floci = json.loads(self.docker("image", "inspect", FLOCI))[0]
        assert (
            floci["Config"]["Labels"]["org.opencontainers.image.revision"] == REVISION
        )
        assert floci["Config"]["Labels"]["org.opencontainers.image.version"] == "2.3.0"
        app = Path(application).read_bytes()
        assert hashlib.sha256(app).hexdigest() == APPLICATION_SHA
        keys = service_keys(app.decode())
        assert Path("/var/run/docker.sock").stat().st_gid == 131
        assert (
            self.docker("info", "--format", "{{.Name}} {{.DockerRootDir}}")
            .decode()
            .strip()
            == "michas-robots /work/docker"
        )
        labels = ["--label", "dml.owner=" + owner, "--label", "dml.fixture=iteration11"]
        network, volume = name + "-net", name + "-data"
        self.state = dict(
            owner=owner,
            name=name,
            network=network,
            volume=volume,
            image=image,
            clients=[],
            jobs=[],
            stopped=False,
        )
        self.save()
        self.docker(
            "network", "create", "--internal", "--driver", "bridge", *labels, network
        )
        self.docker("volume", "create", *labels, volume)
        env = {
            "FLOCI_SERVICES_"
            + key.replace("-", "_").upper()
            + "_ENABLED": (
                "true" if key in {"batch", "s3", "cloudwatchlogs", "iam"} else "false"
            )
            for key in keys
        }
        env.update(
            FLOCI_SERVICES_BATCH_RUNNER_MODE="docker",
            FLOCI_SERVICES_BATCH_DOCKER_NETWORK=network,
            FLOCI_DOCKER_RESOURCE_NAMESPACE=owner,
            FLOCI_HOSTNAME="floci",
            FLOCI_STORAGE_MODE="persistent",
            FLOCI_STORAGE_PERSISTENT_PATH="/app/data",
            FLOCI_DNS_CONTAINER_FALLBACK_ENABLED="false",
            FLOCI_DNS_CONTAINER_FALLBACK_SERVERS="127.0.0.1",
            FLOCI_DNS_SPOOF_AWS_ENDPOINTS="false",
            FLOCI_TLS_ENABLED="false",
            LOCALSTACK_PARITY="false",
            FLOCI_SERVICES_ECS_TASK_ROLE_CREDENTIALS_ENABLED="false",
            FLOCI_SERVICES_EC2_ENABLED="false",
        )
        env_args = [
            arg for key, value in env.items() for arg in ("-e", key + "=" + value)
        ]
        identifier = (
            self.docker(
                "create",
                "--pull=never",
                "--name",
                name,
                *labels,
                "--network",
                network,
                "--network-alias",
                "floci",
                "--no-healthcheck",
                "--user",
                "1001:0",
                "--group-add",
                "131",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--memory",
                "512m",
                "--cpus",
                "1",
                "--pids-limit",
                "256",
                "--log-driver",
                "json-file",
                "--log-opt",
                "max-size=1m",
                "--log-opt",
                "max-file=2",
                "--mount",
                "type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock",
                "--mount",
                "type=volume,src=" + volume + ",dst=/app/data",
                *env_args,
                FLOCI,
                "/app/application",
                "-Dquarkus.http.host=0.0.0.0",
                "-Dfloci.security.allow-unsafe-network-exposure=true",
            )
            .decode()
            .strip()
        )
        self.state["service_id"] = identifier
        self.save()
        self.docker("start", identifier)
        time.sleep(3)
        service = self.inspect(identifier)
        net = json.loads(self.docker("network", "inspect", network))[0]
        vol = json.loads(self.docker("volume", "inspect", volume))[0]
        assert net["Internal"] and net["Labels"]["dml.owner"] == owner
        assert vol["Labels"]["dml.owner"] == owner
        host = service["HostConfig"]
        assert (
            service["State"]["Running"]
            and not host["PortBindings"]
            and host["NetworkMode"] == network
        )
        assert service["Config"]["User"] == "1001:0" and host["GroupAdd"] == ["131"]
        assert (
            host["CapDrop"] == ["ALL"]
            and host["SecurityOpt"] == ["no-new-privileges"]
            and not host["Privileged"]
        )
        assert (
            host["Memory"] == 512 * 1024**2
            and host["NanoCpus"] == 1000000000
            and host["PidsLimit"] == 256
        )
        assert len(service["Mounts"]) == 2 and {
            (v["Type"], v["Destination"]) for v in service["Mounts"]
        } == {("bind", "/var/run/docker.sock"), ("volume", "/app/data")}
        for mount in service["Mounts"]:
            assert (
                mount["Source"] == "/var/run/docker.sock"
                if mount["Type"] == "bind"
                else mount["Name"] == volume
            )
        actual_env = dict(row.split("=", 1) for row in service["Config"]["Env"])
        assert all(actual_env[key] == value for key, value in env.items())
        logs = self.docker("logs", identifier).decode()
        enabled = re.findall(r"Enabled services: \[([^\]]*)\]", logs)
        assert enabled and set(enabled[-1].split(", ")) == {
            "batch",
            "s3",
            "cloudwatchlogs",
            "iam",
        }
        bindings = self.docker(
            "exec",
            identifier,
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
        (self.root / "pre-submit-service.log").write_text(logs)
        (self.root / "pre-submit-bindings.txt").write_text(bindings)
        self.state["profile"] = dict(
            service=service,
            network=net,
            volume=vol,
            released_service_keys=keys,
            enabled=enabled[-1],
            no9169=True,
        )
        self.save()
        provenance = self.client(
            PROVENANCE, copies=((self.root / "artifacts.json", "/work/artifacts.json"),)
        )
        (self.root / "image-installed-provenance.json").write_bytes(provenance)
        self.batch(
            "CreateComputeEnvironment",
            dict(computeEnvironmentName="local", type="UNMANAGED"),
        )
        self.batch(
            "CreateJobQueue",
            dict(
                jobQueueName="local",
                priority=1,
                computeEnvironmentOrder=[dict(order=1, computeEnvironment="local")],
            ),
        )
        self.batch(
            "RegisterJobDefinition",
            dict(
                jobDefinitionName="installed",
                type="container",
                containerProperties=dict(
                    image=image,
                    command=["/opt/dml/bin/python", "-m", "daggerml.floci_worker"],
                    resourceRequirements=[dict(type="MEMORY", value="512")],
                ),
                retryStrategy=dict(attempts=1),
            ),
        )
        assert self.api("PUT", "/dml-local")[0] == 200
        # Actual runtime conditional-write gate, not only pinned source capability.
        key = "/dml-local/profile/" + owner
        assert (
            self.api("PUT", key, "original", headers={"If-None-Match": "*"})[0] == 200
        )
        assert self.api("PUT", key, "changed", headers={"If-None-Match": "*"})[0] == 412
        assert self.api("GET", key) == (200, "original")
        self.state["conditional_put_verified"] = True
        self.save()

    def resume(self):
        assert self.state["stopped"], "resume only an explicitly stopped owned fixture"
        self.clients_stopped()
        assert not self.children()
        for row in self.state["jobs"]:
            proof = row["terminal_proof"]
            assert proof["jobId"] == row["id"] and proof["status"] in (
                "SUCCEEDED",
                "FAILED",
            )
        service = self.inspect(self.state["service_id"])
        assert (
            not service["State"]["Running"]
            and service["Config"]["Labels"]["dml.owner"] == self.state["owner"]
        )
        self.docker("start", service["Id"])
        time.sleep(3)
        assert self.inspect(service["Id"])["State"]["Running"]
        self.state["stopped"] = False
        self.save()

    def stop(self):
        self.jobs_terminal()
        self.clients_stopped()
        assert (
            not self.children()
        ), "owned Batch writer disposition unproved; retain fixture"
        service = self.inspect(self.state["service_id"])
        assert service["Config"]["Labels"]["dml.owner"] == self.state["owner"]
        self.docker("stop", "-t", "20", service["Id"])
        assert not self.inspect(service["Id"])["State"]["Running"]
        assert not self.children()
        (self.root / "stopped-service.log").write_bytes(
            self.docker("logs", service["Id"])
        )
        number = len(list(self.root.glob("service-data*")))
        archive = self.root / (
            "service-data" if number == 0 else "service-data-" + str(number)
        )
        self.docker("cp", service["Id"] + ":/app/data", archive)
        self.state["stopped"] = True
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "stop"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--application", type=Path)
    args = parser.parse_args()
    fixture = Fixture(args.root)
    if args.action == "start":
        assert args.application is not None
        fixture.start(args.application)
    else:
        fixture.stop()


if __name__ == "__main__":
    main()
