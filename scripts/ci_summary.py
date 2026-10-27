#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Print CI results as GitHub Actions notices, so they can be read from the
run page (and its API) without downloading artifacts.

  ci_summary.py tests  <results.xml> <label>   cocotb/JUnit results
  ci_summary.py build  <run dir>                LibreLane final metrics
  ci_summary.py hashes <file> ...               SHA-256 of the given files
"""
import glob
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

MAX = 3500  # keep each annotation well under GitHub's size limit


def notice(title, lines):
    chunk, part = [], 1
    for line in lines + [None]:
        if line is None or sum(len(x) + 1 for x in chunk) + len(line) > MAX:
            if chunk:
                body = "%0A".join(x.replace("%", "%25") for x in chunk)
                print(f"::notice title={title} ({part})::{body}")
                part += 1
            chunk = []
        if line is not None:
            chunk.append(line)


def tests(path, label):
    root = ET.parse(path).getroot()
    lines, npass, nfail, nskip = [], 0, 0, 0
    for tc in root.iter("testcase"):
        if tc.find("failure") is not None or tc.find("error") is not None:
            st, nfail = "FAIL", nfail + 1
        elif tc.find("skipped") is not None:
            st, nskip = "SKIP", nskip + 1
        else:
            st, npass = "PASS", npass + 1
        t = tc.get("time", "")
        sim = tc.get("sim_time_ns", "")
        lines.append(f"{st} {tc.get('name')} time_s={t} sim_ns={sim}")
    head = f"{label}: {npass} pass, {nfail} fail, {nskip} skip"
    notice(label, [head] + lines)


KEYS = re.compile(
    r"^(design__(instance__(area|count|utilization)|die__bbox|core__bbox|"
    r"max_(slew|cap|fanout)_violation__count|lvs_error__count|"
    r"xor_difference__count|power_grid_violation__count)|"
    r"timing__(setup|hold)__(ws|tns|wns)|timing__(setup|hold)_vio__count|"
    r"clock__skew__worst_(setup|hold)|route__(drc_errors|wirelength)|"
    r"magic__(drc_error|illegal_overlap)__count|klayout__drc_error__count|"
    r"antenna__violating__(nets|pins)|power__total|flow__(errors|warnings)__count)"
)


def build(run_dir):
    found = sorted(glob.glob(os.path.join(run_dir, "**", "final", "metrics.json"), recursive=True))
    if not found:
        found = sorted(glob.glob(os.path.join(run_dir, "**", "metrics.json"), recursive=True))
    if not found:
        print("::warning title=build metrics::no metrics.json found")
        return
    path = found[-1]
    m = json.load(open(path))
    lines = [f"source: {path}"]
    for k in sorted(m):
        if KEYS.match(k.split("__corner:")[0]):
            lines.append(f"{k} = {m[k]}")
    notice("build metrics", lines)
    cfg = sorted(glob.glob(os.path.join(run_dir, "**", "resolved.json"), recursive=True))
    if cfg:
        c = json.load(open(cfg[-1]))
        keep = ["CLOCK_PERIOD", "PL_TARGET_DENSITY_PCT", "DIE_AREA", "FP_SIZING",
                "STA_CORNERS", "DEFAULT_CORNER", "PDK", "STD_CELL_LIBRARY"]
        notice("build config", [f"{k} = {c.get(k)}" for k in keep if k in c])


def hashes(files):
    notice("source hashes", [f"{hashlib.sha256(open(f, 'rb').read()).hexdigest()}  {f}" for f in files])


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "tests":
        tests(sys.argv[2], sys.argv[3])
    elif mode == "build":
        build(sys.argv[2])
    elif mode == "hashes":
        hashes(sys.argv[2:])
