#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
#
# Build docs/TEST_REPORT.md and docs/test_vectors/*.csv from the traces that
# test_report.py and test_mac_report.py write to report/out/. Run through
# test/report/run_report.sh, which runs the simulations first.

import collections
import csv
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TEST = os.path.dirname(HERE)
ROOT = os.path.dirname(TEST)
OUT = os.path.join(HERE, "out")
DOCS = os.path.join(ROOT, "docs")
VEC = os.path.join(DOCS, "test_vectors")
sys.path.insert(0, TEST)
import bf16_model as M  # noqa: E402

N = K = 4


# ---------------------------------------------------------------------------
# formatting
# ---------------------------------------------------------------------------
def fv(h):
    """BF16 bits -> short decimal string (exact for every value shown)."""
    if M.is_nan(h):
        return "NaN"
    if M.is_inf(h):
        return "-inf" if h & 0x8000 else "+inf"
    x = M.to_float(h)
    if x == 0:
        return "-0" if h & 0x8000 else "0"
    if abs(x) >= 1e5 or abs(x) < 1e-3:
        return f"{x:.3g}"
    return f"{x:.6g}"


def grid(name, vals, rows, cols, hexes=False):
    cells = [[f"{vals[r * cols + c]:04x}" if hexes else fv(vals[r * cols + c])
              for c in range(cols)] for r in range(rows)]
    return name, cells


def side(*grids):
    """Matrices side by side in one fenced block."""
    ws = [max(4, max(len(c) for row in g for c in row)) for _, g in grids]
    rows = max(len(g) for _, g in grids)
    head, lines = [], []
    for (name, g), w in zip(grids, ws):
        head.append(name.ljust(len(g[0]) * (w + 1) - 1))
    lines.append("   ".join(head).rstrip())
    for r in range(rows):
        parts = []
        for (name, g), w in zip(grids, ws):
            width = len(g[0]) * (w + 1) - 1
            parts.append((" ".join(c.rjust(w) for c in g[r]) if r < len(g) else "").ljust(width))
        lines.append("   ".join(parts).rstrip())
    return "```\n" + "\n".join(lines) + "\n```"


def st(s):
    names = ["BUSY", "DONE", "A_LOADED", "B_LOADED", "RESULT_VALID", "ERROR"]
    on = [n for i, n in enumerate(names) if s >> i & 1]
    return f"`0x{s:02x}` ({' + '.join(on) if on else 'none'})"


def ok(flag):
    return "Pass" if flag else "**FAIL**"


def ops(ev, *names):
    return [e for e in ev if e["op"] in names]


def gemm_block(a, b, got, exp, label=None, hexes=True):
    good = got == exp
    s = f"**{label}**: " if label else ""
    s += (f"DUT = reference, {len(got)}/{len(got)} elements bit-exact." if good
          else f"**MISMATCH**: {sum(x != y for x, y in zip(got, exp))} of {len(got)} elements differ.")
    gs = [grid("A", a, N, K), grid("B", b, K, N), grid("C (DUT)", got, N, N)]
    if hexes:
        gs.append(grid("C hex", got, N, N, True))
    s += "\n\n" + side(*gs)
    if not good:
        s += "\n\n" + side(grid("C (reference)", exp, N, N), grid("ref hex", exp, N, N, True))
    return s


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------
def junit(path):
    if not os.path.exists(path):
        return {}
    res = {}
    for tc in ET.parse(path).getroot().iter("testcase"):
        bad = tc.find("failure") is not None or tc.find("error") is not None
        res[tc.get("name")] = (not bad, float(tc.get("sim_time_ns") or 0))
    return res


def git(*args):
    try:
        return subprocess.check_output(["git", "-C", ROOT, *args], text=True).strip()
    except Exception:
        return "unknown"


_raw = json.load(open(os.path.join(OUT, "fullchip_trace.json")))
trace = {t["test"]: t["events"] for t in _raw}
simtime = {t["test"]: t.get("t1_ns", 0) - t.get("t0_ns", 0) for t in _raw}
mac_rows = list(csv.DictReader(open(os.path.join(OUT, "mac_vectors.csv"))))
rtl = junit(os.path.join(TEST, "results.xml"))
macx = junit(os.path.join(TEST, "mac", "results.xml"))
prep = open(os.path.join(OUT, "prep.txt")).read().strip() if os.path.exists(os.path.join(OUT, "prep.txt")) else "not run"
commit = git("rev-parse", "--short", "HEAD")
commit_date = git("log", "-1", "--format=%ad", "--date=short")
tools = open(os.path.join(OUT, "tools.txt")).read().strip() if os.path.exists(os.path.join(OUT, "tools.txt")) else ""


# ---------------------------------------------------------------------------
# per-test sections
# ---------------------------------------------------------------------------
def sec_tests():
    out = []

    def add(name, desc, body):
        passed = rtl.get(name, (None,))[0]
        out.append(f"### {len(out) + 1}. `{name}`: {ok(passed) if passed is not None else 'not run'}\n\n{desc}\n\n{body}")

    ev = trace["test_id"]
    r = ops(ev, "RECV")[0]["got"]
    add("test_id", "Sends `OP_ID` (0x41) and reads one byte back.",
        "| Sent | Expected | Got | Result |\n| --- | --- | --- | --- |\n"
        f"| `0x41` | `0xA8` | `0x{r:02X}` | {ok(r == 0xA8)} |")

    ev = trace["test_identity"]
    run, rd, rf = ops(ev, "CLEAR_GEMM")[0], ops(ev, "READ_C")[0], ops(ev, "REF")[0]
    add("test_identity", "C = I × B for a hand-picked B. STATUS after the run must show DONE, A_LOADED, B_LOADED and RESULT_VALID.",
        f"Final STATUS: {st(run['status'])}.\n\n" + gemm_block(run["a"], run["b"], rd["got"], rf["exp"]))

    ev = trace["test_random"]
    runs, rds, rfs = ops(ev, "CLEAR_GEMM"), ops(ev, "READ_C"), ops(ev, "REF")
    n_ok = sum(r["got"] == f["exp"] for r, f in zip(rds, rfs))
    body = (f"Seed 1. {len(runs)} independent CLEAR_GEMM runs, every element uniform in [-8, 8] and rounded to BF16. "
            f"{n_ok}/{len(runs)} runs bit-exact. Hex for every run is in `test_vectors/fullchip_vectors.csv`.\n\n")
    body += "\n\n".join(gemm_block(r["a"], r["b"], d["got"], f["exp"], f"Run {i + 1}", hexes=False)
                        for i, (r, d, f) in enumerate(zip(runs, rds, rfs)))
    add("test_random", "Random 4×4 × 4×4 products.", body)

    ev = trace["test_accumulate"]
    r1, r2 = ops(ev, "CLEAR_GEMM")[0], ops(ev, "GEMM")[0]
    rd, rf = ops(ev, "READ_C")[0], ops(ev, "REF")[0]
    body = ("Seed 2. CLEAR_GEMM with (A1, B1), then GEMM (accumulate) with (A2, B2). "
            "Expected: the model's K = 8 chain over [A1 | A2] × [B1 ; B2].\n\n")
    body += side(grid("A1", r1["a"], 4, 4), grid("B1", r1["b"], 4, 4)) + "\n\n"
    body += side(grid("A2", r2["a"], 4, 4), grid("B2", r2["b"], 4, 4)) + "\n\n"
    body += (f"C after accumulate: {'16/16 bit-exact' if rd['got'] == rf['exp'] else '**MISMATCH**'}.\n\n"
             + side(grid("C (DUT)", rd["got"], 4, 4), grid("C hex", rd["got"], 4, 4, True)))
    add("test_accumulate", "GEMM adds into the accumulators instead of clearing them.", body)

    ev = trace["test_rerun_without_reload"]
    run, rds, rf = ops(ev, "CLEAR_GEMM")[0], ops(ev, "READ_C"), ops(ev, "REF")[0]
    body = ("Seed 4. Load once and run CLEAR_GEMM. Run CLEAR_GEMM again with no reload, which must give the same C. "
            "Then run GEMM with no reload, which must give A·B + A·B as a K = 8 chain.\n\n")
    body += side(grid("A", run["a"], 4, 4), grid("B", run["b"], 4, 4)) + "\n\n"
    body += ("| Step | Check | Result |\n| --- | --- | --- |\n"
             "| 1. CLEAR_GEMM | first result | recorded |\n"
             f"| 2. CLEAR_GEMM, no reload | equals step 1 | {ok(rds[1]['got'] == rds[0]['got'])} |\n"
             f"| 3. GEMM, no reload | equals the K = 8 chain | {ok(rds[2]['got'] == rf['exp'])} |\n\n")
    body += side(grid("C step 1", rds[0]["got"], 4, 4), grid("C step 3", rds[2]["got"], 4, 4),
                 grid("step 3 hex", rds[2]["got"], 4, 4, True))
    add("test_rerun_without_reload", "The operand lanes return to order after a feed, so a GEMM can rerun without reloading.", body)

    ev = trace["test_read_element"]
    run, exp = ops(ev, "CLEAR_GEMM")[0], ops(ev, "REF")[0]["exp"]
    rb = [e["got"] for e in ops(ev, "RECV")]
    body = "Seed 3. One CLEAR_GEMM, then `READ_C_ELEMENT` (0x31) for indices 0, 5, 10, 15.\n\n"
    body += side(grid("A", run["a"], 4, 4), grid("B", run["b"], 4, 4)) + "\n\n"
    body += "| Index (row, col) | Low byte | High byte | Got | Expected | Value | Result |\n| --- | --- | --- | --- | --- | --- | --- |\n"
    for j, idx in enumerate((0, 5, 10, 15)):
        lo, hi = rb[2 * j], rb[2 * j + 1]
        g = lo | hi << 8
        body += f"| {idx} ({idx // 4}, {idx % 4}) | `0x{lo:02x}` | `0x{hi:02x}` | `{g:04x}` | `{exp[idx]:04x}` | {fv(g)} | {ok(g == exp[idx])} |\n"
    add("test_read_element", "Single-element reads return the right 16-bit value, low byte first.", body.strip())

    ev = trace["test_unknown_opcode_sets_error"]
    s = [e["got"] for e in ops(ev, "STATUS")]
    add("test_unknown_opcode_sets_error", "An undefined opcode sets ERROR, and a STATUS read clears it.",
        "| Step | Sent | STATUS | Check | Result |\n| --- | --- | --- | --- | --- |\n"
        f"| 1 | `0x7F`, then STATUS | {st(s[0])} | ERROR set | {ok(s[0] & 0x20)} |\n"
        f"| 2 | STATUS again | {st(s[1])} | ERROR cleared | {ok(not s[1] & 0x20)} |")

    ev = trace["test_plan_cases"]
    runs, rds = ops(ev, "CLEAR_GEMM"), ops(ev, "READ_C")
    labels = [("A × I = A (seed 5)", runs[0]["a"]), ("I × A = A", runs[1]["b"]),
              ("All ones × all ones = all 4.0", [M.from_float(4.0)] * 16)]
    body = ""
    for (lab, want), r, d in zip(labels, runs, rds):
        body += (f"**{lab}**: {ok(d['got'] == want)}.\n\n"
                 + side(grid("A", r["a"], 4, 4), grid("B", r["b"], 4, 4), grid("C (DUT)", d["got"], 4, 4),
                        grid("C hex", d["got"], 4, 4, True)) + "\n\n")
    add("test_plan_cases", "Identity on both sides and all ones, checked against exact expected values.", body.strip())

    ev = trace["test_specials"]
    run, rd, rf = ops(ev, "CLEAR_GEMM")[0], ops(ev, "READ_C")[0], ops(ev, "REF")[0]
    g = rd["got"]
    body = ("Inputs: +inf `7f80`, -inf `ff80`, NaN `7fc0`, 3.0e38, the subnormal `0001` (flushed to zero) and -0 `8000`.\n\n"
            + side(grid("A", run["a"], 4, 4), grid("B", run["b"], 4, 4)) + "\n\n"
            + side(grid("A hex", run["a"], 4, 4, True), grid("B hex", run["b"], 4, 4, True)) + "\n\n"
            + f"{'16/16 bit-exact' if g == rf['exp'] else '**MISMATCH**'}.\n\n"
            + side(grid("C (DUT)", g, 4, 4), grid("C hex", g, 4, 4, True)) + "\n\n"
            + "| Element | Exercises | Got | Result |\n| --- | --- | --- | --- |\n"
            + f"| C[0][0] | inf × 2 = inf | {fv(g[0])} | {ok(M.is_inf(g[0]))} |\n"
            + f"| C[0][1] | inf × 0 = NaN | {fv(g[1])} | {ok(M.is_nan(g[1]))} |\n"
            + f"| C[2][0] | 3e38·2 + 3e38·2 overflows | {fv(g[8])} | {ok(M.is_inf(g[8]))} |")
    add("test_specials", "IEEE special values: inf, NaN, inf × 0, inf − inf, signed zeros, subnormal flush-to-zero and overflow.", body)

    ev = trace["test_cancellation"]
    run, rd, rf = ops(ev, "CLEAR_GEMM")[0], ops(ev, "READ_C")[0], ops(ev, "REF")[0]
    add("test_cancellation", "x + (−x) = +0, and near-cancellation (a 2⁻⁷ residue that needs a long normalize shift).",
        gemm_block(run["a"], run["b"], rd["got"], rf["exp"]))

    ev = trace["test_status_bits_and_busy"]
    s = ops(ev, "STATUS", "WAIT_IDLE")
    rds, rfs, lds = ops(ev, "READ_C"), ops(ev, "REF"), ops(ev, "LOAD_A", "LOAD_B")
    body = ("Seed 6.\n\n| Step | Action | Observed | Check |\n| --- | --- | --- | --- |\n"
            f"| 1 | STATUS after reset | {st(s[0]['got'])} | = 0 |\n"
            f"| 2 | LOAD_A, STATUS | {st(s[1]['got'])} | = A_LOADED |\n"
            f"| 3 | LOAD_B, STATUS | {st(s[2]['got'])} | = A_LOADED + B_LOADED |\n"
            "| 4 | CLEAR_GEMM, wait 2 cycles | uio[4] BUSY high | BUSY pin = 1 |\n"
            f"| 5 | LOAD_A of all 1.0 while busy, STATUS | {st(s[3]['got'])} | BUSY + ERROR, not DONE |\n"
            f"| 6 | Poll until idle | {st(s[4]['got'])} | DONE + RESULT_VALID; uio[5] DONE high |\n"
            f"| 7 | READ_C | {ok(rds[0]['got'] == rfs[0]['exp'])} | = A·B (busy LOAD dropped) |\n"
            f"| 8 | CLEAR_GEMM, READ_C | {ok(rds[1]['got'] == rfs[1]['exp'])} | = A·B (stored A unchanged) |\n\n")
    body += side(grid("A", lds[0]["values"], 4, 4), grid("B", lds[1]["values"], 4, 4),
                 grid("C (DUT)", rds[0]["got"], 4, 4), grid("C hex", rds[0]["got"], 4, 4, True))
    add("test_status_bits_and_busy", "STATUS bits across a run; a LOAD sent while busy is dropped and flags ERROR.", body)

    ev = trace["test_ena_low_ignores_input"]
    r = ops(ev, "RECV")[0]["got"]
    add("test_ena_low_ignores_input", "With `ena` low the chip ignores input; `uio_oe` is correct.",
        "| Step | Action | Observed |\n| --- | --- | --- |\n"
        "| 1 | `ena` = 0, send OP_ID | TX_VALID stayed low for 10 cycles |\n"
        f"| 2 | `ena` = 1, send OP_ID | reply `0x{r:02X}` |\n"
        "| 3 | read `uio_oe` | `0b0011_1010` |")

    ev = trace["test_read_c_slow_host"]
    run, rf = ops(ev, "CLEAR_GEMM")[0], ops(ev, "REF")[0]
    rb = [e["got"] for e in ops(ev, "RECV")]
    got = [rb[2 * i] | rb[2 * i + 1] << 8 for i in range(16)]
    add("test_read_c_slow_host", "READ_C holds each byte until the host raises TX_READY.",
        "Seed 7. Drained with a 9-cycle stall before each of the 32 byte reads.\n\n"
        + gemm_block(run["a"], run["b"], got, rf["exp"]))

    ev = trace["test_tiled_matmul"]
    body = ("Seed 8, elements uniform in [−4, 4]. `gemm_protocol.matmul` splits the product into 4×4×4 runs, zero-padding the ragged edges. "
            "Each output tile gets CLEAR_GEMM for its first K block and GEMM for the rest.\n\n")
    for t, f in zip(ops(ev, "TILED_MATMUL"), ops(ev, "REF")):
        n, k, m = t["n"], t["k"], t["m"]
        nrun = -(-n // 4) * -(-m // 4) * -(-k // 4)
        body += (f"**{n}×{k} @ {k}×{m}** ({nrun} on-chip runs): "
                 + (f"{n * m}/{n * m} bit-exact.\n\n" if t["got"] == f["exp"] else "**MISMATCH**.\n\n")
                 + side(grid("A", t["a"], n, k)) + "\n\n" + side(grid("B", t["b"], k, m)) + "\n\n"
                 + side(grid("C (DUT)", t["got"], n, m)) + "\n\n" + side(grid("C hex", t["got"], n, m, True)) + "\n\n")
    add("test_tiled_matmul", "Host tiling beyond the array size: 8×8 × 8×8 and a ragged 5×9 × 9×6.", body.strip())
    return "\n\n".join(out)


# ---------------------------------------------------------------------------
# calculation logic, with a worked example taken from the trace
# ---------------------------------------------------------------------------
def worked_example():
    run = ops(trace["test_random"], "CLEAR_GEMM")[0]
    got = ops(trace["test_random"], "READ_C")[0]["got"]
    a, b = run["a"], run["b"]
    rows = ["| k | a[0][k] | b[k][0] | product = mul(a, b) | acc = add(acc, product) |",
            "| --- | --- | --- | --- | --- |", "| start | | | | `0000` (0) |"]
    acc, exact = 0, 0.0
    for k in range(K):
        av, bv = a[k], b[k * N]
        p = M.mul(av, bv)
        acc = M.add(acc, p)
        exact += M.to_float(av) * M.to_float(bv)
        rows.append(f"| {k} | `{av:04x}` ({fv(av)}) | `{bv:04x}` ({fv(bv)}) | `{p:04x}` ({fv(p)}) | `{acc:04x}` ({fv(acc)}) |")
    return ("\n".join(rows) + "\n\n"
            f"The chip returned `{got[0]:04x}` ({fv(got[0])}) for C[0][0]; the model gives `{acc:04x}`, "
            + ("an exact match. " if got[0] == acc else "**a mismatch**. ") +
            f"The exact real-number dot product is {exact:.6g}. The difference comes from the eight BF16 roundings "
            "(one after each multiply, one after each add), which the hardware performs identically. "
            "This is why the tests compare bit patterns, not values within a tolerance.")


CALC = """## Calculation logic

Every expected value in this report comes from `test/bf16_model.py`, an integer-only model of the chip's arithmetic. A test passes when the chip's 16-bit result is identical to the model's, bit for bit.

### BF16 encoding

A BF16 value is 16 bits: sign (bit 15), exponent (bits 14–7, bias 127) and mantissa (bits 6–0) with a hidden leading 1. The value is (−1)^s × 1.m × 2^(e−127).

| Exponent field | Mantissa | Meaning in this design |
| --- | --- | --- |
| 0 | any | zero; subnormals are read as zero (DAZ) |
| 1–254 | any | normal number |
| 255 | 0 | ±inf |
| 255 | ≠ 0 | NaN; every NaN result is the single quiet NaN `7fc0` |

Host-side conversion (`from_float`) rounds a float32 to BF16 with round-to-nearest-even, flushing subnormals to zero. The decimals shown in this report are the exact values of the bit patterns (`to_float`).

### Multiply, `mul(a, b)`

1. **Specials first.** Any NaN input gives `7fc0`. inf × 0 gives `7fc0`. inf × nonzero gives ±inf. Any zero or subnormal input gives a zero with sign sa ⊕ sb.
2. **Significands.** (0x80 | ma) × (0x80 | mb) is a 16-bit integer, because each operand is 1.m scaled by 2⁷.
3. **Exponent.** e = ea + eb − 127. If product bit 15 is set, the top 8 bits are kept and e increases by 1; otherwise bits 14–7 are kept.
4. **Round to nearest, ties to even.** The bit just below the kept 8 is the guard bit g, and the OR of every lower bit is the sticky bit. The result rounds up when g = 1 and (sticky = 1 or the kept LSB = 1). A carry out of the mantissa renormalizes it.
5. **Range.** e ≥ 255 gives ±inf (overflow). e ≤ 0 gives ±0 (flush to zero).

### Add, `add(a, b)`

1. **Specials.** NaN gives `7fc0`. inf + inf of the same sign gives inf; inf − inf gives `7fc0`. inf + finite gives inf. Zeros pass the other operand through, and 0 + 0 keeps the sign only when both are −0.
2. **Order and align.** Swap so that |a| ≥ |b|. Both significands get three extra low bits (guard, round, sticky). The smaller one shifts right by d = ea − eb, and every bit shifted out is ORed into sticky. If d ≥ 11, the smaller operand becomes sticky only.
3. **Add or subtract** by sign. A carry renormalizes right by one. For a subtraction, an exact zero gives +0; otherwise the result shifts left until the hidden bit is back, lowering e by one per step. This is the long normalize that `test_cancellation` exercises.
4. **Round** with RNE on the guard bit and the round|sticky bits, then apply the same range handling as multiply.

### Multiply-accumulate and matrix product

- `mac(acc, a, b) = add(acc, mul(a, b))`. It is **not fused**: the product is rounded to BF16 before the add, exactly as `bf16_mac_seq` does it.
- `matmul_ref(A, B, n, k, m)` computes each C[i][j] as a chain starting from acc = +0, applying acc = mac(acc, A[i][t], B[t][j]) for t = 0, 1, …, k−1, in the same order the array accumulates. Floating-point addition is not associative, so the order matters for bit-exactness.
- The inner dimension is zero-padded up to a multiple of 4, exactly as the host tiles it. Adding +0 × x leaves a nonzero accumulator unchanged.
- CLEAR_GEMM starts each PE's accumulator from +0. GEMM continues from the current C. So CLEAR_GEMM(A1, B1) followed by GEMM(A2, B2) equals a single K = 8 chain over [A1 | A2] × [B1 ; B2]. `test_accumulate`, `test_rerun_without_reload` and the tiled test check exactly this.
- **Tiling.** For an n×k by k×m product, the host computes each 4×4 output tile as one CLEAR_GEMM on the first 4-wide K block, then one GEMM per remaining block, then a READ_C. That is ⌈n/4⌉·⌈m/4⌉·⌈k/4⌉ runs: 8 runs for 8×8×8 and 12 runs for 5×9×6.

### Worked example: `test_random`, run 1, C[0][0]

{example}

### MAC unit check and latency

`test_mac` drives `bf16_mac_seq` directly with (acc, a, b) and compares `result` with `mac(acc, a, b)`. Latency is the number of clock edges from the `go` pulse to `done`. One row engine serves its 4 PEs in turn every 128-cycle beat, and at most 4 × (27 + 2) + 1 = 117 cycles of each beat are used. A simulation-only assertion in `gemm_controller` fires if any row is still busy at the next beat.

### How the counts in this report are made

- **Pass/fail** per test comes from cocotb's `results.xml`.
- **Bit-exact** counts compare each READ_C value with the `matmul_ref` value the test itself asserted against. Both are captured by `test/report/test_report.py`, which wraps the test helpers without changing what is sent or checked.
- **MAC vectors** and latencies are captured by `test/report/test_mac_report.py`, which uses the same `go`/`done` loop as `test_mac.run`.
- **On-chip run counts:** 1 + 20 + 2 + 3 + 1 + 3 + 1 + 1 + 2 + 1 + (8 + 12) = 55 GEMM runs.
"""


# ---------------------------------------------------------------------------
# MAC section
# ---------------------------------------------------------------------------
def sec_mac():
    lat = collections.Counter(int(r["latency_cycles"]) for r in mac_rows)
    bad = [r for r in mac_rows if r["pass"] != "True"]
    by = collections.Counter(r["suite"] for r in mac_rows)
    s = (f"## BF16 MAC unit (`bf16_mac_seq`)\n\n{len(mac_rows):,} vectors, {len(bad)} mismatches, worst-case latency {max(lat)} cycles.\n\n"
         "| Test | Vectors | Inputs | Result |\n| --- | --- | --- | --- |\n"
         f"| `test_specials` | {by['specials']:,} | every acc × every a of 20 special patterns, b from every third pattern | {ok(macx.get('test_specials', (False,))[0])} |\n"
         f"| `test_random` | {by['random']:,} | seed 1: 10 % specials, 30 % exponents 120–134, 60 % any bit pattern | {ok(macx.get('test_random', (False,))[0])} |\n\n"
         "Latency distribution (cycles: vectors): " + ", ".join(f"{c}: {n:,}" for c, n in sorted(lat.items())) + ".\n\n"
         "Representative special-grid vectors (all vectors are in `test_vectors/mac_vectors.csv`):\n\n"
         "| acc | a | b | Expected | Got | Cycles | Result |\n| --- | --- | --- | --- | --- | --- | --- |\n")
    pick = [("0000", "7f80", "0000"), ("3f80", "7f80", "4000"), ("ff80", "7f80", "4000"), ("3f80", "7fc0", "4000"),
            ("3f80", "3f80", "7f81"), ("7f7f", "7f7f", "4000"), ("ff7f", "7f7f", "4000"), ("0000", "7f7f", "7f00"),
            ("0000", "0001", "4000"), ("0001", "3f80", "807f"), ("0000", "0080", "0080"), ("8000", "8000", "4000"),
            ("8000", "3f80", "0000"), ("bf80", "3f80", "4000"), ("3f81", "3f80", "4000"), ("3fff", "3f81", "4000")]
    idx = {(r["acc"], r["a"], r["b"]): r for r in mac_rows if r["suite"] == "specials"}
    for p in pick:
        r = idx.get(p)
        if r:
            h = lambda x: f"`{x}` ({fv(int(x, 16))})"
            s += f"| {h(r['acc'])} | {h(r['a'])} | {h(r['b'])} | `{r['expected']}` | {h(r['got'])} | {r['latency_cycles']} | {ok(r['pass'] == 'True')} |\n"
    if bad:
        s += "\nMismatches:\n\n| suite | idx | acc | a | b | expected | got |\n| --- | --- | --- | --- | --- | --- | --- |\n"
        s += "".join(f"| {r['suite']} | {r['idx']} | {r['acc']} | {r['a']} | {r['b']} | {r['expected']} | {r['got']} |\n" for r in bad[:50])
    return s.strip()


# ---------------------------------------------------------------------------
# assemble
# ---------------------------------------------------------------------------
def summary():
    n_rtl = sum(v[0] for v in rtl.values())
    n_mac = sum(v[0] for v in macx.values())
    rows = "".join(f"| {i + 1} | `{name}` | {simtime.get(name, 0):,.0f} | {ok(v[0])} |\n" for i, (name, v) in enumerate(rtl.items()))
    return f"""# Test report: 4x4 BF16 systolic array

Commit `{commit}` ({commit_date}). Reproduce with `test/report/run_report.sh`.{(' ' + tools) if tools else ''}

## Summary

| Bench | Result |
| --- | --- |
| Full chip, RTL (`test/test.py`) | {n_rtl}/{len(rtl)} pass |
| BF16 MAC unit (`test/mac`) | {n_mac}/{len(macx)} pass, {len(mac_rows):,} vectors |
| Data prep unit (`test/prep/tb_data_prep_unit.sv`) | {prep} |

The data-prep testbench predates the `step` port of `data_prep_unit` and the one-cycle start latency, and CI does not run it. With `logic step = 1;` declared and one extra cycle after the `start` pulse, it passes at N,K = 4,4 · 2,2 · 8,8 · 4,8 · 8,4.

Gate-level and implementation results are not produced by this script. They come from the `gds` workflow (`gl_test`, `precheck` jobs) and are recorded in [`VALIDATION.md`](VALIDATION.md). As of 2026-11-03, the latest run is [40569980439](https://github.com/Nilovski/tt_bf16_systolic/actions/runs/40569980439): gate-level 14/14 pass, precheck pass, 0 DRC/LVS/antenna errors. Setup slack is −0.695 ns at `max_ss_100C_1v60` and −0.301 ns at `nom_ss_100C_1v60`, and positive at every tt and ff corner.

Matrices are row-major. Values are BF16, shown as exact decimals and as the 16-bit hex pattern the chip returned.

## Full-chip tests

| # | Test | Sim time (ns) | Result |
| --- | --- | --- | --- |
{rows}"""


def fullchip_csv():
    with open(os.path.join(VEC, "fullchip_vectors.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["test", "step", "op", "A_hex", "B_hex", "C_dut_hex", "C_ref_hex", "match"])
        for name, ev in trace.items():
            runs, rds, rfs = ops(ev, "CLEAR_GEMM", "GEMM"), ops(ev, "READ_C"), ops(ev, "REF")
            if name in ("test_identity", "test_random", "test_specials", "test_cancellation", "test_read_c_slow_host"):
                if name == "test_read_c_slow_host":
                    rb = [e["got"] for e in ops(ev, "RECV")]
                    rds = [{"got": [rb[2 * i] | rb[2 * i + 1] << 8 for i in range(16)]}]
                for i, (r, d, f) in enumerate(zip(runs, rds, rfs)):
                    j = lambda v: " ".join(f"{x:04x}" for x in v)
                    w.writerow([name, i + 1, r["op"], j(r["a"]), j(r["b"]), j(d["got"]), j(f["exp"]), d["got"] == f["exp"]])


def main():
    os.makedirs(VEC, exist_ok=True)
    doc = "\n\n".join([summary().rstrip(), sec_tests(), sec_mac(),
                       CALC.replace("{example}", worked_example()).strip()]) + "\n"
    with open(os.path.join(DOCS, "TEST_REPORT.md"), "w") as fh:
        fh.write(doc)
    fullchip_csv()
    with open(os.path.join(VEC, "mac_vectors.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(list(mac_rows[0].keys()))
        w.writerows([list(r.values()) for r in mac_rows])
    print(f"wrote {os.path.relpath(os.path.join(DOCS, 'TEST_REPORT.md'), ROOT)} and docs/test_vectors/")


if __name__ == "__main__":
    main()
