"""Train the floating-point DPD and generate performance evidence."""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from dpd.config import load_project_config
from dpd.dpd_training_config import load_dpd_training_config
from dpd.memory_polynomial import evaluate_memory_polynomial
from dpd.metrics import (
    best_fit_complex_gain,
    evm_rms_percent,
    nmse_db,
    per_column_complex_gain,
)
from dpd.ofdm_analysis import demodulate_ofdm
from dpd.pa_config import load_pa_config
from dpd.pa_model import apply_pa
from dpd.project_paths import PLOTS_DIR, RESULTS_DIR, VECTORS_DIR, create_output_directories
from dpd.spectrum import adjacent_channel_power_ratio_db, welch_psd_db
from dpd.training import train_indirect_learning
from dpd.waveform import papr_db, rms_magnitude
from dpd.waveform_config import load_waveform_config


def _equalized_symbols(
    output_samples: np.ndarray,
    reference_symbols: np.ndarray,
    active_bin_indices: np.ndarray,
    waveform_config,
) -> tuple[np.ndarray, np.ndarray]:
    output_symbols = demodulate_ofdm(
        output_samples,
        waveform_config.ofdm,
        active_bin_indices,
    )
    carrier_gains = per_column_complex_gain(reference_symbols, output_symbols)
    equalized = output_symbols / carrier_gains[np.newaxis, :]
    return output_symbols, equalized


def _ofdm_evm(reference_symbols: np.ndarray, equalized_symbols: np.ndarray) -> float:
    return evm_rms_percent(
        reference_symbols.reshape(-1),
        equalized_symbols.reshape(-1),
        gain=1.0 + 0.0j,
    )


def save_training_plot(history) -> None:
    iterations = [0] + [record.iteration for record in history]
    initial_placeholder = np.nan
    validation = [initial_placeholder] + [record.validation_nmse_db for record in history]
    full = [initial_placeholder] + [record.full_waveform_nmse_db for record in history]

    figure, axis = plt.subplots(figsize=(7.6, 5.0))
    axis.plot(iterations[1:], validation[1:], marker="o", label="Validation NMSE")
    axis.plot(iterations[1:], full[1:], marker="s", label="Full-waveform NMSE")
    for record in history:
        label = "accepted" if record.accepted else "rejected"
        axis.annotate(
            label,
            (record.iteration, record.validation_nmse_db),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
        )
    axis.set_title("Safeguarded indirect-learning convergence")
    axis.set_xlabel("Candidate iteration")
    axis.set_ylabel("Target NMSE (dB)")
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "dpd_training_convergence.png", dpi=160)
    plt.close(figure)


def save_psd_plot(
    original_pa_output: np.ndarray,
    same_gain_output: np.ndarray,
    dpd_output: np.ndarray,
    sample_rate_hz: float,
) -> None:
    frequency, original_psd = welch_psd_db(original_pa_output, sample_rate_hz)
    _, same_gain_psd = welch_psd_db(same_gain_output, sample_rate_hz)
    _, dpd_psd = welch_psd_db(dpd_output, sample_rate_hz)

    figure, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(frequency / 1e6, original_psd, label="PA without DPD")
    axis.plot(frequency / 1e6, same_gain_psd, label="Same-gain backoff")
    axis.plot(frequency / 1e6, dpd_psd, label="DPD + PA")
    axis.set_title("Spectral comparison before and after DPD")
    axis.set_xlabel("Frequency (MHz)")
    axis.set_ylabel("Relative PSD (dB)")
    axis.set_ylim(-100, 5)
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "dpd_psd_comparison.png", dpi=160)
    plt.close(figure)


def save_constellation_plot(
    reference_symbols: np.ndarray,
    original_equalized: np.ndarray,
    same_gain_equalized: np.ndarray,
    dpd_equalized: np.ndarray,
    maximum_points: int,
) -> None:
    reference = reference_symbols.reshape(-1)
    original = original_equalized.reshape(-1)
    same_gain = same_gain_equalized.reshape(-1)
    corrected = dpd_equalized.reshape(-1)
    count = min(maximum_points, reference.size)

    figure, axis = plt.subplots(figsize=(6.8, 6.8))
    axis.scatter(reference[:count].real, reference[:count].imag, s=8, alpha=0.18, label="Ideal")
    axis.scatter(original[:count].real, original[:count].imag, s=8, alpha=0.16, label="PA without DPD")
    axis.scatter(same_gain[:count].real, same_gain[:count].imag, s=8, alpha=0.16, label="Same-gain backoff")
    axis.scatter(corrected[:count].real, corrected[:count].imag, s=8, alpha=0.20, label="DPD + PA")
    axis.set_title("64-QAM constellation linearization")
    axis.set_xlabel("In-phase")
    axis.set_ylabel("Quadrature")
    axis.set_aspect("equal", adjustable="box")
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "dpd_constellation_comparison.png", dpi=160)
    plt.close(figure)


def save_time_plot(
    input_samples: np.ndarray,
    predistorted_samples: np.ndarray,
    dpd_pa_output: np.ndarray,
    target_gain: float,
) -> None:
    count = min(700, input_samples.size)
    sample_index = np.arange(count)

    figure, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(sample_index, np.abs(target_gain * input_samples[:count]), label="Desired output")
    axis.plot(sample_index, np.abs(predistorted_samples[:count]), label="DPD output / PA input")
    axis.plot(sample_index, np.abs(dpd_pa_output[:count]), label="DPD + PA output")
    axis.set_title("DPD envelope and corrected PA output")
    axis.set_xlabel("Sample index")
    axis.set_ylabel("Magnitude")
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "dpd_time_magnitude.png", dpi=160)
    plt.close(figure)


def save_error_plot(
    input_samples: np.ndarray,
    same_gain_output: np.ndarray,
    dpd_output: np.ndarray,
    target_gain: float,
) -> None:
    count = min(1200, input_samples.size)
    desired = target_gain * input_samples[:count]
    same_gain_error = np.abs(same_gain_output[:count] - desired)
    dpd_error = np.abs(dpd_output[:count] - desired)

    figure, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(same_gain_error, label="Same-gain backoff error")
    axis.plot(dpd_error, label="DPD + PA error")
    axis.set_title("Complex-envelope error magnitude")
    axis.set_xlabel("Sample index")
    axis.set_ylabel("Absolute error")
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "dpd_error_magnitude.png", dpi=160)
    plt.close(figure)


def save_coefficient_plot(coefficients: np.ndarray) -> None:
    coefficient_index = np.arange(coefficients.size)

    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    axis.bar(coefficient_index, np.abs(coefficients))
    axis.set_title("Trained Memory Polynomial coefficient magnitudes")
    axis.set_xlabel("Coefficient index")
    axis.set_ylabel("Magnitude")
    axis.set_xticks(coefficient_index)
    axis.grid(True, axis="y")
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "dpd_coefficient_magnitudes.png", dpi=160)
    plt.close(figure)


def main() -> int:
    create_output_directories()
    project_config = load_project_config()
    waveform_config = load_waveform_config()
    pa_config = load_pa_config()
    training_config = load_dpd_training_config()

    input_path = VECTORS_DIR / "ofdm_float_reference.npz"
    if not input_path.exists():
        raise FileNotFoundError(
            "Missing OFDM reference. Run generate_waveform_report.py first."
        )

    with np.load(input_path) as data:
        input_samples = np.asarray(data["samples"], dtype=np.complex128)
        reference_symbols = np.asarray(
            data["frequency_symbols"],
            dtype=np.complex128,
        )
        active_bin_indices = np.asarray(
            data["active_bin_indices"],
            dtype=np.int64,
        )

    original_pa_output = apply_pa(input_samples, pa_config).output_samples

    target_gain = training_config.target.linear_gain
    same_gain_input_scale = (
        target_gain / pa_config.nonlinearity.small_signal_gain
    )
    same_gain_pa_input = same_gain_input_scale * input_samples
    same_gain_output = apply_pa(same_gain_pa_input, pa_config).output_samples

    training_result = train_indirect_learning(
        input_samples,
        project_config.algorithm,
        training_config,
        pa_config,
    )
    predistorted_samples = training_result.predistorter_result.output_samples
    dpd_pa_output = training_result.pa_output_samples

    _, original_equalized = _equalized_symbols(
        original_pa_output,
        reference_symbols,
        active_bin_indices,
        waveform_config,
    )
    _, same_gain_equalized = _equalized_symbols(
        same_gain_output,
        reference_symbols,
        active_bin_indices,
        waveform_config,
    )
    dpd_output_symbols, dpd_equalized = _equalized_symbols(
        dpd_pa_output,
        reference_symbols,
        active_bin_indices,
        waveform_config,
    )

    occupied_bandwidth_hz = (
        waveform_config.ofdm.active_subcarriers
        * waveform_config.report.sample_rate_hz
        / waveform_config.ofdm.ifft_size
    )

    original_best_fit_nmse = nmse_db(input_samples, original_pa_output)
    same_gain_target_nmse = nmse_db(
        input_samples,
        same_gain_output,
        gain=target_gain,
    )
    dpd_target_nmse = nmse_db(
        input_samples,
        dpd_pa_output,
        gain=target_gain,
    )
    dpd_best_fit_nmse = nmse_db(input_samples, dpd_pa_output)

    original_evm = _ofdm_evm(reference_symbols, original_equalized)
    same_gain_evm = _ofdm_evm(reference_symbols, same_gain_equalized)
    dpd_evm = _ofdm_evm(reference_symbols, dpd_equalized)

    original_acpr = adjacent_channel_power_ratio_db(
        original_pa_output,
        waveform_config.report.sample_rate_hz,
        occupied_bandwidth_hz,
    )
    same_gain_acpr = adjacent_channel_power_ratio_db(
        same_gain_output,
        waveform_config.report.sample_rate_hz,
        occupied_bandwidth_hz,
    )
    dpd_acpr = adjacent_channel_power_ratio_db(
        dpd_pa_output,
        waveform_config.report.sample_rate_hz,
        occupied_bandwidth_hz,
    )

    coefficients = training_result.coefficients
    metrics = {
        "method": training_config.method,
        "target_linear_gain": target_gain,
        "sample_count": int(input_samples.size),
        "coefficient_count": int(coefficients.size),
        "accepted_iterations": training_result.accepted_iteration_count,
        "evaluated_candidates": len(training_result.history),
        "training_stop_reason": training_result.training_stop_reason,
        "training_split_index": training_result.training_split_index,
        "predistorter_rms_magnitude": rms_magnitude(predistorted_samples),
        "predistorter_peak_magnitude": float(np.max(np.abs(predistorted_samples))),
        "predistorter_component_saturation_count": (
            training_result.predistorter_result.saturation_count
        ),
        "predistorter_component_saturation_fraction": (
            training_result.predistorter_result.saturation_fraction
        ),
        "dpd_pa_best_fit_gain_real": best_fit_complex_gain(
            input_samples,
            dpd_pa_output,
        ).real,
        "dpd_pa_best_fit_gain_imag": best_fit_complex_gain(
            input_samples,
            dpd_pa_output,
        ).imag,
        "original_pa_best_fit_nmse_db": original_best_fit_nmse,
        "same_gain_backoff_target_nmse_db": same_gain_target_nmse,
        "dpd_pa_target_nmse_db": dpd_target_nmse,
        "dpd_pa_best_fit_nmse_db": dpd_best_fit_nmse,
        "nmse_improvement_vs_original_pa_db": (
            original_best_fit_nmse - dpd_best_fit_nmse
        ),
        "nmse_improvement_vs_same_gain_backoff_db": (
            same_gain_target_nmse - dpd_target_nmse
        ),
        "original_pa_ofdm_evm_percent": original_evm,
        "same_gain_backoff_ofdm_evm_percent": same_gain_evm,
        "dpd_pa_ofdm_evm_percent": dpd_evm,
        "original_pa_acpr_db": original_acpr,
        "same_gain_backoff_acpr_db": same_gain_acpr,
        "dpd_pa_acpr_db": dpd_acpr,
        "original_pa_output_papr_db": papr_db(original_pa_output),
        "same_gain_backoff_output_papr_db": papr_db(same_gain_output),
        "dpd_pa_output_papr_db": papr_db(dpd_pa_output),
        "training_history": [
            {
                "iteration": record.iteration,
                "accepted": record.accepted,
                "training_nmse_db": record.training_nmse_db,
                "validation_nmse_db": record.validation_nmse_db,
                "full_waveform_nmse_db": record.full_waveform_nmse_db,
                "normalized_condition_number": (
                    record.normalized_condition_number
                ),
                "saturation_count": record.saturation_count,
            }
            for record in training_result.history
        ],
        "coefficients": [
            {
                "index": index,
                "real": coefficient.real,
                "imag": coefficient.imag,
                "magnitude": abs(coefficient),
                "phase_degrees": float(np.rad2deg(np.angle(coefficient))),
            }
            for index, coefficient in enumerate(coefficients)
        ],
    }

    np.savez_compressed(
        VECTORS_DIR / "dpd_float_reference.npz",
        input_samples=input_samples,
        original_pa_output=original_pa_output,
        same_gain_pa_input=same_gain_pa_input,
        same_gain_pa_output=same_gain_output,
        coefficients=coefficients,
        predistorter_raw_output=(
            training_result.predistorter_result.raw_output_samples
        ),
        predistorted_samples=predistorted_samples,
        dpd_pa_output=dpd_pa_output,
        reference_symbols=reference_symbols,
        dpd_output_symbols=dpd_output_symbols,
        dpd_equalized_symbols=dpd_equalized,
        active_bin_indices=active_bin_indices,
    )

    metrics_path = RESULTS_DIR / "dpd_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    save_training_plot(training_result.history)
    save_psd_plot(
        original_pa_output,
        same_gain_output,
        dpd_pa_output,
        waveform_config.report.sample_rate_hz,
    )
    save_constellation_plot(
        reference_symbols,
        original_equalized,
        same_gain_equalized,
        dpd_equalized,
        training_config.report.maximum_constellation_points,
    )
    save_time_plot(
        input_samples,
        predistorted_samples,
        dpd_pa_output,
        target_gain,
    )
    save_error_plot(
        input_samples,
        same_gain_output,
        dpd_pa_output,
        target_gain,
    )
    save_coefficient_plot(coefficients)

    print(json.dumps(metrics, indent=2))
    print(f"DPD waveform data: {VECTORS_DIR / 'dpd_float_reference.npz'}")
    print(f"DPD metrics: {metrics_path}")
    print(f"DPD plots: {PLOTS_DIR}")
    print("DPD_REPORT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
