# Digital Predistortion Portfolio Project

This repository will contain:

- A floating-point Python DPD model
- A bit-accurate Python golden-reference model
- Synthesizable SystemVerilog RTL
- A UVM verification environment
- Altair DSim automation
- Waveforms, numerical plots, and regression reports

## Current checkpoint

**Milestone 0 - Development environment and smoke tests**

The current design is intentionally a small counter. Its purpose is to prove that Python,
SystemVerilog, DSim, assertions, waveform dumping, logging, and VS Code tasks work before
DPD arithmetic is introduced.

## Repository layout

digital-predistortion/
├── .vscode/                 VS Code settings and tasks
├── docs/                    Design documentation
├── python/
│   ├── dpd/                 Python package
│   ├── scripts/             Executable Python workflows
│   └── tests/               Pytest tests
├── rtl/                     Synthesizable SystemVerilog
├── verification/            Testbenches and later UVM code
├── simulation/              DSim file lists and runners
├── vectors/                 Python-generated golden vectors
└── reports/
    ├── logs/
    ├── plots/
    ├── results/
    └── waves/

## Prerequisites

- Python 3.11 or newer
- Altair DSim available as the 'dsim' command
- Visual Studio Code
- Git

Verify DSim from a terminal:

dsim -version

## 1. Create the Python environment

### Linux

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

### Windows PowerShell

py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

After creating the environment, open the repository folder in VS Code and select the
'.venv' interpreter if VS Code does not select it automatically.

## 2. Run the Python checks

python -m pytest
python python/scripts/python_smoke.py

Expected results:

- All Pytest tests pass.
- 'reports/plots/python_smoke.png' is created.

## 3. Run the DSim smoke simulation

python simulation/run_smoke.py

The runner invokes DSim using the equivalent command:

dsim \
  -F simulation/filelist_smoke.f \
  -top work.smoke_tb \
  -timescale 1ns/1ps \
  +acc \
  -waves reports/waves/dsim_smoke.vcd \
  -l reports/logs/dsim_smoke.log

Expected results:

- The terminal prints 'DSIM_SMOKE_PASS'.
- The process exits with status zero.
- 'reports/logs/dsim_smoke.log' is created.
- 'reports/waves/dsim_smoke.vcd' is created.

To skip waveform generation:

python simulation/run_smoke.py --no-waves

To use a non-default DSim executable:

python simulation/run_smoke.py --dsim /path/to/dsim

You can also set the 'DSIM_BIN' environment variable.

## 4. Run from VS Code

Open **Terminal → Run Task** and select:

- 'Python: Run unit tests'
- 'Python: Generate smoke plot'
- 'DSim: Show version'
- 'DSim: Run smoke simulation'
- 'Milestone 0: Run all checks'

## Smoke-test behavior

The SystemVerilog test:

1. Holds the counter in reset.
2. Enables it for ten clock cycles.
3. Checks that the result is ten.
4. Disables it and checks that the count holds.
5. Uses concurrent assertions for increment and hold behavior.
6. Prints 'DSIM_SMOKE_PASS' only after every check succeeds.

## Milestone 0 exit criteria

Milestone 0 is complete when:

- 'python -m pytest' passes.
- The Python smoke plot is generated.
- 'python simulation/run_smoke.py' prints 'DSIM_SMOKE_PASS'.
- The DSim log and VCD waveform exist.
- The same commands run from VS Code tasks.
