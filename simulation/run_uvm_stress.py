"""Run the Milestone 13 randomized UVM stress regression."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILELIST_PATH = PROJECT_ROOT / "simulation" / "filelist_uvm_stress.f"

TEST_NAME = "dpd_m13_stress_uvm_test"
TOTAL_SAMPLE_COUNT = 2048
RUNNER_PASS_MARKER = "MILESTONE_13_UVM_STRESS_CHECK_PASS"

FORBIDDEN_PROJECT_WARNINGS = (
    "LatchInferred",
    "AlwaysFFNba",
    "MultiBlockWrite",
    "ReadMemAddr",
)

SUMMARY_PATTERN = re.compile(
    r"DPD_STRESS_SUMMARY "
    r"inputs=(?P<inputs>\d+) "
    r"outputs=(?P<outputs>\d+) "
    r"dropped_on_reset=(?P<dropped>\d+) "
    r"mismatches=(?P<mismatches>\d+) "
    r"unexpected=(?P<unexpected>\d+) "
    r"resets=(?P<resets>\d+) "
    r"identity_inputs=(?P<identity>\d+) "
    r"zero_inputs=(?P<zero>\d+) "
    r"input_idle_cycles=(?P<input_idle>\d+) "
    r"output_stall_cycles=(?P<output_stall>\d+) "
    r"max_output_stall=(?P<max_stall>\d+)"
)

PASS_PATTERN = re.compile(
    r"DPD_UVM_STRESS_PASS "
    r"seed=(?P<seed>\d+) "
    r"inputs=(?P<inputs>\d+) "
    r"outputs=(?P<outputs>\d+) "
    r"dropped=(?P<dropped>\d+) "
    r"mismatches=(?P<mismatches>\d+) "
    r"coefficient_updates=(?P<updates>\d+)"
)


def final_uvm_count(text: str, severity: str) -> int | None:
    matches = re.findall(rf"UVM_{severity}\s*:\s*(\d+)", text)
    if not matches:
        return None
    return int(matches[-1])


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed",
        type=int,
        default=13013,
        help="Deterministic 32-bit stress seed.",
    )
    parser.add_argument(
        "--no-waves",
        action="store_true",
        help="Disable VCD generation.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    seed = arguments.seed & 0xFFFF_FFFF

    dsim = shutil.which(os.environ.get("DSIM_BIN", "dsim"))
    if dsim is None:
        print("ERROR: DSim is not active in this terminal.", file=sys.stderr)
        return 3

    log_path = (
        PROJECT_ROOT
        / "reports"
        / "logs"
        / f"dpd_uvm_stress_seed_{seed}.log"
    )
    result_path = (
        PROJECT_ROOT
        / "reports"
        / "results"
        / f"uvm_stress_seed_{seed}.json"
    )
    wave_path = (
        PROJECT_ROOT
        / "reports"
        / "waves"
        / f"dpd_uvm_stress_seed_{seed}.vcd"
    )

    log_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    wave_path.parent.mkdir(parents=True, exist_ok=True)

    if log_path.exists():
        log_path.unlink()

    command = [
        dsim,
        "-uvm",
        "1.2",
        "-F",
        str(FILELIST_PATH.relative_to(PROJECT_ROOT)),
        "-top",
        "work.dpd_stress_tb",
        "-timescale",
        "1ns/1ps",
        f"+UVM_TESTNAME={TEST_NAME}",
        "+UVM_VERBOSITY=UVM_LOW",
        "+UVM_NO_RELNOTES",
        f"+STRESS_SEED={seed}",
    ]

    if not arguments.no_waves:
        command.extend(
            [
                "+acc",
                "-waves",
                str(wave_path.relative_to(PROJECT_ROOT)),
            ]
        )

    command.extend(
        [
            "-l",
            str(log_path.relative_to(PROJECT_ROOT)),
        ]
    )

    print(f"Running randomized DPD UVM stress regression, seed={seed}:")
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

    if completed.returncode != 0:
        print(f"ERROR: DSim returned {completed.returncode}.", file=sys.stderr)
        return completed.returncode

    present_warnings = [
        warning
        for warning in FORBIDDEN_PROJECT_WARNINGS
        if warning in combined
    ]
    if present_warnings:
        print(
            "ERROR: Project warnings remain: " + ", ".join(present_warnings),
            file=sys.stderr,
        )
        return 4

    for severity in ("WARNING", "ERROR", "FATAL"):
        count = final_uvm_count(combined, severity)
        if count != 0:
            print(
                f"ERROR: UVM {severity.lower()} count is {count}.",
                file=sys.stderr,
            )
            return 5

    summary_matches = list(SUMMARY_PATTERN.finditer(combined))
    pass_matches = list(PASS_PATTERN.finditer(combined))

    if not summary_matches:
        print("ERROR: Missing DPD_STRESS_SUMMARY.", file=sys.stderr)
        return 6

    if not pass_matches:
        print("ERROR: Missing DPD_UVM_STRESS_PASS marker.", file=sys.stderr)
        return 7

    summary = summary_matches[-1]
    passed = pass_matches[-1]

    values = {
        key: int(summary.group(key))
        for key in (
            "inputs",
            "outputs",
            "dropped",
            "mismatches",
            "unexpected",
            "resets",
            "identity",
            "zero",
            "input_idle",
            "output_stall",
            "max_stall",
        )
    }

    if int(passed.group("seed")) != seed:
        print("ERROR: Stress pass marker seed does not match.", file=sys.stderr)
        return 8

    if values["inputs"] != TOTAL_SAMPLE_COUNT:
        print(
            f"ERROR: Input count is {values['inputs']}, expected {TOTAL_SAMPLE_COUNT}.",
            file=sys.stderr,
        )
        return 9

    if values["outputs"] + values["dropped"] != values["inputs"]:
        print(
            "ERROR: Output plus reset-drop accounting does not equal input count.",
            file=sys.stderr,
        )
        return 10

    required_positive = (
        "dropped",
        "resets",
        "identity",
        "zero",
        "input_idle",
        "output_stall",
        "max_stall",
    )
    for field in required_positive:
        if values[field] <= 0:
            print(f"ERROR: Stress field {field} was not exercised.", file=sys.stderr)
            return 11

    if values["mismatches"] != 0 or values["unexpected"] != 0:
        print("ERROR: Stress scoreboard reported failures.", file=sys.stderr)
        return 12

    coefficient_updates = int(passed.group("updates"))
    if coefficient_updates < 3:
        print(
            f"ERROR: Only {coefficient_updates} coefficient updates were observed.",
            file=sys.stderr,
        )
        return 13

    result = {
        "test_name": TEST_NAME,
        "seed": seed,
        "accepted_input_count": values["inputs"],
        "checked_output_count": values["outputs"],
        "dropped_expected_on_reset": values["dropped"],
        "mismatch_count": values["mismatches"],
        "unexpected_output_count": values["unexpected"],
        "reset_count": values["resets"],
        "identity_input_count": values["identity"],
        "zero_input_count": values["zero"],
        "input_idle_cycle_count": values["input_idle"],
        "output_stall_cycle_count": values["output_stall"],
        "maximum_output_stall_cycles": values["max_stall"],
        "coefficient_update_count": coefficient_updates,
        "waveform_dump_enabled": not arguments.no_waves,
        "log_path": str(log_path),
        "waveform_path": None if arguments.no_waves else str(wave_path),
    }
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))
    print(f"DSim log: {log_path}")
    print(f"Regression metrics: {result_path}")
    if not arguments.no_waves:
        print(f"DSim waveform: {wave_path}")
    print(RUNNER_PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
