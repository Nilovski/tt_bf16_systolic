#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Regenerate docs/TEST_REPORT.md and docs/test_vectors/ from fresh simulations.
#
#   pip install -r test/requirements.txt   # cocotb 2.1, pytest
#   test/report/run_report.sh              # needs iverilog on PATH
#
# Runs the full-chip suite and the MAC suite with tracing, tries the
# standalone data-prep testbench, then writes the report.
set -uo pipefail

REPORT="$(cd "$(dirname "$0")" && pwd)"
TEST="$(dirname "$REPORT")"
mkdir -p "$REPORT/out"

echo "Icarus $(iverilog -V 2>&1 | head -1 | awk '{print $4}'), cocotb $(python3 -c 'import cocotb; print(cocotb.__version__)'), Python $(python3 -c 'import platform; print(platform.python_version())')." > "$REPORT/out/tools.txt"

echo "== full chip (RTL)"
( cd "$TEST" && PYTHONPATH="$REPORT:$TEST:${PYTHONPATH:-}" make -B COCOTB_TEST_MODULES=test_report > "$REPORT/out/fullchip.log" 2>&1 )
grep "TESTS=" "$REPORT/out/fullchip.log"

echo "== MAC unit"
( cd "$TEST/mac" && PYTHONPATH="$REPORT:$TEST/mac:${PYTHONPATH:-}" make -B COCOTB_TEST_MODULES=test_mac_report > "$REPORT/out/mac.log" 2>&1 )
grep "TESTS=" "$REPORT/out/mac.log"

echo "== data prep unit"
if iverilog -g2012 -o "$REPORT/out/prep.vvp" "$TEST/prep/tb_data_prep_unit.sv" "$TEST/../src/prep/data_prep_unit.sv" > "$REPORT/out/prep.log" 2>&1; then
    res=$(vvp -n "$REPORT/out/prep.vvp" | grep -E "^(PASS|FAIL)" | tail -1)
    echo "${res:-no PASS/FAIL line}" > "$REPORT/out/prep.txt"
else
    echo "does not compile: $(grep -m1 error "$REPORT/out/prep.log" | sed 's/^[^:]*:[0-9]*: error: //')" > "$REPORT/out/prep.txt"
fi
cat "$REPORT/out/prep.txt"

python3 "$REPORT/make_report.py"
