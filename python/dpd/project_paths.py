"""Centralized repository paths used by project scripts."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = PROJECT_ROOT / "reports"
LOGS_DIR = REPORTS_DIR / "logs"
PLOTS_DIR = REPORTS_DIR / "plots"
RESULTS_DIR = REPORTS_DIR / "results"
WAVES_DIR = REPORTS_DIR / "waves"
VECTORS_DIR = PROJECT_ROOT / "vectors"


def create_output_directories() -> None:
    """Create every generated-output directory used by the project."""

    for directory in (LOGS_DIR, PLOTS_DIR, RESULTS_DIR, WAVES_DIR, VECTORS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
