"""Load and validate the project-wide DPD configuration."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml
from dpd.project_paths import PROJECT_ROOT

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "dpd_config.yaml"

@dataclass(frozen=True)
class FixedPointFormat:
    width: int
    fractional_bits: int
    signed: bool

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Fixed-point width must be greater than zero.")
        if self.fractional_bits < 0 or self.fractional_bits >= self.width:
            raise ValueError("Fractional bits must be in the range 0..width-1.")

    @property
    def integer_bits(self) -> int:
        return self.width - self.fractional_bits

@dataclass(frozen=True)
class AlgorithmConfig:
    model: str
    memory_depth: int
    polynomial_orders: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.model != "memory_polynomial":
            raise ValueError(f"Unsupported algorithm model: {self.model!r}")
        if self.memory_depth <= 0:
            raise ValueError("Memory depth must be greater than zero.")
        if not self.polynomial_orders:
            raise ValueError("At least one polynomial order is required.")
        if len(set(self.polynomial_orders)) != len(self.polynomial_orders):
            raise ValueError("Polynomial orders must be unique.")
        if tuple(sorted(self.polynomial_orders)) != self.polynomial_orders:
            raise ValueError("Polynomial orders must be in ascending order.")
        if any(order <= 0 or order % 2 == 0 for order in self.polynomial_orders):
            raise ValueError("Polynomial orders must be positive odd integers.")

    @property
    def coefficient_count(self) -> int:
        return self.memory_depth * len(self.polynomial_orders)

@dataclass(frozen=True)
class InterfaceConfig:
    protocol: str
    complex_representation: str
    reset_name: str
    reset_active_low: bool
    reset_asynchronous: bool
    input_samples_per_clock: int
    output_samples_per_clock: int

    def __post_init__(self) -> None:
        if self.protocol != "ready_valid":
            raise ValueError("The MVP protocol must be ready_valid.")
        if self.complex_representation != "separate_i_q":
            raise ValueError("The MVP uses separate I and Q ports.")
        if self.input_samples_per_clock != 1 or self.output_samples_per_clock != 1:
            raise ValueError("The MVP processes one complex sample per clock.")

@dataclass(frozen=True)
class VerificationConfig:
    exact_integer_match: bool
    long_regression_sample_count: int

    def __post_init__(self) -> None:
        if not self.exact_integer_match:
            raise ValueError("Exact integer matching is required.")
        if self.long_regression_sample_count <= 0:
            raise ValueError("Regression sample count must be positive.")

@dataclass(frozen=True)
class ProjectConfig:
    project_name: str
    project_version: str
    algorithm: AlgorithmConfig
    sample_format: FixedPointFormat
    coefficient_format: FixedPointFormat
    interface: InterfaceConfig
    verification: VerificationConfig

def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Configuration section {key!r} must be a mapping.")
    return value

def load_project_config(path: Path | str = DEFAULT_CONFIG_PATH) -> ProjectConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"DPD configuration file not found: {config_path}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("The YAML root must be a mapping.")

    project = _mapping(raw, "project")
    algorithm = _mapping(raw, "algorithm")
    sample = _mapping(raw, "sample_format")
    coefficient = _mapping(raw, "coefficient_format")
    interface = _mapping(raw, "interface")
    verification = _mapping(raw, "verification")

    return ProjectConfig(
        project_name=str(project["name"]),
        project_version=str(project["version"]),
        algorithm=AlgorithmConfig(
            model=str(algorithm["model"]),
            memory_depth=int(algorithm["memory_depth"]),
            polynomial_orders=tuple(int(x) for x in algorithm["polynomial_orders"]),
        ),
        sample_format=FixedPointFormat(
            width=int(sample["width"]),
            fractional_bits=int(sample["fractional_bits"]),
            signed=bool(sample["signed"]),
        ),
        coefficient_format=FixedPointFormat(
            width=int(coefficient["width"]),
            fractional_bits=int(coefficient["fractional_bits"]),
            signed=bool(coefficient["signed"]),
        ),
        interface=InterfaceConfig(
            protocol=str(interface["protocol"]),
            complex_representation=str(interface["complex_representation"]),
            reset_name=str(interface["reset_name"]),
            reset_active_low=bool(interface["reset_active_low"]),
            reset_asynchronous=bool(interface["reset_asynchronous"]),
            input_samples_per_clock=int(interface["input_samples_per_clock"]),
            output_samples_per_clock=int(interface["output_samples_per_clock"]),
        ),
        verification=VerificationConfig(
            exact_integer_match=bool(verification["exact_integer_match"]),
            long_regression_sample_count=int(verification["long_regression_sample_count"]),
        ),
    )
