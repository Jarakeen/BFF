from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .resource_cost_modifiers import (
    ActionCostModifier,
    ActionCostModifierSet,
    CostModifierOperation,
)
from .resource_costs import BaseActionCost, ResourceType


@dataclass(frozen=True)
class FinalResourceCost:
    """Final cost charged to one resource pool for an ESO action."""

    resource: ResourceType
    base_amount: float
    flat_reduction: float
    percent_reduction: float
    raw_amount: float
    final_amount: int
    applied_modifiers: tuple[ActionCostModifier, ...]


@dataclass(frozen=True)
class FinalActionCost:
    """Per-resource resolved action cost after verified static reductions."""

    base_cost: BaseActionCost
    resource_costs: tuple[FinalResourceCost, ...]

    def for_resource(self, resource: ResourceType) -> FinalResourceCost:
        for cost in self.resource_costs:
            if cost.resource is resource:
                return cost
        raise ValueError(f"Action does not consume resource: {resource.value}")


def _round_half_up(value: float) -> int:
    return int(Decimal(str(value)).to_integral_value(rounding=ROUND_HALF_UP))


def calculate_final_action_cost(
    base_cost: BaseActionCost,
    modifiers: ActionCostModifierSet = ActionCostModifierSet(),
    *,
    skill_line: str | None = None,
) -> FinalActionCost:
    """Resolve verified ESO static ability-cost reductions per resource.

    Current live tooltip observations verify this reduction path for ordinary
    ability costs::

        round_half_up((base_cost - flat_reduction) * (1 - percent_reduction))

    Flat reductions are therefore applied before percentage reductions. Each
    consumed resource is calculated independently so a Magicka-only modifier
    cannot alter the Stamina side of a compound cost.

    Percentage cost increases are deliberately rejected here. Their ordering
    relative to reductions has not yet been verified by current live evidence.
    """

    applicable = modifiers.applicable_to(base_cost, skill_line=skill_line)

    increase_modifiers = tuple(
        modifier
        for modifier in applicable
        if modifier.operation is CostModifierOperation.PERCENT_INCREASE
    )
    if increase_modifiers:
        sources = ", ".join(modifier.source for modifier in increase_modifiers)
        raise ValueError(
            "Percentage action-cost increase ordering is not yet verified: "
            f"{sources}"
        )

    resolved: list[FinalResourceCost] = []
    for resource in base_cost.resources:
        resource_modifiers = tuple(
            modifier
            for modifier in applicable
            if resource in modifier.resources
        )
        flat = sum(
            modifier.value
            for modifier in resource_modifiers
            if modifier.operation is CostModifierOperation.FLAT_REDUCTION
        )
        percent = sum(
            modifier.value
            for modifier in resource_modifiers
            if modifier.operation is CostModifierOperation.PERCENT_REDUCTION
        )
        if percent > 1.0:
            raise ValueError(
                f"Combined {resource.value} cost reduction exceeds 100%: {percent!r}"
            )

        after_flat = max(0.0, float(base_cost.amount) - flat)
        raw = after_flat * (1.0 - percent)
        resolved.append(
            FinalResourceCost(
                resource=resource,
                base_amount=float(base_cost.amount),
                flat_reduction=flat,
                percent_reduction=percent,
                raw_amount=raw,
                final_amount=_round_half_up(raw),
                applied_modifiers=resource_modifiers,
            )
        )

    return FinalActionCost(
        base_cost=base_cost,
        resource_costs=tuple(resolved),
    )
