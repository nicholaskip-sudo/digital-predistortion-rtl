"""Tests for the floating-point DPD training configuration."""

import pytest

from dpd.dpd_training_config import (
    OutputLimitConfig,
    load_dpd_training_config,
)


def test_default_dpd_training_configuration() -> None:
    config = load_dpd_training_config()

    assert config.method == "indirect_learning_architecture"
    assert config.target.linear_gain == 1.5
    assert config.least_squares.ridge_regularization == 0.0001
    assert config.least_squares.ignore_initial_samples == 8
    assert config.least_squares.training_fraction == 0.75
    assert config.iteration.maximum_iterations == 4
    assert config.iteration.minimum_validation_improvement_db == 0.05
    assert config.output_limit.minimum == -1.0
    assert config.output_limit.maximum == pytest.approx(32767 / 32768)


def test_invalid_output_limits_are_rejected() -> None:
    with pytest.raises(ValueError, match="smaller"):
        OutputLimitConfig(
            mode="component_saturation",
            minimum=1.0,
            maximum=-1.0,
        )
