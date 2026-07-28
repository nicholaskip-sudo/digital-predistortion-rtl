"""Export bit-accurate Python results into DSim-compatible golden vectors."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from dpd.config import load_project_config
from dpd.fixed_point_config import load_fixed_point_config
from dpd.model_spec import build_coefficient_map
from dpd.project_paths import VECTORS_DIR
from dpd.vector_export import (
    GoldenVectorSet,
    export_vector_set,
    sha256_file,
    verify_vector_set_roundtrip,
    write_memh,
)


RTL_VECTOR_ROOT = VECTORS_DIR / "rtl"
IntegerArray = NDArray[np.int64]


def _require_integer_array(
    data: np.lib.npyio.NpzFile,
    name: str,
) -> IntegerArray:
    """Load one required NPZ array and require integer-compatible data."""

    if name not in data:
        raise ValueError(f"Fixed reference is missing required array {name!r}.")

    array = np.asarray(data[name])

    if np.iscomplexobj(array):
        raise ValueError(
            f"Required integer array {name!r} unexpectedly contains complex values."
        )

    if not np.issubdtype(array.dtype, np.integer):
        rounded = np.rint(array)
        if not np.array_equal(array, rounded):
            raise ValueError(
                f"Required integer array {name!r} contains non-integer values."
            )
        array = rounded

    return np.asarray(array, dtype=np.int64)


def _load_fixed_reference(path: Path) -> dict[str, np.ndarray]:
    """Load the fixed reference without discarding complex report arrays.

    Only arrays consumed as RTL integers are converted to int64. Other arrays
    retain their original dtype, including complex floating-point report data.
    """

    if not path.exists():
        raise FileNotFoundError(
            "Bit-accurate reference is missing. "
            "Run generate_fixed_dpd_report.py first."
        )

    required_integer_names = (
        "input_i",
        "input_q",
        "coefficient_i",
        "coefficient_q",
        "output_i",
        "output_q",
    )

    with np.load(path) as data:
        reference: dict[str, np.ndarray] = {
            name: np.asarray(data[name]).copy()
            for name in data.files
        }

        for name in required_integer_names:
            reference[name] = _require_integer_array(data, name)

    return reference


def _vectors_from_reference(
    reference: dict[str, np.ndarray],
    sample_slice: slice,
) -> GoldenVectorSet:
    """Construct one vector set from a slice of the fixed reference."""

    return GoldenVectorSet(
        input_i=np.asarray(reference["input_i"][sample_slice], dtype=np.int64),
        input_q=np.asarray(reference["input_q"][sample_slice], dtype=np.int64),
        expected_i=np.asarray(
            reference["output_i"][sample_slice],
            dtype=np.int64,
        ),
        expected_q=np.asarray(
            reference["output_q"][sample_slice],
            dtype=np.int64,
        ),
        coefficient_i=np.asarray(
            reference["coefficient_i"],
            dtype=np.int64,
        ),
        coefficient_q=np.asarray(
            reference["coefficient_q"],
            dtype=np.int64,
        ),
    )


def _trace_matrix(
    reference: dict[str, np.ndarray],
    key: str,
) -> np.ndarray | None:
    """Return one trace as a two-dimensional sample-by-column matrix."""

    if key not in reference:
        return None

    array = np.asarray(reference[key])

    if array.ndim == 0:
        raise ValueError(f"Trace array {key!r} must have a sample dimension.")
    if np.iscomplexobj(array):
        raise ValueError(f"Trace array {key!r} must contain integer values.")

    if not np.issubdtype(array.dtype, np.integer):
        rounded = np.rint(array)
        if not np.array_equal(array, rounded):
            raise ValueError(
                f"Trace array {key!r} contains non-integer values."
            )
        array = rounded

    return np.asarray(array, dtype=np.int64).reshape(array.shape[0], -1)


def _trace_column_names(prefix: str, column_count: int) -> list[str]:
    """Create stable CSV column names for one trace matrix."""

    if column_count == 1:
        return [prefix]
    return [f"{prefix}_{column}" for column in range(column_count)]


def _write_trace_csv(
    path: Path,
    reference: dict[str, np.ndarray],
    row_count: int,
) -> bool:
    """Write available scalar and multidimensional integer traces.

    Multidimensional traces are flattened after the sample dimension. For
    example, a magnitude trace with three memory positions becomes:

        magnitude_squared_0
        magnitude_squared_1
        magnitude_squared_2
    """

    trace_specs = (
        ("trace_magnitude_squared", "magnitude_squared"),
        ("trace_magnitude_fourth", "magnitude_fourth"),
        ("trace_basis_i", "basis_i"),
        ("trace_basis_q", "basis_q"),
        ("trace_term_i", "term_i"),
        ("trace_term_q", "term_q"),
        ("trace_accumulator_i", "accumulator_i"),
        ("trace_accumulator_q", "accumulator_q"),
    )

    matrices: list[tuple[str, np.ndarray]] = []
    for key, prefix in trace_specs:
        matrix = _trace_matrix(reference, key)
        if matrix is not None:
            matrices.append((prefix, matrix))

    if not matrices:
        return False

    count = min(
        row_count,
        *(int(matrix.shape[0]) for _, matrix in matrices),
    )

    headers = ["sample_index"]
    for prefix, matrix in matrices:
        headers.extend(_trace_column_names(prefix, matrix.shape[1]))

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)

        for sample_index in range(count):
            row: list[int] = [sample_index]
            for _, matrix in matrices:
                row.extend(
                    int(value)
                    for value in matrix[sample_index, :]
                )
            writer.writerow(row)

    return True


def _add_file_to_manifest(
    directory: Path,
    logical_name: str,
    filename: str,
) -> None:
    """Add a generated auxiliary file and checksum to a manifest."""

    manifest_path = directory / "manifest.json"
    file_path = directory / filename

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    if not file_path.exists():
        raise FileNotFoundError(f"Generated file not found: {file_path}")

    manifest: dict[str, Any] = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    files = manifest.setdefault("files", {})
    files[logical_name] = {
        "filename": filename,
        "sha256": sha256_file(file_path),
    }

    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def _generate_vector_io_smoke() -> None:
    """Generate known values for the DSim $readmemh smoke test."""

    output = RTL_VECTOR_ROOT / "vector_io_smoke"
    output.mkdir(parents=True, exist_ok=True)

    signed16 = np.asarray(
        [0, 1, -1, 32767, -32768, 0x1234, -0x1234, 123],
        dtype=np.int64,
    )
    signed24 = np.asarray(
        [
            0,
            1,
            -1,
            0x7FFFFF,
            -0x800000,
            0x123456,
            -0x123456,
            0x010000,
        ],
        dtype=np.int64,
    )

    write_memh(output / "signed16.hex", signed16, 16)
    write_memh(output / "signed24.hex", signed24, 24)

    manifest = {
        "schema_version": 1,
        "purpose": "DSim readmemh signed two's-complement compatibility",
        "signed16_values": signed16.tolist(),
        "signed24_values": signed24.tolist(),
        "files": {
            "signed16": {
                "filename": "signed16.hex",
                "width": 16,
                "word_count": int(signed16.size),
                "sha256": sha256_file(output / "signed16.hex"),
            },
            "signed24": {
                "filename": "signed24.hex",
                "width": 24,
                "word_count": int(signed24.size),
                "sha256": sha256_file(output / "signed24.hex"),
            },
        },
    }

    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    """Export the full, short, and vector-I/O regression datasets."""

    project = load_project_config()
    fixed = load_fixed_point_config()

    reference = _load_fixed_reference(
        VECTORS_DIR / "dpd_fixed_reference.npz"
    )

    coefficient_map = [
        {
            "index": term.coefficient_index,
            "memory_index": term.memory_index,
            "polynomial_order": term.polynomial_order,
            "label": term.label,
        }
        for term in build_coefficient_map(project.algorithm)
    ]

    common_metadata = {
        "project_version": project.project_version,
        "algorithm": project.algorithm.model,
        "memory_depth": project.algorithm.memory_depth,
        "polynomial_orders": list(project.algorithm.polynomial_orders),
        "coefficient_order": coefficient_map,
        "sample_fractional_bits": fixed.formats.sample.fractional_bits,
        "coefficient_fractional_bits": (
            fixed.formats.coefficient.fractional_bits
        ),
        "rounding_mode": fixed.rounding.mode,
        "output_overflow": fixed.overflow.output,
    }

    full_vectors = _vectors_from_reference(reference, slice(None))
    full_directory = RTL_VECTOR_ROOT / "ofdm_nominal"

    full_manifest = export_vector_set(
        output_directory=full_directory,
        test_name="ofdm_nominal",
        vectors=full_vectors,
        sample_width=fixed.formats.sample.width,
        coefficient_width=fixed.formats.coefficient.width,
        metadata=common_metadata,
        debug_row_count=1024,
    )

    verify_vector_set_roundtrip(
        full_directory,
        full_vectors,
        fixed.formats.sample.width,
        fixed.formats.coefficient.width,
    )

    short_count = min(512, full_vectors.sample_count)
    short_vectors = _vectors_from_reference(
        reference,
        slice(0, short_count),
    )
    short_directory = RTL_VECTOR_ROOT / "ofdm_short"

    short_manifest = export_vector_set(
        output_directory=short_directory,
        test_name="ofdm_short",
        vectors=short_vectors,
        sample_width=fixed.formats.sample.width,
        coefficient_width=fixed.formats.coefficient.width,
        metadata=common_metadata,
        debug_row_count=short_count,
    )

    verify_vector_set_roundtrip(
        short_directory,
        short_vectors,
        fixed.formats.sample.width,
        fixed.formats.coefficient.width,
    )

    trace_path = short_directory / "internal_trace.csv"
    if _write_trace_csv(
        trace_path,
        reference,
        short_count,
    ):
        _add_file_to_manifest(
            short_directory,
            logical_name="internal_trace",
            filename=trace_path.name,
        )

    _generate_vector_io_smoke()

    summary = {
        "rtl_vector_root": str(RTL_VECTOR_ROOT),
        "full_test": {
            "directory": str(full_directory),
            "sample_count": full_manifest["sample_count"],
            "coefficient_count": full_manifest["coefficient_count"],
        },
        "short_test": {
            "directory": str(short_directory),
            "sample_count": short_manifest["sample_count"],
            "coefficient_count": short_manifest["coefficient_count"],
        },
        "vector_io_smoke": str(RTL_VECTOR_ROOT / "vector_io_smoke"),
        "roundtrip_check": "exact_integer_match",
        "complex_report_arrays_preserved": True,
        "multidimensional_trace_export": True,
    }

    summary_path = RTL_VECTOR_ROOT / "vector_export_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    print("GOLDEN_VECTOR_EXPORT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
