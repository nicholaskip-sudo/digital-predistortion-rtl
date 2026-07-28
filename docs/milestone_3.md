# Milestone 3 - Behavioral PA

## Goal

Create a repeatable PA model that produces gain compression, AM/PM rotation, memory,
constellation degradation, and spectral regrowth.

## Outputs

vectors/pa_output_float_reference.npz
reports/results/pa_metrics.json
reports/plots/pa_am_am.png
reports/plots/pa_am_pm.png
reports/plots/pa_time_magnitude.png
reports/plots/pa_psd_comparison.png
reports/plots/pa_constellation_comparison.png


## Exit criteria

- All tests pass.
- PA_REPORT_PASS is logged.
- The PA output is finite and deterministic.
- AM/AM compresses below the ideal linear response.
- AM/PM is monotonic and bounded.
- Output ACPR is worse than input ACPR.
- The PA output constellation visibly spreads after one-tap carrier equalization.
