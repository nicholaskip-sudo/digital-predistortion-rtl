"""Print the canonical DPD model specification."""
from dpd.config import load_project_config
from dpd.model_spec import build_coefficient_map

def main() -> int:
    config = load_project_config()
    print(f"Project: {config.project_name} {config.project_version}")
    print(f"Algorithm: {config.algorithm.model}")
    print(f"Memory depth: {config.algorithm.memory_depth}")
    print(f"Polynomial orders: {config.algorithm.polynomial_orders}")
    print(f"Complex coefficient count: {config.algorithm.coefficient_count}")
    print()
    print("INDEX  MEMORY  ORDER  BASIS TERM")
    print("-----  ------  -----  -----------------------------")
    for term in build_coefficient_map(config.algorithm):
        print(f"{term.coefficient_index:5d}  {term.memory_index:6d}  "
              f"{term.polynomial_order:5d}  {term.label}")
    print("\nMODEL_SPEC_PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
