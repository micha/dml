"""Replay Quint's create-ref requests against the C API and check the observed state."""

import argparse
import json
from pathlib import Path
import re
from shutil import copyfile
import subprocess
from tempfile import TemporaryDirectory


TIMEOUT = 15


def quint_state(quint, source, output, fields, init="init"):
    output.unlink(missing_ok=True)
    result = subprocess.run(
        [quint, "run", source, "--backend=typescript", f"--init={init}",
         "--max-samples=1", "--max-steps=0", "--seed=1", "--verbosity=0", f"--out-itf={output}"],
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    if result.returncode or not output.is_file():
        raise ValueError(f"Quint failed for {source.name}/{init}:\n{result.stdout}{result.stderr}")
    trace = json.loads(output.read_text(encoding="utf-8"))
    if (trace["#meta"]["status"] != "ok" or set(trace["vars"]) != fields
            or len(trace["states"]) != 1 or not fields <= trace["states"][0].keys()):
        raise ValueError(f"Expected one successful Quint ITF state for {source.name}/{init}")
    return trace["states"][0]


def read_histories(quint, source, output, init):
    histories = quint_state(quint, source, output, {"histories"}, init)["histories"]
    if not isinstance(histories, list) or not histories:
        raise ValueError("Quint must export at least one history")
    for history in histories:
        if not isinstance(history, list) or not history:
            raise ValueError(f"Expected a nonempty request list, got {history!r}")
        for request in history:
            if (not isinstance(request, dict) or set(request) != {"name", "target"}
                    or request["target"] not in ("A", "B") or not isinstance(request["name"], str)
                    or not re.fullmatch(r"[!-~]+", request["name"])):
                raise ValueError(f"Invalid create-ref request: {request!r}")
    return histories


def read_inventory(scanner, repo):
    output = subprocess.run([scanner, repo], stdout=subprocess.PIPE, text=True,
                            encoding="ascii", check=True, timeout=TIMEOUT).stdout
    inventory = {}
    for line in output.splitlines(keepends=True):
        match = re.fullmatch(r"((?:[0-9a-f]{2})+) ((?:[0-9a-f]{2})*)\n", line)
        if not match or match[1] in inventory:
            raise ValueError(f"Invalid LMDB inventory entry: {line!r}")
        inventory[match[1]] = match[2]
    if not inventory:
        raise ValueError("The scanner returned an empty inventory for an initialized repository")
    return inventory


def inventory_diff(before, after):
    changes = []
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key), after.get(key)
        if old != new:
            kind = "added" if old is None else "removed" if new is None else "modified"
            changes.append(dict(kind=kind, key=key, before=old or "", after=new or ""))
    return changes


def read_line(process, pattern):
    line = process.stdout.readline()
    match = re.fullmatch(pattern + r"\n", line)
    if not match:
        raise ValueError(f"Unexpected replay response {line!r}; expected {pattern}")
    return match.groups()


def observe(runner, scanner, repo, history):
    # The Meson test timeout bounds blocking reads from the interactive child.
    with subprocess.Popen([runner, repo], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          text=True, encoding="ascii") as process:
        try:
            target_a, target_b = read_line(process, r"READY ([0-9a-f]{32}) ([0-9a-f]{32})")
            if target_a == target_b:
                raise ValueError("The runner must seed two distinct commit IDs")
            targets = {"A": target_a, "B": target_b}
            before = read_inventory(scanner, repo)
            if (any(key.startswith(b"refs/heads/".hex()) for key in before)
                    or any(f"objects/commits/{target}".encode("ascii").hex() not in before
                           for target in targets.values())):
                raise ValueError("Expected an unreferenced fixture with both announced commits")
            evidence = []
            for request in history:
                name, target = request["name"], request["target"]
                process.stdin.write(f"{name} {target}\n")
                process.stdin.flush()
                created, committed = read_line(process, r"STEP ([a-z_]+) ([a-z_]+)")
                after = read_inventory(scanner, repo)
                evidence.append(dict(refKey=f"refs/heads/{name}".encode("ascii").hex(),
                                     targetId=targets[target], createStatus=created,
                                     commitStatus=committed, changes=inventory_diff(before, after)))
                before = after
            process.stdin.close()
            status = process.wait(timeout=TIMEOUT)
            if status != 0 or process.stdout.read():
                raise ValueError(f"Replay did not finish cleanly (exit status {status})")
            return evidence
        except BaseException:
            process.kill()
            raise


def quint_literal(value):
    # The generated module only contains lists, fixed field names, hex and status strings.
    if isinstance(value, str) and re.fullmatch(r"[a-z0-9_]*", value):
        return json.dumps(value)
    if isinstance(value, dict) and all(re.fullmatch(r"[a-z][a-zA-Z]*", key) for key in value):
        return "{ " + ", ".join(f"{key}: {quint_literal(item)}" for key, item in value.items()) + " }"
    if isinstance(value, list):
        return "List(" + ", ".join(map(quint_literal, value)) + ")"
    raise ValueError(f"Cannot encode Quint evidence value: {value!r}")


def evaluate(quint, rules, directory, observations):
    copyfile(rules, directory / "ref_rules.qnt")
    module = directory / "ref_observations.qnt"
    histories = ",\n    ".join(map(quint_literal, observations))
    module.write_text(
        'module ref_observations {\n'
        '  import ref_rules.* from "./ref_rules"\n'
        f'  pure val evidence: List[List[Attempt]] = List(\n    {histories}\n  )\n'
        '  var verdicts: List[List[str]]\n'
        '  var controls: bool\n'
        '  action init = all {\n'
        "    verdicts' = evidence.foldl(List(), (rows, row) => rows.append(historyVerdicts(row))),\n"
        "    controls' = controlsPass\n"
        '  }\n'
        "  action step = all { verdicts' = verdicts, controls' = controls }\n"
        '}\n', encoding="utf-8",
    )
    state = quint_state(quint, module, directory / "verdicts.itf.json", {"verdicts", "controls"})
    if state["controls"] is not True:
        raise ValueError("A fabricated observation escaped a Quint frame rule")
    return state["verdicts"]


def check_verdicts(histories, observations, verdicts):
    exercised = set()
    for history, evidence, results in zip(histories, observations, verdicts, strict=True):
        for request, attempt, verdict in zip(history, evidence, results, strict=True):
            if verdict not in ("created", "duplicate"):
                raise ValueError(f"Quint verdict {verdict}: {request}; observed {json.dumps(attempt)}")
            exercised.add(verdict)
        print(f"{history}: {', '.join(results)}")
    if exercised != {"created", "duplicate"}:
        raise ValueError(f"Expected to exercise both create and duplicate rules, got {exercised}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("quint", "runner", "scanner", "histories", "rules"):
        # Meson may pass ./ref_replay; Path alone would drop the ./ and use PATH.
        parser.add_argument(argument, type=lambda path: Path(path).absolute())
    args = parser.parse_args()
    with TemporaryDirectory(prefix="dml-create-ref-") as tmp:
        directory = Path(tmp)
        trace = directory / "histories.itf.json"
        directed = read_histories(args.quint, args.histories, trace, "init")
        changed = read_histories(args.quint, args.histories, trace, "changedInit")
        if directed == changed:
            raise ValueError("The changed Quint histories must send different requests to the runner")
        histories = directed + changed
        observations = [observe(args.runner, args.scanner, directory / f"repo-{i}", history)
                        for i, history in enumerate(histories)]
        verdicts = evaluate(args.quint, args.rules, directory, observations)
        check_verdicts(histories, observations, verdicts)
        print("Quint rejected the fabricated overwrite and unrelated write.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"create_ref check failed: {error}") from error
