"""Run the warning-clean complete 36,864-sample RTL DPD regression."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILELIST_PATH = PROJECT_ROOT / "simulation" / "filelist_dpd_core.f"
LOG_PATH = PROJECT_ROOT / "reports" / "logs" / "dpd_core_full.log"
RESULT_PATH = PROJECT_ROOT / "reports" / "results" / "rtl_full_regression.json"

VECTOR_DIRECTORY = "vectors/rtl/ofdm_nominal"
VECTOR_PATH = PROJECT_ROOT / VECTOR_DIRECTORY / "input_i.hex"

SAMPLE_COUNT = 36864
TEST_NAME = "ofdm_nominal"
SIMULATION_PASS_PREFIX = (
    f"DPD_CORE_REGRESSION_PASS test={TEST_NAME} samples={SAMPLE_COUNT}"
)
RUNNER_PASS_MARKER = "MILESTONE_10_RTL_FULL_WARNING_CLEAN_PASS"

FORBIDDEN_WARNINGS = (
    "MultiBlockWrite",
    "LatchInferred",
    "AlwaysFFNba",
    "ReadMemAddr",
)

RESULT_PATTERN = re.compile(
    r"DPD_CORE_REGRESSION_PASS "
    r"test=(?P<test>\S+) "
    r"samples=(?P<samples>\d+) "
    r"cycles=(?P<cycles>\d+) "
    r"latency_cycles=(?P<latency>\d+)"
)


def main() -> int:
    if not VECTOR_PATH.exists():
        print(
            "ERROR: Full RTL vectors are missing. Run "
            "python python/scripts/generate_golden_vectors.py first.",
            file=sys.stderr,
        )
        return 2

    dsim = shutil.which(os.environ.get("DSIM_BIN", "dsim"))
    if dsim is None:
        print("ERROR: DSim is not active in this terminal.", file=sys.stderr)
        return 3

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)

    command = [
        dsim,
        "-F",
        str(FILELIST_PATH.relative_to(PROJECT_ROOT)),
        "-top",
        "work.dpd_core_tb",
        "-timescale",
        "1ns/1ps",
        f"+VECTOR_DIR={VECTOR_DIRECTORY}",
        f"+TEST_NAME={TEST_NAME}",
        f"+SAMPLE_COUNT={SAMPLE_COUNT}",
        "-l",
        str(LOG_PATH.relative_to(PROJECT_ROOT)),
    ]

    print("Running warning-clean complete RTL DPD regression:")
    print(" ".join(command))

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(completed.stdout, end="")

    log_text = ""
    if LOG_PATH.exists():
        log_text = LOG_PATH.read_text(encoding="utf-8", errors="replace")

    combined = completed.stdout + "\n" + log_text

    if completed.returncode != 0:
        print(f"ERROR: DSim returned {completed.returncode}.", file=sys.stderr)
        return completed.returncode

    if SIMULATION_PASS_PREFIX not in combined:
        print(
            f"ERROR: Missing pass marker {SIMULATION_PASS_PREFIX}.",
            file=sys.stderr,
        )
        return 4

    present_warnings = [
        warning for warning in FORBIDDEN_WARNINGS
        if warning in combined
    ]
    if present_warnings:
        print(
            "ERROR: Forbidden warnings remain: "
            + ", ".join(present_warnings),
            file=sys.stderr,
        )
        return 5

    matches = list(RESULT_PATTERN.finditer(combined))
    if not matches:
        print("ERROR: Could not parse regression statistics.", file=sys.stderr)
        return 6

    match = matches[-1]
    samples = int(match.group("samples"))
    cycles = int(match.group("cycles"))
    latency = int(match.group("latency"))

    result = {
        "test_name": match.group("test"),
        "sample_count": samples,
        "cycle_count": cycles,
        "latency_cycles": latency,
        "accepted_samples_per_cycle": samples / cycles,
        "exact_integer_match": True,
        "forbidden_warning_count": 0,
        "waveform_dump_enabled": False,
        "log_path": str(LOG_PATH),
    }

    RESULT_PATH.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2))
    print(f"DSim log: {LOG_PATH}")
    print(f"Regression metrics: {RESULT_PATH}")
    print(RUNNER_PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
