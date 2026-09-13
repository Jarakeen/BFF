from __future__ import annotations

"""Reviewed timing semantics for target-Health conditions on periodic damage.

Periodic source-magnitude timing and target-Health condition timing are separate
facts. A DoT can snapshot its source magnitude at cast time while still checking
recipient Health at each tick, or vice versa. This service models only the latter.

No generic default is provided. Callers must supply reviewed semantics for the exact
canonical skill/component before target-Health-conditioned periodic damage may resolve.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.skill_coefficient_repository import ability_entity_id


class PeriodicTargetHealthTimingPolicy(str, Enum):
    SNAPSHOT_AT_CAST = "snapshot_at_cast"
    DYNAMIC_AT_TICK = "dynamic_at_tick"


@dataclass(frozen=True)
class RotationPeriodicTargetHealthSemantics:
    skill_entity_id: str
    coefficient_number: int
    policy: PeriodicTargetHealthTimingPolicy
    source: str

    def __post_init__(self) -> None:
        identity = ability_entity_id(self.skill_entity_id)
        if not identity:
            raise ValueError("periodic target-Health semantics require a skill identity")
        if int(self.coefficient_number) <= 0:
            raise ValueError("periodic target-Health coefficient_number must be positive")
        source = str(self.source or "").strip()
        if not source:
            raise ValueError("periodic target-Health semantics require provenance")
        policy = self.policy
        if not isinstance(policy, PeriodicTargetHealthTimingPolicy):
            policy = PeriodicTargetHealthTimingPolicy(str(policy))
        object.__setattr__(self, "skill_entity_id", identity)
        object.__setattr__(self, "coefficient_number", int(self.coefficient_number))
        object.__setattr__(self, "policy", policy)
        object.__setattr__(self, "source", source)


class RotationPeriodicTargetHealthSemanticsService:
    """Resolve one exact reviewed target-Health timing semantic."""

    def __init__(
        self,
        semantics: tuple[RotationPeriodicTargetHealthSemantics, ...] = (),
    ) -> None:
        self.semantics = tuple(semantics)

    def resolve(
        self,
        *,
        skill_name: str,
        coefficient_number: int,
    ) -> RotationPeriodicTargetHealthSemantics | None:
        identity = ability_entity_id(skill_name)
        matches = tuple(
            row
            for row in self.semantics
            if row.skill_entity_id == identity
            and row.coefficient_number == int(coefficient_number)
        )
        return matches[0] if len(matches) == 1 else None


__all__ = [
    "PeriodicTargetHealthTimingPolicy",
    "RotationPeriodicTargetHealthSemantics",
    "RotationPeriodicTargetHealthSemanticsService",
]
