"""Tests for the project-wide DPD specification."""

from __future__ import annotations

import pytest

from dpd.config import AlgorithmConfig, load_project_config
from dpd.model_spec import build_coefficient_map, coefficient_index


def test_default_configuration() -> None:
    config = load_project_config()

    assert config.algorithm.model == "memory_polynomial"
    assert config.algorithm.memory_depth == 3
    assert config.algorithm.polynomial_orders == (1, 3, 5)
    assert config.algorithm.coefficient_count == 9

    assert config.sample_format.width == 16
    assert config.sample_format.fractional_bits == 15
    assert config.sample_format.signed

    assert config.coefficient_format.width == 24
    assert config.coefficient_format.fractional_bits == 16
    assert config.coefficient_format.signed


def test_coefficient_map_has_canonical_order() -> None:
    config = load_project_config()
    terms = build_coefficient_map(config.algorithm)

    actual = [
        (term.coefficient_index, term.memory_index, term.polynomial_order)
        for term in terms
    ]

    assert actual == [
        (0, 0, 1),
        (1, 0, 3),
        (2, 0, 5),
        (3, 1, 1),
        (4, 1, 3),
        (5, 1, 5),
        (6, 2, 1),
        (7, 2, 3),
        (8, 2, 5),
    ]


@pytest.mark.parametrize(
    ("memory_index", "polynomial_order", "expected_index"),
    [
        (0, 1, 0),
        (0, 3, 1),
        (0, 5, 2),
        (1, 1, 3),
        (1, 3, 4),
        (1, 5, 5),
        (2, 1, 6),
        (2, 3, 7),
        (2, 5, 8),
    ],
)
def test_coefficient_index(
    memory_index: int,
    polynomial_order: int,
    expected_index: int,
) -> None:
    config = load_project_config()
    assert (
        coefficient_index(
            config.algorithm,
            memory_index,
            polynomial_order,
        )
        == expected_index
    )


def test_even_polynomial_order_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive odd"):
        AlgorithmConfig(
            model="memory_polynomial",
            memory_depth=3,
            polynomial_orders=(1, 2, 3),
        )


def test_duplicate_polynomial_order_is_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        AlgorithmConfig(
            model="memory_polynomial",
            memory_depth=3,
            polynomial_orders=(1, 3, 3),
        )
