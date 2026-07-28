"""Floating-point Memory Polynomial basis and evaluation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from dpd.config import AlgorithmConfig


ComplexArray = NDArray[np.complex128]


@dataclass(frozen=True)
class MemoryPolynomialResult:
    """Raw and component-limited output from a Memory Polynomial."""

    input_samples: ComplexArray
    raw_output_samples: ComplexArray
    output_samples: ComplexArray
    saturation_count: int

    @property
    def saturation_fraction(self) -> float:
        """Return the fraction of complex samples with either component limited."""

        if self.output_samples.size == 0:
            return 0.0
        return self.saturation_count / self.output_samples.size


def _complex_vector(samples: ComplexArray) -> ComplexArray:
    samples = np.asarray(samples, dtype=np.complex128)
    if samples.ndim != 1:
        raise ValueError("Memory Polynomial input must be one-dimensional.")
    if not np.all(np.isfinite(samples.real)):
        raise ValueError("Memory Polynomial input contains non-finite real values.")
    if not np.all(np.isfinite(samples.imag)):
        raise ValueError("Memory Polynomial input contains non-finite imaginary values.")
    return samples


def build_basis_matrix(
    samples: ComplexArray,
    config: AlgorithmConfig,
) -> ComplexArray:
    """Build a zero-padded, memory-major, order-minor basis matrix.

    Column ordering is identical to the canonical coefficient map:

    - memory index 0, orders 1/3/5
    - memory index 1, orders 1/3/5
    - memory index 2, orders 1/3/5
    """

    samples = _complex_vector(samples)
    sample_count = samples.size
    basis = np.zeros(
        (sample_count, config.coefficient_count),
        dtype=np.complex128,
    )

    column_index = 0
    for memory_index in range(config.memory_depth):
        delayed = np.zeros(sample_count, dtype=np.complex128)
        if memory_index == 0:
            delayed[:] = samples
        elif memory_index < sample_count:
            delayed[memory_index:] = samples[:-memory_index]

        magnitude_squared = np.abs(delayed) ** 2

        for polynomial_order in config.polynomial_orders:
            envelope_exponent = (polynomial_order - 1) // 2
            basis[:, column_index] = (
                delayed * np.power(magnitude_squared, envelope_exponent)
            )
            column_index += 1

    return basis


def identity_coefficients(config: AlgorithmConfig) -> ComplexArray:
    """Return coefficients that reproduce the input exactly."""

    coefficients = np.zeros(config.coefficient_count, dtype=np.complex128)
    coefficients[0] = 1.0 + 0.0j
    return coefficients


def evaluate_memory_polynomial(
    samples: ComplexArray,
    coefficients: ComplexArray,
    config: AlgorithmConfig,
    component_minimum: float | None = None,
    component_maximum: float | None = None,
) -> MemoryPolynomialResult:
    """Evaluate the Memory Polynomial and optionally saturate I and Q separately."""

    samples = _complex_vector(samples)
    coefficients = np.asarray(coefficients, dtype=np.complex128)

    if coefficients.shape != (config.coefficient_count,):
        raise ValueError(
            f"Expected {config.coefficient_count} coefficients, "
            f"received shape {coefficients.shape}."
        )
    if not np.all(np.isfinite(coefficients.real)):
        raise ValueError("Coefficient real components must be finite.")
    if not np.all(np.isfinite(coefficients.imag)):
        raise ValueError("Coefficient imaginary components must be finite.")

    raw_output = build_basis_matrix(samples, config) @ coefficients

    if component_minimum is None and component_maximum is None:
        output = raw_output.copy()
        saturation_count = 0
    else:
        if component_minimum is None or component_maximum is None:
            raise ValueError("Both component limits must be supplied together.")
        if component_minimum >= component_maximum:
            raise ValueError("Component minimum must be smaller than maximum.")

        saturation_mask = (
            (raw_output.real < component_minimum)
            | (raw_output.real > component_maximum)
            | (raw_output.imag < component_minimum)
            | (raw_output.imag > component_maximum)
        )
        output = (
            np.clip(raw_output.real, component_minimum, component_maximum)
            + 1j * np.clip(raw_output.imag, component_minimum, component_maximum)
        )
        saturation_count = int(np.count_nonzero(saturation_mask))

    return MemoryPolynomialResult(
        input_samples=samples.copy(),
        raw_output_samples=np.asarray(raw_output, dtype=np.complex128),
        output_samples=np.asarray(output, dtype=np.complex128),
        saturation_count=saturation_count,
    )
