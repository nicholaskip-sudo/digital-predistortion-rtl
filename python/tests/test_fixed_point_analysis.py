"""Tests for range-analysis and quantization helpers."""

from __future__ import annotations

import numpy as np
import pytest

from dpd.fixed_point_analysis import (
    dequantize_real,
    empirical_basis_maxima,
    quantize_real,
    required_signed_integer_bits,
    round_half_away_from_zero,
    saturate_integer,
    theoretical_basis_component_bound,
    worst_case_accumulator_component_bound,
)
from dpd.fixed_point_config import NumericFormat


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.49, 0.0),
        (0.50, 1.0),
        (1.50, 2.0),
        (-0.49, 0.0),
        (-0.50, -1.0),
        (-1.50, -2.0),
        (2.51, 3.0),
        (-2.51, -3.0),
    ],
)
def test_round_half_away_from_zero(value: float, expected: float) -> None:
    assert float(round_half_away_from_zero(value)) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-200, -128),
        (-128, -128),
        (0, 0),
        (127, 127),
        (200, 127),
    ],
)
def test_signed_saturation(value: int, expected: int) -> None:
    fmt = NumericFormat(width=8, fractional_bits=0, signed=True)
    result = saturate_integer(value, fmt)
    assert int(result) == expected


def test_real_quantization_and_reconstruction() -> None:
    fmt = NumericFormat(width=8, fractional_bits=4, signed=True)
    values = np.array([0.0, 0.5, -0.5, 7.9, -9.0])

    integer, summary = quantize_real(values, fmt)
    reconstructed = dequantize_real(integer, fmt)

    np.testing.assert_array_equal(integer, np.array([0, 8, -8, 126, -128]))
    assert reconstructed[-1] == -8.0
    assert summary.saturation_count == 1


def test_empirical_basis_ranges() -> None:
    samples = np.array([0.5 + 0.25j, -0.75 + 0.1j], dtype=np.complex128)
    ranges = empirical_basis_maxima(samples)

    assert set(ranges) == {1, 3, 5}
    assert ranges[3]["maximum_complex_magnitude"] > ranges[1]["maximum_complex_magnitude"] * 0.1
    assert all(value["maximum_absolute_real"] >= 0.0 for value in ranges.values())


def test_theoretical_basis_bounds() -> None:
    assert theoretical_basis_component_bound(1) == 1.0
    assert theoretical_basis_component_bound(3) == 2.0
    assert theoretical_basis_component_bound(5) == 4.0


def test_required_integer_bits() -> None:
    assert required_signed_integer_bits(0.0) == 1
    assert required_signed_integer_bits(1.0) == 1
    assert required_signed_integer_bits(4.0) == 3
    assert required_signed_integer_bits(18432.0) == 16


def test_worst_case_accumulator_bound() -> None:
    bound = worst_case_accumulator_component_bound(
        coefficient_count=9,
        basis_component_bound=4.0,
        coefficient_component_bound=128.0,
    )

    assert bound == 9216.0
