"""Interpret Quint request histories against native DML and report Quint's verdicts."""

import argparse
import json
from pathlib import Path
import re
from reprlib import repr as short_repr
from shutil import copyfile
import subprocess
from tempfile import TemporaryDirectory

from replay_core import Suite


# The transfer model checks hundreds of steps with exact packed rows. Meson
# also bounds the total replay and verdict time.
TIMEOUT = 60


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
    match trace:
        case {"#meta": {"status": "ok"}, "vars": list(names), "states": [dict(state)]}:
            if all(isinstance(name, str) for name in names) and set(names) == fields <= state.keys():
                return state
    raise ValueError(f"Expected one successful Quint ITF state for {source.name}/{init}")


def read_histories(quint, source, output, initializers):
    histories = []
    groups = []
    for init in initializers:
        group = quint_state(quint, source, output, {"histories"}, init)["histories"]
        if not isinstance(group, list) or not group:
            raise ValueError(f"{init}: expected a nonempty list of histories")
        if group in groups:
            raise ValueError(f"{init}: expected different requests from previous initializers")
        for index, history in enumerate(group, 1):
            if not isinstance(history, list) or not history:
                raise ValueError(f"{init}, history {index}: expected a nonempty list of requests")
            for step, request in enumerate(history, 1):
                if (not isinstance(request, dict) or set(request) != {"op", "args"}
                        or not isinstance(request["op"], str)
                        or not re.fullmatch(r"[a-z][a-z0-9_]*", request["op"])
                        or not isinstance(request["args"], list)
                        or not all(isinstance(arg, str) for arg in request["args"])):
                    raise ValueError(f"{init}, history {index}, step {step}: "
                                     f"invalid request {short_repr(request)}")
        groups.append(group)
        histories.extend(group)
    if not histories:
        raise ValueError("Expected at least one history initializer")
    return histories


def replay_history(suite, directory, requests):
    directory.mkdir()
    with suite.history(directory) as replay:
        attempts = []
        for step, request in enumerate(requests, 1):
            operation = replay.operations.get(request["op"])
            context = f"{directory.name}, step {step}: {short_repr(request)}"
            if operation is None:
                raise ValueError(f"{context}: unknown operation")
            try:
                attempt = operation(*request["args"])
            except Exception as error:
                raise ValueError(f"{context}: {error}") from error
            if not isinstance(attempt, dict):
                raise ValueError(f"{context}: operation must return an observation record")
            attempts.append(attempt)
        return {"attempts": attempts}


def quint_literal(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    # Quint 0.33.1 preserves backslashes in source string literals. Embed only
    # printable ASCII without quotes or backslashes; adapters can hex-encode bytes.
    if isinstance(value, str) and re.fullmatch(r"[\x20-\x21\x23-\x5b\x5d-\x7e]*", value):
        return json.dumps(value)
    if isinstance(value, dict) and all(re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", key) for key in value):
        return "{ " + ", ".join(f"{key}: {quint_literal(item)}" for key, item in value.items()) + " }"
    if isinstance(value, list):
        return "List(" + ", ".join(map(quint_literal, value)) + ")"
    raise ValueError(f"Cannot encode Quint evidence value: {short_repr(value)}")


def evaluate(quint, rules, directory, observations, imports=()):
    # The rule module exports a common interface; Observation is suite-specific.
    if not re.fullmatch(r"[a-z][a-z0-9_]*", rules.stem):
        raise ValueError(f"Invalid Quint rules module name: {rules.stem!r}")
    for source in (rules, *imports):
        destination = directory / source.name
        if destination.exists() or source.name == "trace_observations.qnt":
            raise ValueError(f"Duplicate or reserved Quint module path: {source.name}")
        copyfile(source, destination)
    module = directory / "trace_observations.qnt"
    rows = ",\n    ".join(map(quint_literal, observations))
    module.write_text(
        'module trace_observations {\n'
        f'  import {rules.stem}.* from "./{rules.stem}"\n'
        f'  pure val evidence: List[Observation] = List(\n    {rows}\n  )\n'
        '  var verdicts: List[List[str]]\n'
        '  var accepting: List[List[bool]]\n'
        '  var coverage: bool\n'
        '  var controls: bool\n'
        '  action init = {\n'
        '    val results = evidence.foldl(List(), (out, row) => out.append(historyVerdicts(row)))\n'
        '    all {\n'
        "      verdicts' = results,\n"
        "      accepting' = results.foldl(List(), (out, row) =>\n"
        '        out.append(row.foldl(List(), (flags, verdict) => flags.append(verdictAccepted(verdict))))),\n'
        "      coverage' = coveragePass(evidence, results),\n"
        "      controls' = controlsPass\n"
        '    }\n'
        '  }\n'
        "  action step = all { verdicts' = verdicts, accepting' = accepting,\n"
        "                      coverage' = coverage, controls' = controls }\n"
        '}\n', encoding="utf-8",
    )
    return quint_state(quint, module, directory / "verdicts.itf.json",
                       {"verdicts", "accepting", "coverage", "controls"})


def check_verdicts(histories, observations, state):
    if state["controls"] is not True:
        raise ValueError("A fabricated observation escaped a Quint rule")
    verdict_rows, acceptance_rows = state["verdicts"], state["accepting"]
    if not all(isinstance(rows, list) and len(rows) == len(histories)
               for rows in (verdict_rows, acceptance_rows)):
        raise ValueError("Expected one Quint verdict row per history")
    rows = zip(histories, observations, verdict_rows, acceptance_rows, strict=True)
    for index, (history, evidence, verdicts, accepting) in enumerate(rows, 1):
        if (not all(isinstance(row, list) and len(row) == len(history) for row in (verdicts, accepting))
                or not all(isinstance(verdict, str) for verdict in verdicts)
                or not all(isinstance(flag, bool) for flag in accepting)):
            raise ValueError(f"history {index}: expected one Quint verdict and acceptance flag per step")
        steps = zip(history, evidence["attempts"], verdicts, accepting, strict=True)
        labels = []
        for step, (request, attempt, verdict, accepted) in enumerate(steps, 1):
            context = f"history {index}, step {step}: {short_repr(request)}"
            if accepted is not True:
                raise ValueError(f"{context}: Quint verdict {verdict}; observed {short_repr(attempt)}")
            args = ", ".join(arg if len(arg) <= 80 else short_repr(arg) for arg in request["args"])
            label = f'{request["op"]}({args})'
            status = attempt.get("status", verdict)
            labels.append(f"{label}={status}")
        print(f"history {index}: {', '.join(labels)}")
    if state["coverage"] is not True:
        raise ValueError("Quint's required history coverage was not met")
    print("Quint's synthetic rule controls passed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init", action="append", help="history initializer (default: init)")
    parser.add_argument("--quint-module", type=Path, action="append", default=[], help="local Quint rules import")
    # Preserve the intended path if Meson passes a relative build artifact.
    def absolute_path(path):
        return Path(path).absolute()

    parser.add_argument("quint", type=absolute_path)
    parser.add_argument("binding", help="daggerml.core import or path to the private replay extension")
    for argument in ("scanner", "histories", "rules"):
        parser.add_argument(argument, type=absolute_path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="dml-histories-") as tmp:
        directory = Path(tmp)
        histories = read_histories(args.quint, args.histories, directory / "histories.itf.json", args.init or ["init"])
        suite = Suite(args.binding, args.scanner)
        observations = [replay_history(suite, directory / f"history-{index}", history)
                        for index, history in enumerate(histories, 1)]
        state = evaluate(args.quint, args.rules, directory, observations, args.quint_module)
        check_verdicts(histories, observations, state)


if __name__ == "__main__":
    try:
        main()
    except (ImportError, OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"trace interpretation failed: {error}") from error
