from __future__ import annotations

"""Proof-safe weapon trait/enchantment relevance for Extreme max-resource records.

This service audits the complete canonical weapon-trait and weapon-enchantment
inventories exposed by the existing repositories. It does not duplicate weapon
math. It answers only whether any reviewed weapon source can change Max Health,
Max Magicka, or Max Stamina.

Current-resource restores are intentionally irrelevant to max-resource objectives.
Unknown trait rule types, unknown enchantment effect types, empty canonical rows,
or missing effects fail closed.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.rule_repository import RuleRepository
from minmax.weapon_enchantment_repository import WeaponEnchantmentRepository


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")
_TARGET_EFFECT_TYPES = {
    "max_health": "max_health",
    "max_magicka": "max_magicka",
    "max_stamina": "max_stamina",
}

# Canonical weapon-enchantment parser/runtime channels which do not increase a
# player's primary resource maximum. Restore channels affect the current pool.
_KNOWN_IRRELEVANT_ENCHANT_EFFECTS = {
    "damage",
    "health_restore",
    "magicka_restore",
    "stamina_restore",
    "damage_shield",
    "weapon_spell_damage",
    "weapon_spell_damage_reduction",
    "physical_spell_resistance_reduction",
}

# Canonical weapon-trait rule channels. Enchantment amplification/cooldown only
# matters if the audited enchantment universe contains a max-resource effect.
_KNOWN_IRRELEVANT_TRAIT_RULES = {
    "weapon_damage",
    "weapon_spell_critical",
    "physical_spell_penetration",
    "physical_spell_resistance",
    "healing_done",
    "status_effect_chance",
    "ultimate_gain_chance",
    "kill_experience",
    "weapon_enchantment_effect",
    "enchantment_cooldown_reduction",
}


@dataclass(frozen=True)
class ExtremeWeaponResourceRelevanceAudit:
    objective_key: str
    enchantments_reviewed: int
    traits_reviewed: int
    relevant_enchantments: tuple[str, ...]
    relevant_traits: tuple[str, ...]
    enchant_effect_types_reviewed: tuple[str, ...]
    trait_rule_types_reviewed: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return (
            self.enchantments_reviewed > 0
            and self.traits_reviewed > 0
            and not self.unresolved
        )

    @property
    def objective_irrelevance_proven(self) -> bool:
        return (
            self.denominator_proven
            and not self.relevant_enchantments
            and not self.relevant_traits
        )


class ExtremeWeaponResourceRelevanceService:
    """Audit all canonical weapon traits/enchants for one max-resource objective."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        enchantment_repository: WeaponEnchantmentRepository | None = None,
        rule_repository: RuleRepository | None = None,
    ) -> None:
        if database_path is None and (
            enchantment_repository is None or rule_repository is None
        ):
            raise ValueError(
                "database_path is required unless both weapon repositories are supplied"
            )
        self.enchantment_repository = enchantment_repository or WeaponEnchantmentRepository(
            database_path  # type: ignore[arg-type]
        )
        self.rule_repository = rule_repository or RuleRepository(
            database_path  # type: ignore[arg-type]
        )

    def build(self, objective_key: str) -> ExtremeWeaponResourceRelevanceAudit:
        key = str(objective_key or "").strip().casefold()
        target_effect = _TARGET_EFFECT_TYPES.get(key)
        if target_effect is None:
            raise KeyError(f"unreviewed Extreme weapon resource objective: {objective_key!r}")

        unresolved: list[str] = []
        relevant_enchants: list[str] = []
        relevant_traits: list[str] = []
        enchant_effect_types: set[str] = set()
        trait_rule_types: set[str] = set()

        enchantments = tuple(self.enchantment_repository.list_items())
        if not enchantments:
            unresolved.append("Canonical weapon enchantment catalog is empty")

        for item_id, name in enchantments:
            effects = tuple(
                self.enchantment_repository.get_effects(
                    int(item_id),
                    use_max_value=True,
                )
            )
            if not effects:
                unresolved.append(
                    f"Canonical weapon enchantment has no mapped effects: {name} ({item_id})"
                )
                continue
            for effect in effects:
                effect_type = str(effect.effect_type or "").strip().casefold()
                if not effect_type:
                    unresolved.append(
                        f"Canonical weapon enchantment has effect without type: {name} ({item_id})"
                    )
                    continue
                enchant_effect_types.add(effect_type)
                if effect_type == target_effect:
                    relevant_enchants.append(str(name))
                elif effect_type not in _KNOWN_IRRELEVANT_ENCHANT_EFFECTS:
                    unresolved.append(
                        f"Unreviewed weapon enchantment effect type for {key}: {effect_type} ({name})"
                    )

        trait_names = tuple(self.rule_repository.list_weapon_trait_names())
        if not trait_names:
            unresolved.append("Canonical weapon trait catalog is empty")

        for name in trait_names:
            rules = tuple(self.rule_repository.get_weapon_trait_rules(name))
            if not rules:
                unresolved.append(f"Canonical weapon trait has no mapped rules: {name}")
                continue
            for rule in rules:
                rule_type = str(rule.rule_type or "").strip().casefold()
                if not rule_type:
                    unresolved.append(f"Canonical weapon trait has rule without type: {name}")
                    continue
                trait_rule_types.add(rule_type)
                if rule_type in {"max_health", "max_magicka", "max_stamina"}:
                    if rule_type == target_effect:
                        relevant_traits.append(str(name))
                    continue
                if rule_type not in _KNOWN_IRRELEVANT_TRAIT_RULES:
                    unresolved.append(
                        f"Unreviewed weapon trait rule type for {key}: {rule_type} ({name})"
                    )

        return ExtremeWeaponResourceRelevanceAudit(
            objective_key=key,
            enchantments_reviewed=len(enchantments),
            traits_reviewed=len(trait_names),
            relevant_enchantments=tuple(sorted(set(relevant_enchants), key=str.casefold)),
            relevant_traits=tuple(sorted(set(relevant_traits), key=str.casefold)),
            enchant_effect_types_reviewed=tuple(sorted(enchant_effect_types)),
            trait_rule_types_reviewed=tuple(sorted(trait_rule_types)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
