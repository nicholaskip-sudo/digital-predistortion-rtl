"""Tests for the fixed-point numerical specification."""

import pytest

from dpd.fixed_point_config import NumericFormat, load_fixed_point_config


def test_default_fixed_point_configuration() -> None:
    config = load_fixed_point_config()

    assert config.rounding.mode == "nearest_ties_away_from_zero"
    assert config.formats.sample == NumericFormat(16, 15, True)
    assert config.formats.basis == NumericFormat(24, 20, True)
    assert config.formats.coefficient == NumericFormat(24, 16, True)
    assert config.formats.accumulator == NumericFormat(54, 36, True)


def test_derived_binary_point_shifts() -> None:
    config = load_fixed_point_config()

    assert config.order1_basis_shift == 5
    assert config.order3_basis_right_shift == 25
    assert config.order5_basis_right_shift == 55
    assert config.output_right_shift == 21


def test_coefficient_format_has_required_range() -> None:
    coefficient = load_fixed_point_config().formats.coefficient

    assert coefficient.minimum_real == -128.0
    assert coefficient.maximum_real > 127.99
    assert coefficient.maximum_real > 32.7


def test_accumulator_has_guard_bits() -> None:
    accumulator = load_fixed_point_config().formats.accumulator

    assert accumulator.integer_bits == 18
    assert accumulator.maximum_real > 131071.0


def test_invalid_fractional_width_is_rejected() -> None:
    with pytest.raises(ValueError, match="smaller than width"):
        NumericFormat(width=16, fractional_bits=16, signed=True)
