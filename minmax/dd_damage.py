from dataclasses import dataclass

from .dd_damage_profile import get_dd_damage_profile
from .dd_mitigation import DDMitigationResult
from .dd_stat_evaluation import DDStatEvaluation


@dataclass(frozen=True)
class DDDamageEvent:
    """A single modeled DD damage event."""

    base_value: float
    scaling_coefficient: float = 0.0

    damage_type: str | None = None
    can_crit: bool = True


@dataclass(frozen=True)
class DDDamageResult:
    """Resolved damage for a single modeled event."""

    base_damage: float
    scaled_damage: float
    critical_chance: float
    critical_damage: float
    expected_damage: float

    offensive_stat: str
    offensive_power: float

    penetration_stat: str | None
    penetration: float

    mitigation_multiplier: float = 1.0
    mitigated_damage: float = 0.0


def calculate_dd_damage(
    event: DDDamageEvent,
    stats: DDStatEvaluation,
    *,
    mitigation: DDMitigationResult | None = None,
) -> DDDamageResult:
    """Calculate expected damage for a modeled DD event."""

    if event.base_value < 0:
        raise ValueError(
            "Base damage cannot be negative."
        )

    if event.scaling_coefficient < 0:
        raise ValueError(
            "Scaling coefficient cannot be negative."
        )

    if event.damage_type is None:
        offensive_stat = "combined_offensive_power"
        offensive_power = (
            stats.weapon_damage
            + stats.spell_damage
        )
        penetration_stat = None
        penetration = 0.0

    else:
        profile = get_dd_damage_profile(
            event.damage_type
        )

        offensive_stat = profile.offensive_stat

        if offensive_stat == "weapon_damage":
            offensive_power = stats.weapon_damage
        elif offensive_stat == "spell_damage":
            offensive_power = stats.spell_damage
        else:
            raise ValueError(
                f"Unsupported offensive stat: "
                f"{offensive_stat!r}"
            )

        penetration_stat = profile.penetration_stat

        if penetration_stat == "physical_penetration":
            penetration = (
                stats.effective_physical_penetration
            )
        elif penetration_stat == "spell_penetration":
            penetration = (
                stats.effective_spell_penetration
            )
        else:
            raise ValueError(
                f"Unsupported penetration stat: "
                f"{penetration_stat!r}"
            )

    scaled_damage = (
        event.base_value
        + offensive_power * event.scaling_coefficient
    )

    if not event.can_crit:
        critical_chance = 0.0
        critical_damage = 0.0
        expected_damage = scaled_damage

    else:
        critical_chance = (
            stats.effective_critical_chance / 100.0
        )

        critical_damage = (
            stats.effective_critical_damage / 100.0
        )

        expected_damage = (
            scaled_damage
            * (
                1.0
                + critical_chance * critical_damage
            )
        )

    if mitigation is None:
        mitigation_multiplier = 1.0
    else:
        mitigation_multiplier = (
            mitigation.damage_multiplier
        )

    mitigated_damage = (
        expected_damage * mitigation_multiplier
    )

    return DDDamageResult(
        base_damage=event.base_value,
        scaled_damage=scaled_damage,
        critical_chance=critical_chance,
        critical_damage=critical_damage,
        expected_damage=expected_damage,
        offensive_stat=offensive_stat,
        offensive_power=offensive_power,
        penetration_stat=penetration_stat,
        penetration=penetration,
        mitigation_multiplier=mitigation_multiplier,
        mitigated_damage=mitigated_damage,
    )