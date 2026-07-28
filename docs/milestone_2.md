# Milestone 2 - Communication Waveform Generator

## Goal

Produce repeatable complex-baseband waveforms and plots.

## Tasks

1. Load a dedicated waveform YAML configuration.
2. Generate QPSK, 16-QAM, and 64-QAM symbols.
3. Generate oversampled OFDM with symmetric occupied carriers.
4. Add RMS and peak normalization.
5. Calculate PAPR.
6. Add impulse, tone, ramp, and two-tone generators.
7. Generate time-domain, constellation, PSD, and magnitude-distribution plots.
8. Save deterministic floating-point waveform data.
9. Verify all behavior with Pytest.

## Generated outputs

vectors/ofdm_float_reference.npz
reports/results/waveform_metrics.json
reports/plots/ofdm_time_domain.png
reports/plots/qam_constellation.png
reports/plots/ofdm_psd.png
reports/plots/ofdm_magnitude_histogram.png


## Exit criteria

- All existing and new Python tests pass.
- The waveform script prints 'WAVEFORM_REPORT_PASS'.
- The generated sample count matches the configuration.
- Repeated runs with the same seed produce identical samples.
- RMS normalization reaches the configured target.
- PAPR is finite and positive.
- All four plots are generated.
