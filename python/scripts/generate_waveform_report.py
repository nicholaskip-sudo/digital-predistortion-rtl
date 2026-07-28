"""Generate deterministic OFDM data and presentation-ready waveform plots."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from dpd.project_paths import PLOTS_DIR, RESULTS_DIR, VECTORS_DIR, create_output_directories
from dpd.spectrum import welch_psd_db
from dpd.waveform import generate_ofdm, normalize_signal, papr_db, rms_magnitude
from dpd.waveform_config import load_waveform_config


def save_time_domain_plot(samples: np.ndarray) -> None:
    """Plot the first 512 I/Q samples."""

    display_count = min(512, samples.size)
    sample_index = np.arange(display_count)

    figure, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(sample_index, samples[:display_count].real, label="I")
    axis.plot(sample_index, samples[:display_count].imag, label="Q")
    axis.set_title("Normalized OFDM complex envelope")
    axis.set_xlabel("Sample index")
    axis.set_ylabel("Amplitude")
    axis.grid(True)
    axis.legend()
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "ofdm_time_domain.png", dpi=160)
    plt.close(figure)


def save_constellation_plot(symbols: np.ndarray) -> None:
    """Plot the generated QAM constellation."""

    flattened = symbols.reshape(-1)
    display_count = min(5000, flattened.size)

    figure, axis = plt.subplots(figsize=(6.4, 6.4))
    axis.scatter(
        flattened[:display_count].real,
        flattened[:display_count].imag,
        s=8,
        alpha=0.35,
    )
    axis.set_title("Generated 64-QAM symbols")
    axis.set_xlabel("In-phase")
    axis.set_ylabel("Quadrature")
    axis.set_aspect("equal", adjustable="box")
    axis.grid(True)
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "qam_constellation.png", dpi=160)
    plt.close(figure)


def save_psd_plot(
    samples: np.ndarray,
    sample_rate_hz: float,
) -> None:
    """Plot a normalized centered Welch PSD."""

    frequency_hz, psd_db = welch_psd_db(
        samples,
        sample_rate_hz=sample_rate_hz,
    )

    figure, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(frequency_hz / 1e6, psd_db)
    axis.set_title("OFDM power spectral density")
    axis.set_xlabel("Frequency (MHz)")
    axis.set_ylabel("Relative PSD (dB)")
    axis.set_ylim(-100, 5)
    axis.grid(True)
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "ofdm_psd.png", dpi=160)
    plt.close(figure)


def save_magnitude_histogram(samples: np.ndarray) -> None:
    """Plot the complex-envelope magnitude distribution."""

    figure, axis = plt.subplots(figsize=(8.4, 4.8))
    axis.hist(np.abs(samples), bins=80)
    axis.set_title("OFDM envelope magnitude distribution")
    axis.set_xlabel("Magnitude")
    axis.set_ylabel("Sample count")
    axis.grid(True)
    figure.tight_layout()
    figure.savefig(PLOTS_DIR / "ofdm_magnitude_histogram.png", dpi=160)
    plt.close(figure)


def main() -> int:
    """Generate vectors, metrics, and plots."""

    create_output_directories()
    config = load_waveform_config()
    rng = np.random.default_rng(config.seed)

    generated = generate_ofdm(
        config=config.ofdm,
        qam_order=config.qam.order,
        rng=rng,
    )
    samples = normalize_signal(
        generated.samples,
        mode=config.normalization.mode,
        target=config.normalization.target,
    )

    np.savez_compressed(
        VECTORS_DIR / "ofdm_float_reference.npz",
        samples=samples,
        frequency_symbols=generated.frequency_symbols,
        active_bin_indices=generated.active_bin_indices,
    )

    metrics = {
        "seed": config.seed,
        "qam_order": config.qam.order,
        "symbol_count": config.ofdm.symbol_count,
        "base_fft_size": config.ofdm.base_fft_size,
        "ifft_size": config.ofdm.ifft_size,
        "active_subcarriers": config.ofdm.active_subcarriers,
        "oversampling": config.ofdm.oversampling,
        "cyclic_prefix_samples": config.ofdm.cyclic_prefix_samples,
        "sample_count": int(samples.size),
        "sample_rate_hz": config.report.sample_rate_hz,
        "normalization_mode": config.normalization.mode,
        "normalization_target": config.normalization.target,
        "rms_magnitude": rms_magnitude(samples),
        "peak_magnitude": float(np.max(np.abs(samples))),
        "papr_db": papr_db(samples),
    }

    metrics_path = RESULTS_DIR / "waveform_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    save_time_domain_plot(samples)
    save_constellation_plot(generated.frequency_symbols)
    save_psd_plot(samples, config.report.sample_rate_hz)
    save_magnitude_histogram(samples)

    print(json.dumps(metrics, indent=2))
    print(f"Waveform data: {VECTORS_DIR / 'ofdm_float_reference.npz'}")
    print(f"Metrics: {metrics_path}")
    print(f"Plots: {PLOTS_DIR}")
    print("WAVEFORM_REPORT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
