# Golden Vector File Contract

## Purpose

The bit-accurate Python model is the authority for all RTL sample comparisons.
This contract defines how its signed integers are transferred into DSim.

## Directory structure

vectors/rtl/
├── ofdm_nominal/
│   ├── manifest.json
│   ├── input_i.hex
│   ├── input_q.hex
│   ├── expected_i.hex
│   ├── expected_q.hex
│   ├── coefficients_i.hex
│   ├── coefficients_q.hex
│   ├── samples_debug.csv
│   └── coefficients.csv
├── ofdm_short/
│   ├── the same vector files
│   └── internal_trace.csv
└── vector_io_smoke/
    ├── signed16.hex
    ├── signed24.hex
    └── manifest.json

## Hexadecimal encoding

- One word per line
- Uppercase hexadecimal
- No '0x' prefix
- Fixed width
- Two's-complement signed encoding

Examples for 16-bit values:

Decimal       Hex
0             0000
1             0001
-1            FFFF
32767         7FFF
-32768        8000


Examples for 24-bit values:

Decimal       Hex
0             000000
1             000001
-1            FFFFFF
8388607       7FFFFF
-8388608      800000


## Widths

Input I/Q       16 bits, Q1.15
Expected I/Q    16 bits, Q1.15
Coefficient I/Q 24 bits, Q8.16

## Manifest

Each regression set includes:

- Schema version
- Test name
- Sample count
- Coefficient count
- Data widths
- Algorithm parameters
- Coefficient ordering
- Rounding rule
- Overflow rule
- Per-file SHA-256 checksums

Pipeline latency remains 'null' until the integrated RTL architecture freezes it.

## Debug CSV files

CSV files are for humans and plotting. RTL must consume the hexadecimal files.

The short OFDM set also includes internal Python traces for later mismatch diagnosis.
