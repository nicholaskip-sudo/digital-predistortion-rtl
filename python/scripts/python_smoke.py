"""Generate a deterministic plot to verify the Python modelling environment."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from dpd import __version__
from dpd.project_paths import PLOTS_DIR, create_output_directories


def main() -> int:
    """Generate a simple complex-envelope plot and report its location."""

    create_output_directories()

    sample_index = np.arange(128)
    complex_tone = 0.75 * np.exp(1j * 2.0 * np.pi * sample_index / 32.0)

    figure, axis = plt.subplots(figsize=(9, 4.5))
    axis.plot(sample_index, complex_tone.real, label="I")
    axis.plot(sample_index, complex_tone.imag, label="Q")
    axis.set_title("Python environment smoke test")
    axis.set_xlabel("Sample index")
    axis.set_ylabel("Normalized amplitude")
    axis.grid(True)
    axis.legend()
    figure.tight_layout()

    output_path = PLOTS_DIR / "python_smoke.png"
    figure.savefig(output_path, dpi=150)
    plt.close(figure)

    print(f"dpd package version: {__version__}")
    print(f"PYTHON_SMOKE_PASS: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
