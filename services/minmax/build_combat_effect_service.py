from __future__ import annotations

from .build import Build
from .combat_effects import CombatEffect
from .weapon_enchantment_effect_service import (
    WeaponEnchantmentEffectService,
)


class BuildCombatEffectService:
    """Resolve combat effects contributed by an equipped build."""

    def __init__(
        self,
        weapon_enchantment_service: WeaponEnchantmentEffectService,
    ):
        self.weapon_enchantment_service = weapon_enchantment_service

    def resolve_effects(
        self,
        build: Build,
        *,
        use_max_value: bool = True,
    ) -> list[CombatEffect]:
        """Resolve combat effects from all equipped weapons."""

        effects: list[CombatEffect] = []

        for weapon in build.weapons:
            if weapon.enchantment_item_id is None:
                continue

            effects.extend(
                self.weapon_enchantment_service.resolve_effects(
                    weapon.enchantment_item_id,
                    weapon_trait=weapon.trait,
                    weapon_quality=weapon.quality,
                    use_max_value=use_max_value,
                )
            )

        return effects
    