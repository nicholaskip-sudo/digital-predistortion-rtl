"""Smoke tests for the initial Python environment."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from dpd import __version__
from dpd.project_paths import create_output_directories


def test_package_version() -> None:
    """The local DPD package must be importable."""

    assert __version__ == "0.1.0"


def test_complex_numpy_arithmetic() -> None:
    """NumPy must perform the complex arithmetic needed by DPD modelling."""

    samples = np.array([1.0 + 1.0j, -0.5 + 0.25j], dtype=np.complex128)
    magnitude_squared = samples.real**2 + samples.imag**2

    np.testing.assert_allclose(magnitude_squared, np.array([2.0, 0.3125]))


def test_matplotlib_can_write_png(tmp_path) -> None:
    """Matplotlib must work without requiring a graphical display."""

    figure, axis = plt.subplots()
    axis.plot([0, 1, 2], [0, 1, 0])

    output_path = tmp_path / "smoke.png"
    figure.savefig(output_path)
    plt.close(figure)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_project_output_directories_can_be_created() -> None:
    """The common output-directory helper must complete without an error."""

    create_output_directories()
