"""Safeguarded indirect-learning training for the Memory Polynomial DPD."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from dpd.config import AlgorithmConfig
from dpd.dpd_training_config import DpdTrainingConfig
from dpd.memory_polynomial import (
    MemoryPolynomialResult,
    build_basis_matrix,
    evaluate_memory_polynomial,
    identity_coefficients,
)
from dpd.metrics import nmse_db
from dpd.pa_config import PaConfig
from dpd.pa_model import apply_pa


ComplexArray = NDArray[np.complex128]
FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class LeastSquaresResult:
    """One normalized ridge least-squares solution."""

    coefficients: ComplexArray
    normalized_condition_number: float
    residual_nmse_db: float


@dataclass(frozen=True)
class TrainingIteration:
    """One evaluated postdistorter candidate."""

    iteration: int
    accepted: bool
    training_nmse_db: float
    validation_nmse_db: float
    full_waveform_nmse_db: float
    normalized_condition_number: float
    saturation_count: int


@dataclass(frozen=True)
class DpdTrainingResult:
    """Final DPD coefficients, waveforms, and iteration history."""

    coefficients: ComplexArray
    predistorter_result: MemoryPolynomialResult
    pa_output_samples: ComplexArray
    history: tuple[TrainingIteration, ...]
    training_stop_reason: str
    training_split_index: int

    @property
    def accepted_iteration_count(self) -> int:
        """Return the number of accepted postdistorter updates."""

        return sum(record.accepted for record in self.history)


def fit_memory_polynomial(
    input_samples: ComplexArray,
    target_samples: ComplexArray,
    algorithm_config: AlgorithmConfig,
    ridge_regularization: float,
    first_sample: int = 0,
    stop_sample: int | None = None,
) -> LeastSquaresResult:
    """Fit complex Memory Polynomial coefficients with column normalization.

    Column normalization prevents the order-1, order-3, and order-5 basis terms
    from having vastly different numerical scales. Optional ridge rows are added
    to the normalized least-squares system.
    """

    input_samples = np.asarray(input_samples, dtype=np.complex128)
    target_samples = np.asarray(target_samples, dtype=np.complex128)

    if input_samples.ndim != 1 or target_samples.ndim != 1:
        raise ValueError("Least-squares inputs must be one-dimensional.")
    if input_samples.shape != target_samples.shape:
        raise ValueError("Least-squares input and target shapes must match.")
    if input_samples.size == 0:
        raise ValueError("Least-squares vectors cannot be empty.")
    if ridge_regularization < 0.0:
        raise ValueError("Ridge regularization cannot be negative.")

    selected_stop = input_samples.size if stop_sample is None else stop_sample
    if first_sample < 0 or selected_stop > input_samples.size:
        raise ValueError("Least-squares sample range is outside the waveform.")
    if first_sample >= selected_stop:
        raise ValueError("Least-squares sample range is empty.")

    complete_basis = build_basis_matrix(input_samples, algorithm_config)
    basis = complete_basis[first_sample:selected_stop]
    target = target_samples[first_sample:selected_stop]

    column_rms = np.sqrt(np.mean(np.abs(basis) ** 2, axis=0))
    if np.any(column_rms == 0.0):
        raise ValueError("A Memory Polynomial basis column has zero energy.")

    normalized_basis = basis / column_rms[np.newaxis, :]
    condition_number = float(np.linalg.cond(normalized_basis))

    if ridge_regularization > 0.0:
        ridge_rows = np.sqrt(ridge_regularization) * np.eye(
            algorithm_config.coefficient_count,
            dtype=np.complex128,
        )
        solve_basis = np.vstack((normalized_basis, ridge_rows))
        solve_target = np.concatenate(
            (
                target,
                np.zeros(
                    algorithm_config.coefficient_count,
                    dtype=np.complex128,
                ),
            )
        )
    else:
        solve_basis = normalized_basis
        solve_target = target

    normalized_coefficients, _, _, _ = np.linalg.lstsq(
        solve_basis,
        solve_target,
        rcond=None,
    )
    coefficients = normalized_coefficients / column_rms
    fitted_target = basis @ coefficients

    return LeastSquaresResult(
        coefficients=np.asarray(coefficients, dtype=np.complex128),
        normalized_condition_number=condition_number,
        residual_nmse_db=nmse_db(target, fitted_target, gain=1.0 + 0.0j),
    )


def _evaluate_candidate(
    input_samples: ComplexArray,
    coefficients: ComplexArray,
    algorithm_config: AlgorithmConfig,
    training_config: DpdTrainingConfig,
    pa_config: PaConfig,
) -> tuple[MemoryPolynomialResult, ComplexArray]:
    predistorter = evaluate_memory_polynomial(
        input_samples,
        coefficients,
        algorithm_config,
        component_minimum=training_config.output_limit.minimum,
        component_maximum=training_config.output_limit.maximum,
    )
    pa_output = apply_pa(predistorter.output_samples, pa_config).output_samples
    return predistorter, pa_output


def train_indirect_learning(
    input_samples: ComplexArray,
    algorithm_config: AlgorithmConfig,
    training_config: DpdTrainingConfig,
    pa_config: PaConfig,
) -> DpdTrainingResult:
    """Train a Memory Polynomial using safeguarded indirect learning.

    Each iteration fits a postdistorter that maps normalized PA output back to
    the PA input. The candidate is copied to the predistorter only when it
    improves held-out validation NMSE by the configured minimum amount. This
    safeguard prevents later indirect-learning iterations from diverging.
    """

    input_samples = np.asarray(input_samples, dtype=np.complex128)
    if input_samples.ndim != 1 or input_samples.size == 0:
        raise ValueError("Training input must be a nonempty one-dimensional array.")

    split_index = int(
        np.floor(input_samples.size * training_config.least_squares.training_fraction)
    )
    first_sample = max(
        algorithm_config.memory_depth - 1,
        training_config.least_squares.ignore_initial_samples,
    )

    if split_index <= first_sample:
        raise ValueError("Training split leaves no usable least-squares samples.")
    if split_index >= input_samples.size:
        raise ValueError("Training split leaves no validation samples.")

    target_gain = training_config.target.linear_gain
    coefficients = identity_coefficients(algorithm_config)
    current_predistorter, current_pa_output = _evaluate_candidate(
        input_samples,
        coefficients,
        algorithm_config,
        training_config,
        pa_config,
    )
    current_validation_nmse = nmse_db(
        input_samples[split_index:],
        current_pa_output[split_index:],
        gain=target_gain,
    )

    history: list[TrainingIteration] = []
    stop_reason = "maximum_iterations_reached"

    for iteration in range(1, training_config.iteration.maximum_iterations + 1):
        normalized_pa_output = current_pa_output / target_gain
        least_squares = fit_memory_polynomial(
            input_samples=normalized_pa_output,
            target_samples=current_predistorter.output_samples,
            algorithm_config=algorithm_config,
            ridge_regularization=(
                training_config.least_squares.ridge_regularization
            ),
            first_sample=first_sample,
            stop_sample=split_index,
        )

        candidate_predistorter, candidate_pa_output = _evaluate_candidate(
            input_samples,
            least_squares.coefficients,
            algorithm_config,
            training_config,
            pa_config,
        )
        candidate_training_nmse = nmse_db(
            input_samples[first_sample:split_index],
            candidate_pa_output[first_sample:split_index],
            gain=target_gain,
        )
        candidate_validation_nmse = nmse_db(
            input_samples[split_index:],
            candidate_pa_output[split_index:],
            gain=target_gain,
        )
        candidate_full_nmse = nmse_db(
            input_samples,
            candidate_pa_output,
            gain=target_gain,
        )

        improvement_db = current_validation_nmse - candidate_validation_nmse
        accepted = (
            improvement_db
            >= training_config.iteration.minimum_validation_improvement_db
        )

        history.append(
            TrainingIteration(
                iteration=iteration,
                accepted=accepted,
                training_nmse_db=candidate_training_nmse,
                validation_nmse_db=candidate_validation_nmse,
                full_waveform_nmse_db=candidate_full_nmse,
                normalized_condition_number=(
                    least_squares.normalized_condition_number
                ),
                saturation_count=candidate_predistorter.saturation_count,
            )
        )

        if not accepted:
            stop_reason = "candidate_failed_validation_guard"
            break

        coefficients = least_squares.coefficients
        current_predistorter = candidate_predistorter
        current_pa_output = candidate_pa_output
        current_validation_nmse = candidate_validation_nmse

    return DpdTrainingResult(
        coefficients=np.asarray(coefficients, dtype=np.complex128),
        predistorter_result=current_predistorter,
        pa_output_samples=np.asarray(current_pa_output, dtype=np.complex128),
        history=tuple(history),
        training_stop_reason=stop_reason,
        training_split_index=split_index,
    )
