"""Run the warning-clean 512-sample RTL DPD regression with DSim."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILELIST_PATH = PROJECT_ROOT / "simulation" / "filelist_dpd_core.f"
LOG_PATH = PROJECT_ROOT / "reports" / "logs" / "dpd_core_short.log"
WAVE_PATH = PROJECT_ROOT / "reports" / "waves" / "dpd_core_short.vcd"
VECTOR_DIRECTORY = "vectors/rtl/ofdm_short"
VECTOR_PATH = PROJECT_ROOT / VECTOR_DIRECTORY / "input_i.hex"

SAMPLE_COUNT = 512
TEST_NAME = "ofdm_short"
SIMULATION_PASS_MARKER = (
    f"DPD_CORE_REGRESSION_PASS test={TEST_NAME} samples={SAMPLE_COUNT}"
)
RUNNER_PASS_MARKER = "MILESTONE_10_RTL_SHORT_WARNING_CLEAN_PASS"

FORBIDDEN_WARNINGS = (
    "MultiBlockWrite",
    "LatchInferred",
    "AlwaysFFNba",
    "ReadMemAddr",
)


def main() -> int:
    if not VECTOR_PATH.exists():
        print(
            "ERROR: Short RTL vectors are missing. Run "
            "python python/scripts/generate_golden_vectors.py first.",
            file=sys.stderr,
        )
        return 2

    dsim = shutil.which(os.environ.get("DSIM_BIN", "dsim"))
    if dsim is None:
        print("ERROR: DSim is not active in this terminal.", file=sys.stderr)
        return 3

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    WAVE_PATH.parent.mkdir(parents=True, exist_ok=True)

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
        "+acc",
        "-waves",
        str(WAVE_PATH.relative_to(PROJECT_ROOT)),
        "-l",
        str(LOG_PATH.relative_to(PROJECT_ROOT)),
    ]

    print("Running warning-clean RTL DPD short regression:")
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

    if SIMULATION_PASS_MARKER not in combined:
        print(
            f"ERROR: Missing pass marker {SIMULATION_PASS_MARKER}.",
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

    print(f"DSim log: {LOG_PATH}")
    print(f"DSim waveform: {WAVE_PATH}")
    print(RUNNER_PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
