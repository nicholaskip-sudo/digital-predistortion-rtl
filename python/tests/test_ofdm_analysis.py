"""Tests for OFDM receive-side analysis."""

import numpy as np

from dpd.ofdm_analysis import demodulate_ofdm
from dpd.waveform import generate_ofdm
from dpd.waveform_config import load_waveform_config


def test_ofdm_demodulation_recovers_generated_symbols() -> None:
    config = load_waveform_config()
    generated = generate_ofdm(config.ofdm, config.qam.order, np.random.default_rng(config.seed))
    recovered = demodulate_ofdm(
        generated.samples,
        config.ofdm,
        generated.active_bin_indices,
    )
    np.testing.assert_allclose(recovered, generated.frequency_symbols, atol=1e-12)
