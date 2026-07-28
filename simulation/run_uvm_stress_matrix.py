"""Run the Milestone 13 randomized UVM stress test across fixed seeds."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEEDS = (13, 13013, 12648430)
RESULT_PATH = (
    PROJECT_ROOT
    / "reports"
    / "results"
    / "uvm_stress_matrix.json"
)
PASS_MARKER = "MILESTONE_13_UVM_STRESS_MATRIX_PASS"


def main() -> int:
    completed_seeds: list[int] = []

    for seed in SEEDS:
        print()
        print("=" * 78)
        print(f"Randomized UVM stress seed {seed}")
        print("=" * 78)

        completed = subprocess.run(
            [
                sys.executable,
                "simulation/run_uvm_stress.py",
                "--seed",
                str(seed),
                "--no-waves",
            ],
            cwd=PROJECT_ROOT,
            check=False,
        )

        if completed.returncode != 0:
            print(
                f"ERROR: Stress seed {seed} failed with status "
                f"{completed.returncode}.",
                file=sys.stderr,
            )
            return completed.returncode

        completed_seeds.append(seed)

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "seeds": completed_seeds,
                "seed_count": len(completed_seeds),
                "all_passed": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"Stress matrix metrics: {RESULT_PATH}")
    print(PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
