"""Deterministic complex-baseband waveform generation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from dpd.waveform_config import OfdmConfig


ComplexArray = NDArray[np.complex128]
FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class OfdmWaveform:
    """Generated OFDM samples and the QAM symbols used to create them."""

    samples: ComplexArray
    frequency_symbols: ComplexArray
    active_bin_indices: NDArray[np.int64]
    ifft_size: int
    cyclic_prefix_samples: int


def _validate_nonempty(signal: ComplexArray) -> None:
    if signal.ndim != 1:
        raise ValueError("Waveform must be a one-dimensional array.")
    if signal.size == 0:
        raise ValueError("Waveform cannot be empty.")
    if not np.all(np.isfinite(signal.real)) or not np.all(np.isfinite(signal.imag)):
        raise ValueError("Waveform contains non-finite values.")


def qam_symbols(
    order: int,
    count: int,
    rng: np.random.Generator,
) -> ComplexArray:
    """Generate normalized square-QAM symbols.

    The constellation is normalized to unit average power over the complete
    ideal constellation. This function selects constellation points directly;
    bit-to-symbol Gray mapping will be added only if a coded bitstream is needed.
    """

    if order not in (4, 16, 64):
        raise ValueError("Supported QAM orders are 4, 16, and 64.")
    if count <= 0:
        raise ValueError("QAM symbol count must be positive.")

    side_length = int(np.sqrt(order))
    levels = np.arange(-(side_length - 1), side_length, 2, dtype=np.float64)

    i_indices = rng.integers(0, side_length, size=count)
    q_indices = rng.integers(0, side_length, size=count)

    normalization = np.sqrt((2.0 / 3.0) * (order - 1))
    symbols = (levels[i_indices] + 1j * levels[q_indices]) / normalization
    return np.asarray(symbols, dtype=np.complex128)


def active_subcarrier_indices(
    ifft_size: int,
    active_subcarriers: int,
) -> NDArray[np.int64]:
    """Return symmetric active-bin indices while leaving DC unused."""

    if ifft_size <= 0:
        raise ValueError("IFFT size must be positive.")
    if active_subcarriers <= 0 or active_subcarriers % 2 != 0:
        raise ValueError("Active-subcarrier count must be a positive even integer.")
    if active_subcarriers >= ifft_size:
        raise ValueError("Active-subcarrier count must be smaller than IFFT size.")

    half = active_subcarriers // 2
    positive = np.arange(1, half + 1, dtype=np.int64)
    negative = np.arange(ifft_size - half, ifft_size, dtype=np.int64)
    return np.concatenate((positive, negative))


def generate_ofdm(
    config: OfdmConfig,
    qam_order: int,
    rng: np.random.Generator,
) -> OfdmWaveform:
    """Generate oversampled complex-baseband OFDM symbols with a cyclic prefix."""

    ifft_size = config.ifft_size
    active_bins = active_subcarrier_indices(
        ifft_size=ifft_size,
        active_subcarriers=config.active_subcarriers,
    )

    qam_count = config.symbol_count * config.active_subcarriers
    qam = qam_symbols(order=qam_order, count=qam_count, rng=rng)
    frequency_symbols = qam.reshape(
        config.symbol_count,
        config.active_subcarriers,
    )

    time_symbols = np.empty(
        (config.symbol_count, ifft_size),
        dtype=np.complex128,
    )

    for symbol_index in range(config.symbol_count):
        frequency_grid = np.zeros(ifft_size, dtype=np.complex128)
        frequency_grid[active_bins] = frequency_symbols[symbol_index]

        # NumPy's IFFT contains a 1/N factor. Multiplication by sqrt(N) creates
        # a unitary transform so frequency- and time-domain energy correspond.
        time_symbols[symbol_index] = (
            np.fft.ifft(frequency_grid) * np.sqrt(ifft_size)
        )

    cp_samples = config.cyclic_prefix_samples
    if cp_samples:
        cyclic_prefix = time_symbols[:, -cp_samples:]
        complete_symbols = np.concatenate((cyclic_prefix, time_symbols), axis=1)
    else:
        complete_symbols = time_symbols

    samples = complete_symbols.reshape(-1)
    return OfdmWaveform(
        samples=np.asarray(samples, dtype=np.complex128),
        frequency_symbols=np.asarray(frequency_symbols, dtype=np.complex128),
        active_bin_indices=active_bins,
        ifft_size=ifft_size,
        cyclic_prefix_samples=cp_samples,
    )


def normalize_signal(
    signal: ComplexArray,
    mode: str,
    target: float,
) -> ComplexArray:
    """Normalize a waveform by RMS magnitude or peak magnitude."""

    signal = np.asarray(signal, dtype=np.complex128)
    _validate_nonempty(signal)

    if target <= 0.0:
        raise ValueError("Normalization target must be positive.")
    if mode == "none":
        return signal.copy()

    if mode == "rms":
        reference = rms_magnitude(signal)
    elif mode == "peak":
        reference = float(np.max(np.abs(signal)))
    else:
        raise ValueError("Normalization mode must be none, peak, or rms.")

    if reference == 0.0:
        raise ValueError("Cannot normalize an all-zero signal.")

    return np.asarray(signal * (target / reference), dtype=np.complex128)


def rms_magnitude(signal: ComplexArray) -> float:
    """Return root-mean-square complex-envelope magnitude."""

    signal = np.asarray(signal, dtype=np.complex128)
    _validate_nonempty(signal)
    return float(np.sqrt(np.mean(np.abs(signal) ** 2)))


def papr_db(signal: ComplexArray) -> float:
    """Return peak-to-average power ratio in decibels."""

    signal = np.asarray(signal, dtype=np.complex128)
    _validate_nonempty(signal)

    power = np.abs(signal) ** 2
    average_power = float(np.mean(power))
    if average_power == 0.0:
        raise ValueError("PAPR is undefined for an all-zero signal.")

    return float(10.0 * np.log10(float(np.max(power)) / average_power))


def complex_impulse(
    sample_count: int,
    amplitude: complex = 1.0 + 0.0j,
    index: int = 0,
) -> ComplexArray:
    """Generate a complex impulse."""

    if sample_count <= 0:
        raise ValueError("Sample count must be positive.")
    if index < 0 or index >= sample_count:
        raise ValueError("Impulse index is outside the waveform.")

    signal = np.zeros(sample_count, dtype=np.complex128)
    signal[index] = amplitude
    return signal


def complex_tone(
    sample_count: int,
    normalized_frequency: float,
    amplitude: complex = 1.0 + 0.0j,
    initial_phase_rad: float = 0.0,
) -> ComplexArray:
    """Generate a complex exponential.

    normalized_frequency is measured in cycles per sample.
    """

    if sample_count <= 0:
        raise ValueError("Sample count must be positive.")
    if not -0.5 <= normalized_frequency < 0.5:
        raise ValueError("Normalized frequency must lie in [-0.5, 0.5).")

    sample_index = np.arange(sample_count, dtype=np.float64)
    phase = (
        2.0 * np.pi * normalized_frequency * sample_index
        + initial_phase_rad
    )
    return np.asarray(amplitude * np.exp(1j * phase), dtype=np.complex128)


def amplitude_ramp(
    sample_count: int,
    start_amplitude: float = 0.0,
    stop_amplitude: float = 1.0,
    phase_rad: float = 0.0,
) -> ComplexArray:
    """Generate a constant-phase complex amplitude ramp."""

    if sample_count <= 0:
        raise ValueError("Sample count must be positive.")
    if start_amplitude < 0.0 or stop_amplitude < 0.0:
        raise ValueError("Ramp amplitudes cannot be negative.")

    amplitudes = np.linspace(
        start_amplitude,
        stop_amplitude,
        sample_count,
        dtype=np.float64,
    )
    return np.asarray(amplitudes * np.exp(1j * phase_rad), dtype=np.complex128)


def two_tone(
    sample_count: int,
    normalized_frequency_1: float,
    normalized_frequency_2: float,
    amplitude_1: complex = 0.5 + 0.0j,
    amplitude_2: complex = 0.5 + 0.0j,
) -> ComplexArray:
    """Generate the sum of two complex tones."""

    first = complex_tone(
        sample_count,
        normalized_frequency_1,
        amplitude=amplitude_1,
    )
    second = complex_tone(
        sample_count,
        normalized_frequency_2,
        amplitude=amplitude_2,
    )
    return np.asarray(first + second, dtype=np.complex128)
