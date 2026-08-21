from __future__ import annotations

from services.minmax.skill_scaling_rule import SkillScalingMode


def classify_skill_scaling(
    description: str,
) -> SkillScalingMode:
    """
    Identify the scaling rule explicitly stated in a skill description.

    This intentionally uses only wording that we have evidence for.
    It does not attempt to infer arbitrary scaling behavior.
    """

    text = description.lower()

    if "higher of your max health or magicka" in text:
        return SkillScalingMode.MAX_HEALTH_OR_MAGICKA

    if "higher of your weapon or spell damage" in text:
        return SkillScalingMode.MAX_WEAPON_OR_SPELL_DAMAGE

    if "scales off your max health" in text:
        return SkillScalingMode.MAX_HEALTH

    if "scales off your max magicka" in text:
        return SkillScalingMode.MAX_MAGICKA

    if "scales off your max stamina" in text:
        return SkillScalingMode.MAX_STAMINA

    if "scales off the higher of your max magicka and stamina" in text:
        return SkillScalingMode.MAX_MAGICKA_OR_STAMINA

    return SkillScalingMode.STANDARD_OFFENSIVE