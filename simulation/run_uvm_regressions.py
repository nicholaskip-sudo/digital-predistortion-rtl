"""Run the complete DPD UVM regression sequence."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMMANDS = (
    ("Short UVM regression", "simulation/run_uvm_short.py"),
    ("Full UVM and coverage regression", "simulation/run_uvm_full.py"),
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
    print("MILESTONE_12_UVM_REGRESSION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
