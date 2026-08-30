from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DamageTakenModifiers:
    """Additive target-side Damage Taken for one combat snapshot.

    Values are decimal ratios: +0.05 means 5% more damage taken and -0.05
    means 5% less damage taken. This stage is intentionally separate from
    attacker Damage Done and resistance mitigation.
    """

    generic: float = 0.0

    def __post_init__(self) -> None:
        if self.generic < -1.0:
            raise ValueError("Damage Taken cannot be below -100%")


@dataclass(frozen=True)
class DamageTakenBreakdown:
    generic: float = 0.0

    @property
    def total(self) -> float:
        return float(self.generic)

    @property
    def multiplier(self) -> float:
        return max(0.0, 1.0 + self.total)


def resolve_damage_taken(
    modifiers: DamageTakenModifiers,
) -> DamageTakenBreakdown:
    """Resolve the target-side Damage Taken bucket for one event."""

    return DamageTakenBreakdown(generic=float(modifiers.generic))
