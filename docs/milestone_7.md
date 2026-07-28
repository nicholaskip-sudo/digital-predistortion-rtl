# Milestone 7 - Golden Reference Vectors

## Goal

Create a stable and verifiable file interface between Python, SystemVerilog, DSim,
and the future UVM scoreboard.

## Tasks

1. Encode signed 16-bit and 24-bit values in fixed-width hexadecimal.
2. Prove exact Python write/read round trips.
3. Export the complete 36,864-sample OFDM regression.
4. Export a 512-sample debug regression.
5. Export all nine complex coefficients.
6. Produce JSON manifests and SHA-256 checksums.
7. Produce human-readable CSV files.
8. Verify DSim '$readmemh' signed interpretation.

## Pass markers

GOLDEN_VECTOR_EXPORT_PASS
VECTOR_IO_SMOKE_PASS
MILESTONE_7_VECTOR_IO_CHECK_PASS

