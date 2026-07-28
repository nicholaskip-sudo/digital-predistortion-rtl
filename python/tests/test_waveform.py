"""Tests for deterministic QAM, OFDM, and directed waveforms."""

from __future__ import annotations

import numpy as np
import pytest

from dpd.waveform import (
    active_subcarrier_indices,
    amplitude_ramp,
    complex_impulse,
    complex_tone,
    generate_ofdm,
    normalize_signal,
    papr_db,
    qam_symbols,
    rms_magnitude,
    two_tone,
)
from dpd.waveform_config import load_waveform_config


@pytest.mark.parametrize("order", [4, 16, 64])
def test_qam_generation_is_deterministic(order: int) -> None:
    first = qam_symbols(order, 4096, np.random.default_rng(7))
    second = qam_symbols(order, 4096, np.random.default_rng(7))

    np.testing.assert_array_equal(first, second)


@pytest.mark.parametrize("order", [4, 16, 64])
def test_complete_qam_constellation_has_unit_average_power(order: int) -> None:
    side = int(np.sqrt(order))
    levels = np.arange(-(side - 1), side, 2, dtype=np.float64)
    constellation = np.array(
        [i + 1j * q for i in levels for q in levels],
        dtype=np.complex128,
    )
    constellation /= np.sqrt((2.0 / 3.0) * (order - 1))

    assert np.mean(np.abs(constellation) ** 2) == pytest.approx(1.0)


def test_active_bins_are_unique_symmetric_and_exclude_dc() -> None:
    bins = active_subcarrier_indices(1024, 192)

    assert bins.size == 192
    assert np.unique(bins).size == 192
    assert 0 not in bins
    assert np.count_nonzero(bins < 512) == 96
    assert np.count_nonzero(bins >= 512) == 96


def test_ofdm_shape_and_reproducibility() -> None:
    config = load_waveform_config()

    first = generate_ofdm(
        config.ofdm,
        config.qam.order,
        np.random.default_rng(config.seed),
    )
    second = generate_ofdm(
        config.ofdm,
        config.qam.order,
        np.random.default_rng(config.seed),
    )

    assert first.samples.shape == (config.ofdm.total_samples,)
    assert first.frequency_symbols.shape == (
        config.ofdm.symbol_count,
        config.ofdm.active_subcarriers,
    )
    np.testing.assert_array_equal(first.samples, second.samples)
    np.testing.assert_array_equal(
        first.frequency_symbols,
        second.frequency_symbols,
    )


def test_rms_normalization() -> None:
    signal = np.array([1 + 1j, -2 + 0.5j, 0.2 - 0.4j], dtype=np.complex128)
    normalized = normalize_signal(signal, mode="rms", target=0.25)

    assert rms_magnitude(normalized) == pytest.approx(0.25)


def test_peak_normalization() -> None:
    signal = np.array([1 + 1j, -2 + 0.5j, 0.2 - 0.4j], dtype=np.complex128)
    normalized = normalize_signal(signal, mode="peak", target=0.80)

    assert np.max(np.abs(normalized)) == pytest.approx(0.80)


def test_ofdm_papr_is_finite_and_positive() -> None:
    config = load_waveform_config()
    generated = generate_ofdm(
        config.ofdm,
        config.qam.order,
        np.random.default_rng(config.seed),
    )

    value = papr_db(generated.samples)
    assert np.isfinite(value)
    assert value > 0.0


def test_complex_impulse() -> None:
    signal = complex_impulse(16, amplitude=0.5 - 0.25j, index=5)

    assert np.count_nonzero(signal) == 1
    assert signal[5] == 0.5 - 0.25j


def test_complex_tone_has_constant_magnitude() -> None:
    signal = complex_tone(
        128,
        normalized_frequency=1.0 / 32.0,
        amplitude=0.7 + 0.0j,
    )

    np.testing.assert_allclose(np.abs(signal), 0.7, atol=1e-12)


def test_amplitude_ramp_endpoints() -> None:
    signal = amplitude_ramp(
        32,
        start_amplitude=0.1,
        stop_amplitude=0.9,
        phase_rad=np.pi / 4.0,
    )

    assert abs(signal[0]) == pytest.approx(0.1)
    assert abs(signal[-1]) == pytest.approx(0.9)


def test_two_tone_matches_sum_of_individual_tones() -> None:
    combined = two_tone(
        64,
        normalized_frequency_1=0.05,
        normalized_frequency_2=-0.08,
    )
    expected = (
        complex_tone(64, 0.05, amplitude=0.5 + 0.0j)
        + complex_tone(64, -0.08, amplitude=0.5 + 0.0j)
    )

    np.testing.assert_allclose(combined, expected)
