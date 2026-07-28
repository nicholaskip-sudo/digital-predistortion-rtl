# Milestone 4 - Floating-Point DPD

## Goal

Train and evaluate a nine-coefficient Memory Polynomial predistorter.

## Tasks

1. Build the canonical Memory Polynomial basis matrix.
2. Evaluate complex coefficients in memory-major, order-minor order.
3. Implement normalized ridge least squares.
4. Implement safeguarded Indirect Learning Architecture training.
5. Hold out 25 percent of the waveform for validation.
6. Apply component-wise output saturation compatible with Q1.15.
7. Compare PA without DPD, same-gain simple backoff, and DPD plus PA.
8. Generate NMSE, EVM, ACPR, convergence, coefficient, constellation, PSD, and error evidence.

## Generated outputs

vectors/dpd_float_reference.npz
reports/results/dpd_metrics.json
reports/plots/dpd_training_convergence.png
reports/plots/dpd_psd_comparison.png
reports/plots/dpd_constellation_comparison.png
reports/plots/dpd_time_magnitude.png
reports/plots/dpd_error_magnitude.png
reports/plots/dpd_coefficient_magnitudes.png

## Exit criteria

- All Python tests pass.
- At least one ILA candidate is accepted.
- DPD best-fit NMSE improves by at least 8 dB relative to the original PA result.
- DPD target NMSE improves by at least 5 dB relative to same-gain simple backoff.
- OFDM EVM improves relative to both baselines.
- ACPR improves relative to the original PA output.
- The report prints 'DPD_REPORT_PASS'.
