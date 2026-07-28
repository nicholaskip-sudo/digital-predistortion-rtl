"""Spectrum helpers used by waveform and DPD reports.

This module intentionally uses NumPy only so it works on managed Windows hosts
that block some compiled SciPy extension modules.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

ComplexArray = NDArray[np.complex128]
FloatArray = NDArray[np.float64]


def _validate_samples(samples: ComplexArray, sample_rate_hz: float, segment_length: int) -> ComplexArray:
    samples = np.asarray(samples, dtype=np.complex128)
    if samples.ndim != 1 or samples.size == 0:
        raise ValueError("Samples must be a nonempty one-dimensional array.")
    if not np.all(np.isfinite(samples.real)) or not np.all(np.isfinite(samples.imag)):
        raise ValueError("Samples contain non-finite values.")
    if sample_rate_hz <= 0.0:
        raise ValueError("Sample rate must be positive.")
    if segment_length <= 0:
        raise ValueError("Segment length must be positive.")
    return samples


def welch_psd_db(samples: ComplexArray, sample_rate_hz: float, segment_length: int = 4096) -> tuple[FloatArray, FloatArray]:
    """Return a centered, peak-normalized, two-sided Welch PSD."""
    samples = _validate_samples(samples, sample_rate_hz, segment_length)
    nperseg = min(segment_length, samples.size)
    window = np.ones(1, dtype=np.float64) if nperseg == 1 else np.hanning(nperseg)
    step = max(1, nperseg // 2)
    starts = list(range(0, samples.size - nperseg + 1, step)) or [0]
    accumulated = np.zeros(nperseg, dtype=np.float64)
    window_power = float(np.sum(window**2))

    for start in starts:
        segment = samples[start : start + nperseg]
        if segment.size < nperseg:
            padded = np.zeros(nperseg, dtype=np.complex128)
            padded[: segment.size] = segment
            segment = padded
        segment = segment - np.mean(segment)
        spectrum = np.fft.fft(segment * window)
        accumulated += np.abs(spectrum) ** 2 / (sample_rate_hz * window_power)

    psd = np.fft.fftshift(accumulated / len(starts))
    frequency_hz = np.fft.fftshift(np.fft.fftfreq(nperseg, d=1.0 / sample_rate_hz))
    psd_db = 10.0 * np.log10(np.maximum(psd, np.finfo(np.float64).tiny))
    psd_db -= np.max(psd_db)
    return np.asarray(frequency_hz), np.asarray(psd_db)


def adjacent_channel_power_ratio_db(
    samples: ComplexArray,
    sample_rate_hz: float,
    occupied_bandwidth_hz: float,
) -> float:
    """Estimate combined adjacent-band to main-band power ratio.

    The main channel spans +/- occupied_bandwidth/2. The two adjacent regions
    span from one half-bandwidth to three half-bandwidths on both sides.
    """
    samples = _validate_samples(samples, sample_rate_hz, max(1, samples.size))
    if occupied_bandwidth_hz <= 0.0:
        raise ValueError("Occupied bandwidth must be positive.")
    if 1.5 * occupied_bandwidth_hz >= sample_rate_hz / 2.0:
        raise ValueError("Sample rate is too small for the requested adjacent bands.")

    window = np.hanning(samples.size) if samples.size > 1 else np.ones(1)
    spectrum = np.fft.fftshift(np.fft.fft((samples - np.mean(samples)) * window))
    power = np.abs(spectrum) ** 2
    frequency_hz = np.fft.fftshift(np.fft.fftfreq(samples.size, d=1.0 / sample_rate_hz))

    half_band = occupied_bandwidth_hz / 2.0
    main_mask = np.abs(frequency_hz) <= half_band
    adjacent_mask = (
        (np.abs(frequency_hz) > half_band)
        & (np.abs(frequency_hz) <= 3.0 * half_band)
    )
    main_power = float(np.sum(power[main_mask]))
    adjacent_power = float(np.sum(power[adjacent_mask]))
    if main_power == 0.0 or adjacent_power == 0.0:
        return float("-inf")
    return float(10.0 * np.log10(adjacent_power / main_power))
