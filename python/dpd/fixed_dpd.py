"""Bit-accurate integer Memory Polynomial DPD reference model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from dpd.config import load_project_config
from dpd.fixed_point_analysis import dequantize_real, quantize_complex
from dpd.fixed_point_config import FixedPointConfig, NumericFormat, load_fixed_point_config


IntegerArray = NDArray[np.int64]
ComplexArray = NDArray[np.complex128]


@dataclass(frozen=True)
class FixedDpdStatistics:
    """Run-time numerical statistics from one fixed-point evaluation."""

    sample_count: int
    basis_saturation_count: int
    output_saturation_count: int
    maximum_absolute_accumulator_i: int
    maximum_absolute_accumulator_q: int


@dataclass(frozen=True)
class FixedDpdTrace:
    """Optional internal trace for the first selected samples."""

    magnitude_squared: NDArray[np.uint64]
    magnitude_fourth: NDArray[np.uint64]
    basis_i: IntegerArray
    basis_q: IntegerArray
    term_i: IntegerArray
    term_q: IntegerArray
    accumulator_i: IntegerArray
    accumulator_q: IntegerArray


@dataclass(frozen=True)
class FixedDpdResult:
    """Integer output, statistics, and optional internal trace."""

    input_i: IntegerArray
    input_q: IntegerArray
    output_i: IntegerArray
    output_q: IntegerArray
    statistics: FixedDpdStatistics
    trace: FixedDpdTrace | None

    def output_complex(self, config: FixedPointConfig | None = None) -> ComplexArray:
        """Return the fixed output reconstructed as complex floating point."""

        selected = load_fixed_point_config() if config is None else config
        real = dequantize_real(self.output_i, selected.formats.output)
        imag = dequantize_real(self.output_q, selected.formats.output)
        return np.asarray(real + 1j * imag, dtype=np.complex128)


def round_shift_right(value: int, shift: int) -> int:
    """Arithmetic right shift with nearest, ties away from zero."""

    if shift < 0:
        raise ValueError("Right-shift count cannot be negative.")
    if shift == 0:
        return int(value)

    half = 1 << (shift - 1)
    if value >= 0:
        return int((value + half) >> shift)
    return int(-(((-value) + half) >> shift))


def _saturate_scalar(value: int, numeric_format: NumericFormat) -> tuple[int, bool]:
    if value < numeric_format.minimum_integer:
        return numeric_format.minimum_integer, True
    if value > numeric_format.maximum_integer:
        return numeric_format.maximum_integer, True
    return int(value), False


def _require_scalar_range(value: int, numeric_format: NumericFormat, name: str) -> int:
    if value < numeric_format.minimum_integer or value > numeric_format.maximum_integer:
        raise OverflowError(
            f"{name} value {value} exceeds {numeric_format.width}-bit range "
            f"[{numeric_format.minimum_integer}, {numeric_format.maximum_integer}]."
        )
    return int(value)


def _integer_vector(values: NDArray[np.integer] | list[int], name: str) -> IntegerArray:
    array = np.asarray(values)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional.")
    if not np.issubdtype(array.dtype, np.integer):
        raise TypeError(f"{name} must contain integers.")
    return np.asarray(array, dtype=np.int64)


def _validate_vector_range(
    values: IntegerArray,
    numeric_format: NumericFormat,
    name: str,
) -> None:
    if values.size == 0:
        return
    minimum = int(np.min(values))
    maximum = int(np.max(values))
    if minimum < numeric_format.minimum_integer or maximum > numeric_format.maximum_integer:
        raise ValueError(
            f"{name} values [{minimum}, {maximum}] exceed the configured range."
        )


def quantize_input_samples(
    samples: ComplexArray,
    config: FixedPointConfig | None = None,
) -> tuple[IntegerArray, IntegerArray, int]:
    """Quantize complex floating-point input samples to the external Q format."""

    selected = load_fixed_point_config() if config is None else config
    input_i, input_q, summary = quantize_complex(samples, selected.formats.sample)
    return input_i, input_q, summary.saturation_count


def _basis_components(
    sample_i: int,
    sample_q: int,
    polynomial_order: int,
    config: FixedPointConfig,
) -> tuple[int, int, int, int, int]:
    """Return basis I/Q, mag-squared, mag-fourth, and saturation count."""

    mag_sq = sample_i * sample_i + sample_q * sample_q
    _require_scalar_range(mag_sq, config.formats.magnitude_squared, "magnitude squared")

    mag_fourth = mag_sq * mag_sq
    _require_scalar_range(
        mag_fourth,
        config.formats.magnitude_fourth,
        "magnitude fourth",
    )

    if polynomial_order == 1:
        raw_i = sample_i << config.order1_basis_shift
        raw_q = sample_q << config.order1_basis_shift
    elif polynomial_order == 3:
        raw_i = round_shift_right(
            sample_i * mag_sq,
            config.order3_basis_right_shift,
        )
        raw_q = round_shift_right(
            sample_q * mag_sq,
            config.order3_basis_right_shift,
        )
    elif polynomial_order == 5:
        raw_i = round_shift_right(
            sample_i * mag_fourth,
            config.order5_basis_right_shift,
        )
        raw_q = round_shift_right(
            sample_q * mag_fourth,
            config.order5_basis_right_shift,
        )
    else:
        raise ValueError(f"Unsupported polynomial order: {polynomial_order}")

    basis_i, saturated_i = _saturate_scalar(raw_i, config.formats.basis)
    basis_q, saturated_q = _saturate_scalar(raw_q, config.formats.basis)
    saturation_count = int(saturated_i) + int(saturated_q)
    return basis_i, basis_q, mag_sq, mag_fourth, saturation_count


def _complex_multiply(
    basis_i: int,
    basis_q: int,
    coefficient_i: int,
    coefficient_q: int,
    config: FixedPointConfig,
) -> tuple[int, int]:
    """Perform one exact complex basis-by-coefficient multiplication."""

    product_ii = _require_scalar_range(
        basis_i * coefficient_i,
        config.formats.real_product,
        "basis_i*coefficient_i",
    )
    product_qq = _require_scalar_range(
        basis_q * coefficient_q,
        config.formats.real_product,
        "basis_q*coefficient_q",
    )
    product_iq = _require_scalar_range(
        basis_i * coefficient_q,
        config.formats.real_product,
        "basis_i*coefficient_q",
    )
    product_qi = _require_scalar_range(
        basis_q * coefficient_i,
        config.formats.real_product,
        "basis_q*coefficient_i",
    )

    term_i = _require_scalar_range(
        product_ii - product_qq,
        config.formats.complex_term,
        "complex term I",
    )
    term_q = _require_scalar_range(
        product_iq + product_qi,
        config.formats.complex_term,
        "complex term Q",
    )
    return term_i, term_q


def apply_fixed_dpd(
    input_i: NDArray[np.integer] | list[int],
    input_q: NDArray[np.integer] | list[int],
    coefficient_i: NDArray[np.integer] | list[int],
    coefficient_q: NDArray[np.integer] | list[int],
    *,
    config: FixedPointConfig | None = None,
    trace_length: int = 0,
) -> FixedDpdResult:
    """Evaluate the complete DPD using integer operations only.

    Delay-line state is initialized to complex zero. Coefficients use the
    canonical memory-major, order-minor mapping established in Milestone 1.
    """

    selected = load_fixed_point_config() if config is None else config
    project = load_project_config()

    input_i_array = _integer_vector(input_i, "input_i")
    input_q_array = _integer_vector(input_q, "input_q")
    coefficient_i_array = _integer_vector(coefficient_i, "coefficient_i")
    coefficient_q_array = _integer_vector(coefficient_q, "coefficient_q")

    if input_i_array.shape != input_q_array.shape:
        raise ValueError("Input I and Q arrays must have matching shapes.")
    if coefficient_i_array.shape != coefficient_q_array.shape:
        raise ValueError("Coefficient I and Q arrays must have matching shapes.")
    if coefficient_i_array.size != project.algorithm.coefficient_count:
        raise ValueError(
            f"Expected {project.algorithm.coefficient_count} coefficients, "
            f"received {coefficient_i_array.size}."
        )
    if trace_length < 0:
        raise ValueError("Trace length cannot be negative.")

    _validate_vector_range(input_i_array, selected.formats.sample, "input_i")
    _validate_vector_range(input_q_array, selected.formats.sample, "input_q")
    _validate_vector_range(
        coefficient_i_array,
        selected.formats.coefficient,
        "coefficient_i",
    )
    _validate_vector_range(
        coefficient_q_array,
        selected.formats.coefficient,
        "coefficient_q",
    )

    sample_count = input_i_array.size
    output_i = np.zeros(sample_count, dtype=np.int64)
    output_q = np.zeros(sample_count, dtype=np.int64)

    selected_trace_length = min(trace_length, sample_count)
    trace_mag_sq = np.zeros(
        (selected_trace_length, project.algorithm.memory_depth),
        dtype=np.uint64,
    )
    trace_mag_fourth = np.zeros_like(trace_mag_sq)
    trace_basis_i = np.zeros(
        (selected_trace_length, project.algorithm.coefficient_count),
        dtype=np.int64,
    )
    trace_basis_q = np.zeros_like(trace_basis_i)
    trace_term_i = np.zeros_like(trace_basis_i)
    trace_term_q = np.zeros_like(trace_basis_i)
    trace_acc_i = np.zeros(selected_trace_length, dtype=np.int64)
    trace_acc_q = np.zeros(selected_trace_length, dtype=np.int64)

    basis_saturation_count = 0
    output_saturation_count = 0
    maximum_absolute_accumulator_i = 0
    maximum_absolute_accumulator_q = 0

    orders = project.algorithm.polynomial_orders
    order_count = len(orders)

    for sample_index in range(sample_count):
        accumulator_i = 0
        accumulator_q = 0

        for memory_index in range(project.algorithm.memory_depth):
            delayed_index = sample_index - memory_index
            if delayed_index >= 0:
                delayed_i = int(input_i_array[delayed_index])
                delayed_q = int(input_q_array[delayed_index])
            else:
                delayed_i = 0
                delayed_q = 0

            cached_mag_sq = 0
            cached_mag_fourth = 0

            for order_slot, polynomial_order in enumerate(orders):
                coefficient_index = memory_index * order_count + order_slot
                (
                    basis_i,
                    basis_q,
                    mag_sq,
                    mag_fourth,
                    basis_saturations,
                ) = _basis_components(
                    delayed_i,
                    delayed_q,
                    polynomial_order,
                    selected,
                )
                cached_mag_sq = mag_sq
                cached_mag_fourth = mag_fourth
                basis_saturation_count += basis_saturations

                term_i, term_q = _complex_multiply(
                    basis_i,
                    basis_q,
                    int(coefficient_i_array[coefficient_index]),
                    int(coefficient_q_array[coefficient_index]),
                    selected,
                )

                accumulator_i = _require_scalar_range(
                    accumulator_i + term_i,
                    selected.formats.accumulator,
                    "accumulator I",
                )
                accumulator_q = _require_scalar_range(
                    accumulator_q + term_q,
                    selected.formats.accumulator,
                    "accumulator Q",
                )

                if sample_index < selected_trace_length:
                    trace_basis_i[sample_index, coefficient_index] = basis_i
                    trace_basis_q[sample_index, coefficient_index] = basis_q
                    trace_term_i[sample_index, coefficient_index] = term_i
                    trace_term_q[sample_index, coefficient_index] = term_q

            if sample_index < selected_trace_length:
                trace_mag_sq[sample_index, memory_index] = cached_mag_sq
                trace_mag_fourth[sample_index, memory_index] = cached_mag_fourth

        maximum_absolute_accumulator_i = max(
            maximum_absolute_accumulator_i,
            abs(accumulator_i),
        )
        maximum_absolute_accumulator_q = max(
            maximum_absolute_accumulator_q,
            abs(accumulator_q),
        )

        rounded_i = round_shift_right(
            accumulator_i,
            selected.output_right_shift,
        )
        rounded_q = round_shift_right(
            accumulator_q,
            selected.output_right_shift,
        )

        output_i_value, saturated_i = _saturate_scalar(
            rounded_i,
            selected.formats.output,
        )
        output_q_value, saturated_q = _saturate_scalar(
            rounded_q,
            selected.formats.output,
        )
        output_saturation_count += int(saturated_i) + int(saturated_q)
        output_i[sample_index] = output_i_value
        output_q[sample_index] = output_q_value

        if sample_index < selected_trace_length:
            trace_acc_i[sample_index] = accumulator_i
            trace_acc_q[sample_index] = accumulator_q

    trace = None
    if selected_trace_length:
        trace = FixedDpdTrace(
            magnitude_squared=trace_mag_sq,
            magnitude_fourth=trace_mag_fourth,
            basis_i=trace_basis_i,
            basis_q=trace_basis_q,
            term_i=trace_term_i,
            term_q=trace_term_q,
            accumulator_i=trace_acc_i,
            accumulator_q=trace_acc_q,
        )

    statistics = FixedDpdStatistics(
        sample_count=sample_count,
        basis_saturation_count=basis_saturation_count,
        output_saturation_count=output_saturation_count,
        maximum_absolute_accumulator_i=maximum_absolute_accumulator_i,
        maximum_absolute_accumulator_q=maximum_absolute_accumulator_q,
    )

    return FixedDpdResult(
        input_i=input_i_array.copy(),
        input_q=input_q_array.copy(),
        output_i=output_i,
        output_q=output_q,
        statistics=statistics,
        trace=trace,
    )
