"""Generate the bit-accurate DPD dataset, metrics, traces, and plots."""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from dpd.dpd_training_config import load_dpd_training_config
from dpd.fixed_dpd import apply_fixed_dpd, quantize_input_samples
from dpd.fixed_point_analysis import dequantize_real
from dpd.fixed_point_config import load_fixed_point_config
from dpd.metrics import best_fit_complex_gain, evm_rms_percent, nmse_db, per_column_complex_gain
from dpd.ofdm_analysis import demodulate_ofdm
from dpd.pa_config import load_pa_config
from dpd.pa_model import apply_pa
from dpd.project_paths import PLOTS_DIR, RESULTS_DIR, VECTORS_DIR, create_output_directories
from dpd.spectrum import adjacent_channel_power_ratio_db, welch_psd_db
from dpd.waveform_config import load_waveform_config


def raw_nmse_db(reference: np.ndarray, observed: np.ndarray) -> float:
    error_power = float(np.mean(np.abs(observed - reference) ** 2))
    reference_power = float(np.mean(np.abs(reference) ** 2))
    if reference_power == 0.0:
        raise ValueError("Reference power is zero.")
    if error_power == 0.0:
        return float("-inf")
    return float(10.0 * np.log10(error_power / reference_power))


def equalized_ofdm_evm(
    samples: np.ndarray,
    reference_symbols: np.ndarray,
    active_bin_indices: np.ndarray,
    waveform_config,
) -> float:
    observed_symbols = demodulate_ofdm(
        samples,
        waveform_config.ofdm,
        active_bin_indices,
    )
    gains = per_column_complex_gain(reference_symbols, observed_symbols)
    equalized = observed_symbols / gains[np.newaxis, :]
    return evm_rms_percent(
        reference_symbols.reshape(-1),
        equalized.reshape(-1),
        gain=1.0 + 0.0j,
    )


def save_overlay_plot(floating: np.ndarray, fixed: np.ndarray) -> None:
    count = min(700, floating.size)
    index = np.arange(count)
    figure, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(index, floating[:count].real, label="Floating DPD I")
    axis.plot(index, fixed[:count].real, label="Fixed DPD I", linestyle="--")
    axis.set_title("Predistorter output: floating vs bit-accurate")
    axis.set_xlabel("Sample index")
    axis.set_ylabel("I amplitude")
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "fixed_dpd_float_overlay.png", dpi=160)
    plt.close(figure)


def save_error_plot(floating: np.ndarray, fixed: np.ndarray) -> None:
    count = min(1600, floating.size)
    error = fixed[:count] - floating[:count]
    figure, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(np.abs(error))
    axis.set_title("Bit-accurate predistorter complex error magnitude")
    axis.set_xlabel("Sample index")
    axis.set_ylabel("Absolute error")
    axis.grid(True)
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "fixed_dpd_error_magnitude.png", dpi=160)
    plt.close(figure)


def save_error_histogram(floating: np.ndarray, fixed: np.ndarray) -> None:
    error = fixed - floating
    figure, axis = plt.subplots(figsize=(8.6, 4.8))
    axis.hist(np.concatenate((error.real, error.imag)), bins=100)
    axis.set_title("Bit-accurate DPD component-error distribution")
    axis.set_xlabel("Fixed minus floating component")
    axis.set_ylabel("Count")
    axis.grid(True)
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "fixed_dpd_error_histogram.png", dpi=160)
    plt.close(figure)


def save_psd_plot(float_pa: np.ndarray, fixed_pa: np.ndarray, sample_rate_hz: float) -> None:
    frequency, float_psd = welch_psd_db(float_pa, sample_rate_hz)
    _, fixed_psd = welch_psd_db(fixed_pa, sample_rate_hz)
    figure, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(frequency / 1e6, float_psd, label="Floating DPD + PA")
    axis.plot(frequency / 1e6, fixed_psd, label="Fixed DPD + PA", linestyle="--")
    axis.set_title("PA output PSD after floating and fixed DPD")
    axis.set_xlabel("Frequency (MHz)")
    axis.set_ylabel("Relative PSD (dB)")
    axis.set_ylim(-100, 5)
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "fixed_dpd_pa_psd.png", dpi=160)
    plt.close(figure)


def save_internal_range_plot(result, config) -> None:
    labels = ["Accumulator I", "Accumulator Q"]
    values = [
        result.statistics.maximum_absolute_accumulator_i,
        result.statistics.maximum_absolute_accumulator_q,
    ]
    maximum = config.formats.accumulator.maximum_integer
    percentages = [100.0 * value / maximum for value in values]
    figure, axis = plt.subplots(figsize=(7.6, 4.8))
    axis.bar(labels, percentages)
    axis.set_title("Maximum accumulator utilization")
    axis.set_ylabel("Percent of positive full scale")
    axis.grid(True, axis="y")
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "fixed_dpd_accumulator_utilization.png", dpi=160)
    plt.close(figure)


def main() -> int:
    create_output_directories()
    fixed_config = load_fixed_point_config()
    waveform_config = load_waveform_config()
    pa_config = load_pa_config()
    training_config = load_dpd_training_config()

    waveform_path = VECTORS_DIR / "ofdm_float_reference.npz"
    coefficient_path = VECTORS_DIR / "dpd_quantized_coefficients.npz"
    floating_path = VECTORS_DIR / "dpd_float_reference.npz"
    for path in (waveform_path, coefficient_path, floating_path):
        if not path.exists():
            raise FileNotFoundError(f"Required input is missing: {path}")

    with np.load(waveform_path) as data:
        input_samples = np.asarray(data["samples"], dtype=np.complex128)
        reference_symbols = np.asarray(data["frequency_symbols"], dtype=np.complex128)
        active_bin_indices = np.asarray(data["active_bin_indices"], dtype=np.int64)

    with np.load(coefficient_path) as data:
        coefficient_i = np.asarray(data["coefficient_i"], dtype=np.int64)
        coefficient_q = np.asarray(data["coefficient_q"], dtype=np.int64)

    with np.load(floating_path) as data:
        floating_predistorted = np.asarray(data["predistorted_samples"], dtype=np.complex128)
        floating_pa_output = np.asarray(data["dpd_pa_output"], dtype=np.complex128)

    input_i, input_q, input_saturation_count = quantize_input_samples(
        input_samples,
        fixed_config,
    )
    result = apply_fixed_dpd(
        input_i,
        input_q,
        coefficient_i,
        coefficient_q,
        config=fixed_config,
        trace_length=512,
    )
    fixed_predistorted = result.output_complex(fixed_config)
    fixed_pa_output = apply_pa(fixed_predistorted, pa_config).output_samples

    target_gain = training_config.target.linear_gain
    occupied_bandwidth_hz = (
        waveform_config.ofdm.active_subcarriers
        * waveform_config.report.sample_rate_hz
        / waveform_config.ofdm.ifft_size
    )

    floating_metrics = json.loads(
        (RESULTS_DIR / "dpd_metrics.json").read_text(encoding="utf-8")
    )

    fixed_best_gain = best_fit_complex_gain(input_samples, fixed_pa_output)
    fixed_target_nmse = nmse_db(input_samples, fixed_pa_output, gain=target_gain)
    fixed_best_nmse = nmse_db(input_samples, fixed_pa_output)
    fixed_evm = equalized_ofdm_evm(
        fixed_pa_output,
        reference_symbols,
        active_bin_indices,
        waveform_config,
    )
    fixed_acpr = adjacent_channel_power_ratio_db(
        fixed_pa_output,
        waveform_config.report.sample_rate_hz,
        occupied_bandwidth_hz,
    )

    difference = fixed_predistorted - floating_predistorted
    output_lsb = 2.0 ** (-fixed_config.formats.output.fractional_bits)

    metrics = {
        "model": "bit_accurate_memory_polynomial",
        "sample_count": int(input_samples.size),
        "coefficient_count": int(coefficient_i.size),
        "input_quantization_saturation_count": input_saturation_count,
        "basis_saturation_count": result.statistics.basis_saturation_count,
        "output_saturation_count": result.statistics.output_saturation_count,
        "maximum_absolute_accumulator_i": result.statistics.maximum_absolute_accumulator_i,
        "maximum_absolute_accumulator_q": result.statistics.maximum_absolute_accumulator_q,
        "accumulator_positive_full_scale": fixed_config.formats.accumulator.maximum_integer,
        "fixed_vs_float_predistorter_raw_nmse_db": raw_nmse_db(
            floating_predistorted,
            fixed_predistorted,
        ),
        "fixed_vs_float_predistorter_rms_complex_error": float(
            np.sqrt(np.mean(np.abs(difference) ** 2))
        ),
        "fixed_vs_float_predistorter_maximum_complex_error": float(
            np.max(np.abs(difference))
        ),
        "fixed_vs_float_maximum_component_error_lsb": float(
            max(np.max(np.abs(difference.real)), np.max(np.abs(difference.imag)))
            / output_lsb
        ),
        "fixed_dpd_pa_best_fit_gain_real": fixed_best_gain.real,
        "fixed_dpd_pa_best_fit_gain_imag": fixed_best_gain.imag,
        "floating_dpd_pa_target_nmse_db": floating_metrics["dpd_pa_target_nmse_db"],
        "fixed_dpd_pa_target_nmse_db": fixed_target_nmse,
        "target_nmse_degradation_db": (
            fixed_target_nmse - floating_metrics["dpd_pa_target_nmse_db"]
        ),
        "floating_dpd_pa_best_fit_nmse_db": floating_metrics["dpd_pa_best_fit_nmse_db"],
        "fixed_dpd_pa_best_fit_nmse_db": fixed_best_nmse,
        "best_fit_nmse_degradation_db": (
            fixed_best_nmse - floating_metrics["dpd_pa_best_fit_nmse_db"]
        ),
        "floating_dpd_pa_ofdm_evm_percent": floating_metrics["dpd_pa_ofdm_evm_percent"],
        "fixed_dpd_pa_ofdm_evm_percent": fixed_evm,
        "floating_dpd_pa_acpr_db": floating_metrics["dpd_pa_acpr_db"],
        "fixed_dpd_pa_acpr_db": fixed_acpr,
    }

    trace_payload = {}
    if result.trace is not None:
        trace_payload = {
            "trace_magnitude_squared": result.trace.magnitude_squared,
            "trace_magnitude_fourth": result.trace.magnitude_fourth,
            "trace_basis_i": result.trace.basis_i,
            "trace_basis_q": result.trace.basis_q,
            "trace_term_i": result.trace.term_i,
            "trace_term_q": result.trace.term_q,
            "trace_accumulator_i": result.trace.accumulator_i,
            "trace_accumulator_q": result.trace.accumulator_q,
        }

    np.savez_compressed(
        VECTORS_DIR / "dpd_fixed_reference.npz",
        input_i=input_i,
        input_q=input_q,
        coefficient_i=coefficient_i,
        coefficient_q=coefficient_q,
        output_i=result.output_i,
        output_q=result.output_q,
        fixed_predistorted=fixed_predistorted,
        fixed_pa_output=fixed_pa_output,
        **trace_payload,
    )

    metrics_path = RESULTS_DIR / "fixed_dpd_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    save_overlay_plot(floating_predistorted, fixed_predistorted)
    save_error_plot(floating_predistorted, fixed_predistorted)
    save_error_histogram(floating_predistorted, fixed_predistorted)
    save_psd_plot(
        floating_pa_output,
        fixed_pa_output,
        waveform_config.report.sample_rate_hz,
    )
    save_internal_range_plot(result, fixed_config)

    print(json.dumps(metrics, indent=2))
    print(f"Fixed reference: {VECTORS_DIR / 'dpd_fixed_reference.npz'}")
    print(f"Fixed metrics: {metrics_path}")
    print(f"Plots: {PLOTS_DIR}")
    print("FIXED_DPD_MODEL_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
