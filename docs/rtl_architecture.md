# First Bit-Accurate RTL Architecture

## Scope

This milestone implements the complete nine-term fixed-point Memory Polynomial in
SystemVerilog and compares 512 samples exactly against the Python reference.

## Interface

The core uses a one-stage elastic ready/valid output register.

Input accepted:  in_valid && in_ready
Output consumed: out_valid && out_ready

The entire arithmetic state stalls while an unconsumed output is present.

## Latency and throughput

- Latency: one registered output cycle after an accepted input
- Sustained throughput: one complex sample per clock when 'out_ready' remains high
- Backpressure: stalls input acceptance and delay-line updates

## Arithmetic

The SystemVerilog implementation follows the frozen numerical contract:

Input              Q1.15
Magnitude squared  UQ2.30
Magnitude fourth   UQ4.60
Basis              Q4.20
Coefficient        Q8.16
Complex term       Q13.36
Accumulator        Q18.36
Output             Q1.15


Every precision reduction uses nearest rounding with ties away from zero.

## Verification

The short test:

- Loads 512 Python-generated input samples
- Loads nine complex coefficients
- Loads 512 exact expected outputs
- Applies deterministic output backpressure
- Checks every transferred output with case inequality
- Asserts output stability during backpressure
- Asserts input stability until acceptance
