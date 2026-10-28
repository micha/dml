"""Endpoint-driven SSH progress with external remote-gate control, no Docker import.

prepare NEW_STORY HOST PORT USER KEY KNOWN_HOSTS REMOTE_PYTHON REMOTE_ROOT REMOTE_GATE
own SAVED_JOB                       # application retains foreground execution client
observe SAVED_JOB NEW_PACKET         # short-lived read-only client
receive CALLER SAVED_JOB PACKET REF  # endpoint need not exist

The external fixture/application controller creates/releases the declared remote
initial-release/publication-release gates. No shared mounts or runtime gate action.
"""

import json
from pathlib import Path
import subprocess
import sys

from daggerml import Datum, Repository
from daggerml.exchange import (
    prepare_exchange,
    record_exchange_request,
    receive_observation,
)
from daggerml.local import put_local_binding, run_step
from daggerml.ssh import (
    SSHRemote,
    load_ssh_exchange,
    save_ssh_exchange,
    stage_ssh_exchange,
    start_ssh_exchange,
    observe_ssh_exchange,
)


# Captured trusted source; gate IO is declared application policy, not a helper hook.
SLOW_ADD = b"""import sys,time,daggerml as d
from pathlib import Path
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.read() as t:
 def value(name): return t.get_datum(t.get_node(t.lookup_node(c.inputs,name)).datum).value
 directory=Path(value('gate'))
 expected=value('interpreter')
 assert sys.executable==expected
 assert d.__file__.startswith('/opt/dml/lib/')
 assert d._core.__file__.startswith('/opt/dml/lib/')
 left,right=value('left'),value('right')
 assert type(left) is int and type(right) is int
 failure=value('fail')
print('installed-ssh-progress-child',sys.executable,d.__file__,flush=True)
def gate(phase):
 deadline=time.monotonic()+60
 while not (directory/(phase+'-release')).exists():
  if time.monotonic()>deadline: raise TimeoutError('remote example gate expired')
  time.sleep(.02)
gate('initial')
with d.Repository(c.repository_path) as r,r.write() as t:
 n=t.put_literal(t.put_datum(left+right))
 publish_result(t,c,t.put_dag(root=n,bindings={'result':n}))
gate('publication')
if failure: raise RuntimeError('after publication')
"""


def prepare(directory, remote, gate):
    directory = Path(directory).resolve()
    directory.mkdir()
    caller = directory / "caller.dml"
    warm_source = Path(__file__).with_name("local_add.py").read_bytes()
    with Repository(caller, create=True) as repo, repo.write() as tx:
        nodes = {
            name: tx.put_literal(tx.put_datum(value))
            for name, value in (
                ("left", 4),
                ("right", 7),
                ("gate", gate),
                ("interpreter", remote.python),
                ("fail", False),
            )
        }
        inputs = tx.put_dag(root=nodes["left"], bindings=nodes)
        binding = put_local_binding(
            tx, source=SLOW_ADD, interpreter=remote.python, timeout_ms=150000
        )
        warm_binding = put_local_binding(
            tx, source=warm_source, interpreter=sys.executable, timeout_ms=10000
        )
        hidden = tx.put_datum("composite-only child")
        keep = tx.put_dag(
            root=tx.put_literal(
                tx.put_datum(
                    Datum.map(
                        [
                            (
                                tx.put_datum(Datum.list([hidden, hidden])),
                                tx.put_datum(Datum.set([hidden])),
                            )
                        ]
                    )
                )
            )
        )
        base = tx.put_commit(
            tx.put_tree({"binding": binding, "inputs": inputs, "keep": keep})
        )
        sentinel = tx.put_commit(tx.put_tree({"sentinel": keep}))
        tx.create_ref("main", base)
        tx.create_ref("sentinel", sentinel)
    warm = run_step(
        caller,
        head_ref="main",
        intent_uri="urn:example:prior-add",
        binding=warm_binding,
        inputs=inputs,
        scratch_dir=directory,
    )
    base = warm.final_commit
    unused = record_exchange_request(
        caller,
        commit=base,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:example:add-i64",
        ref="unstarted",
    )
    recorded = record_exchange_request(
        caller,
        commit=base,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:example:add-i64",
        ref="submission-1",
    )
    workspace = directory / "input"
    spec = prepare_exchange(
        caller,
        commit=recorded.commit,
        request=recorded.request,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri=recorded.intent_uri,
        worker_ref="work",
        workspace=workspace,
    )
    job = stage_ssh_exchange(
        remote,
        workspace=workspace,
        expected=spec,
        control=directory / "control",
        timeout_ms=20000,
    )
    save_ssh_exchange(directory / "saved", job)
    return {
        "base": str(base),
        "request": str(recorded.request),
        "unstarted": str(unused.request),
        "saved": str(directory / "saved"),
    }


def own(saved):
    launch = start_ssh_exchange(load_ssh_exchange(saved), connect_timeout_ms=10000)
    # The application retains the actual owner throughout; no timeout kill/disconnect.
    # Normal trusted child gates/binding are finite. If local reaping is uncertain,
    # retain the application rather than exiting and leaving an unowned connection.
    while True:
        try:
            code = launch.wait(timeout=180)
            return {"local_status": code}
        except (subprocess.TimeoutExpired, OSError):
            if launch.process.poll() is not None:
                raise
            print(
                "execution owner retained; external investigation/gate release required",
                file=sys.stderr,
                flush=True,
            )


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    if not args:
        raise ValueError("expected prepare/own/observe/receive mode")
    mode, *values = args
    if mode == "prepare" and len(values) == 9:
        directory, host, port, user, key, hosts, python, root, gate = values
        result = prepare(
            directory, SSHRemote(host, int(port), user, key, hosts, python, root), gate
        )
    elif mode == "own" and len(values) == 1:
        result = own(values[0])
    elif mode == "observe" and len(values) == 2:
        saved, packet = values
        got = observe_ssh_exchange(
            load_ssh_exchange(saved), packet=packet, timeout_ms=20000
        )
        result = {
            "lifecycle": got.lifecycle,
            "phase": got.phase,
            "commit": None if got.snapshot is None else str(got.snapshot.commit),
        }
    elif mode == "receive" and len(values) == 4:
        caller, saved, packet, ref = values
        got = receive_observation(
            caller, packet=packet, expected=load_ssh_exchange(saved).expected, ref=ref
        )
        result = {
            "lifecycle": got.lifecycle,
            "phase": got.phase,
            "commit": str(got.commit),
            "ref": got.ref,
        }
    else:
        raise ValueError("invalid progress mode/arguments")
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
