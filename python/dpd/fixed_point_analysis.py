"""Range and quantization analysis for the fixed-point architecture."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from numpy.typing import NDArray

from dpd.fixed_point_config import NumericFormat


FloatArray = NDArray[np.float64]
ComplexArray = NDArray[np.complex128]
IntegerArray = NDArray[np.int64]


@dataclass(frozen=True)
class QuantizationSummary:
    count: int
    saturation_count: int
    maximum_absolute_error: float
    rms_error: float


def round_half_away_from_zero(values: FloatArray | float) -> NDArray[np.float64]:
    """Round real values to nearest integer, with exact ties away from zero."""

    array = np.asarray(values, dtype=np.float64)
    rounded = np.sign(array) * np.floor(np.abs(array) + 0.5)
    return np.asarray(rounded, dtype=np.float64)


def saturate_integer(
    values: NDArray[np.int64] | int,
    numeric_format: NumericFormat,
) -> IntegerArray:
    """Saturate stored integers to a format's legal range."""

    array = np.asarray(values, dtype=np.int64)
    clipped = np.clip(
        array,
        numeric_format.minimum_integer,
        numeric_format.maximum_integer,
    )
    return np.asarray(clipped, dtype=np.int64)


def quantize_real(
    values: FloatArray | float,
    numeric_format: NumericFormat,
) -> tuple[IntegerArray, QuantizationSummary]:
    """Quantize real values with symmetric round-to-nearest and saturation."""

    array = np.asarray(values, dtype=np.float64)
    scale = float(1 << numeric_format.fractional_bits)

    unbounded = round_half_away_from_zero(array * scale)
    saturated = np.clip(
        unbounded,
        numeric_format.minimum_integer,
        numeric_format.maximum_integer,
    )

    integer_values = np.asarray(saturated, dtype=np.int64)
    reconstructed = integer_values.astype(np.float64) / scale
    error = reconstructed - array

    summary = QuantizationSummary(
        count=int(array.size),
        saturation_count=int(np.count_nonzero(unbounded != saturated)),
        maximum_absolute_error=float(np.max(np.abs(error))) if array.size else 0.0,
        rms_error=(
            float(np.sqrt(np.mean(error**2)))
            if array.size
            else 0.0
        ),
    )
    return integer_values, summary


def dequantize_real(
    values: NDArray[np.int64] | int,
    numeric_format: NumericFormat,
) -> FloatArray:
    """Convert stored integers back to real values."""

    array = np.asarray(values, dtype=np.int64)
    scale = float(1 << numeric_format.fractional_bits)
    return np.asarray(array.astype(np.float64) / scale, dtype=np.float64)


def quantize_complex(
    values: ComplexArray,
    numeric_format: NumericFormat,
) -> tuple[IntegerArray, IntegerArray, QuantizationSummary]:
    """Quantize complex values component-by-component."""

    array = np.asarray(values, dtype=np.complex128)
    real_integer, real_summary = quantize_real(array.real, numeric_format)
    imag_integer, imag_summary = quantize_real(array.imag, numeric_format)

    combined_error = (
        dequantize_real(real_integer, numeric_format)
        + 1j * dequantize_real(imag_integer, numeric_format)
        - array
    )

    summary = QuantizationSummary(
        count=int(array.size * 2),
        saturation_count=(
            real_summary.saturation_count + imag_summary.saturation_count
        ),
        maximum_absolute_error=(
            float(np.max(np.abs(combined_error))) if array.size else 0.0
        ),
        rms_error=(
            float(np.sqrt(np.mean(np.abs(combined_error) ** 2)))
            if array.size
            else 0.0
        ),
    )
    return real_integer, imag_integer, summary


def empirical_basis_maxima(
    samples: ComplexArray,
    polynomial_orders: tuple[int, ...] = (1, 3, 5),
) -> dict[int, dict[str, float]]:
    """Return empirical complex and component maxima for each basis order."""

    samples = np.asarray(samples, dtype=np.complex128)
    if samples.ndim != 1 or samples.size == 0:
        raise ValueError("Samples must be a nonempty one-dimensional array.")

    result: dict[int, dict[str, float]] = {}
    magnitude = np.abs(samples)

    for order in polynomial_orders:
        if order <= 0 or order % 2 == 0:
            raise ValueError("Polynomial orders must be positive odd integers.")

        basis = samples * magnitude ** (order - 1)
        result[order] = {
            "maximum_complex_magnitude": float(np.max(np.abs(basis))),
            "maximum_absolute_real": float(np.max(np.abs(basis.real))),
            "maximum_absolute_imag": float(np.max(np.abs(basis.imag))),
        }

    return result


def theoretical_basis_component_bound(order: int) -> float:
    """Return a conservative bound for Q1.15 complex input components.

    Each component is bounded by one and |x|^2 is bounded by two.
    Therefore each real or imaginary basis component is bounded by
    2^((order-1)/2).
    """

    if order <= 0 or order % 2 == 0:
        raise ValueError("Polynomial order must be a positive odd integer.")

    return float(2 ** ((order - 1) // 2))


def required_signed_integer_bits(maximum_absolute_value: float) -> int:
    """Return signed integer bits, including sign, needed for a magnitude."""

    if maximum_absolute_value < 0.0:
        raise ValueError("Maximum absolute value cannot be negative.")
    if maximum_absolute_value == 0.0:
        return 1

    return int(math.ceil(math.log2(maximum_absolute_value))) + 1


def worst_case_accumulator_component_bound(
    coefficient_count: int,
    basis_component_bound: float,
    coefficient_component_bound: float,
) -> float:
    """Bound one accumulated complex output component.

    A complex real or imaginary term contains two real products. The
    coefficient_count terms are then accumulated.
    """

    if coefficient_count <= 0:
        raise ValueError("Coefficient count must be positive.")
    if basis_component_bound < 0.0:
        raise ValueError("Basis bound cannot be negative.")
    if coefficient_component_bound < 0.0:
        raise ValueError("Coefficient bound cannot be negative.")

    return (
        coefficient_count
        * 2.0
        * basis_component_bound
        * coefficient_component_bound
    )
