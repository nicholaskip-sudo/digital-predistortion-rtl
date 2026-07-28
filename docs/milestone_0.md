# Milestone 0 - Environment and Toolchain Baseline

## Objective

Prove the development toolchain before introducing DPD algorithm complexity.

## Why a counter is used

A counter exercises the essential RTL and verification mechanisms:

- Clock and active-low reset
- Sequential SystemVerilog logic
- Parameterization
- Immediate assertions
- Concurrent SystemVerilog assertions
- Testbench stimulus
- Pass/fail exit behavior
- Waveform generation

If this test fails, the cause is likely installation, licensing, command-line configuration,
file paths, or simulator behavior-not DPD mathematics.

## Checkpoint M0-A - Python

### Goal

Verify that the Python package imports and that NumPy, Matplotlib, and Pytest work.

### Command

python -m pytest
python python/scripts/python_smoke.py


### Pass criteria

- Every test passes.
- 'PYTHON_SMOKE_PASS' is printed.
- 'reports/plots/python_smoke.png' exists.

## Checkpoint M0-B - DSim

### Goal

Verify that DSim can compile, elaborate, and run a SystemVerilog design in one invocation.

### Command

python simulation/run_smoke.py


### Pass criteria

- 'DSIM_SMOKE_PASS' appears.
- 'MILESTONE_0_DSIM_CHECK_PASS' appears.
- DSim exits with status zero.
- A log is created.
- A VCD waveform is created.

## Checkpoint M0-C - VS Code

### Goal

Verify that the terminal commands are reproducible through workspace tasks.

### Procedure

1. Open the repository root in VS Code.
2. Select the '.venv' Python interpreter.
3. Open **Terminal → Run Task**.
4. Run 'Milestone 0: Run all checks'.

### Pass criteria

All dependent tasks finish successfully.

## Completion record

Record the following after the checks:


Python version:
Pytest result:
DSim version:
DSim smoke result:
Waveform path:
Host operating system:
Date:

