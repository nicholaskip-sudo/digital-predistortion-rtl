"""Tests for the NumPy-only spectrum reporting helpers."""

from __future__ import annotations

import numpy as np
import pytest

from dpd.spectrum import adjacent_channel_power_ratio_db, welch_psd_db
from dpd.waveform import complex_tone, generate_ofdm
from dpd.waveform_config import load_waveform_config


def test_welch_psd_is_centered_and_normalized() -> None:
    samples = complex_tone(8192, normalized_frequency=0.125, amplitude=0.7+0j)
    frequency_hz, psd_db = welch_psd_db(samples, 1_000_000.0, 1024)
    assert frequency_hz.shape == psd_db.shape
    assert np.max(psd_db) == pytest.approx(0.0)
    assert abs(frequency_hz[int(np.argmax(psd_db))] - 125_000.0) < 2_000.0


def test_welch_psd_is_repeatable() -> None:
    samples = complex_tone(4096, -0.20, amplitude=0.5+0j)
    f1, p1 = welch_psd_db(samples, 2_000_000.0, 512)
    f2, p2 = welch_psd_db(samples, 2_000_000.0, 512)
    np.testing.assert_array_equal(f1, f2)
    np.testing.assert_array_equal(p1, p2)


def test_welch_psd_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="nonempty"):
        welch_psd_db(np.array([], dtype=np.complex128), 1_000_000.0)


def test_ofdm_adjacent_power_is_below_main_channel_power() -> None:
    config = load_waveform_config()
    generated = generate_ofdm(config.ofdm, config.qam.order, np.random.default_rng(config.seed))
    occupied = config.ofdm.active_subcarriers * config.report.sample_rate_hz / config.ofdm.ifft_size
    acpr = adjacent_channel_power_ratio_db(generated.samples, config.report.sample_rate_hz, occupied)
    assert np.isfinite(acpr)
    assert acpr < -15.0
