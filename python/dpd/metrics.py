"""Numerical quality metrics shared by PA and DPD reports."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


ComplexArray = NDArray[np.complex128]


def _matching_vectors(
    reference: ComplexArray,
    observed: ComplexArray,
) -> tuple[ComplexArray, ComplexArray]:
    reference = np.asarray(reference, dtype=np.complex128)
    observed = np.asarray(observed, dtype=np.complex128)

    if reference.ndim != 1 or observed.ndim != 1:
        raise ValueError("Metric inputs must be one-dimensional arrays.")
    if reference.shape != observed.shape:
        raise ValueError("Reference and observed arrays must have matching shapes.")
    if reference.size == 0:
        raise ValueError("Metric inputs cannot be empty.")
    return reference, observed


def best_fit_complex_gain(
    reference: ComplexArray,
    observed: ComplexArray,
) -> complex:
    """Return the least-squares scalar gain mapping reference to observed."""

    reference, observed = _matching_vectors(reference, observed)
    denominator = np.vdot(reference, reference)
    if abs(denominator) == 0.0:
        raise ValueError("Cannot estimate gain from an all-zero reference.")
    return complex(np.vdot(reference, observed) / denominator)


def nmse_db(
    reference: ComplexArray,
    observed: ComplexArray,
    gain: complex | None = None,
) -> float:
    """Return normalized mean-square error in decibels."""

    reference, observed = _matching_vectors(reference, observed)
    selected_gain = (
        best_fit_complex_gain(reference, observed) if gain is None else gain
    )
    desired = selected_gain * reference
    error_power = float(np.mean(np.abs(observed - desired) ** 2))
    desired_power = float(np.mean(np.abs(desired) ** 2))
    if desired_power == 0.0:
        raise ValueError("Desired signal power is zero.")
    if error_power == 0.0:
        return float("-inf")
    return float(10.0 * np.log10(error_power / desired_power))


def evm_rms_percent(
    reference: ComplexArray,
    observed: ComplexArray,
    gain: complex | None = None,
) -> float:
    """Return RMS error-vector magnitude as a percentage."""

    reference, observed = _matching_vectors(reference, observed)
    selected_gain = (
        best_fit_complex_gain(reference, observed) if gain is None else gain
    )
    desired = selected_gain * reference
    error_power = float(np.mean(np.abs(observed - desired) ** 2))
    desired_power = float(np.mean(np.abs(desired) ** 2))
    if desired_power == 0.0:
        raise ValueError("Desired signal power is zero.")
    return float(100.0 * np.sqrt(error_power / desired_power))


def per_column_complex_gain(
    reference: NDArray[np.complex128],
    observed: NDArray[np.complex128],
) -> NDArray[np.complex128]:
    """Estimate one least-squares gain for each matrix column."""

    reference = np.asarray(reference, dtype=np.complex128)
    observed = np.asarray(observed, dtype=np.complex128)
    if reference.ndim != 2 or observed.ndim != 2:
        raise ValueError("Per-column gain inputs must be two-dimensional.")
    if reference.shape != observed.shape:
        raise ValueError("Reference and observed matrices must have matching shapes.")

    numerator = np.sum(np.conj(reference) * observed, axis=0)
    denominator = np.sum(np.abs(reference) ** 2, axis=0)
    if np.any(denominator == 0.0):
        raise ValueError("A reference column has zero energy.")
    return np.asarray(numerator / denominator, dtype=np.complex128)
