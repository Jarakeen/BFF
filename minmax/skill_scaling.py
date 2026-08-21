from __future__ import annotations

from dataclasses import dataclass

from minmax.build import Build
from minmax.stat_ids import StatId


@dataclass(frozen=True)
class SkillScalingInputs:
    """
    Raw build attributes available to skill scaling rules.

    These are intentionally NOT resolved into a single A or P value.

    A = ability/resource scaling
    P = offensive power scaling
    """

    max_health: float
    max_magicka: float
    max_stamina: float
    weapon_damage: float
    spell_damage: float


def get_skill_scaling_inputs(
    build: Build,
) -> SkillScalingInputs:
    """
    Extract raw attributes from a build.

    Skill-specific scaling rules are resolved separately.
    """

    return SkillScalingInputs(
        max_health=build.base_stats.get(
            StatId.MAX_HEALTH.value,
            0.0,
        ),
        max_magicka=build.base_stats.get(
            StatId.MAX_MAGICKA.value,
            0.0,
        ),
        max_stamina=build.base_stats.get(
            StatId.MAX_STAMINA.value,
            0.0,
        ),
        weapon_damage=build.base_stats.get(
            StatId.WEAPON_DAMAGE.value,
            0.0,
        ),
        spell_damage=build.base_stats.get(
            StatId.SPELL_DAMAGE.value,
            0.0,
        ),
    )