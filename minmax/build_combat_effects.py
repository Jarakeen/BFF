from dataclasses import dataclass

from .combat_effect_classifier import (
    CombatEffectCategory,
    classify_combat_effect,
)
from .combat_effects import CombatEffect


@dataclass(frozen=True)
class BuildCombatEffects:
    """Resolved combat effects contributed by a build."""

    effects: tuple[CombatEffect, ...]

    @property
    def damage(self) -> tuple[CombatEffect, ...]:
        return tuple(
            effect
            for effect in self.effects
            if classify_combat_effect(effect)
            == CombatEffectCategory.DAMAGE
        )

    @property
    def damage_modifiers(self) -> tuple[CombatEffect, ...]:
        return tuple(
            effect
            for effect in self.effects
            if classify_combat_effect(effect)
            == CombatEffectCategory.DAMAGE_MODIFIER
        )

    @property
    def healing(self) -> tuple[CombatEffect, ...]:
        return tuple(
            effect
            for effect in self.effects
            if classify_combat_effect(effect)
            == CombatEffectCategory.HEALING
        )

    @property
    def healing_modifiers(self) -> tuple[CombatEffect, ...]:
        return tuple(
            effect
            for effect in self.effects
            if classify_combat_effect(effect)
            == CombatEffectCategory.HEALING_MODIFIER
        )

    @property
    def target_debuffs(self) -> tuple[CombatEffect, ...]:
        return tuple(
            effect
            for effect in self.effects
            if classify_combat_effect(effect)
            == CombatEffectCategory.TARGET_DEBUFF
        )