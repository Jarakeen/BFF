from __future__ import annotations

"""Target-side ESO Critical Resistance math.

At effective level 66 (CP160+), 66 Critical Resistance removes one percentage
point from the attacker's Critical Damage bonus. Critical Resistance cannot
make a critical strike deal less damage than the equivalent non-critical hit.

This module models that target-side reduction separately from armor resistance,
Damage Taken, and attacker Critical Damage so the combat pipeline remains
auditable.
"""

from dataclasses import dataclass


CRITICAL_RESISTANCE_PER_PERCENT = 66.0


@dataclass(frozen=True)
class CriticalResistanceResult:
    target_critical_resistance: float
    reduction_percent: float
    attacker_critical_damage_percent: float
    effective_critical_damage_percent: float

    @property
    def effective_critical_damage_fraction(self) -> float:
        return self.effective_critical_damage_percent / 100.0


def resolve_critical_resistance(
    attacker_critical_damage_percent: float,
    target_critical_resistance: float = 0.0,
    *,
    resistance_per_percent: float = CRITICAL_RESISTANCE_PER_PERCENT,
) -> CriticalResistanceResult:
    """Reduce the attacker's crit-damage bonus by target Critical Resistance.

    Inputs and outputs use percentage points for Critical Damage. For example,
    an attacker bonus of 50.0 with 1320 target Critical Resistance resolves to
    30.0 effective Critical Damage because 1320 / 66 = 20 percentage points.
    """

    if attacker_critical_damage_percent < 0:
        raise ValueError("Attacker Critical Damage cannot be negative.")
    if target_critical_resistance < 0:
        raise ValueError("Target Critical Resistance cannot be negative.")
    if resistance_per_percent <= 0:
        raise ValueError("Critical Resistance conversion must be positive.")

    reduction_percent = target_critical_resistance / resistance_per_percent
    effective = max(0.0, attacker_critical_damage_percent - reduction_percent)

    return CriticalResistanceResult(
        target_critical_resistance=float(target_critical_resistance),
        reduction_percent=float(reduction_percent),
        attacker_critical_damage_percent=float(attacker_critical_damage_percent),
        effective_critical_damage_percent=float(effective),
    )
