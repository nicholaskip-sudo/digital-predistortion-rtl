# Milestone 12 - Full UVM Regression and Functional Coverage

## Goal

Run the complete 36,864-sample OFDM dataset through the UVM 1.2 environment, preserve
exact bit-accurate checking, and add functional coverage for data and ready/valid
behavior.

## Regression modes

### Short debug test

Test:       dpd_short_uvm_test
Dataset:    vectors/rtl/ofdm_short
Samples:    512
Waveform:   enabled


### Full coverage test

Test:       dpd_full_uvm_test
Dataset:    vectors/rtl/ofdm_nominal
Samples:    36864
Waveform:   disabled


The full test avoids VCD generation so the long regression remains focused on
scoreboarding and coverage.

## Required pass markers

DPD_UVM_FULL_PASS samples=36864 mismatches=0
DPD_FUNCTIONAL_COVERAGE_PASS
UVM_WARNING :    0
UVM_ERROR :    0
UVM_FATAL :    0
MILESTONE_12_UVM_FULL_COVERAGE_CHECK_PASS


## Generated artifacts

reports/logs/dpd_uvm_full.log
reports/results/uvm_full_regression.json
reports/coverage/uvm_full/metrics.db
reports/coverage/uvm_full/html/


The HTML report is generated when 'dcreport' is present in the DSim installation.
The SQLite coverage database remains the authoritative coverage artifact.
