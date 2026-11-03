# SPDX-License-Identifier: Apache-2.0
#
# Full-chip suite (test/test.py) with tracing, for docs/TEST_REPORT.md.
#
# Runs the same 14 cocotb tests, unchanged in what they send and check, and
# records every LOAD, GEMM run, STATUS read, READ_C result and reference value
# to report/out/fullchip_trace.json. Run through test/report/run_report.sh.

import functools
import json
import os

import cocotb
from cocotb.regression import Test, TestGenerator
from cocotb.utils import get_sim_time

import test as T  # test/test.py
import bf16_model as M
import gemm_protocol as gp

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

_log = []          # [{"test": name, "events": [...]}]
_cur = [None]
_depth = [0]       # >0 while inside a traced call: nested calls are not logged


def _flush():
    with open(os.path.join(OUT, "fullchip_trace.json"), "w") as fh:
        json.dump(_log, fh)


def _ev(**kw):
    if _depth[0] == 0 and _cur[0] is not None:
        kw["t_ns"] = get_sim_time("ns")
        _cur[0]["events"].append(kw)


def _traced(fn, record):
    """Wrap an async helper; record(result, *args) builds the event."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        _depth[0] += 1
        try:
            result = await fn(*args, **kwargs)
        finally:
            _depth[0] -= 1
        _ev(**record(result, *args, **kwargs))
        return result
    return wrapper


# ---- patch the helpers test.py calls (looked up as module globals) --------
T.run = _traced(T.run, lambda r, dut, a, b, accumulate=False: dict(
    op="GEMM" if accumulate else "CLEAR_GEMM", a=list(a), b=list(b), status=r))
T.read_c = _traced(T.read_c, lambda r, dut: dict(op="READ_C", got=r))
T.status = _traced(T.status, lambda r, dut: dict(op="STATUS", got=r))
T.wait_idle = _traced(T.wait_idle, lambda r, dut, *a, **k: dict(op="WAIT_IDLE", got=r))
T.recv_byte = _traced(T.recv_byte, lambda r, dut, *a, **k: dict(op="RECV", got=r))
T.send_byte = _traced(T.send_byte, lambda r, dut, value: dict(op="SEND", byte=value))
T.load = _traced(T.load, lambda r, dut, opcode, values: dict(
    op="LOAD_A" if opcode == T.OP_LOAD_A else "LOAD_B", values=list(values)))

_matmul_ref = M.matmul_ref


def _ref(a, b, n, k, m, kpad=4):
    exp = _matmul_ref(a, b, n, k, m, kpad=kpad)
    _ev(op="REF", n=n, k=k, m=m, a=list(a), b=list(b), exp=exp)
    return exp


M.matmul_ref = _ref

gp.matmul = _traced(gp.matmul, lambda r, dut, a, b, n, k, m: dict(
    op="TILED_MATMUL", n=n, k=k, m=m, a=list(a), b=list(b), got=r))


# ---- re-export every test, tagging events with the running test's name ----
def _named(name, func):
    @functools.wraps(func)
    async def wrapper(dut, *args, **kwargs):
        _cur[0] = {"test": name, "events": [], "t0_ns": get_sim_time("ns")}
        _log.append(_cur[0])
        try:
            await func(dut, *args, **kwargs)
        finally:
            _cur[0]["t1_ns"] = get_sim_time("ns")
            _flush()
    return wrapper


for _name, _obj in list(vars(T).items()):
    if isinstance(_obj, (Test, TestGenerator)):
        _obj.func = _named(_obj.func.__name__, _obj.func)
        globals()[_name] = _obj
del _name, _obj
