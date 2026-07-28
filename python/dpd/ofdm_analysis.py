"""OFDM receive-side helpers used for PA and DPD evaluation."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from dpd.waveform_config import OfdmConfig


ComplexArray = NDArray[np.complex128]


def demodulate_ofdm(
    samples: ComplexArray,
    config: OfdmConfig,
    active_bin_indices: NDArray[np.int64],
) -> ComplexArray:
    """Remove the cyclic prefix, FFT each symbol, and return active carriers."""

    samples = np.asarray(samples, dtype=np.complex128)
    active_bin_indices = np.asarray(active_bin_indices, dtype=np.int64)

    if samples.ndim != 1:
        raise ValueError("OFDM samples must be one-dimensional.")
    if samples.size != config.total_samples:
        raise ValueError(
            f"Expected {config.total_samples} samples, received {samples.size}."
        )
    if active_bin_indices.shape != (config.active_subcarriers,):
        raise ValueError("Active-bin index count does not match the OFDM configuration.")

    complete_symbols = samples.reshape(
        config.symbol_count,
        config.samples_per_symbol,
    )
    time_symbols = complete_symbols[:, config.cyclic_prefix_samples :]
    frequency_grid = np.fft.fft(time_symbols, axis=1) / np.sqrt(config.ifft_size)
    return np.asarray(
        frequency_grid[:, active_bin_indices],
        dtype=np.complex128,
    )
