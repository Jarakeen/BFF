from minmax.skill_scaling_classifier import (
    classify_skill_scaling,
)
from minmax.skill_scaling_rule import (
    SkillScalingMode,
)


def test_conjured_ward_uses_health_or_magicka():
    description = (
        "This ability scales off the higher of your "
        "Max Health or Magicka."
    )

    assert classify_skill_scaling(description) == (
        SkillScalingMode.MAX_HEALTH_OR_MAGICKA
    )


def test_bone_shield_uses_health():
    description = (
        "This ability scales off your Max Health."
    )

    assert classify_skill_scaling(description) == (
        SkillScalingMode.MAX_HEALTH
    )


def test_arctic_wind_uses_health():
    description = (
        "This ability scales off your Max Health."
    )

    assert classify_skill_scaling(description) == (
        SkillScalingMode.MAX_HEALTH
    )


def test_burning_light_uses_weapon_or_spell_damage():
    description = (
        "This effect scales off the higher of your "
        "Weapon or Spell Damage."
    )

    assert classify_skill_scaling(description) == (
        SkillScalingMode.MAX_WEAPON_OR_SPELL_DAMAGE
    )


def test_unqualified_skill_uses_standard_offensive_scaling():
    description = (
        "Deals Magic Damage to an enemy."
    )

    assert classify_skill_scaling(description) == (
        SkillScalingMode.STANDARD_OFFENSIVE
    )