"""Tests for least-squares fitting and indirect-learning training."""

from __future__ import annotations

import numpy as np

from dpd.config import AlgorithmConfig, load_project_config
from dpd.dpd_training_config import load_dpd_training_config
from dpd.memory_polynomial import build_basis_matrix
from dpd.metrics import nmse_db
from dpd.pa_config import load_pa_config
from dpd.pa_model import apply_pa
from dpd.training import fit_memory_polynomial, train_indirect_learning
from dpd.waveform import generate_ofdm
from dpd.waveform_config import OfdmConfig, load_waveform_config


def test_least_squares_recovers_known_coefficients() -> None:
    config = AlgorithmConfig(
        model="memory_polynomial",
        memory_depth=2,
        polynomial_orders=(1, 3),
    )
    rng = np.random.default_rng(44)
    samples = 0.2 * (
        rng.standard_normal(4096) + 1j * rng.standard_normal(4096)
    )
    expected_coefficients = np.array(
        [0.9 + 0.1j, -0.4 + 0.2j, 0.05 - 0.03j, 0.1 + 0.04j],
        dtype=np.complex128,
    )
    target = build_basis_matrix(samples, config) @ expected_coefficients

    fitted = fit_memory_polynomial(
        samples,
        target,
        config,
        ridge_regularization=0.0,
        first_sample=2,
    )

    np.testing.assert_allclose(
        fitted.coefficients,
        expected_coefficients,
        atol=1e-11,
    )
    assert fitted.residual_nmse_db < -250.0
    assert np.isfinite(fitted.normalized_condition_number)


def _small_training_waveform() -> np.ndarray:
    waveform_config = load_waveform_config()
    small_ofdm = OfdmConfig(
        symbol_count=12,
        base_fft_size=waveform_config.ofdm.base_fft_size,
        active_subcarriers=waveform_config.ofdm.active_subcarriers,
        cyclic_prefix_length=waveform_config.ofdm.cyclic_prefix_length,
        oversampling=waveform_config.ofdm.oversampling,
    )
    generated = generate_ofdm(
        small_ofdm,
        waveform_config.qam.order,
        np.random.default_rng(waveform_config.seed),
    )
    samples = generated.samples
    rms = np.sqrt(np.mean(np.abs(samples) ** 2))
    return np.asarray(samples * (0.2 / rms), dtype=np.complex128)


def test_indirect_learning_is_deterministic_and_improves_nmse() -> None:
    samples = _small_training_waveform()
    algorithm_config = load_project_config().algorithm
    training_config = load_dpd_training_config()
    pa_config = load_pa_config()

    baseline_output = apply_pa(samples, pa_config).output_samples
    baseline_nmse = nmse_db(samples, baseline_output)

    first = train_indirect_learning(
        samples,
        algorithm_config,
        training_config,
        pa_config,
    )
    second = train_indirect_learning(
        samples,
        algorithm_config,
        training_config,
        pa_config,
    )

    np.testing.assert_array_equal(first.coefficients, second.coefficients)
    np.testing.assert_array_equal(first.pa_output_samples, second.pa_output_samples)

    corrected_nmse = nmse_db(samples, first.pa_output_samples)
    assert corrected_nmse < baseline_nmse - 5.0
    assert first.accepted_iteration_count >= 1
    assert first.history[0].accepted
    assert first.coefficients.shape == (algorithm_config.coefficient_count,)


def test_trained_output_respects_component_limits() -> None:
    samples = _small_training_waveform()
    result = train_indirect_learning(
        samples,
        load_project_config().algorithm,
        load_dpd_training_config(),
        load_pa_config(),
    )
    limit = load_dpd_training_config().output_limit

    assert np.min(result.predistorter_result.output_samples.real) >= limit.minimum
    assert np.max(result.predistorter_result.output_samples.real) <= limit.maximum
    assert np.min(result.predistorter_result.output_samples.imag) >= limit.minimum
    assert np.max(result.predistorter_result.output_samples.imag) <= limit.maximum
