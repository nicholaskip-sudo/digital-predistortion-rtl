"""Tests for the floating-point Memory Polynomial."""

from __future__ import annotations

import numpy as np
import pytest

from dpd.config import AlgorithmConfig, load_project_config
from dpd.memory_polynomial import (
    build_basis_matrix,
    evaluate_memory_polynomial,
    identity_coefficients,
)


def test_basis_matrix_shape_matches_configuration() -> None:
    config = load_project_config().algorithm
    samples = np.array([1 + 1j, 0.5 - 0.25j, -0.2 + 0.3j])

    basis = build_basis_matrix(samples, config)

    assert basis.shape == (samples.size, config.coefficient_count)


def test_basis_order_and_memory_are_exact() -> None:
    config = AlgorithmConfig(
        model="memory_polynomial",
        memory_depth=2,
        polynomial_orders=(1, 3),
    )
    samples = np.array([1 + 0j, 2 + 0j, 3 + 0j], dtype=np.complex128)

    basis = build_basis_matrix(samples, config)

    expected = np.array(
        [
            [1, 1, 0, 0],
            [2, 8, 1, 1],
            [3, 27, 2, 8],
        ],
        dtype=np.complex128,
    )
    np.testing.assert_allclose(basis, expected)


def test_identity_coefficients_reproduce_input() -> None:
    config = load_project_config().algorithm
    samples = np.array(
        [0.1 + 0.2j, -0.4 + 0.3j, 0.2 - 0.1j],
        dtype=np.complex128,
    )

    result = evaluate_memory_polynomial(
        samples,
        identity_coefficients(config),
        config,
    )

    np.testing.assert_array_equal(result.output_samples, samples)
    assert result.saturation_count == 0


def test_component_saturation_limits_i_and_q_separately() -> None:
    config = AlgorithmConfig(
        model="memory_polynomial",
        memory_depth=1,
        polynomial_orders=(1,),
    )
    samples = np.array([2 + 3j, -2 - 3j, 0.2 + 0.3j])

    result = evaluate_memory_polynomial(
        samples,
        np.array([1 + 0j]),
        config,
        component_minimum=-1.0,
        component_maximum=0.75,
    )

    expected = np.array([0.75 + 0.75j, -1 - 1j, 0.2 + 0.3j])
    np.testing.assert_allclose(result.output_samples, expected)
    assert result.saturation_count == 2
    assert result.saturation_fraction == pytest.approx(2 / 3)


def test_wrong_coefficient_count_is_rejected() -> None:
    config = load_project_config().algorithm

    with pytest.raises(ValueError, match="Expected 9"):
        evaluate_memory_polynomial(
            np.ones(8, dtype=np.complex128),
            np.ones(8, dtype=np.complex128),
            config,
        )
