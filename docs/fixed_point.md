# Fixed-Point Numerical Specification

## Design change after floating-point training

The original provisional coefficient format was signed 18-bit Q3.15, with a real range
of approximately -4 to +4.

Floating-point training produced a maximum coefficient magnitude of approximately 32.6
and a maximum real component of approximately 31.4. Q3.15 therefore cannot represent
the trained model.

The coefficient format is changed to signed 24-bit Q8.16:

- Range: -128 to approximately +128
- Resolution: 2^-16
- Sufficient headroom for the current coefficients
- No coefficient saturation expected

## Fixed formats

| Quantity | Width | Fraction | Signed | Conventional name |
|---|---:|---:|---:|---|
| Input/output component | 16 | 15 | yes | Q1.15 |
| Magnitude squared | 32 | 30 | no | UQ2.30 |
| Magnitude fourth | 64 | 60 | no | UQ4.60 |
| Common basis component | 24 | 20 | yes | Q4.20 |
| Coefficient component | 24 | 16 | yes | Q8.16 |
| Real product | 48 | 36 | yes | Q12.36 |
| Complex term | 49 | 36 | yes | Q13.36 |
| Accumulator | 54 | 36 | yes | Q18.36 |
| Final output | 16 | 15 | yes | Q1.15 |

The 'Qm.n' names count the sign bit inside 'm'.

## Basis generation

Input I and Q are signed Q1.15 integers.

Magnitude squared:


mag_sq = I*I + Q*Q


This is unsigned UQ2.30.

Magnitude fourth:


mag_fourth = mag_sq * mag_sq


This is unsigned UQ4.60.

All three polynomial orders are converted to one signed Q4.20 basis format.

Order 1:


basis1 = input << 5


Order 3:


raw3 = input * mag_sq
basis3 = round(raw3 / 2^25)


Order 5:


raw5 = input * mag_fourth
basis5 = round(raw5 / 2^55)


Each basis conversion saturates to signed 24 bits, although the theoretical Q1.15 input
range fits inside Q4.20 without saturation.

## Complex coefficient multiplication

Basis and coefficients use:

basis       Q4.20
coefficient Q8.16


Each real multiplication produces Q12.36 in 48 bits.

For basis 'b = br + j*bi' and coefficient 'c = cr + j*ci':


real = br*cr - bi*ci
imag = br*ci + bi*cr


The add/subtract result uses 49 bits with 36 fractional bits.

## Accumulation

Nine complex terms are accumulated into signed 54-bit Q18.36 values.

Accumulator overflow is treated as a design error. It must not wrap or silently
saturate during normal operation.

## Final output conversion

The accumulator has 36 fractional bits and output has 15.


output = round(accumulator / 2^21)


The rounded value saturates to signed Q1.15.

## Rounding mode

Every precision reduction uses round-to-nearest with exact half-way cases rounded away
from zero.

For right shift 's':

positive: (value + 2^(s-1)) >> s
negative: -((abs(value) + 2^(s-1)) >> s)


This rule will be implemented identically in Python and SystemVerilog.
