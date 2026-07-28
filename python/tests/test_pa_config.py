"""Tests for the behavioral PA configuration."""

from dpd.pa_config import load_pa_config


def test_default_pa_configuration() -> None:
    config = load_pa_config()
    assert config.model == "wiener_rapp_ampm"
    assert len(config.memory.input_taps) == 3
    assert config.memory.input_taps[0] == 1.0 + 0.0j
    assert config.nonlinearity.small_signal_gain == 2.0
    assert config.nonlinearity.saturation_amplitude == 0.60
    assert config.nonlinearity.rapp_smoothness == 2.5
    assert config.nonlinearity.ampm_max_degrees == 18.0
