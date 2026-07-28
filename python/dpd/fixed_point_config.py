"""Load and validate the fixed-point numerical specification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from dpd.project_paths import PROJECT_ROOT


DEFAULT_FIXED_POINT_CONFIG_PATH = (
    PROJECT_ROOT / "config" / "fixed_point_config.yaml"
)


@dataclass(frozen=True)
class NumericFormat:
    """A binary fixed-point storage format."""

    width: int
    fractional_bits: int
    signed: bool

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Width must be positive.")
        if self.fractional_bits < 0:
            raise ValueError("Fractional bits cannot be negative.")
        if self.fractional_bits >= self.width:
            raise ValueError("Fractional bits must be smaller than width.")

    @property
    def integer_bits(self) -> int:
        """Return non-fractional bits, including the sign bit when signed."""

        return self.width - self.fractional_bits

    @property
    def minimum_integer(self) -> int:
        """Return the smallest stored integer."""

        if self.signed:
            return -(1 << (self.width - 1))
        return 0

    @property
    def maximum_integer(self) -> int:
        """Return the largest stored integer."""

        if self.signed:
            return (1 << (self.width - 1)) - 1
        return (1 << self.width) - 1

    @property
    def minimum_real(self) -> float:
        """Return the smallest representable real value."""

        return self.minimum_integer / (1 << self.fractional_bits)

    @property
    def maximum_real(self) -> float:
        """Return the largest representable real value."""

        return self.maximum_integer / (1 << self.fractional_bits)


@dataclass(frozen=True)
class RoundingConfig:
    mode: str

    def __post_init__(self) -> None:
        if self.mode != "nearest_ties_away_from_zero":
            raise ValueError(
                "The MVP rounding mode must be nearest_ties_away_from_zero."
            )


@dataclass(frozen=True)
class OverflowConfig:
    basis: str
    coefficient: str
    accumulator: str
    output: str

    def __post_init__(self) -> None:
        valid = {"saturate", "error"}
        values = {
            "basis": self.basis,
            "coefficient": self.coefficient,
            "accumulator": self.accumulator,
            "output": self.output,
        }
        for name, value in values.items():
            if value not in valid:
                raise ValueError(
                    f"Overflow policy {name!r} must be saturate or error."
                )


@dataclass(frozen=True)
class FixedPointFormats:
    sample: NumericFormat
    magnitude_squared: NumericFormat
    magnitude_fourth: NumericFormat
    basis: NumericFormat
    coefficient: NumericFormat
    real_product: NumericFormat
    complex_term: NumericFormat
    accumulator: NumericFormat
    output: NumericFormat


@dataclass(frozen=True)
class FixedPointConfig:
    rounding: RoundingConfig
    overflow: OverflowConfig
    formats: FixedPointFormats

    def __post_init__(self) -> None:
        formats = self.formats

        if formats.sample != formats.output:
            raise ValueError("Input and output formats must match for the MVP.")

        if formats.magnitude_squared.fractional_bits != (
            2 * formats.sample.fractional_bits
        ):
            raise ValueError("Magnitude-squared fractional bits are inconsistent.")

        if formats.magnitude_fourth.fractional_bits != (
            2 * formats.magnitude_squared.fractional_bits
        ):
            raise ValueError("Magnitude-fourth fractional bits are inconsistent.")

        expected_product_fraction = (
            formats.basis.fractional_bits
            + formats.coefficient.fractional_bits
        )
        if formats.real_product.fractional_bits != expected_product_fraction:
            raise ValueError("Real-product fractional bits are inconsistent.")

        if formats.complex_term.fractional_bits != expected_product_fraction:
            raise ValueError("Complex-term fractional bits are inconsistent.")

        if formats.accumulator.fractional_bits != expected_product_fraction:
            raise ValueError("Accumulator fractional bits are inconsistent.")

        if formats.complex_term.width < formats.real_product.width + 1:
            raise ValueError(
                "Complex-term width needs one bit for add/subtract growth."
            )

        if formats.accumulator.width < formats.complex_term.width + 4:
            raise ValueError(
                "Accumulator needs at least four growth bits for nine terms."
            )

    @property
    def order1_basis_shift(self) -> int:
        """Left shift converting input Q format to the common basis format."""

        return (
            self.formats.basis.fractional_bits
            - self.formats.sample.fractional_bits
        )

    @property
    def order3_basis_right_shift(self) -> int:
        """Right shift converting x*|x|^2 to the common basis format."""

        raw_fraction = (
            self.formats.sample.fractional_bits
            + self.formats.magnitude_squared.fractional_bits
        )
        return raw_fraction - self.formats.basis.fractional_bits

    @property
    def order5_basis_right_shift(self) -> int:
        """Right shift converting x*|x|^4 to the common basis format."""

        raw_fraction = (
            self.formats.sample.fractional_bits
            + self.formats.magnitude_fourth.fractional_bits
        )
        return raw_fraction - self.formats.basis.fractional_bits

    @property
    def output_right_shift(self) -> int:
        """Right shift converting accumulator format to output format."""

        return (
            self.formats.accumulator.fractional_bits
            - self.formats.output.fractional_bits
        )


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Configuration section {key!r} must be a mapping.")
    return value


def _format(data: dict[str, Any]) -> NumericFormat:
    return NumericFormat(
        width=int(data["width"]),
        fractional_bits=int(data["fractional_bits"]),
        signed=bool(data["signed"]),
    )


def load_fixed_point_config(
    path: Path | str = DEFAULT_FIXED_POINT_CONFIG_PATH,
) -> FixedPointConfig:
    """Load and validate the fixed-point YAML specification."""

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Fixed-point configuration not found: {config_path}"
        )

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Fixed-point configuration root must be a mapping.")

    rounding_data = _mapping(raw, "rounding")
    overflow_data = _mapping(raw, "overflow")
    format_data = _mapping(raw, "formats")

    return FixedPointConfig(
        rounding=RoundingConfig(mode=str(rounding_data["mode"])),
        overflow=OverflowConfig(
            basis=str(overflow_data["basis"]),
            coefficient=str(overflow_data["coefficient"]),
            accumulator=str(overflow_data["accumulator"]),
            output=str(overflow_data["output"]),
        ),
        formats=FixedPointFormats(
            sample=_format(_mapping(format_data, "sample")),
            magnitude_squared=_format(
                _mapping(format_data, "magnitude_squared")
            ),
            magnitude_fourth=_format(
                _mapping(format_data, "magnitude_fourth")
            ),
            basis=_format(_mapping(format_data, "basis")),
            coefficient=_format(_mapping(format_data, "coefficient")),
            real_product=_format(_mapping(format_data, "real_product")),
            complex_term=_format(_mapping(format_data, "complex_term")),
            accumulator=_format(_mapping(format_data, "accumulator")),
            output=_format(_mapping(format_data, "output")),
        ),
    )
