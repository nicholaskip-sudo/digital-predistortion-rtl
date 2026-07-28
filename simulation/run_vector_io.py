"""Verify DSim $readmemh compatibility with exported signed vectors."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILELIST_PATH = PROJECT_ROOT / "simulation" / "filelist_vector_io.f"
LOG_PATH = PROJECT_ROOT / "reports" / "logs" / "vector_io_smoke.log"
VECTOR_PATH = (
    PROJECT_ROOT / "vectors" / "rtl" / "vector_io_smoke" / "signed16.hex"
)
PASS_MARKER = "VECTOR_IO_SMOKE_PASS"


def main() -> int:
    if not VECTOR_PATH.exists():
        print(
            "ERROR: Vector files are missing. Run "
            "python python/scripts/generate_golden_vectors.py first.",
            file=sys.stderr,
        )
        return 2

    dsim = shutil.which(os.environ.get("DSIM_BIN", "dsim"))
    if dsim is None:
        print("ERROR: DSim is not active in this terminal.", file=sys.stderr)
        return 3

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    command = [
        dsim,
        "-F",
        str(FILELIST_PATH.relative_to(PROJECT_ROOT)),
        "-top",
        "work.vector_io_smoke_tb",
        "-timescale",
        "1ns/1ps",
        "-l",
        str(LOG_PATH.relative_to(PROJECT_ROOT)),
    ]

    print("Running vector I/O smoke test:")
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
        print(
            f"ERROR: DSim returned {completed.returncode}.",
            file=sys.stderr,
        )
        return completed.returncode

    if PASS_MARKER not in combined:
        print(
            f"ERROR: Missing pass marker {PASS_MARKER}.",
            file=sys.stderr,
        )
        return 4

    print(f"DSim log: {LOG_PATH}")
    print("MILESTONE_7_VECTOR_IO_CHECK_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
