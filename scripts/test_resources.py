"""Resource limits for optional parallel validation, not DML runtime policy.

Only read host/process allocation. Never set affinity, resource limits or deadlines.
The initial 1-GiB worker allowance includes coverage/subprocess headroom; report
sampled worker-tree RSS separately so future sizing changes can use evidence.
"""

import math
from pathlib import Path, PurePosixPath
import re
import sys

MIB = 1024 ** 2
DEFAULT_WORKER_MB = 1024
DEFAULT_RESERVE_MB = 1024


def _positive(value):
    number = int(value)
    if number <= 0:
        raise ValueError("resource allowance must be a positive integer")
    return number


def worker_plan(cpus, available, *, worker_mb=DEFAULT_WORKER_MB,
                reserve_mb=DEFAULT_RESERVE_MB):
    worker_bytes = _positive(worker_mb) * MIB
    reserve_bytes = _positive(reserve_mb) * MIB
    memory_workers = None if available is None else max(0, int(available - reserve_bytes) // worker_bytes)
    if memory_workers == 0:
        raise ValueError("insufficient detected memory for one worker plus reserve")
    if cpus is None or available is None:
        return dict(workers=1, cpus=cpus, available_bytes=available,
                    worker_bytes=worker_bytes, reserve_bytes=reserve_bytes,
                    reason="resource detection incomplete; conservative serial fallback")
    if not math.isfinite(cpus) or cpus <= 0:
        raise ValueError("invalid detected CPU allocation")
    return dict(workers=min(max(1, math.floor(cpus)), memory_workers), cpus=cpus,
                available_bytes=available, worker_bytes=worker_bytes,
                reserve_bytes=reserve_bytes, reason="minimum of CPU and memory capacity")


def _unescape(value):
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), value)


def cgroup_locations(membership, mounts):
    """Map namespaced v1/v2 memberships to visible mount roots and ancestors."""
    groups = {}
    for line in membership.splitlines():
        _, controllers, path = line.split(":", 2)
        for controller in controllers.split(","):
            groups[controller] = PurePosixPath(path)
    result = []
    for line in mounts.splitlines():
        before, after = line.split(" - ", 1)
        filesystem, _, options = after.split()[:3]
        if filesystem not in ("cgroup", "cgroup2"):
            continue
        fields = before.split()
        root, mount = PurePosixPath(_unescape(fields[3])), Path(_unescape(fields[4]))
        controllers = ("",) if filesystem == "cgroup2" else tuple(options.split(","))
        for controller in controllers:
            if controller not in groups or controller not in ("", "cpu", "memory"):
                continue
            member = groups[controller]
            if ".." in member.parts or not member.is_absolute():
                raise ValueError("invalid cgroup membership")
            relative = member.relative_to(root)
            current = mount.joinpath(*relative.parts)
            while True:
                result.append((controller, current))
                if current == mount:
                    break
                current = current.parent
    return result


def _read(path):
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return None


def cgroup_limits(locations):
    cpu_limits, memory_limits = [], []
    for controller, path in locations:
        if controller in ("", "cpu"):
            if controller == "":
                value = _read(path / "cpu.max")
                pair = None if value is None else value.split()
            else:
                quota, period = (_read(path / n) for n in ("cpu.cfs_quota_us", "cpu.cfs_period_us"))
                pair = None if quota is None and period is None else (quota, period)
            if pair is not None:
                quota, period = pair
                period = _positive(period)
                if quota not in ("max", "-1"):
                    cpu_limits.append(_positive(quota) / period)
        if controller in ("", "memory"):
            limit_name, usage_name = (("memory.max", "memory.current") if controller == "" else
                                      ("memory.limit_in_bytes", "memory.usage_in_bytes"))
            limit = _read(path / limit_name)
            if limit is not None and limit != "max":
                limit = int(limit)
                if limit < 0:
                    raise ValueError("invalid cgroup memory limit")
                # Kernel v1 unlimited sentinel is far above realistic RAM sizes.
                if controller == "memory" and limit >= 2 ** 60:
                    continue
                usage = int(_read(path / usage_name))
                if usage < 0:
                    raise ValueError("invalid cgroup memory usage")
                memory_limits.append(max(0, limit - usage))
    return (min(cpu_limits) if cpu_limits else None,
            min(memory_limits) if memory_limits else None)


def detect_resources(*, provider=None, platform=None, proc=Path("/proc")):
    if provider is None:
        import psutil
        provider = psutil
    platform = sys.platform if platform is None else platform
    notes = []
    try:
        logical = provider.cpu_count()
        physical = provider.cpu_count(logical=False)
        # Avoid treating SMT threads as additional full cores. Affinity and
        # quotas below still cap the actual process allocation.
        cpus = min(logical, physical or logical) if logical else None
        process = provider.Process()
        if hasattr(process, "cpu_affinity"):
            cpus = min(cpus, len(process.cpu_affinity())) if cpus else None
    except (OSError, provider.Error):
        cpus = None
        notes.append("CPU allocation probe unavailable")
    try:
        available = provider.virtual_memory().available
    except (OSError, provider.Error):
        available = None
        notes.append("available memory probe unavailable")
    if platform.startswith("linux"):
        try:
            membership, mounts = (_read(proc / n) for n in ("self/cgroup", "self/mountinfo"))
            if membership is None or mounts is None:
                raise ValueError("cgroup discovery unavailable")
            cpu_limit, memory_limit = cgroup_limits(cgroup_locations(membership, mounts))
            if cpu_limit is not None and cpus is not None:
                cpus = min(cpus, cpu_limit)
            if memory_limit is not None and available is not None:
                available = min(available, memory_limit)
        except (OSError, ValueError, TypeError):
            cpus, available = None, None
            notes.append("container allocation probe unavailable or malformed")
    return cpus, available, notes
