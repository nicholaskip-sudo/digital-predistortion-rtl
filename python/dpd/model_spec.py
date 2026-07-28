"""Canonical Memory Polynomial coefficient ordering."""
from __future__ import annotations
from dataclasses import dataclass
from dpd.config import AlgorithmConfig

@dataclass(frozen=True)
class BasisTerm:
    coefficient_index: int
    memory_index: int
    polynomial_order: int

    @property
    def label(self) -> str:
        if self.polynomial_order == 1:
            return f"x[n-{self.memory_index}]"
        power = self.polynomial_order - 1
        return f"x[n-{self.memory_index}]*|x[n-{self.memory_index}]|^{power}"

def build_coefficient_map(config: AlgorithmConfig) -> tuple[BasisTerm, ...]:
    terms: list[BasisTerm] = []
    for memory_index in range(config.memory_depth):
        for order_slot, polynomial_order in enumerate(config.polynomial_orders):
            terms.append(BasisTerm(
                coefficient_index=memory_index * len(config.polynomial_orders) + order_slot,
                memory_index=memory_index,
                polynomial_order=polynomial_order,
            ))
    return tuple(terms)

def coefficient_index(
    config: AlgorithmConfig,
    memory_index: int,
    polynomial_order: int,
) -> int:
    if memory_index < 0 or memory_index >= config.memory_depth:
        raise IndexError(f"Memory index {memory_index} is out of range.")
    try:
        order_slot = config.polynomial_orders.index(polynomial_order)
    except ValueError as error:
        raise ValueError(f"Polynomial order {polynomial_order} is not configured.") from error
    return memory_index * len(config.polynomial_orders) + order_slot
