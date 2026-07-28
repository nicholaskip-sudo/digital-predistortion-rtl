"""Run the 512-sample UVM 1.2 DPD regression with Altair DSim."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILELIST_PATH = PROJECT_ROOT / "simulation" / "filelist_uvm.f"
LOG_PATH = PROJECT_ROOT / "reports" / "logs" / "dpd_uvm_short.log"
WAVE_PATH = PROJECT_ROOT / "reports" / "waves" / "dpd_uvm_short.vcd"
VECTOR_DIRECTORY = "vectors/rtl/ofdm_short"
VECTOR_PATH = PROJECT_ROOT / VECTOR_DIRECTORY / "input_i.hex"

SAMPLE_COUNT = 512
TEST_NAME = "dpd_short_uvm_test"
PASS_MARKER = f"DPD_UVM_SHORT_PASS samples={SAMPLE_COUNT} mismatches=0"
RUNNER_PASS_MARKER = "MILESTONE_11_UVM_SHORT_CHECK_PASS"

FORBIDDEN_PROJECT_WARNINGS = (
    "LatchInferred",
    "AlwaysFFNba",
    "MultiBlockWrite",
    "ReadMemAddr",
)


def final_uvm_count(text: str, severity: str) -> int | None:
    matches = re.findall(
        rf"UVM_{severity}\s*:\s*(\d+)",
        text,
    )
    if not matches:
        return None
    return int(matches[-1])


def main() -> int:
    if not VECTOR_PATH.exists():
        print(
            "ERROR: UVM input vectors are missing. Run "
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
        "-uvm",
        "1.2",
        "-F",
        str(FILELIST_PATH.relative_to(PROJECT_ROOT)),
        "-top",
        "work.dpd_uvm_tb",
        "-timescale",
        "1ns/1ps",
        f"+UVM_TESTNAME={TEST_NAME}",
        "+UVM_VERBOSITY=UVM_LOW",
        "+UVM_NO_RELNOTES",
        f"+VECTOR_DIR={VECTOR_DIRECTORY}",
        f"+SAMPLE_COUNT={SAMPLE_COUNT}",
        "+acc",
        "-waves",
        str(WAVE_PATH.relative_to(PROJECT_ROOT)),
        "-l",
        str(LOG_PATH.relative_to(PROJECT_ROOT)),
    ]

    print("Running DPD UVM 1.2 short regression:")
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

    if PASS_MARKER not in combined:
        print(f"ERROR: Missing pass marker {PASS_MARKER}.", file=sys.stderr)
        return 4

    present_warnings = [
        warning
        for warning in FORBIDDEN_PROJECT_WARNINGS
        if warning in combined
    ]
    if present_warnings:
        print(
            "ERROR: Project warnings remain: "
            + ", ".join(present_warnings),
            file=sys.stderr,
        )
        return 5

    error_count = final_uvm_count(combined, "ERROR")
    fatal_count = final_uvm_count(combined, "FATAL")
    warning_count = final_uvm_count(combined, "WARNING")

    if error_count != 0:
        print(f"ERROR: UVM error count is {error_count}.", file=sys.stderr)
        return 6

    if fatal_count != 0:
        print(f"ERROR: UVM fatal count is {fatal_count}.", file=sys.stderr)
        return 7

    if warning_count != 0:
        print(f"ERROR: UVM warning count is {warning_count}.", file=sys.stderr)
        return 8

    print(f"DSim log: {LOG_PATH}")
    print(f"DSim waveform: {WAVE_PATH}")
    print(RUNNER_PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
