from __future__ import annotations

from .build import Build
from .build_combat_effect_service import BuildCombatEffectService
from .build_combat_effects import BuildCombatEffects
from .combat_effects import CombatEffect
from .support_effect import SupportEffect
from .support_effect_category import SupportEffectCategory
from .support_effect_registry import SupportEffectRegistry
from .support_target_type import SupportTargetType


class BuildSupportEffectService:
    """
    Resolves the SupportEffects a Build actually represents, and returns
    them as a SupportEffectRegistry:

        Build -> BuildSupportEffectService -> SupportEffectRegistry

    Currently supported sources
    ----------------------------
    - Weapon enchantments (`Build.weapons`). This reuses the existing
      BuildCombatEffectService / WeaponEnchantmentEffectService pipeline
      to resolve each equipped enchantment's CombatEffects, then reuses
      BuildCombatEffects.target_debuffs (the existing classifier) to
      identify which of those effects are genuine group-relevant debuffs
      (currently: resistance reduction).

      Plain damage and self-healing enchantment effects are deliberately
      NOT converted into SupportEffects just because they came from an
      enchantment - e.g. Frost damage alone stays a CombatEffect. A
      future status/proc system decides whether that damage can
      contribute to Chilled/Brittle; that separation is preserved here.

    Not yet supported (left out rather than guessed)
    --------------------------------------------------
    - Gear sets (`Build.gear_sets`): GearSetEffectResolver currently only
      produces generic self-stat Effects with no reliable target
      information, so a group-targeted set bonus (e.g. a set that grants
      Major Courage) cannot yet be distinguished from an ordinary
      personal stat bonus. Left for future work.
    - Armor glyphs (`Build.armor_glyphs`): no effect-resolution pipeline
      currently connects glyph item ids to effects.
    - Champion Points: not represented on Build at all yet.
    - Skills: not represented on Build at all yet.
    - Race (`Build.race_id`): RaceEffectService resolves personal stat
      effects only, not group support effects.
    - Role/class: not represented on Build at all yet, so
      `SupportEffect.role_relevance` is always left empty here rather
      than guessed.
    """

    def __init__(
        self,
        build_combat_effect_service: BuildCombatEffectService,
    ) -> None:
        self.build_combat_effect_service = build_combat_effect_service

    def resolve(self, build: Build) -> SupportEffectRegistry:
        """Resolve a Build into a SupportEffectRegistry."""

        combat_effects = self.build_combat_effect_service.resolve_effects(
            build,
        )

        build_combat_effects = BuildCombatEffects(
            effects=tuple(combat_effects),
        )

        registry = SupportEffectRegistry()

        for combat_effect in build_combat_effects.target_debuffs:
            registry.add(self._as_support_effect(combat_effect))

        return registry

    @staticmethod
    def _as_support_effect(combat_effect: CombatEffect) -> SupportEffect:
        """
        Convert a classified target-debuff CombatEffect into a
        SupportEffect. Only called for effects already identified as
        TARGET_DEBUFF - nothing here re-decides what counts as support.
        """

        return SupportEffect(
            source=combat_effect.source,
            name=combat_effect.source,
            category=SupportEffectCategory.DEBUFF,
            effect_type=combat_effect.effect_type,
            target_type=SupportTargetType.ENEMY,
            magnitude=combat_effect.value,
            unit=combat_effect.unit,
            duration=combat_effect.duration_value,
            resistance_reduction=combat_effect.value,
        )
