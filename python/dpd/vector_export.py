"""Export and validate simulator-compatible fixed-point vector files."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import json
from pathlib import Path
import string
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray


IntegerArray = NDArray[np.int64]


@dataclass(frozen=True)
class GoldenVectorSet:
    """Integer arrays forming one complete DPD regression dataset."""

    input_i: IntegerArray
    input_q: IntegerArray
    expected_i: IntegerArray
    expected_q: IntegerArray
    coefficient_i: IntegerArray
    coefficient_q: IntegerArray

    def validate(self) -> None:
        """Validate sample and coefficient dimensions."""

        sample_lengths = {
            int(np.asarray(self.input_i).size),
            int(np.asarray(self.input_q).size),
            int(np.asarray(self.expected_i).size),
            int(np.asarray(self.expected_q).size),
        }
        if len(sample_lengths) != 1:
            raise ValueError("Input and expected sample arrays must have equal lengths.")

        coefficient_lengths = {
            int(np.asarray(self.coefficient_i).size),
            int(np.asarray(self.coefficient_q).size),
        }
        if len(coefficient_lengths) != 1:
            raise ValueError("Coefficient I and Q arrays must have equal lengths.")

        if next(iter(sample_lengths)) <= 0:
            raise ValueError("A vector set must contain at least one sample.")
        if next(iter(coefficient_lengths)) <= 0:
            raise ValueError("A vector set must contain at least one coefficient.")

    @property
    def sample_count(self) -> int:
        """Return the number of complex samples."""

        self.validate()
        return int(np.asarray(self.input_i).size)

    @property
    def coefficient_count(self) -> int:
        """Return the number of complex coefficients."""

        self.validate()
        return int(np.asarray(self.coefficient_i).size)


def signed_limits(width: int) -> tuple[int, int]:
    """Return the legal signed integer range for a bit width."""

    if width <= 0:
        raise ValueError("Bit width must be positive.")
    return -(1 << (width - 1)), (1 << (width - 1)) - 1


def hex_digit_count(width: int) -> int:
    """Return hexadecimal digits required to store a bit width."""

    if width <= 0:
        raise ValueError("Bit width must be positive.")
    return (width + 3) // 4


def encode_twos_complement(value: int, width: int) -> str:
    """Encode one signed integer as fixed-width uppercase hexadecimal."""

    minimum, maximum = signed_limits(width)
    integer_value = int(value)

    if integer_value < minimum or integer_value > maximum:
        raise ValueError(
            f"Value {integer_value} is outside signed {width}-bit range "
            f"{minimum}..{maximum}."
        )

    mask = (1 << width) - 1
    encoded = integer_value & mask
    return f"{encoded:0{hex_digit_count(width)}X}"


def decode_twos_complement(text: str, width: int) -> int:
    """Decode one hexadecimal word as a signed integer.

    Underscores are accepted as visual separators, but every remaining
    character must be a hexadecimal digit. Character validity is checked
    before width so malformed input receives the most useful error message.
    """

    token = text.strip().replace("_", "")
    if not token:
        raise ValueError("Hexadecimal token cannot be empty.")

    if any(character not in string.hexdigits for character in token):
        raise ValueError(f"Invalid hexadecimal token: {token!r}")

    digit_count = hex_digit_count(width)
    if len(token) > digit_count:
        raise ValueError(
            f"Token {token!r} exceeds {digit_count} hexadecimal digits."
        )

    unsigned_value = int(token, 16)

    if unsigned_value >= (1 << width):
        raise ValueError(f"Token {token!r} exceeds {width} bits.")

    sign_bit = 1 << (width - 1)
    if unsigned_value & sign_bit:
        return unsigned_value - (1 << width)
    return unsigned_value


def write_memh(
    path: Path | str,
    values: IntegerArray | list[int],
    width: int,
) -> None:
    """Write one fixed-width two's-complement word per line."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    array = np.asarray(values, dtype=np.int64).reshape(-1)
    if array.size == 0:
        raise ValueError("Cannot write an empty memory file.")

    lines = [encode_twos_complement(int(value), width) for value in array]
    output_path.write_text("\n".join(lines) + "\n", encoding="ascii")


def read_memh(path: Path | str, width: int) -> IntegerArray:
    """Read a simple one-word-per-line hexadecimal memory file.

    Blank lines and trailing // or # comments are ignored.
    """

    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Memory file not found: {input_path}")

    values: list[int] = []
    for line_number, raw_line in enumerate(
        input_path.read_text(encoding="ascii").splitlines(),
        start=1,
    ):
        token = raw_line.split("//", 1)[0].split("#", 1)[0].strip()
        if not token:
            continue

        try:
            values.append(decode_twos_complement(token, width))
        except ValueError as error:
            raise ValueError(
                f"{input_path}:{line_number}: {error}"
            ) from error

    if not values:
        raise ValueError(f"Memory file contains no data: {input_path}")

    return np.asarray(values, dtype=np.int64)


def sha256_file(path: Path | str) -> str:
    """Return a lowercase SHA-256 digest for a file."""

    file_path = Path(path)
    digest = hashlib.sha256()

    with file_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def _write_samples_csv(
    path: Path,
    vectors: GoldenVectorSet,
    row_count: int,
) -> None:
    """Write a human-readable sample preview."""

    count = min(row_count, vectors.sample_count)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "sample_index",
                "input_i",
                "input_q",
                "expected_i",
                "expected_q",
            ]
        )
        for index in range(count):
            writer.writerow(
                [
                    index,
                    int(vectors.input_i[index]),
                    int(vectors.input_q[index]),
                    int(vectors.expected_i[index]),
                    int(vectors.expected_q[index]),
                ]
            )


def _write_coefficients_csv(path: Path, vectors: GoldenVectorSet) -> None:
    """Write all complex coefficients in decimal integer form."""

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["coefficient_index", "coefficient_i", "coefficient_q"])
        for index in range(vectors.coefficient_count):
            writer.writerow(
                [
                    index,
                    int(vectors.coefficient_i[index]),
                    int(vectors.coefficient_q[index]),
                ]
            )


def export_vector_set(
    output_directory: Path | str,
    test_name: str,
    vectors: GoldenVectorSet,
    sample_width: int,
    coefficient_width: int,
    metadata: Mapping[str, Any],
    debug_row_count: int = 1024,
) -> dict[str, Any]:
    """Export one complete vector set and return its manifest."""

    vectors.validate()

    if not test_name.strip():
        raise ValueError("Test name cannot be empty.")
    if debug_row_count <= 0:
        raise ValueError("Debug row count must be positive.")

    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)

    files = {
        "input_i": ("input_i.hex", vectors.input_i, sample_width),
        "input_q": ("input_q.hex", vectors.input_q, sample_width),
        "expected_i": ("expected_i.hex", vectors.expected_i, sample_width),
        "expected_q": ("expected_q.hex", vectors.expected_q, sample_width),
        "coefficient_i": (
            "coefficients_i.hex",
            vectors.coefficient_i,
            coefficient_width,
        ),
        "coefficient_q": (
            "coefficients_q.hex",
            vectors.coefficient_q,
            coefficient_width,
        ),
    }

    for _, (filename, values, width) in files.items():
        write_memh(output_path / filename, values, width)

    _write_samples_csv(
        output_path / "samples_debug.csv",
        vectors,
        debug_row_count,
    )
    _write_coefficients_csv(
        output_path / "coefficients.csv",
        vectors,
    )

    file_manifest: dict[str, Any] = {}
    for logical_name, (filename, values, width) in files.items():
        file_path = output_path / filename
        file_manifest[logical_name] = {
            "filename": filename,
            "width": width,
            "word_count": int(np.asarray(values).size),
            "sha256": sha256_file(file_path),
        }

    for logical_name, filename in {
        "samples_debug": "samples_debug.csv",
        "coefficients_csv": "coefficients.csv",
    }.items():
        file_path = output_path / filename
        file_manifest[logical_name] = {
            "filename": filename,
            "sha256": sha256_file(file_path),
        }

    manifest = {
        "schema_version": 1,
        "test_name": test_name,
        "sample_count": vectors.sample_count,
        "coefficient_count": vectors.coefficient_count,
        "sample_width": sample_width,
        "coefficient_width": coefficient_width,
        "hex_encoding": "fixed_width_twos_complement_uppercase",
        "line_format": "one_word_per_line",
        "expected_latency_cycles": None,
        "metadata": dict(metadata),
        "files": file_manifest,
    }

    manifest_path = output_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return manifest


def verify_vector_set_roundtrip(
    output_directory: Path | str,
    vectors: GoldenVectorSet,
    sample_width: int,
    coefficient_width: int,
) -> None:
    """Read exported files and prove exact integer reconstruction."""

    output_path = Path(output_directory)

    checks = [
        ("input_i.hex", vectors.input_i, sample_width),
        ("input_q.hex", vectors.input_q, sample_width),
        ("expected_i.hex", vectors.expected_i, sample_width),
        ("expected_q.hex", vectors.expected_q, sample_width),
        ("coefficients_i.hex", vectors.coefficient_i, coefficient_width),
        ("coefficients_q.hex", vectors.coefficient_q, coefficient_width),
    ]

    for filename, expected, width in checks:
        actual = read_memh(output_path / filename, width)
        np.testing.assert_array_equal(
            actual,
            np.asarray(expected, dtype=np.int64).reshape(-1),
        )
