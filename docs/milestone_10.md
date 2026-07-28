# Milestone 10 - Warning-Clean RTL Baseline

## Goal

Preserve exact arithmetic behavior while removing all known DSim warnings from the
DPD core regressions.

## Warnings removed

MultiBlockWrite
LatchInferred
AlwaysFFNba
ReadMemAddr

## RTL correction

The combinational datapath assigns explicit defaults to every intermediate array
element and scalar before performing the arithmetic. This removes ambiguity for
simulation and synthesis tools without changing calculated values.

## Testbench corrections

- '$readmemh' uses start and finish addresses based on 'sample_count'.
- Temporary blocking assignments were removed from the 'always_ff' scoreboard.
- Every persistent clocked variable uses nonblocking assignment.

## Runner enforcement

The short and full runners treat any of the four warning classes as failure.

## Expected markers

MILESTONE_10_RTL_SHORT_WARNING_CLEAN_PASS
MILESTONE_10_RTL_FULL_WARNING_CLEAN_PASS

