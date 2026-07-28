"""Run the complete Milestone 13 verification sequence."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMMANDS = (
    ("Existing UVM short baseline", "simulation/run_uvm_short.py"),
    ("Randomized UVM stress matrix", "simulation/run_uvm_stress_matrix.py"),
    ("Expected-failure protocol tests", "simulation/run_protocol_negative.py"),
)


def main() -> int:
    for name, script in COMMANDS:
        print()
        print("=" * 78)
        print(name)
        print("=" * 78)

        completed = subprocess.run(
            [sys.executable, script],
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
    print("MILESTONE_13_STRESS_REGRESSION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
