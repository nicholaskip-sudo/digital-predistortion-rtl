# Pre-UVM Verification Plan

## Current verification layers

| Layer | Purpose |
|---|---|
| Python unit tests | Algorithm, formats, quantization, vectors |
| DSim package tests | Shared constants and coefficient ordering |
| Vector I/O smoke | '$readmemh' and signed two's-complement agreement |
| Short RTL regression | 512 samples with VCD and internal debug |
| Full RTL regression | 36,864 exact output comparisons |

## Protocol properties

The RTL regression checks:

1. Output data remains stable while 'out_valid && !out_ready'.
2. Input data remains stable while 'in_valid && !in_ready'.
3. Output valid requires a previously accepted unmatched input.
4. The output count equals the input count.
5. Every output I/Q integer equals the Python reference.

## Regression entry point

python .\simulation\run_rtl_regressions.py

The combined pass marker is:

PRE_UVM_RTL_REGRESSION_PASS

This becomes the stable baseline before introducing UVM classes.
