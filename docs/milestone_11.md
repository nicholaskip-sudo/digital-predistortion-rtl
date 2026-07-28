# Milestone 11 - First UVM Regression

## Goal

Introduce a structured UVM 1.2 verification environment without changing the DUT or
the Python golden-reference contract.

## Dataset

vectors/rtl/ofdm_short
512 complex samples
9 complex coefficients

## Exact comparison

The UVM scoreboard compares every transferred output using four-state exact equality.

## Expected markers

DPD_UVM_SHORT_PASS samples=512 mismatches=0
UVM_ERROR :    0
UVM_FATAL :    0
MILESTONE_11_UVM_SHORT_CHECK_PASS


## Generated outputs

reports/logs/dpd_uvm_short.log
reports/waves/dpd_uvm_short.vcd

