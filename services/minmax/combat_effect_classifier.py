from enum import Enum

from .combat_effects import CombatEffect


class CombatEffectCategory(str, Enum):
    DAMAGE = "damage"
    HEALING = "healing"
    TARGET_DEBUFF = "target_debuff"
    OTHER = "other"


DAMAGE_EFFECT_TYPES = frozenset({
    "damage",
})

HEALING_EFFECT_TYPES = frozenset({
    "health_restore",
})

TARGET_DEBUFF_EFFECT_TYPES = frozenset({
    "physical_spell_resistance_reduction",
})


def classify_combat_effect(
    effect: CombatEffect,
) -> CombatEffectCategory:

    if effect.effect_type in DAMAGE_EFFECT_TYPES:
        return CombatEffectCategory.DAMAGE

    if effect.effect_type in HEALING_EFFECT_TYPES:
        return CombatEffectCategory.HEALING

    if effect.effect_type in TARGET_DEBUFF_EFFECT_TYPES:
        return CombatEffectCategory.TARGET_DEBUFF

    return CombatEffectCategory.OTHER