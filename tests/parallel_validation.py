"""Early-loaded optional parallel test policy/reporting; no DML runtime changes."""

import json
import os
from pathlib import Path
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path(os.environ.get("DML_BIN", ROOT / "build/check/dml")).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from test_resources import detect_resources, worker_plan


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_auto_num_workers(config):
    try:
        cpus, memory, notes = detect_resources()
        plan = worker_plan(cpus, memory,
            worker_mb=os.environ.get("DML_TEST_WORKER_MB", "1024"),
            reserve_mb=os.environ.get("DML_TEST_RESERVE_MB", "1024"))
    except (TypeError, ValueError) as error:
        raise pytest.UsageError(str(error)) from error
    plan["notes"] = notes
    maximum = getattr(config.option, "maxprocesses", None)
    if maximum is not None:
        plan["workers"] = min(plan["workers"], maximum)
    config._dml_worker_plan = plan
    return plan["workers"]


def pytest_configure(config):
    config.addinivalue_line("markers", "xdist_group(name): keep shared-fixture tests together")
    worker = getattr(config, "workerinput", {}).get("workerid", "controller")
    config._dml_worker = worker
    config._dml_properties = []
    config._dml_stop_sample = threading.Event()
    config._dml_memory = {"peak_sampled_tree_rss": 0, "samples": 0, "errors": 0}
    if worker != "controller":
        # The check script merges raw worker counters with initial C-test data.
        destination = os.environ.get("DML_TEST_GCOV_DIR")
        if destination:
            path = Path(destination) / worker
            path.mkdir(parents=True, exist_ok=True)
            os.environ["GCOV_PREFIX"] = str(path)
            os.environ["GCOV_PREFIX_STRIP"] = str(len(BUILD.parts) - 1)


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    if not any(config.pluginmanager.hasplugin(n) for n in ("xdist", "xdist.plugin")):
        return
    # Group CONSUMING modules: module-scoped fixtures belong to each requester.
    shared = {"frozen", "reuse_history", "native_lifecycle_binary"}
    for item in items:
        if shared.intersection(item.fixturenames):
            item.add_marker(pytest.mark.xdist_group(item.path.stem))


def _sample_memory(config):
    import psutil
    process = psutil.Process()
    while True:
        try:
            processes = [process, *process.children(recursive=True)]
            total = 0
            for child in processes:
                try:
                    total += child.memory_info().rss
                except (psutil.Error, OSError):
                    config._dml_memory["errors"] += 1
            config._dml_memory["peak_sampled_tree_rss"] = max(
                config._dml_memory["peak_sampled_tree_rss"], total)
            config._dml_memory["samples"] += 1
        except (psutil.Error, OSError):
            config._dml_memory["errors"] += 1
        if config._dml_stop_sample.wait(1):
            break


def pytest_sessionstart(session):
    config = session.config
    if config._dml_worker != "controller":
        config._dml_sample_thread = threading.Thread(target=_sample_memory, args=(config,), daemon=True)
        config._dml_sample_thread.start()
    elif getattr(config.option, "numprocesses", 0):
        report = config.pluginmanager.getplugin("terminalreporter")
        if report:
            plan = getattr(config, "_dml_worker_plan", {"reason": "explicit worker count"})
            report.write_line("DML parallel resources: " + json.dumps(dict(plan, selected_workers=config.option.numprocesses)))


@pytest.fixture(scope="session", name="record_testsuite_property")
def _record_suite_property(record_testsuite_property, request):
    original = record_testsuite_property
    if request.config._dml_worker == "controller":
        return original
    def recorded(name, value):
        original(name, value)
        request.config._dml_properties.append((name, str(value)))
    return recorded


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    config._dml_stop_sample.set()
    thread = getattr(config, "_dml_sample_thread", None)
    if thread is not None:
        thread.join()
    if config._dml_worker != "controller":
        config.workeroutput["dml_properties"] = config._dml_properties
        config.workeroutput["dml_memory"] = config._dml_memory


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node, error):
    from _pytest.junitxml import xml_key
    config = node.config
    xml = config.stash.get(xml_key, None)
    output = getattr(node, "workeroutput", {}) or {}
    properties = output.get("dml_properties", [])
    if xml is not None:
        for name, value in properties:
            xml.add_global_property(name, value)
    destination = Path(os.environ.get("DML_TEST_REPORT_DIR", ROOT / "build/test-results/parallel"))
    destination.mkdir(parents=True, exist_ok=True)
    (destination / (node.gateway.id + ".json")).write_text(json.dumps({
        "worker": node.gateway.id, "exitstatus": output.get("exitstatus"),
        "crashed": error is not None, "memory": output.get("dml_memory"),
        "suite_properties": properties,
    }, indent=2) + "\n")


def pytest_terminal_summary(terminalreporter):
    config = terminalreporter.config
    if config._dml_worker == "controller" and getattr(config.option, "numprocesses", 0):
        destination = Path(os.environ.get("DML_TEST_REPORT_DIR", ROOT / "build/test-results/parallel"))
        destination.mkdir(parents=True, exist_ok=True)
        plan = dict(getattr(config, "_dml_worker_plan", {"reason": "explicit worker count"}),
                    selected_workers=config.option.numprocesses)
        (destination / "resources.json").write_text(json.dumps(plan, indent=2) + "\n")
        terminalreporter.write_line("DML worker memory/resource reports: " + str(destination))
