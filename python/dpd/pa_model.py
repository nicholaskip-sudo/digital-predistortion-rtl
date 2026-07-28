"""Behavioral power-amplifier model with memory, AM/AM, and AM/PM."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from dpd.pa_config import PaConfig, PaNonlinearityConfig


ComplexArray = NDArray[np.complex128]
FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class PaResult:
    """Intermediate and final signals from one PA evaluation."""

    input_samples: ComplexArray
    memory_samples: ComplexArray
    output_samples: ComplexArray
    output_magnitude: FloatArray
    phase_rotation_rad: FloatArray


def _complex_vector(samples: ComplexArray) -> ComplexArray:
    samples = np.asarray(samples, dtype=np.complex128)
    if samples.ndim != 1:
        raise ValueError("PA input must be a one-dimensional complex array.")
    if not np.all(np.isfinite(samples.real)) or not np.all(np.isfinite(samples.imag)):
        raise ValueError("PA input contains non-finite values.")
    return samples


def apply_causal_fir(samples: ComplexArray, taps: tuple[complex, ...]) -> ComplexArray:
    """Apply a causal complex FIR while preserving the input length."""

    samples = _complex_vector(samples)
    if not taps:
        raise ValueError("At least one FIR tap is required.")
    if samples.size == 0:
        return samples.copy()

    filtered = np.convolve(
        samples,
        np.asarray(taps, dtype=np.complex128),
        mode="full",
    )[: samples.size]
    return np.asarray(filtered, dtype=np.complex128)


def rapp_ampm_characteristic(
    input_magnitude: FloatArray,
    config: PaNonlinearityConfig,
) -> tuple[FloatArray, FloatArray]:
    """Evaluate memoryless Rapp AM/AM and saturating AM/PM curves."""

    magnitude = np.asarray(input_magnitude, dtype=np.float64)
    if np.any(magnitude < 0.0):
        raise ValueError("Input magnitude cannot be negative.")
    if not np.all(np.isfinite(magnitude)):
        raise ValueError("Input magnitude must be finite.")

    linear_output = config.small_signal_gain * magnitude
    ratio = linear_output / config.saturation_amplitude
    exponent = 2.0 * config.rapp_smoothness

    output_magnitude = linear_output / np.power(
        1.0 + np.power(ratio, exponent),
        1.0 / exponent,
    )

    transition_ratio = magnitude / config.ampm_transition_amplitude
    phase_fraction = np.square(transition_ratio) / (
        1.0 + np.square(transition_ratio)
    )
    phase_rotation_rad = np.deg2rad(config.ampm_max_degrees) * phase_fraction

    return (
        np.asarray(output_magnitude, dtype=np.float64),
        np.asarray(phase_rotation_rad, dtype=np.float64),
    )


def apply_pa(samples: ComplexArray, config: PaConfig) -> PaResult:
    """Apply the causal memory filter followed by nonlinear AM/AM and AM/PM."""

    input_samples = _complex_vector(samples)
    memory_samples = apply_causal_fir(
        input_samples,
        taps=config.memory.input_taps,
    )

    input_magnitude = np.abs(memory_samples)
    output_magnitude, phase_rotation_rad = rapp_ampm_characteristic(
        input_magnitude,
        config.nonlinearity,
    )

    input_phase = np.angle(memory_samples)
    output_samples = output_magnitude * np.exp(
        1j * (input_phase + phase_rotation_rad)
    )

    # Preserve an exact complex zero for zero-magnitude inputs.
    output_samples = np.where(
        input_magnitude == 0.0,
        0.0 + 0.0j,
        output_samples,
    )

    return PaResult(
        input_samples=input_samples.copy(),
        memory_samples=np.asarray(memory_samples, dtype=np.complex128),
        output_samples=np.asarray(output_samples, dtype=np.complex128),
        output_magnitude=np.asarray(output_magnitude, dtype=np.float64),
        phase_rotation_rad=np.asarray(phase_rotation_rad, dtype=np.float64),
    )
