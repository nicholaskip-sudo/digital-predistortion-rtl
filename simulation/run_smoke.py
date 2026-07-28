"""Run the Milestone 0 SystemVerilog smoke test with Altair DSim."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = PROJECT_ROOT / "reports" / "logs" / "dsim_smoke.log"
WAVE_PATH = PROJECT_ROOT / "reports" / "waves" / "dsim_smoke.vcd"
FILELIST_PATH = PROJECT_ROOT / "simulation" / "filelist_smoke.f"
PASS_MARKER = "DSIM_SMOKE_PASS"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dsim",
        default=os.environ.get("DSIM_BIN", "dsim"),
        help="DSim executable path. Defaults to DSIM_BIN or 'dsim'.",
    )
    parser.add_argument(
        "--no-waves",
        action="store_true",
        help="Run without producing a VCD waveform.",
    )
    return parser.parse_args()


def resolve_executable(executable: str) -> str:
    """Resolve DSim from an explicit path or the current PATH."""

    explicit_path = Path(executable).expanduser()
    if explicit_path.parent != Path(".") or explicit_path.is_absolute():
        if explicit_path.exists():
            return str(explicit_path.resolve())
        raise FileNotFoundError(f"DSim executable does not exist: {explicit_path}")

    resolved = shutil.which(executable)
    if resolved is None:
        raise FileNotFoundError(
            "Could not find the 'dsim' executable. Run 'dsim -version' in this "
            "terminal, set DSIM_BIN, or pass --dsim /path/to/dsim."
        )
    return resolved


def build_command(dsim_executable: str, waves_enabled: bool) -> list[str]:
    """Build the single-invocation DSim command."""

    command = [
        dsim_executable,
        "-F",
        str(FILELIST_PATH.relative_to(PROJECT_ROOT)),
        "-top",
        "work.smoke_tb",
        "-timescale",
        "1ns/1ps",
        "+acc",
    ]

    if waves_enabled:
        command.extend(
            [
                "-waves",
                str(WAVE_PATH.relative_to(PROJECT_ROOT)),
            ]
        )

    command.extend(
        [
            "-l",
            str(LOG_PATH.relative_to(PROJECT_ROOT)),
        ]
    )
    return command


def main() -> int:
    """Run DSim and validate the smoke-test pass marker."""

    arguments = parse_arguments()

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    WAVE_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        dsim_executable = resolve_executable(arguments.dsim)
    except FileNotFoundError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    command = build_command(dsim_executable, waves_enabled=not arguments.no_waves)

    print("Running DSim smoke test:")
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

    combined_output = completed.stdout + "\n" + log_text

    if completed.returncode != 0:
        print(
            f"ERROR: DSim returned nonzero exit status {completed.returncode}.",
            file=sys.stderr,
        )
        return completed.returncode

    if PASS_MARKER not in combined_output:
        print(
            f"ERROR: Simulation exited without the required marker {PASS_MARKER!r}.",
            file=sys.stderr,
        )
        return 3

    if not arguments.no_waves and not WAVE_PATH.exists():
        print(
            f"ERROR: DSim passed, but the waveform was not created: {WAVE_PATH}",
            file=sys.stderr,
        )
        return 4

    print(f"DSim log: {LOG_PATH}")
    if not arguments.no_waves:
        print(f"DSim waveform: {WAVE_PATH}")
    print("MILESTONE_0_DSIM_CHECK_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
