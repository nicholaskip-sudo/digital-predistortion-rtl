"""Generate fixed-point range analysis, coefficient data, and plots."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from dpd.config import load_project_config
from dpd.fixed_point_analysis import (
    dequantize_real,
    empirical_basis_maxima,
    quantize_complex,
    required_signed_integer_bits,
    theoretical_basis_component_bound,
    worst_case_accumulator_component_bound,
)
from dpd.fixed_point_config import load_fixed_point_config
from dpd.project_paths import PLOTS_DIR, RESULTS_DIR, VECTORS_DIR, create_output_directories


def load_trained_coefficients(metrics_path: Path) -> np.ndarray:
    """Load complex floating-point coefficients from the DPD metrics JSON."""

    if not metrics_path.exists():
        raise FileNotFoundError(
            "DPD metrics are missing. Run generate_dpd_report.py first."
        )

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    coefficient_entries = metrics.get("coefficients")
    if not isinstance(coefficient_entries, list):
        raise ValueError("DPD metrics do not contain a coefficient list.")

    return np.asarray(
        [
            complex(float(entry["real"]), float(entry["imag"]))
            for entry in coefficient_entries
        ],
        dtype=np.complex128,
    )


def save_coefficient_plot(
    floating: np.ndarray,
    quantized: np.ndarray,
) -> None:
    indices = np.arange(floating.size)

    figure, axis = plt.subplots(figsize=(9.5, 4.8))
    axis.plot(indices, np.abs(floating), marker="o", label="Floating point")
    axis.plot(indices, np.abs(quantized), marker="x", label="Quantized")
    axis.set_title("DPD coefficient magnitude: floating vs Q8.16")
    axis.set_xlabel("Coefficient index")
    axis.set_ylabel("Magnitude")
    axis.set_xticks(indices)
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "fixed_point_coefficient_quantization.png", dpi=160)
    plt.close(figure)


def save_basis_range_plot(
    empirical: dict[int, dict[str, float]],
    theoretical: dict[int, float],
) -> None:
    orders = sorted(empirical)
    empirical_values = [
        max(
            empirical[order]["maximum_absolute_real"],
            empirical[order]["maximum_absolute_imag"],
        )
        for order in orders
    ]
    theoretical_values = [theoretical[order] for order in orders]

    x = np.arange(len(orders))
    width = 0.36

    figure, axis = plt.subplots(figsize=(8.6, 4.8))
    axis.bar(x - width / 2, empirical_values, width, label="Observed component")
    axis.bar(x + width / 2, theoretical_values, width, label="Q1.15 bound")
    axis.set_title("Memory Polynomial basis component ranges")
    axis.set_xlabel("Polynomial order")
    axis.set_ylabel("Maximum absolute component")
    axis.set_xticks(x, [str(order) for order in orders])
    axis.grid(True, axis="y")
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "fixed_point_basis_ranges.png", dpi=160)
    plt.close(figure)


def main() -> int:
    create_output_directories()

    project = load_project_config()
    fixed = load_fixed_point_config()

    waveform_path = VECTORS_DIR / "ofdm_float_reference.npz"
    if not waveform_path.exists():
        raise FileNotFoundError(
            "OFDM reference is missing. Run generate_waveform_report.py first."
        )

    with np.load(waveform_path) as waveform_data:
        samples = np.asarray(waveform_data["samples"], dtype=np.complex128)

    coefficients = load_trained_coefficients(
        RESULTS_DIR / "dpd_metrics.json"
    )

    if coefficients.size != project.algorithm.coefficient_count:
        raise ValueError(
            "Trained coefficient count does not match the algorithm specification."
        )

    coefficient_i, coefficient_q, coefficient_summary = quantize_complex(
        coefficients,
        fixed.formats.coefficient,
    )
    reconstructed_coefficients = (
        dequantize_real(coefficient_i, fixed.formats.coefficient)
        + 1j * dequantize_real(coefficient_q, fixed.formats.coefficient)
    )

    empirical = empirical_basis_maxima(
        samples,
        project.algorithm.polynomial_orders,
    )
    theoretical = {
        order: theoretical_basis_component_bound(order)
        for order in project.algorithm.polynomial_orders
    }

    largest_basis_bound = max(theoretical.values())
    coefficient_component_bound = max(
        abs(fixed.formats.coefficient.minimum_real),
        abs(fixed.formats.coefficient.maximum_real),
    )
    accumulator_bound = worst_case_accumulator_component_bound(
        project.algorithm.coefficient_count,
        largest_basis_bound,
        coefficient_component_bound,
    )
    required_accumulator_integer_bits = required_signed_integer_bits(
        accumulator_bound
    )

    np.savez_compressed(
        VECTORS_DIR / "dpd_quantized_coefficients.npz",
        coefficient_i=coefficient_i,
        coefficient_q=coefficient_q,
        coefficient_float=coefficients,
        coefficient_quantized=reconstructed_coefficients,
    )

    report = {
        "project_version": project.project_version,
        "rounding_mode": fixed.rounding.mode,
        "overflow_policy": {
            "basis": fixed.overflow.basis,
            "coefficient": fixed.overflow.coefficient,
            "accumulator": fixed.overflow.accumulator,
            "output": fixed.overflow.output,
        },
        "formats": {
            name: {
                "width": getattr(fixed.formats, name).width,
                "fractional_bits": getattr(fixed.formats, name).fractional_bits,
                "integer_bits": getattr(fixed.formats, name).integer_bits,
                "signed": getattr(fixed.formats, name).signed,
                "minimum_real": getattr(fixed.formats, name).minimum_real,
                "maximum_real": getattr(fixed.formats, name).maximum_real,
            }
            for name in (
                "sample",
                "magnitude_squared",
                "magnitude_fourth",
                "basis",
                "coefficient",
                "real_product",
                "complex_term",
                "accumulator",
                "output",
            )
        },
        "shifts": {
            "order1_basis_left_shift": fixed.order1_basis_shift,
            "order3_basis_right_shift": fixed.order3_basis_right_shift,
            "order5_basis_right_shift": fixed.order5_basis_right_shift,
            "output_right_shift": fixed.output_right_shift,
        },
        "coefficient_analysis": {
            "count": int(coefficients.size),
            "maximum_floating_component": float(
                max(np.max(np.abs(coefficients.real)), np.max(np.abs(coefficients.imag)))
            ),
            "maximum_floating_magnitude": float(np.max(np.abs(coefficients))),
            "saturation_count": coefficient_summary.saturation_count,
            "maximum_absolute_complex_error": coefficient_summary.maximum_absolute_error,
            "rms_complex_error": coefficient_summary.rms_error,
        },
        "basis_empirical_ranges": {
            str(order): values for order, values in empirical.items()
        },
        "basis_theoretical_component_bounds": {
            str(order): value for order, value in theoretical.items()
        },
        "accumulator_analysis": {
            "worst_case_component_bound": accumulator_bound,
            "required_signed_integer_bits_including_sign": (
                required_accumulator_integer_bits
            ),
            "selected_integer_bits_including_sign": (
                fixed.formats.accumulator.integer_bits
            ),
            "selected_width": fixed.formats.accumulator.width,
            "selected_fractional_bits": fixed.formats.accumulator.fractional_bits,
        },
    }

    report_path = RESULTS_DIR / "fixed_point_range_analysis.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    save_coefficient_plot(coefficients, reconstructed_coefficients)
    save_basis_range_plot(empirical, theoretical)

    print(json.dumps(report, indent=2))
    print(
        "Quantized coefficients: "
        f"{VECTORS_DIR / 'dpd_quantized_coefficients.npz'}"
    )
    print(f"Range analysis: {report_path}")
    print(f"Plots: {PLOTS_DIR}")
    print("FIXED_POINT_SPEC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
