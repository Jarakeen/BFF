from __future__ import annotations

from dataclasses import dataclass

from models.build_model import GearSlot, PlayerBuild

from .character_progression import CharacterProgression
from .jewelry_cost_modifier_repository import JewelryCostModifierRepository
from .jewelry_trait_repository import JewelryTraitRepository
from .resource_cost_modifiers import (
    ActionCostModifier,
    ActionCostModifierSet,
    CostModifierOperation,
)
from .resource_costs import ResourceType


_JEWELRY_COST_ENCHANT_TO_GLYPH = {
    "reduce spell cost": "Glyph of Reduce Spell Cost",
    "reduce magicka cost": "Glyph of Reduce Spell Cost",
    "reduce feat cost": "Glyph of Reduce Feat Cost",
    "reduce stamina cost": "Glyph of Reduce Feat Cost",
    "reduce skill cost": "Glyph of Reduce Skill Cost",
    "reduce resource cost": "Glyph of Reduce Skill Cost",
}

# Verified max-rank standing passive values. These are build-cost events rather
# than persistent character-sheet stats, so they live in the action-cost path.
_BRETON_MAGICKA_MASTERY = 0.07
_IMPERIAL_RED_DIAMOND = 0.06
_REDGUARD_MARTIAL_TRAINING = 0.08
_LIGHT_ARMOR_EVOCATION_PER_PIECE = 0.02

_WEAPON_SKILL_LINES = (
    "Two Handed",
    "One Hand and Shield",
    "Dual Wield",
    "Bow",
    "Destruction Staff",
    "Restoration Staff",
)


@dataclass(frozen=True)
class BuildActionCostModifiers:
    modifiers: ActionCostModifierSet = ActionCostModifierSet()
    unresolved: tuple[str, ...] = ()


class BuildActionCostModifierResolver:
    """Resolve verified static action-cost modifiers from one saved build.

    Jewelry glyphs are read from the existing DB-backed glyph data. Standing
    racial passives follow the same max-rank endgame assumption already used by
    the racial stat pipeline. Armor passives remain explicitly gated by
    CharacterProgression skill-line ownership.
    """

    def __init__(
        self,
        jewelry_cost_repository: JewelryCostModifierRepository,
        jewelry_trait_repository: JewelryTraitRepository | None = None,
    ) -> None:
        self.jewelry_cost_repository = jewelry_cost_repository
        self.jewelry_trait_repository = jewelry_trait_repository

    @staticmethod
    def _light_armor_count(build: PlayerBuild) -> int:
        return sum(
            1
            for entry in build.Armor.values()
            if str(entry.get("Weight", "") or "").strip().casefold() == "light"
        )

    @staticmethod
    def _standing_passive_modifiers(
        build: PlayerBuild,
        progression: CharacterProgression | None,
    ) -> tuple[ActionCostModifier, ...]:
        modifiers: list[ActionCostModifier] = []
        race = str(build.Race or "").strip().casefold()

        if race == "breton":
            modifiers.append(
                ActionCostModifier(
                    source="Breton: Magicka Mastery",
                    operation=CostModifierOperation.PERCENT_REDUCTION,
                    value=_BRETON_MAGICKA_MASTERY,
                    resources=(ResourceType.MAGICKA,),
                )
            )
        elif race == "imperial":
            modifiers.append(
                ActionCostModifier(
                    source="Imperial: Red Diamond",
                    operation=CostModifierOperation.PERCENT_REDUCTION,
                    value=_IMPERIAL_RED_DIAMOND,
                    resources=(
                        ResourceType.HEALTH,
                        ResourceType.MAGICKA,
                        ResourceType.STAMINA,
                        ResourceType.ULTIMATE,
                    ),
                )
            )
        elif race == "redguard":
            modifiers.append(
                ActionCostModifier(
                    source="Redguard: Martial Training",
                    operation=CostModifierOperation.PERCENT_REDUCTION,
                    value=_REDGUARD_MARTIAL_TRAINING,
                    resources=(
                        ResourceType.HEALTH,
                        ResourceType.MAGICKA,
                        ResourceType.STAMINA,
                        ResourceType.ULTIMATE,
                    ),
                    skill_lines=_WEAPON_SKILL_LINES,
                )
            )

        if progression is not None and progression.owns_skill_line("Light Armor"):
            light_count = BuildActionCostModifierResolver._light_armor_count(build)
            if light_count:
                modifiers.append(
                    ActionCostModifier(
                        source=f"Light Armor: Evocation ({light_count} pieces)",
                        operation=CostModifierOperation.PERCENT_REDUCTION,
                        value=_LIGHT_ARMOR_EVOCATION_PER_PIECE * light_count,
                        resources=(ResourceType.MAGICKA,),
                    )
                )

        return tuple(modifiers)

    def _jewelry_multiplier(
        self,
        slot_name: str,
        slot: GearSlot,
        unresolved: list[str],
    ) -> tuple[float, str]:
        trait = str(slot.Trait or "").strip()
        if trait.casefold() != "infused":
            return 1.0, ""

        if self.jewelry_trait_repository is None:
            unresolved.append(f"{slot_name}: Infused jewelry trait repository unavailable")
            return 0.0, ""

        quality = str(slot.Quality or "").strip()
        percent = self.jewelry_trait_repository.get_infused_enchantment_percent(quality)
        if percent is None:
            unresolved.append(
                f"{slot_name}: Infused jewelry value unavailable for quality {quality or 'unset'}"
            )
            return 0.0, ""

        return 1.0 + (percent / 100.0), f" (Infused +{percent:g}%)"

    def resolve(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression | None = None,
    ) -> BuildActionCostModifiers:
        modifiers: list[ActionCostModifier] = list(
            self._standing_passive_modifiers(build, progression)
        )
        unresolved: list[str] = []
        slots = (
            ("Necklace", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
        )

        for slot_name, slot in slots:
            enchant = str(slot.Enchant or "").strip()
            if not enchant:
                continue

            glyph_name = _JEWELRY_COST_ENCHANT_TO_GLYPH.get(enchant.casefold())
            if glyph_name is None:
                # Non-cost jewelry enchants belong to the character-stat path,
                # not this resolver. Do not mark them unresolved here.
                continue

            level = str(slot.Level or "").strip()
            tier = str(slot.EnchantTier or "").strip()
            if level.casefold() != "cp160" or tier.casefold() != "truly superb":
                unresolved.append(
                    f"{slot_name} {enchant}: needs verified level/tier scaling "
                    f"({level or 'level unset'}, {tier or 'tier unset'})"
                )
                continue

            multiplier, trait_label = self._jewelry_multiplier(slot_name, slot, unresolved)
            if multiplier == 0.0:
                continue

            resolved = self.jewelry_cost_repository.get_by_name(
                glyph_name,
                use_max_value=True,
                multiplier=multiplier,
                source_prefix=slot_name,
            )
            if not resolved:
                unresolved.append(f"{slot_name} cost glyph not found: {glyph_name}")
                continue

            if trait_label:
                resolved = tuple(
                    ActionCostModifier(
                        source=f"{modifier.source}{trait_label}",
                        operation=modifier.operation,
                        value=modifier.value,
                        resources=modifier.resources,
                        ability_ids=modifier.ability_ids,
                        skill_lines=modifier.skill_lines,
                    )
                    for modifier in resolved
                )
            modifiers.extend(resolved)

        return BuildActionCostModifiers(
            modifiers=ActionCostModifierSet(tuple(modifiers)),
            unresolved=tuple(unresolved),
        )
