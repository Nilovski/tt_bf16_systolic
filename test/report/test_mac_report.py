# SPDX-License-Identifier: Apache-2.0
#
# MAC unit suite (test/mac/test_mac.py) with tracing, for docs/TEST_REPORT.md.
#
# Same two tests and the same vectors; every (acc, a, b) case is written to
# report/out/mac_vectors.csv with the model's expected value, the DUT result
# and the go-to-done latency. Run through test/report/run_report.sh.

import csv
import functools
import os

from cocotb.regression import Test, TestGenerator
from cocotb.triggers import RisingEdge

import bf16_model as m
import test_mac as T  # test/mac/test_mac.py

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

_rows = []
_suite = [None]


async def _run(dut, acc, a, b):
    """test_mac.run, plus a record of the case and its latency in cycles."""
    dut.a.value = a
    dut.b.value = b
    dut.acc.value = acc
    dut.go.value = 1
    await RisingEdge(dut.clk)
    dut.go.value = 0
    for n in range(1, 64):
        await RisingEdge(dut.clk)
        if int(dut.done.value):
            T.worst[0] = max(T.worst[0], n)
            got = int(dut.result.value)
            exp = m.mac(acc, a, b)
            _rows.append([_suite[0], len([r for r in _rows if r[0] == _suite[0]]),
                          f"{acc:04x}", f"{a:04x}", f"{b:04x}", f"{exp:04x}",
                          f"{got:04x}", n, got == exp])
            return got
    raise AssertionError("MAC never finished")


T.run = _run


def _flush():
    with open(os.path.join(OUT, "mac_vectors.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["suite", "idx", "acc", "a", "b", "expected", "got",
                    "latency_cycles", "pass"])
        w.writerows(_rows)


def _named(name, func):
    @functools.wraps(func)
    async def wrapper(dut, *args, **kwargs):
        _suite[0] = name.replace("test_", "")
        try:
            await func(dut, *args, **kwargs)
        finally:
            _flush()
    return wrapper


for _name, _obj in list(vars(T).items()):
    if isinstance(_obj, (Test, TestGenerator)):
        _obj.func = _named(_obj.func.__name__, _obj.func)
        globals()[_name] = _obj
del _name, _obj
