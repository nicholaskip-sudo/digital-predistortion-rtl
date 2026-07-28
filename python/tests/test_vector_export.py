"""Tests for hexadecimal golden-vector export."""

from __future__ import annotations

import json

import numpy as np
import pytest

from dpd.vector_export import (
    GoldenVectorSet,
    decode_twos_complement,
    encode_twos_complement,
    export_vector_set,
    hex_digit_count,
    read_memh,
    sha256_file,
    signed_limits,
    verify_vector_set_roundtrip,
    write_memh,
)


@pytest.mark.parametrize(
    ("width", "digits"),
    [(1, 1), (16, 4), (24, 6)],
)
def test_hex_digit_count(width: int, digits: int) -> None:
    assert hex_digit_count(width) == digits


@pytest.mark.parametrize(
    ("value", "width", "encoded"),
    [
        (0, 16, "0000"),
        (1, 16, "0001"),
        (-1, 16, "FFFF"),
        (32767, 16, "7FFF"),
        (-32768, 16, "8000"),
        (0x123456, 24, "123456"),
        (-0x123456, 24, "EDCBAA"),
    ],
)
def test_encode_twos_complement(
    value: int,
    width: int,
    encoded: str,
) -> None:
    assert encode_twos_complement(value, width) == encoded
    assert decode_twos_complement(encoded, width) == value


def test_signed_limits() -> None:
    assert signed_limits(16) == (-32768, 32767)
    assert signed_limits(24) == (-8388608, 8388607)


def test_out_of_range_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="outside signed 16-bit"):
        encode_twos_complement(32768, 16)


def test_signed16_roundtrip(tmp_path) -> None:
    values = np.asarray(
        [0, 1, -1, 32767, -32768, 4660, -4660],
        dtype=np.int64,
    )
    path = tmp_path / "signed16.hex"

    write_memh(path, values, 16)
    actual = read_memh(path, 16)

    np.testing.assert_array_equal(actual, values)


def test_signed24_roundtrip(tmp_path) -> None:
    values = np.asarray(
        [0, 1, -1, 8388607, -8388608, 0x123456, -0x123456],
        dtype=np.int64,
    )
    path = tmp_path / "signed24.hex"

    write_memh(path, values, 24)
    actual = read_memh(path, 24)

    np.testing.assert_array_equal(actual, values)


def test_comments_and_blank_lines_are_ignored(tmp_path) -> None:
    path = tmp_path / "comments.hex"
    path.write_text(
        "0001 // one\n\nFFFF # minus one\n",
        encoding="ascii",
    )

    actual = read_memh(path, 16)
    np.testing.assert_array_equal(actual, np.asarray([1, -1]))


def test_invalid_hex_token_reports_error(tmp_path) -> None:
    path = tmp_path / "bad.hex"
    path.write_text("NOT_HEX\n", encoding="ascii")

    with pytest.raises(ValueError, match="Invalid hexadecimal token"):
        read_memh(path, 16)


def test_vector_set_rejects_length_mismatch() -> None:
    vectors = GoldenVectorSet(
        input_i=np.asarray([1, 2]),
        input_q=np.asarray([1]),
        expected_i=np.asarray([1, 2]),
        expected_q=np.asarray([1, 2]),
        coefficient_i=np.asarray([1]),
        coefficient_q=np.asarray([1]),
    )

    with pytest.raises(ValueError, match="equal lengths"):
        vectors.validate()


def test_export_manifest_and_roundtrip(tmp_path) -> None:
    vectors = GoldenVectorSet(
        input_i=np.asarray([1, -1, 32767], dtype=np.int64),
        input_q=np.asarray([-2, 2, -32768], dtype=np.int64),
        expected_i=np.asarray([3, -3, 10], dtype=np.int64),
        expected_q=np.asarray([4, -4, -10], dtype=np.int64),
        coefficient_i=np.asarray([65536, -1], dtype=np.int64),
        coefficient_q=np.asarray([0, 2], dtype=np.int64),
    )

    manifest = export_vector_set(
        output_directory=tmp_path,
        test_name="unit_test",
        vectors=vectors,
        sample_width=16,
        coefficient_width=24,
        metadata={"seed": 7},
        debug_row_count=2,
    )

    assert manifest["sample_count"] == 3
    assert manifest["coefficient_count"] == 2
    assert manifest["metadata"]["seed"] == 7

    manifest_from_disk = json.loads(
        (tmp_path / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest_from_disk["test_name"] == "unit_test"

    for file_entry in manifest_from_disk["files"].values():
        filename = file_entry["filename"]
        assert (tmp_path / filename).exists()
        assert file_entry["sha256"] == sha256_file(tmp_path / filename)

    verify_vector_set_roundtrip(
        tmp_path,
        vectors,
        sample_width=16,
        coefficient_width=24,
    )
