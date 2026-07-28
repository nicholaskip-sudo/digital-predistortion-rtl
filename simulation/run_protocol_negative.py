"""Prove that the ready/valid protocol assertions reject bad behavior."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILELIST_PATH = PROJECT_ROOT / "simulation" / "filelist_protocol_negative.f"
LOG_DIRECTORY = PROJECT_ROOT / "reports" / "logs"
PASS_MARKER = "MILESTONE_13_NEGATIVE_PROTOCOL_CHECK_PASS"

TESTS = (
    (
        "input_stability",
        "UVM interface: input changed before acceptance.",
    ),
    (
        "output_stability",
        "UVM interface: output changed while backpressured.",
    ),
)


def run_negative_test(
    dsim: str,
    test_name: str,
    expected_message: str,
) -> bool:
    log_path = LOG_DIRECTORY / f"negative_{test_name}.log"
    if log_path.exists():
        log_path.unlink()

    command = [
        dsim,
        "-F",
        str(FILELIST_PATH.relative_to(PROJECT_ROOT)),
        "-top",
        "work.dpd_protocol_negative_tb",
        "-timescale",
        "1ns/1ps",
        f"+NEGATIVE_TEST={test_name}",
        "-l",
        str(log_path.relative_to(PROJECT_ROOT)),
    ]

    print(f"Running expected-failure protocol test: {test_name}")
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
    if log_path.exists():
        log_text = log_path.read_text(encoding="utf-8", errors="replace")

    combined = completed.stdout + "\n" + log_text

    if "NEGATIVE_PROTOCOL_TEST_UNEXPECTED_PASS" in combined:
        print(
            f"ERROR: Negative test {test_name} did not trigger its assertion.",
            file=sys.stderr,
        )
        return False

    if expected_message not in combined:
        print(
            f"ERROR: Negative test {test_name} did not emit the expected assertion message.",
            file=sys.stderr,
        )
        return False

    print(
        f"EXPECTED_ASSERTION_OBSERVED test={test_name} "
        f"returncode={completed.returncode}"
    )
    return True


def main() -> int:
    dsim = shutil.which(os.environ.get("DSIM_BIN", "dsim"))
    if dsim is None:
        print("ERROR: DSim is not active in this terminal.", file=sys.stderr)
        return 3

    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    for test_name, expected_message in TESTS:
        if not run_negative_test(dsim, test_name, expected_message):
            return 4

    print(PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
