from enum import Enum

from .combat_effects import CombatEffect


class CombatEffectCategory(str, Enum):
    DAMAGE = "damage"
    DAMAGE_MODIFIER = "damage_modifier"
    HEALING = "healing"
    HEALING_MODIFIER = "healing_modifier"
    TARGET_DEBUFF = "target_debuff"
    OTHER = "other"


DAMAGE_EFFECT_TYPES = frozenset({
    "damage",
})

DAMAGE_MODIFIER_EFFECT_TYPES = frozenset({
    "damage_done",
    "direct_damage_done",
    "flame_damage_done",
    "single_target_damage_done",
    "damage_amplification",
})

HEALING_EFFECT_TYPES = frozenset({
    "health_restore",
})

HEALING_MODIFIER_EFFECT_TYPES = frozenset({
    "healing_done",
})

TARGET_DEBUFF_EFFECT_TYPES = frozenset({
    "physical_spell_resistance_reduction",
})


def classify_combat_effect(
    effect: CombatEffect,
) -> CombatEffectCategory:
    """Classify an already-resolved combat effect by semantic role."""

    if effect.effect_type in DAMAGE_EFFECT_TYPES:
        return CombatEffectCategory.DAMAGE

    if effect.effect_type in DAMAGE_MODIFIER_EFFECT_TYPES:
        return CombatEffectCategory.DAMAGE_MODIFIER

    if effect.effect_type in HEALING_EFFECT_TYPES:
        return CombatEffectCategory.HEALING

    if effect.effect_type in HEALING_MODIFIER_EFFECT_TYPES:
        return CombatEffectCategory.HEALING_MODIFIER

    if effect.effect_type in TARGET_DEBUFF_EFFECT_TYPES:
        return CombatEffectCategory.TARGET_DEBUFF

    return CombatEffectCategory.OTHER