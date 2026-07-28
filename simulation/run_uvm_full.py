"""Run the full 36,864-sample UVM DPD regression and coverage report."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILELIST_PATH = PROJECT_ROOT / "simulation" / "filelist_uvm.f"
LOG_PATH = PROJECT_ROOT / "reports" / "logs" / "dpd_uvm_full.log"
RESULT_PATH = PROJECT_ROOT / "reports" / "results" / "uvm_full_regression.json"
COVERAGE_ROOT = PROJECT_ROOT / "reports" / "coverage" / "uvm_full"
COVERAGE_DATABASE_SOURCE = PROJECT_ROOT / "metrics.db"
COVERAGE_DATABASE_COPY = COVERAGE_ROOT / "metrics.db"
COVERAGE_HTML_DIRECTORY = COVERAGE_ROOT / "html"

VECTOR_DIRECTORY = "vectors/rtl/ofdm_nominal"
VECTOR_PATH = PROJECT_ROOT / VECTOR_DIRECTORY / "input_i.hex"

SAMPLE_COUNT = 36864
TEST_NAME = "dpd_full_uvm_test"
PASS_MARKER = f"DPD_UVM_FULL_PASS samples={SAMPLE_COUNT} mismatches=0"
COVERAGE_PASS_MARKER = "DPD_FUNCTIONAL_COVERAGE_PASS"
RUNNER_PASS_MARKER = "MILESTONE_12_UVM_FULL_COVERAGE_CHECK_PASS"

FORBIDDEN_PROJECT_WARNINGS = (
    "LatchInferred",
    "AlwaysFFNba",
    "MultiBlockWrite",
    "ReadMemAddr",
)

COVERAGE_SUMMARY_PATTERN = re.compile(
    r"DPD_COVERAGE_SUMMARY "
    r"stream=(?P<stream>[0-9]+(?:\.[0-9]+)?) "
    r"stall=(?P<stall>[0-9]+(?:\.[0-9]+)?) "
    r"input_transfers=(?P<input_transfers>\d+) "
    r"output_transfers=(?P<output_transfers>\d+) "
    r"saturated_outputs=(?P<saturated_outputs>\d+) "
    r"max_output_stall=(?P<max_output_stall>\d+)"
)

MANDATORY_COVERAGE_PATTERN = re.compile(
    r"DPD_FUNCTIONAL_COVERAGE_PASS "
    r"input_quadrants=(?P<input_quadrants>\d+)/4 "
    r"output_quadrants=(?P<output_quadrants>\d+)/4 "
    r"input_magnitude=(?P<input_magnitude>\d+)/4 "
    r"output_magnitude=(?P<output_magnitude>\d+)/4 "
    r"protocol_states=(?P<protocol_states>\d+)/6 "
    r"ready_states=(?P<ready_states>\d+)/2 "
    r"saturation_states=(?P<saturation_states>\d+)/2"
)


def final_uvm_count(text: str, severity: str) -> int | None:
    matches = re.findall(
        rf"UVM_{severity}\s*:\s*(\d+)",
        text,
    )
    if not matches:
        return None
    return int(matches[-1])


def find_dcreport(dsim_path: str) -> Path | None:
    dsim_file = Path(dsim_path)
    candidates = (
        dsim_file.with_name("dcreport.EXE"),
        dsim_file.with_name("dcreport.exe"),
        dsim_file.with_name("dcreport"),
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    discovered = shutil.which("dcreport")
    if discovered is not None:
        return Path(discovered)

    return None


def generate_html_coverage_report(
    dsim_path: str,
    coverage_database: Path,
) -> tuple[bool, str]:
    dcreport = find_dcreport(dsim_path)
    if dcreport is None:
        return False, "dcreport was not found in the DSim installation."

    if COVERAGE_HTML_DIRECTORY.exists():
        shutil.rmtree(COVERAGE_HTML_DIRECTORY)
    COVERAGE_HTML_DIRECTORY.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [
            str(dcreport),
            "-out_dir",
            str(COVERAGE_HTML_DIRECTORY),
            str(coverage_database),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    print(completed.stdout, end="")

    if completed.returncode != 0:
        return (
            False,
            f"dcreport returned {completed.returncode}.",
        )

    return True, str(COVERAGE_HTML_DIRECTORY)


def main() -> int:
    if not VECTOR_PATH.exists():
        print(
            "ERROR: Full UVM vectors are missing. Run "
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
    COVERAGE_ROOT.mkdir(parents=True, exist_ok=True)

    if COVERAGE_DATABASE_SOURCE.exists():
        COVERAGE_DATABASE_SOURCE.unlink()

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
        "-l",
        str(LOG_PATH.relative_to(PROJECT_ROOT)),
    ]

    print("Running full DPD UVM regression with functional coverage:")
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

    if COVERAGE_PASS_MARKER not in combined:
        print(
            f"ERROR: Missing coverage marker {COVERAGE_PASS_MARKER}.",
            file=sys.stderr,
        )
        return 5

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
        return 6

    error_count = final_uvm_count(combined, "ERROR")
    fatal_count = final_uvm_count(combined, "FATAL")
    warning_count = final_uvm_count(combined, "WARNING")

    if error_count != 0:
        print(f"ERROR: UVM error count is {error_count}.", file=sys.stderr)
        return 7

    if fatal_count != 0:
        print(f"ERROR: UVM fatal count is {fatal_count}.", file=sys.stderr)
        return 8

    if warning_count != 0:
        print(f"ERROR: UVM warning count is {warning_count}.", file=sys.stderr)
        return 9

    coverage_matches = list(COVERAGE_SUMMARY_PATTERN.finditer(combined))
    mandatory_matches = list(MANDATORY_COVERAGE_PATTERN.finditer(combined))

    if not coverage_matches:
        print("ERROR: Could not parse the coverage summary.", file=sys.stderr)
        return 10

    if not mandatory_matches:
        print("ERROR: Could not parse mandatory coverage results.", file=sys.stderr)
        return 11

    coverage_match = coverage_matches[-1]
    mandatory_match = mandatory_matches[-1]

    input_transfers = int(coverage_match.group("input_transfers"))
    output_transfers = int(coverage_match.group("output_transfers"))

    if input_transfers != SAMPLE_COUNT or output_transfers != SAMPLE_COUNT:
        print(
            "ERROR: Coverage transfer counts do not match the dataset: "
            f"input={input_transfers}, output={output_transfers}.",
            file=sys.stderr,
        )
        return 12

    mandatory_expected = {
        "input_quadrants": 4,
        "output_quadrants": 4,
        "input_magnitude": 4,
        "output_magnitude": 4,
        "protocol_states": 6,
        "ready_states": 2,
        "saturation_states": 2,
    }

    for field, expected in mandatory_expected.items():
        actual = int(mandatory_match.group(field))
        if actual != expected:
            print(
                f"ERROR: Mandatory coverage {field} is {actual}/{expected}.",
                file=sys.stderr,
            )
            return 13

    if not COVERAGE_DATABASE_SOURCE.exists():
        print(
            "ERROR: DSim did not produce metrics.db.",
            file=sys.stderr,
        )
        return 14

    shutil.copy2(COVERAGE_DATABASE_SOURCE, COVERAGE_DATABASE_COPY)

    html_generated, html_result = generate_html_coverage_report(
        dsim,
        COVERAGE_DATABASE_COPY,
    )

    if not html_generated:
        print(
            f"WARNING: HTML coverage report was not generated: {html_result}",
            file=sys.stderr,
        )

    result = {
        "test_name": TEST_NAME,
        "sample_count": SAMPLE_COUNT,
        "mismatch_count": 0,
        "input_transfer_count": input_transfers,
        "output_transfer_count": output_transfers,
        "stream_coverage_percent": float(coverage_match.group("stream")),
        "stall_coverage_percent": float(coverage_match.group("stall")),
        "saturated_output_count": int(
            coverage_match.group("saturated_outputs")
        ),
        "max_output_stall_cycles": int(
            coverage_match.group("max_output_stall")
        ),
        "mandatory_coverage": {
            field: int(mandatory_match.group(field))
            for field in mandatory_expected
        },
        "uvm_warning_count": warning_count,
        "uvm_error_count": error_count,
        "uvm_fatal_count": fatal_count,
        "waveform_dump_enabled": False,
        "coverage_database": str(COVERAGE_DATABASE_COPY),
        "coverage_html_generated": html_generated,
        "coverage_html_directory": (
            str(COVERAGE_HTML_DIRECTORY) if html_generated else None
        ),
        "log_path": str(LOG_PATH),
    }

    RESULT_PATH.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2))
    print(f"DSim log: {LOG_PATH}")
    print(f"Regression metrics: {RESULT_PATH}")
    print(f"Coverage database: {COVERAGE_DATABASE_COPY}")
    if html_generated:
        print(f"Coverage HTML: {COVERAGE_HTML_DIRECTORY}")
    print(RUNNER_PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
