from __future__ import annotations

from .combat_effects import CombatEffect
from .enchantment_calculation import calculate_enchantment_effect
from .rule_effects import RuleEffect
from .rule_repository import RuleRepository
from .weapon_enchantment_repository import WeaponEnchantmentRepository


class WeaponEnchantmentEffectService:
    """Resolve weapon enchantments with applicable trait rules."""

    def __init__(
        self,
        enchantment_repository: WeaponEnchantmentRepository,
        rule_repository: RuleRepository,
    ):
        self.enchantment_repository = enchantment_repository
        self.rule_repository = rule_repository

    def resolve_effects(
        self,
        enchantment_item_id: int,
        *,
        weapon_trait: str | None = None,
        weapon_quality: str | None = None,
        use_max_value: bool = True,
    ) -> list[CombatEffect]:
        """Resolve enchantment combat effects after applicable rules."""

        base_effects = self.enchantment_repository.get_effects(
            enchantment_item_id,
            use_max_value=use_max_value,
        )

        rules: list[RuleEffect] = []

        if (
            weapon_trait == "Infused"
            and weapon_quality is not None
        ):
            rules.append(
                self.rule_repository.get_infused_effect(
                    gear_type="Weapon",
                    quality=weapon_quality,
                )
            )

        if weapon_trait is not None and weapon_trait != "Infused":
            rules.extend(
                self.rule_repository.get_weapon_enchantment_rules(
                    weapon_trait,
                )
            )

        if not rules:
            return base_effects

        resolved: list[CombatEffect] = []

        for effect in base_effects:
            calculation = calculate_enchantment_effect(
                base_value=effect.value,
                rules=rules,
            )

            resolved.append(
                CombatEffect(
                    effect_type=effect.effect_type,
                    value=calculation.final_value,
                    source=effect.source,
                    unit=effect.unit,
                    damage_type=effect.damage_type,
                    target=effect.target,
                    duration_value=effect.duration_value,
                    duration_unit=effect.duration_unit,
                )
            )

        return resolved
