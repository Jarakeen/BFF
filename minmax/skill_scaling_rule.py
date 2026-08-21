from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from minmax.skill_scaling import SkillScalingInputs


class SkillScalingMode(str, Enum):
    STANDARD_OFFENSIVE = "standard_offensive"

    MAX_HEALTH = "max_health"
    MAX_MAGICKA = "max_magicka"
    MAX_STAMINA = "max_stamina"

    MAX_HEALTH_OR_MAGICKA = "max_health_or_magicka"
    MAX_MAGICKA_OR_STAMINA = "max_magicka_or_stamina"

    MAX_WEAPON_OR_SPELL_DAMAGE = "max_weapon_or_spell_damage"


@dataclass(frozen=True)
class SkillScalingResult:
    """
    Resolved A and P values for one coefficient component.
    """

    ability: float
    power: float


def resolve_skill_scaling(
    inputs: SkillScalingInputs,
    mode: SkillScalingMode,
) -> SkillScalingResult:

    if mode == SkillScalingMode.STANDARD_OFFENSIVE:
        return SkillScalingResult(
            ability=max(
                inputs.max_magicka,
                inputs.max_stamina,
            ),
            power=max(
                inputs.weapon_damage,
                inputs.spell_damage,
            ),
        )

    if mode == SkillScalingMode.MAX_HEALTH:
        return SkillScalingResult(
            ability=inputs.max_health,
            power=0.0,
        )

    if mode == SkillScalingMode.MAX_MAGICKA:
        return SkillScalingResult(
            ability=inputs.max_magicka,
            power=0.0,
        )

    if mode == SkillScalingMode.MAX_STAMINA:
        return SkillScalingResult(
            ability=inputs.max_stamina,
            power=0.0,
        )

    if mode == SkillScalingMode.MAX_HEALTH_OR_MAGICKA:
        return SkillScalingResult(
            ability=max(
                inputs.max_health,
                inputs.max_magicka,
            ),
            power=0.0,
        )

    if mode == SkillScalingMode.MAX_MAGICKA_OR_STAMINA:
        return SkillScalingResult(
            ability=max(
                inputs.max_magicka,
                inputs.max_stamina,
            ),
            power=0.0,
        )

    if mode == SkillScalingMode.MAX_WEAPON_OR_SPELL_DAMAGE:
        return SkillScalingResult(
            ability=0.0,
            power=max(
                inputs.weapon_damage,
                inputs.spell_damage,
            ),
        )

    raise ValueError(
        f"Unsupported skill scaling mode: {mode!r}"
    )