# Milestone 8 - First Bit-Accurate RTL DPD Core

## Goal

Implement the complete fixed-point DPD arithmetic in synthesizable SystemVerilog and
prove exact agreement with the Python model on the 512-sample debug set.

## Added files

rtl/dpd_core.sv
verification/dpd_core_tb.sv
simulation/filelist_dpd_core.f
simulation/run_dpd_core.py
docs/rtl_architecture.md

'rtl/dpd_pkg.sv' is replaced with a complete version containing the shared rounding
and saturation helpers.

## Pass markers

DPD_CORE_SHORT_PASS
MILESTONE_8_RTL_SHORT_CHECK_PASS

## Exit criteria

- Existing Python tests remain passing.
- Existing specification simulations remain passing.
- All 512 output samples match Python exactly.
- Ready/valid backpressure does not lose or duplicate samples.
- Output remains stable while stalled.
- A VCD waveform is generated.
