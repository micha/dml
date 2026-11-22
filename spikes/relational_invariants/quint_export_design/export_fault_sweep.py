"""Sweep native and binding allocation failures without importing the comparison tooling."""

import os
import sys

import daggerml as dml
from daggerml import _core_fault, transfer


def sweep_faults(get_rows, expected, arm, reset, expected_error, minimum):
    for nth in range(1, 1025):
        arm(nth)
        try:
            rows = get_rows()
        except expected_error as error:
            if isinstance(error, dml.DmlError):
                assert error.code == "out_of_memory", error
            reset()
            assert get_rows() == expected, f"Failed to recover after allocation {nth}"
        else:
            assert rows == expected and nth > minimum
            return nth - 1
        finally:
            reset()
    raise AssertionError("Allocation sweep did not reach its non-triggering control")


def compare_faults(repo):
    core = dml._core
    limits = transfer.MAX_OBJECTS, transfer.MAX_RECORD_BYTES, transfer.MAX_PACKED_BYTES
    with dml.Repository(repo) as owner, owner.read() as tx:
        commit = tx.get_ref("main")
        expected = dml._call(core._export_rows, tx._handle, commit.bytes, *limits)
        assert isinstance(expected, tuple) and expected

    dml._core = _core_fault
    try:
        with dml.Repository(repo) as owner, owner.read() as tx:
            def get_rows():
                return dml._call(_core_fault._export_rows, tx._handle, commit.bytes, *limits)

            c_allocations = sweep_faults(get_rows, expected,
                                         lambda nth: _core_fault.native_fault(1, nth, 0),
                                         lambda: _core_fault.native_fault(0, 0, 0),
                                         dml.DmlError, len(expected))
            py_allocations = sweep_faults(get_rows, expected,
                                          lambda nth: _core_fault.set_fault(2, nth),
                                          lambda: _core_fault.set_fault(0, 0),
                                          MemoryError, len(expected))
    finally:
        dml._core = core
    assert py_allocations == 1 + len(expected), "Expected one tuple and one conversion per row"
    return {"native_allocations": c_allocations, "binding_allocations": py_allocations}


if __name__ == "__main__":
    if not __debug__ or len(sys.argv) != 2:
        raise SystemExit("Usage: python export_fault_sweep.py /path/to/pristine/fixture.dml")
    print(f"Interpreter PID: {os.getpid()}")
    print(compare_faults(sys.argv[1]))
