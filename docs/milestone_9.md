# Milestone 9 - Full RTL Arithmetic Regression

## Goal

Promote the first 512-sample RTL test into a clean, reusable regression harness and
prove exact agreement across the complete 36,864-sample OFDM dataset.

## Testbench cleanup

The earlier testbench initialized driver variables in one block and updated them in a
clocked block. DSim correctly warned that these variables had multiple procedural
writers.

The replacement testbench follows a strict ownership model:

- Reset generator owns only 'rst_n'.
- Combinational input driver owns 'in_valid', 'in_i', and 'in_q'.
- Combinational backpressure generator owns 'out_ready'.
- One clocked block owns all counters and scoreboard state.

The full run must contain no 'MultiBlockWrite' warning.

## Parameterized regression

The same testbench supports both datasets through plusargs:

+VECTOR_DIR=<directory>
+TEST_NAME=<name>
+SAMPLE_COUNT=<count>

## Regression modes

### Short

Dataset:  vectors/rtl/ofdm_short
Samples:  512
Waveform: enabled


### Full

Dataset:  vectors/rtl/ofdm_nominal
Samples:  36864
Waveform: disabled

The full VCD is intentionally disabled because dumping the complete combinational
datapath for tens of thousands of samples would create a large file and obscure the
actual arithmetic-regression objective.

## Generated result

reports/results/rtl_full_regression.json

The result records sample count, cycle count, measured latency, throughput under
deterministic backpressure, and exact-integer-match status.
