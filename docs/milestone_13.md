# Milestone 13 - Randomized Stress, Reset Recovery, and Negative Testing

## Goal

Extend the verified DPD core beyond fixed golden-vector playback with deterministic
randomized traffic, interruption recovery, run-time coefficient changes, and
expected-failure assertion tests.

## Positive UVM stress test

The stress environment is independent of the Milestone 12 golden-vector environment.
It uses coefficient configurations whose expected behavior is exact and simple:

- Identity mode: coefficient 0 is '+1.0' in Q8.16; all other coefficients are zero.
  The expected output equals the accepted input sample.
- Zero mode: all coefficients are zero. The expected output is '(0, 0)'.

This allows the scoreboard to predict every result dynamically while samples, gaps,
and output backpressure are randomized.

## Stress phases

1. Drive 1,024 samples in identity mode.
2. After at least 257 accepted inputs, wait for a backpressured output and assert
   reset for three cycles.
3. Confirm the pending output is flushed and traffic recovers.
4. Update coefficients to zero without reset and drive 512 samples.
5. Update coefficients back to identity and drive 512 recovery samples.

Total accepted input transactions per seed: 2,048.

## Deterministic randomization

A 32-bit LFSR generates:

- Complex input samples
- Zero-to-three-cycle input gaps
- Randomized output-ready behavior

Periodic directed minimum, maximum, zero, and sign-boundary samples are mixed into
the stream.

## Required stress closure

The test requires:

- Zero data mismatches
- Zero unexpected outputs
- At least one reset interruption
- At least one output discarded by reset
- Identity and zero coefficient modes exercised
- At least three coefficient updates
- Input idle cycles exercised
- Output backpressure exercised
- Exact accounting: checked outputs plus reset-dropped outputs equals accepted inputs

## Negative protocol tests

Two expected-failure tests deliberately violate the interface rules:

1. Change input data while 'in_valid && !in_ready'.
2. Change output data while 'out_valid && !out_ready'.

The regression passes only when the corresponding SVA assertion fires. An
unexpectedly successful negative simulation is treated as failure.

## Pass markers

MILESTONE_13_UVM_STRESS_CHECK_PASS
MILESTONE_13_UVM_STRESS_MATRIX_PASS
MILESTONE_13_NEGATIVE_PROTOCOL_CHECK_PASS
MILESTONE_13_STRESS_REGRESSION_PASS

