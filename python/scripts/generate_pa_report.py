"""Apply the behavioral PA to the OFDM reference and create engineering plots."""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from dpd.metrics import (
    best_fit_complex_gain,
    evm_rms_percent,
    nmse_db,
    per_column_complex_gain,
)
from dpd.ofdm_analysis import demodulate_ofdm
from dpd.pa_config import load_pa_config
from dpd.pa_model import apply_pa, rapp_ampm_characteristic
from dpd.project_paths import PLOTS_DIR, RESULTS_DIR, VECTORS_DIR, create_output_directories
from dpd.spectrum import adjacent_channel_power_ratio_db, welch_psd_db
from dpd.waveform import papr_db, rms_magnitude
from dpd.waveform_config import load_waveform_config


def save_am_am_plot(pa_config) -> None:
    maximum_input = 1.0
    input_magnitude = np.linspace(
        0.0,
        maximum_input,
        pa_config.report.characterization_points,
    )
    output_magnitude, _ = rapp_ampm_characteristic(
        input_magnitude,
        pa_config.nonlinearity,
    )
    linear_output = pa_config.nonlinearity.small_signal_gain * input_magnitude

    figure, axis = plt.subplots(figsize=(7.2, 5.0))
    axis.plot(input_magnitude, output_magnitude, label="PA AM/AM")
    axis.plot(input_magnitude, linear_output, linestyle="--", label="Ideal linear gain")
    axis.set_title("PA AM/AM characteristic")
    axis.set_xlabel("Input magnitude")
    axis.set_ylabel("Output magnitude")
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "pa_am_am.png", dpi=160)
    plt.close(figure)


def save_am_pm_plot(pa_config) -> None:
    input_magnitude = np.linspace(
        0.0,
        1.0,
        pa_config.report.characterization_points,
    )
    _, phase_rad = rapp_ampm_characteristic(
        input_magnitude,
        pa_config.nonlinearity,
    )

    figure, axis = plt.subplots(figsize=(7.2, 5.0))
    axis.plot(input_magnitude, np.rad2deg(phase_rad))
    axis.set_title("PA AM/PM characteristic")
    axis.set_xlabel("Input magnitude")
    axis.set_ylabel("Phase rotation (degrees)")
    axis.grid(True)
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "pa_am_pm.png", dpi=160)
    plt.close(figure)


def save_time_plot(input_samples: np.ndarray, output_samples: np.ndarray) -> None:
    count = min(700, input_samples.size)
    sample_index = np.arange(count)
    figure, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(sample_index, np.abs(input_samples[:count]), label="PA input")
    axis.plot(sample_index, np.abs(output_samples[:count]), label="PA output")
    axis.set_title("PA envelope compression in time")
    axis.set_xlabel("Sample index")
    axis.set_ylabel("Magnitude")
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "pa_time_magnitude.png", dpi=160)
    plt.close(figure)


def save_psd_plot(input_samples: np.ndarray, output_samples: np.ndarray, sample_rate_hz: float) -> None:
    input_frequency, input_psd = welch_psd_db(input_samples, sample_rate_hz)
    output_frequency, output_psd = welch_psd_db(output_samples, sample_rate_hz)

    figure, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(input_frequency / 1e6, input_psd, label="PA input")
    axis.plot(output_frequency / 1e6, output_psd, label="PA output")
    axis.set_title("Spectral regrowth caused by the PA")
    axis.set_xlabel("Frequency (MHz)")
    axis.set_ylabel("Relative PSD (dB)")
    axis.set_ylim(-100, 5)
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "pa_psd_comparison.png", dpi=160)
    plt.close(figure)


def save_constellation_plot(reference_symbols: np.ndarray, equalized_symbols: np.ndarray) -> None:
    reference = reference_symbols.reshape(-1)
    observed = equalized_symbols.reshape(-1)
    count = min(6000, reference.size)

    figure, axis = plt.subplots(figsize=(6.5, 6.5))
    axis.scatter(reference[:count].real, reference[:count].imag, s=8, alpha=0.25, label="Ideal")
    axis.scatter(observed[:count].real, observed[:count].imag, s=8, alpha=0.25, label="After PA")
    axis.set_title("64-QAM constellation before and after PA")
    axis.set_xlabel("In-phase")
    axis.set_ylabel("Quadrature")
    axis.set_aspect("equal", adjustable="box")
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "pa_constellation_comparison.png", dpi=160)
    plt.close(figure)


def main() -> int:
    create_output_directories()
    waveform_config = load_waveform_config()
    pa_config = load_pa_config()

    input_path = VECTORS_DIR / "ofdm_float_reference.npz"
    if not input_path.exists():
        raise FileNotFoundError(
            "Missing OFDM input data. Run generate_waveform_report.py first."
        )

    with np.load(input_path) as data:
        input_samples = np.asarray(data["samples"], dtype=np.complex128)
        reference_symbols = np.asarray(data["frequency_symbols"], dtype=np.complex128)
        active_bin_indices = np.asarray(data["active_bin_indices"], dtype=np.int64)

    pa_result = apply_pa(input_samples, pa_config)
    output_symbols = demodulate_ofdm(
        pa_result.output_samples,
        waveform_config.ofdm,
        active_bin_indices,
    )

    carrier_gains = per_column_complex_gain(reference_symbols, output_symbols)
    equalized_symbols = output_symbols / carrier_gains[np.newaxis, :]

    global_gain = best_fit_complex_gain(input_samples, pa_result.output_samples)
    occupied_bandwidth_hz = (
        waveform_config.ofdm.active_subcarriers
        * waveform_config.report.sample_rate_hz
        / waveform_config.ofdm.ifft_size
    )

    metrics = {
        "model": pa_config.model,
        "sample_count": int(input_samples.size),
        "memory_taps": [
            {"real": tap.real, "imag": tap.imag}
            for tap in pa_config.memory.input_taps
        ],
        "configured_small_signal_gain": pa_config.nonlinearity.small_signal_gain,
        "configured_saturation_amplitude": pa_config.nonlinearity.saturation_amplitude,
        "configured_ampm_max_degrees": pa_config.nonlinearity.ampm_max_degrees,
        "best_fit_gain_real": global_gain.real,
        "best_fit_gain_imag": global_gain.imag,
        "best_fit_gain_magnitude": abs(global_gain),
        "time_domain_nmse_db": nmse_db(input_samples, pa_result.output_samples, global_gain),
        "time_domain_evm_percent": evm_rms_percent(input_samples, pa_result.output_samples, global_gain),
        "ofdm_evm_after_one_tap_equalization_percent": evm_rms_percent(
            reference_symbols.reshape(-1),
            equalized_symbols.reshape(-1),
            gain=1.0 + 0.0j,
        ),
        "input_rms_magnitude": rms_magnitude(input_samples),
        "output_rms_magnitude": rms_magnitude(pa_result.output_samples),
        "input_peak_magnitude": float(np.max(np.abs(input_samples))),
        "output_peak_magnitude": float(np.max(np.abs(pa_result.output_samples))),
        "input_papr_db": papr_db(input_samples),
        "output_papr_db": papr_db(pa_result.output_samples),
        "occupied_bandwidth_hz": occupied_bandwidth_hz,
        "input_acpr_db": adjacent_channel_power_ratio_db(
            input_samples,
            waveform_config.report.sample_rate_hz,
            occupied_bandwidth_hz,
        ),
        "output_acpr_db": adjacent_channel_power_ratio_db(
            pa_result.output_samples,
            waveform_config.report.sample_rate_hz,
            occupied_bandwidth_hz,
        ),
    }

    np.savez_compressed(
        VECTORS_DIR / "pa_output_float_reference.npz",
        input_samples=input_samples,
        memory_samples=pa_result.memory_samples,
        output_samples=pa_result.output_samples,
        reference_symbols=reference_symbols,
        output_symbols=output_symbols,
        equalized_symbols=equalized_symbols,
        active_bin_indices=active_bin_indices,
    )

    metrics_path = RESULTS_DIR / "pa_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    save_am_am_plot(pa_config)
    save_am_pm_plot(pa_config)
    save_time_plot(input_samples, pa_result.output_samples)
    save_psd_plot(input_samples, pa_result.output_samples, waveform_config.report.sample_rate_hz)
    save_constellation_plot(reference_symbols, equalized_symbols)

    print(json.dumps(metrics, indent=2))
    print(f"PA waveform data: {VECTORS_DIR / 'pa_output_float_reference.npz'}")
    print(f"PA metrics: {metrics_path}")
    print(f"PA plots: {PLOTS_DIR}")
    print("PA_REPORT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
