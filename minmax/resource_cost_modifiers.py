from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .resource_costs import BaseActionCost, ResourceType


class CostModifierOperation(str, Enum):
    """Supported static operations that may alter an action's resource cost.

    Phase 4 deliberately models modifier identity before implementing ESO's
    final ordering/rounding rules. Values are positive magnitudes; the operation
    states whether that magnitude reduces or increases cost.
    """

    FLAT_REDUCTION = "flat_reduction"
    PERCENT_REDUCTION = "percent_reduction"
    PERCENT_INCREASE = "percent_increase"


@dataclass(frozen=True)
class ActionCostModifier:
    """One auditable modifier that may apply to a resolved ability cost.

    Resource filters are required because ESO has resource-specific cost
    reductions. Optional ability/skill-line filters support narrower passives
    without hardcoding name checks into the cost engine.

    This contract intentionally contains no combat trigger state. Effects that
    require "after", "while", "when", proc state, repeated casts, etc. belong
    in the conditional/combat-state layer rather than static cost inputs.
    """

    source: str
    operation: CostModifierOperation
    value: float
    resources: tuple[ResourceType, ...]
    ability_ids: tuple[int, ...] = ()
    skill_lines: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.source or "").strip():
            raise ValueError("Action cost modifier requires a source")
        if self.value < 0:
            raise ValueError(f"Action cost modifier value cannot be negative: {self.value}")
        if not self.resources:
            raise ValueError("Action cost modifier must target at least one resource")
        if self.operation in {
            CostModifierOperation.PERCENT_REDUCTION,
            CostModifierOperation.PERCENT_INCREASE,
        } and self.value > 1.0:
            raise ValueError(
                "Percentage action cost modifiers use decimal ratios; "
                f"received {self.value!r}"
            )

    def applies_to(
        self,
        cost: BaseActionCost,
        *,
        skill_line: str | None = None,
    ) -> bool:
        if not any(resource in self.resources for resource in cost.resources):
            return False

        if self.ability_ids and cost.ability_id not in self.ability_ids:
            return False

        if self.skill_lines:
            normalized = str(skill_line or "").strip().casefold()
            allowed = {value.strip().casefold() for value in self.skill_lines if value.strip()}
            if normalized not in allowed:
                return False

        return True


@dataclass(frozen=True)
class ActionCostModifierSet:
    """Static cost modifiers retained with provenance and eligibility intact."""

    modifiers: tuple[ActionCostModifier, ...] = ()

    def applicable_to(
        self,
        cost: BaseActionCost,
        *,
        skill_line: str | None = None,
    ) -> tuple[ActionCostModifier, ...]:
        return tuple(
            modifier
            for modifier in self.modifiers
            if modifier.applies_to(cost, skill_line=skill_line)
        )
