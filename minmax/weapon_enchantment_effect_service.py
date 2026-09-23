from __future__ import annotations

from .combat_effects import CombatEffect
from .enchantment_calculation import calculate_enchantment_effect
from .rule_effects import RuleEffect
from .rule_repository import RuleRepository
from .weapon_enchantment_repository import WeaponEnchantmentRepository
from .combat_cooldown_rules import (
    CooldownRuleResult,
    calculate_cooldown_from_rules,
)

class WeaponEnchantmentEffectService:
    """Resolve weapon enchantments with applicable trait rules."""

    def __init__(
        self,
        enchantment_repository: WeaponEnchantmentRepository,
        rule_repository: RuleRepository,
    ):
        self.enchantment_repository = enchantment_repository
        self.rule_repository = rule_repository

    def get_applicable_rules(
        self,
        *,
        weapon_trait: str | None = None,
        weapon_quality: str | None = None,
    ) -> list[RuleEffect]:
        """Return all rules applicable to the equipped weapon."""

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
            rules.append(
                self.rule_repository.get_infused_weapon_cooldown_effect()
            )

        if (
            weapon_trait is not None
            and weapon_trait != "Infused"
        ):
            rules.extend(
                self.rule_repository.get_weapon_trait_rules(
                    weapon_trait,
                )
            )

        return rules

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

        rules = self.get_applicable_rules(
            weapon_trait=weapon_trait,
            weapon_quality=weapon_quality,
        )

        if not rules:
            return base_effects

        resolved: list[CombatEffect] = []

        for effect in base_effects:
            effect_rules = rules
            if str(effect.damage_type or "").strip().casefold() == "oblivion":
                # Update 23 defines player-sourced Oblivion Damage as bypassing
                # positive/negative bonuses. Weapon-enchantment strength rules
                # therefore must not inflate Decrease Health damage; cooldown
                # modifiers remain separately available through resolve_cooldown().
                effect_rules = [
                    rule
                    for rule in rules
                    if rule.rule_type
                    not in {"enchantment_effect", "weapon_enchantment_effect"}
                ]
            calculation = calculate_enchantment_effect(
                base_value=effect.value,
                rules=effect_rules,
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
                    scaling_type=effect.scaling_type,
                    condition=effect.condition,
                )
            )

        return resolved

    def resolve_cooldown(
        self,
        *,
        base_cooldown: float,
        weapon_trait: str | None = None,
        weapon_quality: str | None = None,
    ) -> CooldownRuleResult:
        """Resolve an enchantment cooldown after applicable weapon rules."""

        rules = self.get_applicable_rules(
            weapon_trait=weapon_trait,
            weapon_quality=weapon_quality,
        )

        return calculate_cooldown_from_rules(
            base_cooldown=base_cooldown,
            rules=rules,
        )