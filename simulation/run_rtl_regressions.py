"""Run the complete pre-UVM RTL regression sequence."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMMANDS = (
    ("DPD specification", "simulation/run_spec.py"),
    ("Fixed-point specification", "simulation/run_fixed_spec.py"),
    ("Vector I/O compatibility", "simulation/run_vector_io.py"),
    ("Short DPD core regression", "simulation/run_dpd_core.py"),
    ("Full DPD core regression", "simulation/run_dpd_core_full.py"),
)


def main() -> int:
    for name, relative_script in COMMANDS:
        print()
        print("=" * 78)
        print(name)
        print("=" * 78)

        completed = subprocess.run(
            [sys.executable, relative_script],
            cwd=PROJECT_ROOT,
            check=False,
        )

        if completed.returncode != 0:
            print(
                f"ERROR: {name} failed with status "
                f"{completed.returncode}.",
                file=sys.stderr,
            )
            return completed.returncode

    print()
    print("PRE_UVM_RTL_REGRESSION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
