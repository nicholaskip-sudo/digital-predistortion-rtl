# Bit-Accurate Python DPD Model

## Purpose

This model is the authoritative numerical reference for RTL. It does not use floating-point operations inside the DPD datapath. All basis generation, complex multiplication,
accumulation, rounding, and saturation are performed on integers.

## Processing order

For every accepted complex sample:

1. Shift the three-sample I/Q delay line.
2. Calculate magnitude squared for each memory tap.
3. Calculate magnitude fourth.
4. Generate order-1, order-3, and order-5 basis components.
5. Round each nonlinear basis term to Q4.20.
6. Multiply each basis term by its Q8.16 complex coefficient.
7. Accumulate all nine Q13.36 complex terms in Q18.36.
8. Round the accumulator right by 21 bits.
9. Saturate the final I and Q components to Q1.15.

## Delay initialization

Samples before index zero are exact complex zero. This rule must be duplicated by the RTL
sample delay line after reset.

## Exact rounding

All right shifts use nearest rounding with exact ties away from zero.

## Overflow behavior

- Basis: saturate and count
- Real product: error if the full product does not fit
- Complex term: error if add/subtract growth does not fit
- Accumulator: error if any addition exceeds Q18.36
- Output: saturate and count

## RTL comparison contract

The future scoreboard compares the signed integers directly:

rtl_out_i == python_output_i
rtl_out_q == python_output_q


No tolerance is used for the RTL correctness regression.
