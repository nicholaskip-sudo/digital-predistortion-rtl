# Milestone 6 - Bit-Accurate Python Reference

## Goal

Implement the exact integer datapath that the SystemVerilog RTL must reproduce.

## Deliverables

python/dpd/fixed_dpd.py
python/tests/test_fixed_dpd.py
python/scripts/generate_fixed_dpd_report.py
vectors/dpd_fixed_reference.npz
reports/results/fixed_dpd_metrics.json
reports/plots/fixed_dpd_float_overlay.png
reports/plots/fixed_dpd_error_magnitude.png
reports/plots/fixed_dpd_error_histogram.png
reports/plots/fixed_dpd_pa_psd.png
reports/plots/fixed_dpd_accumulator_utilization.png

## Exit criteria

- All Python tests pass.
- Identity and memory-delay directed tests are bit exact.
- No basis saturation occurs for the OFDM regression.
- No accumulator overflow occurs.
- Fixed-point DPD retains useful PA linearization performance.
- The script prints 'FIXED_DPD_MODEL_PASS'.
- The NPZ dataset contains input, coefficient, output, and internal-trace integers.
