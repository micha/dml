"""Resource-aware worker selection with synthetic host/container allocations."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from test_resources import MIB, cgroup_limits, cgroup_locations, detect_resources, worker_plan


@pytest.mark.parametrize("cpus,memory,expected", [(8, 24, 8), (32, 5, 4), (2, 7, 2), (1.5, 9, 1), (0.5, 9, 1)])
def test_worker_count_minimum_of_effective_cpu_and_memory(cpus, memory, expected):
    assert worker_plan(cpus, memory * 1024 * MIB)["workers"] == expected


@pytest.mark.parametrize("cpus,memory", [(None, 4 * 1024 * MIB), (8, None), (None, None)])
def test_unknown_resources_use_one_worker(cpus, memory):
    assert worker_plan(cpus, memory)["workers"] == 1


@pytest.mark.parametrize("cpu,memory,worker,reserve", [
    (8, 1 * 1024 * MIB, 1024, 1024), (None, 0, 1024, 1024),
    (8, -1, 1024, 1024), (0, 4 * 1024 * MIB, 1024, 1024),
    (float("nan"), 4 * 1024 * MIB, 1024, 1024),
    (8, 4 * 1024 * MIB, 0, 1024), (8, 4 * 1024 * MIB, 1024, -1),
    (8, 4 * 1024 * MIB, "invalid", 1024),
])
def test_invalid_or_insufficient_allocation_is_error_not_oversubscription(cpu, memory, worker, reserve):
    with pytest.raises(ValueError):
        worker_plan(cpu, memory, worker_mb=worker, reserve_mb=reserve)


def write(root, **files):
    root.mkdir(parents=True, exist_ok=True)
    for name, value in files.items():
        (root / name.replace("__", ".")).write_text(str(value))


def mounts(root, filesystem="cgroup2", controllers="rw", mounted_root="/"):
    path = str(root).replace(" ", r"\040")
    return f"1 0 0:1 {mounted_root} {path} rw - {filesystem} cgroup {controllers}\n"


def test_v2_nested_parent_limits_and_current_usage(tmp_path):
    group = tmp_path / "cgroup with spaces"
    write(group, cpu__max="max 100000", memory__max="max")
    write(group / "user", cpu__max="150000 100000", memory__max=4 * 1024 * MIB, memory__current=1024 * MIB)
    write(group / "user/job", cpu__max="300000 100000", memory__max=8 * 1024 * MIB, memory__current=0)
    locations = cgroup_locations("0::/user/job\n", mounts(group))
    assert [p for c, p in locations] == [group / "user/job", group / "user", group]
    assert cgroup_limits(locations) == (1.5, 3 * 1024 * MIB)
    assert cgroup_locations("0::/user/job\n", mounts(group, mounted_root="/user"))[0][1] == group / "job"


def test_v1_controller_mounts_unlimited_and_tighter_usage(tmp_path):
    cpu, memory = tmp_path / "cpu", tmp_path / "memory"
    write(cpu, cpu__cfs_quota_us=-1, cpu__cfs_period_us=100000)
    write(cpu / "job", cpu__cfs_quota_us=200000, cpu__cfs_period_us=100000)
    write(memory, memory__limit_in_bytes=2 ** 63 - 4096, memory__usage_in_bytes=0)
    write(memory / "job", memory__limit_in_bytes=4 * 1024 * MIB, memory__usage_in_bytes=2 * 1024 * MIB)
    data = mounts(cpu, "cgroup", "rw,cpu,cpuacct") + mounts(memory, "cgroup", "rw,memory")
    locations = cgroup_locations("1:cpu,cpuacct:/job\n2:memory:/job\n", data)
    assert cgroup_limits(locations) == (2, 2 * 1024 * MIB)
    assert cgroup_locations("0::/\n", "1 0 0:1 / /tmp rw - tmpfs tmpfs rw\n") == []


def test_missing_files_mean_no_exposed_limit_not_fake_zero(tmp_path):
    assert cgroup_limits([("", tmp_path), ("cpu", tmp_path), ("memory", tmp_path)]) == (None, None)
    assert cgroup_locations("0::/\n", mounts(tmp_path, "cgroup", "rw,pids")) == []


@pytest.mark.parametrize("quota,period", [("broken", "100000"), ("100000", "0"), ("100000 200000", "100000")])
def test_malformed_cpu_limit_rejected(tmp_path, quota, period):
    write(tmp_path, cpu__max=quota + " " + period)
    with pytest.raises(ValueError):
        cgroup_limits([("", tmp_path)])


@pytest.mark.parametrize("limit,usage", [("10", "-1"), ("-1", "0"), ("10", "bad")])
def test_bad_memory_limit_rejected(tmp_path, limit, usage):
    write(tmp_path, memory__max=limit, memory__current=usage)
    with pytest.raises(ValueError):
        cgroup_limits([("", tmp_path)])


def test_zero_and_exceeded_memory_limit_are_insufficient(tmp_path):
    write(tmp_path, memory__max=0, memory__current=1)
    assert cgroup_limits([("", tmp_path)]) == (None, 0)


@pytest.mark.parametrize("member", ["/../escape", "relative"])
def test_membership_cannot_escape_visible_mount(tmp_path, member):
    with pytest.raises(ValueError):
        cgroup_locations("0::" + member + "\n", mounts(tmp_path))


class ProbeError(Exception):
    pass


def provider(*, cpus=8, physical=None, memory=12 * 1024 * MIB, affinity=True, cpu_error=False, mem_error=False):
    def cpu_count(logical=True):
        if cpu_error:
            raise ProbeError()
        return cpus if logical else physical
    def virtual_memory():
        if mem_error:
            raise ProbeError()
        return SimpleNamespace(available=memory)
    return SimpleNamespace(Error=ProbeError, cpu_count=cpu_count, virtual_memory=virtual_memory,
                           Process=lambda: SimpleNamespace(cpu_affinity=lambda: [0, 1]) if affinity else object())


def test_host_affinity_and_platform_without_affinity():
    assert detect_resources(provider=provider(), platform="darwin")[:2] == (2, 12 * 1024 * MIB)
    assert detect_resources(provider=provider(affinity=False), platform="darwin")[0] == 8
    assert detect_resources(provider=provider(cpus=None), platform="win32")[0] is None
    assert detect_resources(provider=provider(physical=4, affinity=False), platform="darwin")[0] == 4
    assert detect_resources(provider=provider(physical=4), platform="win32")[0] == 2


@pytest.mark.parametrize("cpu_error,mem_error", [(True, False), (False, True)])
def test_host_probe_failure_is_explicit_fallback(cpu_error, mem_error):
    cpu, memory, notes = detect_resources(provider=provider(cpu_error=cpu_error, mem_error=mem_error), platform="darwin")
    assert notes and worker_plan(cpu, memory)["workers"] == 1


def test_container_probes_affinity_and_parent_limits(tmp_path):
    group = tmp_path / "group"
    write(group, cpu__max="100000 100000", memory__max=4 * 1024 * MIB, memory__current=1024 * MIB)
    write(tmp_path / "self", cgroup="0::/\n", mountinfo=mounts(group))
    assert detect_resources(provider=provider(), platform="linux", proc=tmp_path) == (1, 3 * 1024 * MIB, [])
    cpu, memory, _ = detect_resources(provider=provider(cpus=None, mem_error=True), platform="linux", proc=tmp_path)
    assert cpu is None and memory is None


def test_missing_malformed_and_unreadable_container_metadata(tmp_path, monkeypatch):
    assert detect_resources(provider=provider(), platform="linux", proc=tmp_path)[:2] == (None, None)
    write(tmp_path / "self", cgroup="not a membership", mountinfo="not a mount")
    assert detect_resources(provider=provider(), platform="linux", proc=tmp_path)[2]
    original = Path.read_text
    def inaccessible(path, *args, **kwargs):
        if path.name == "mountinfo":
            raise PermissionError()
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", inaccessible)
    assert detect_resources(provider=provider(), platform="linux", proc=tmp_path)[2]


def test_real_read_only_host_probe_and_policy():
    cpu, memory, notes = detect_resources()
    # A read-only probe test must not assume the host has enough RAM to run the
    # real 1-GiB worker profile. This tiny allowance does NOT launch a worker.
    plan = worker_plan(cpu, memory, worker_mb=1, reserve_mb=1)
    assert plan["workers"] >= 1
    assert type(notes) is list


def test_xdist_hook_honors_memory_cpu_and_explicit_maximum(monkeypatch):
    import parallel_validation as plugin
    monkeypatch.setattr(plugin, "detect_resources", lambda: (8, 5 * 1024 * MIB, []))
    monkeypatch.setenv("DML_TEST_WORKER_MB", "1024")
    monkeypatch.setenv("DML_TEST_RESERVE_MB", "1024")
    config = SimpleNamespace(option=SimpleNamespace(maxprocesses=2))
    assert plugin.pytest_xdist_auto_num_workers(config) == 2
    assert config._dml_worker_plan["workers"] == 2
    config.option.maxprocesses = None
    assert plugin.pytest_xdist_auto_num_workers(config) == 4


@pytest.mark.parametrize("worker,memory", [("0", 8 * 1024 * MIB), ("1024", 1024 * MIB)])
def test_xdist_hook_rejects_invalid_or_insufficient_allowance(monkeypatch, worker, memory):
    import parallel_validation as plugin
    monkeypatch.setattr(plugin, "detect_resources", lambda: (8, memory, []))
    monkeypatch.setenv("DML_TEST_WORKER_MB", worker)
    monkeypatch.setenv("DML_TEST_RESERVE_MB", "1024")
    with pytest.raises(pytest.UsageError):
        plugin.pytest_xdist_auto_num_workers(SimpleNamespace(option=SimpleNamespace(maxprocesses=None)))
