from dataclasses import dataclass

from .damage_done import DamageDoneBreakdown, DamageDoneModifiers, resolve_damage_done
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
    is_dot: bool = False
    is_aoe: bool = False


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

    damage_done: DamageDoneBreakdown = DamageDoneBreakdown()
    damage_done_multiplier: float = 1.0
    damage_done_damage: float = 0.0

    mitigation_multiplier: float = 1.0
    mitigated_damage: float = 0.0


def calculate_dd_damage(
    event: DDDamageEvent,
    stats: DDStatEvaluation,
    *,
    mitigation: DDMitigationResult | None = None,
    damage_done: DamageDoneModifiers = DamageDoneModifiers(),
) -> DDDamageResult:
    """Calculate expected damage for a modeled DD event.

    Applicable Damage Done categories are additive inside one ESO event bucket:
    generic + damage type + Direct/DoT + Single Target/AoE.  That bucket is
    applied to the scaled event before expected critical damage and target
    mitigation.  With the default zero-value modifiers this preserves the
    pre-Phase-3 behavior exactly.
    """

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

    damage_done_breakdown = resolve_damage_done(
        damage_done,
        damage_type=event.damage_type,
        is_dot=event.is_dot,
        is_aoe=event.is_aoe,
    )
    damage_done_multiplier = damage_done_breakdown.multiplier
    damage_done_damage = scaled_damage * damage_done_multiplier

    if not event.can_crit:
        critical_chance = 0.0
        critical_damage = 0.0
        expected_damage = damage_done_damage

    else:
        critical_chance = (
            stats.effective_critical_chance / 100.0
        )

        critical_damage = (
            stats.effective_critical_damage / 100.0
        )

        expected_damage = (
            damage_done_damage
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
        damage_done=damage_done_breakdown,
        damage_done_multiplier=damage_done_multiplier,
        damage_done_damage=damage_done_damage,
        mitigation_multiplier=mitigation_multiplier,
        mitigated_damage=mitigated_damage,
    )