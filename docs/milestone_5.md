# Milestone 5 - Fixed-Point Numerical Specification

## Goal

Freeze every fixed-point width, binary point, shift, rounding rule, and overflow rule
before writing the bit-accurate model or RTL arithmetic.

## Main result

Floating-point training proved that the original 18-bit Q3.15 coefficient format was
not viable. It is replaced by 24-bit Q8.16.

## Tasks

1. Define external and internal number formats.
2. Define exact order-1, order-3, and order-5 basis shifts.
3. Define complex-product width growth.
4. Define accumulator width.
5. Define output rounding and saturation.
6. Quantize the trained coefficients and measure quantization error.
7. Analyze empirical and theoretical basis ranges.
8. Verify Python and SystemVerilog constants independently.

## Generated outputs

vectors/dpd_quantized_coefficients.npz
reports/results/fixed_point_range_analysis.json
reports/plots/fixed_point_coefficient_quantization.png
reports/plots/fixed_point_basis_ranges.png
reports/logs/dpd_fixed_spec.log

## Exit criteria

- All Python tests pass.
- No trained coefficient saturates.
- Selected coefficient format represents the largest trained coefficient.
- Accumulator integer width exceeds the calculated requirement.
- Python prints 'FIXED_POINT_SPEC_PASS'.
- DSim prints 'DPD_FIXED_SPEC_PASS'.
- DSim runner prints 'MILESTONE_5_FIXED_SPEC_CHECK_PASS'.
