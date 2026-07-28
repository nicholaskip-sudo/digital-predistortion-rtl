# Numerical Baseline Specification

## External sample format

Input and output I/Q components use signed 16-bit Q1.15.

- Integer range: -32768 through 32767
- Real range: -1.0 through 1 - 2^-15

## Coefficient format

Coefficient components use signed 24-bit Q8.16.

- Integer range: -8388608 through 8388607
- Real range: -128.0 through 127.99998474121094
- Resolution: 2^-16

## Internal basis format

All order-1, order-3, and order-5 complex basis components are converted to signed
24-bit Q4.20 before coefficient multiplication.

## Product and accumulator formats

- Real products: signed 48-bit Q12.36
- Complex products: signed 49-bit Q13.36
- Accumulator: signed 54-bit Q18.36

## Matching rule

The RTL is compared against the bit-accurate Python model using exact signed integer
equality after latency alignment.

rtl_i == expected_i
rtl_q == expected_q


## Rounding and overflow

- Precision reduction: nearest, ties away from zero
- Basis conversion: saturate
- Coefficient quantization: saturate
- Accumulator overflow: error
- Final output: saturate to Q1.15
