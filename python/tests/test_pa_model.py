"""Tests for PA memory, AM/AM, AM/PM, and complete evaluation."""

from __future__ import annotations

import numpy as np
import pytest

from dpd.pa_config import load_pa_config
from dpd.pa_model import apply_causal_fir, apply_pa, rapp_ampm_characteristic
from dpd.waveform import complex_impulse, complex_tone


def test_causal_fir_impulse_response_matches_taps() -> None:
    taps = (1.0 + 0.0j, 0.2 - 0.1j, -0.05 + 0.02j)
    impulse = complex_impulse(8)
    output = apply_causal_fir(impulse, taps)
    np.testing.assert_allclose(output[:3], np.asarray(taps))
    np.testing.assert_allclose(output[3:], 0.0)


def test_small_signal_gain_is_approximately_linear() -> None:
    config = load_pa_config().nonlinearity
    input_magnitude = np.array([1e-6, 1e-4, 1e-3])
    output_magnitude, _ = rapp_ampm_characteristic(input_magnitude, config)
    np.testing.assert_allclose(
        output_magnitude / input_magnitude,
        config.small_signal_gain,
        rtol=1e-8,
    )


def test_high_amplitude_compresses_below_linear_response() -> None:
    config = load_pa_config().nonlinearity
    input_magnitude = np.array([0.1, 0.5, 1.0])
    output_magnitude, _ = rapp_ampm_characteristic(input_magnitude, config)
    linear = config.small_signal_gain * input_magnitude
    assert output_magnitude[-1] < linear[-1]
    assert output_magnitude[-1] < config.saturation_amplitude * 1.01


def test_ampm_is_monotonic_and_bounded() -> None:
    config = load_pa_config().nonlinearity
    magnitude = np.linspace(0.0, 3.0, 1000)
    _, phase = rapp_ampm_characteristic(magnitude, config)
    assert np.all(np.diff(phase) >= 0.0)
    assert np.rad2deg(phase[-1]) < config.ampm_max_degrees
    assert np.rad2deg(phase[-1]) > 0.95 * config.ampm_max_degrees


def test_zero_input_produces_exact_zero_output() -> None:
    config = load_pa_config()
    result = apply_pa(np.zeros(32, dtype=np.complex128), config)
    np.testing.assert_array_equal(result.output_samples, 0.0 + 0.0j)


def test_complete_pa_is_deterministic_and_finite() -> None:
    config = load_pa_config()
    samples = complex_tone(1024, normalized_frequency=0.03, amplitude=0.45 + 0.0j)
    first = apply_pa(samples, config)
    second = apply_pa(samples, config)
    np.testing.assert_array_equal(first.output_samples, second.output_samples)
    assert first.output_samples.shape == samples.shape
    assert np.all(np.isfinite(first.output_samples.real))
    assert np.all(np.isfinite(first.output_samples.imag))
