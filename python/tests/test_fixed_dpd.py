"""Tests for the bit-accurate integer DPD model."""

from __future__ import annotations

import numpy as np
import pytest

from dpd.fixed_dpd import apply_fixed_dpd, round_shift_right
from dpd.fixed_point_config import load_fixed_point_config


@pytest.mark.parametrize(
    ("value", "shift", "expected"),
    [
        (0, 3, 0),
        (3, 1, 2),
        (1, 1, 1),
        (-1, 1, -1),
        (-3, 1, -2),
        (7, 2, 2),
        (-7, 2, -2),
        (16, 0, 16),
    ],
)
def test_round_shift_right(value: int, shift: int, expected: int) -> None:
    assert round_shift_right(value, shift) == expected


def _identity_coefficients() -> tuple[np.ndarray, np.ndarray]:
    coefficient_i = np.zeros(9, dtype=np.int64)
    coefficient_q = np.zeros(9, dtype=np.int64)
    coefficient_i[0] = 1 << 16
    return coefficient_i, coefficient_q


def test_identity_coefficient_is_bit_exact() -> None:
    input_i = np.array([0, 1, -1, 1234, -2345, 32767, -32768], dtype=np.int64)
    input_q = np.array([0, -2, 2, -456, 789, -32768, 32767], dtype=np.int64)
    coefficient_i, coefficient_q = _identity_coefficients()

    result = apply_fixed_dpd(input_i, input_q, coefficient_i, coefficient_q)

    np.testing.assert_array_equal(result.output_i, input_i)
    np.testing.assert_array_equal(result.output_q, input_q)
    assert result.statistics.output_saturation_count == 0


def test_memory_one_identity_coefficient_creates_one_sample_delay() -> None:
    input_i = np.array([100, 200, -300, 400], dtype=np.int64)
    input_q = np.array([-50, 60, 70, -80], dtype=np.int64)
    coefficient_i = np.zeros(9, dtype=np.int64)
    coefficient_q = np.zeros(9, dtype=np.int64)
    coefficient_i[3] = 1 << 16

    result = apply_fixed_dpd(input_i, input_q, coefficient_i, coefficient_q)

    np.testing.assert_array_equal(result.output_i, np.array([0, 100, 200, -300]))
    np.testing.assert_array_equal(result.output_q, np.array([0, -50, 60, 70]))


def test_zero_input_produces_exact_zero() -> None:
    coefficient_i = np.arange(9, dtype=np.int64) * 1000
    coefficient_q = -coefficient_i

    result = apply_fixed_dpd(
        np.zeros(16, dtype=np.int64),
        np.zeros(16, dtype=np.int64),
        coefficient_i,
        coefficient_q,
    )

    assert np.count_nonzero(result.output_i) == 0
    assert np.count_nonzero(result.output_q) == 0


def test_positive_and_negative_output_saturation() -> None:
    coefficient_i = np.zeros(9, dtype=np.int64)
    coefficient_q = np.zeros(9, dtype=np.int64)
    coefficient_i[0] = 4 << 16

    result = apply_fixed_dpd(
        np.array([20000, -20000], dtype=np.int64),
        np.zeros(2, dtype=np.int64),
        coefficient_i,
        coefficient_q,
    )

    np.testing.assert_array_equal(result.output_i, np.array([32767, -32768]))
    assert result.statistics.output_saturation_count == 2


def test_trace_contains_canonical_nine_terms() -> None:
    coefficient_i, coefficient_q = _identity_coefficients()
    result = apply_fixed_dpd(
        np.array([1024, 2048], dtype=np.int64),
        np.array([512, -256], dtype=np.int64),
        coefficient_i,
        coefficient_q,
        trace_length=2,
    )

    assert result.trace is not None
    assert result.trace.basis_i.shape == (2, 9)
    assert result.trace.term_i.shape == (2, 9)
    assert result.trace.magnitude_squared.shape == (2, 3)
    assert result.trace.accumulator_i.shape == (2,)


def test_model_is_deterministic() -> None:
    rng = np.random.default_rng(123)
    input_i = rng.integers(-12000, 12000, size=128, dtype=np.int64)
    input_q = rng.integers(-12000, 12000, size=128, dtype=np.int64)
    coefficient_i = rng.integers(-100000, 100000, size=9, dtype=np.int64)
    coefficient_q = rng.integers(-100000, 100000, size=9, dtype=np.int64)

    first = apply_fixed_dpd(input_i, input_q, coefficient_i, coefficient_q)
    second = apply_fixed_dpd(input_i, input_q, coefficient_i, coefficient_q)

    np.testing.assert_array_equal(first.output_i, second.output_i)
    np.testing.assert_array_equal(first.output_q, second.output_q)
    assert first.statistics == second.statistics


def test_coefficient_count_must_be_nine() -> None:
    with pytest.raises(ValueError, match="Expected 9 coefficients"):
        apply_fixed_dpd(
            np.zeros(1, dtype=np.int64),
            np.zeros(1, dtype=np.int64),
            np.zeros(8, dtype=np.int64),
            np.zeros(8, dtype=np.int64),
        )


def test_input_range_is_checked() -> None:
    coefficient_i, coefficient_q = _identity_coefficients()
    with pytest.raises(ValueError, match="input_i values"):
        apply_fixed_dpd(
            np.array([32768], dtype=np.int64),
            np.array([0], dtype=np.int64),
            coefficient_i,
            coefficient_q,
        )


def test_full_scale_input_does_not_overflow_internal_formats() -> None:
    config = load_fixed_point_config()
    coefficient_i, coefficient_q = _identity_coefficients()
    result = apply_fixed_dpd(
        np.array([config.formats.sample.minimum_integer, config.formats.sample.maximum_integer]),
        np.array([config.formats.sample.maximum_integer, config.formats.sample.minimum_integer]),
        coefficient_i,
        coefficient_q,
    )

    assert result.statistics.basis_saturation_count == 0
    assert result.statistics.maximum_absolute_accumulator_i > 0
