from __future__ import annotations

from dataclasses import replace

from models.build_model import GearSlot, PlayerBuild

from .block_stats import BlockCostModifier
from .gear_stat_inputs import GearCalculationInputs


# Current CP160 armor-trait values by item quality.
# Sturdy reduces Block Cost by this percentage per equipped armor piece.
STURDY_PERCENT_BY_QUALITY = {
    "white": 0.020,
    "normal": 0.020,
    "green": 0.025,
    "fine": 0.025,
    "blue": 0.030,
    "superior": 0.030,
    "purple": 0.035,
    "epic": 0.035,
    "gold": 0.040,
    "legendary": 0.040,
}

# CP160 Truly Superb Gold Glyph of Bracing.
TRULY_SUPERB_BRACING_REDUCTION = 203.0

# Gold jewelry Infused increases enchantment effectiveness by 60%.
JEWELRY_INFUSED_PERCENT_BY_QUALITY = {
    "white": 0.24,
    "normal": 0.24,
    "green": 0.30,
    "fine": 0.30,
    "blue": 0.36,
    "superior": 0.36,
    "purple": 0.48,
    "epic": 0.48,
    "gold": 0.60,
    "legendary": 0.60,
}

_BRACING_ENCHANT_NAMES = {
    "block cost",
    "reduce block cost",
    "bracing",
    "glyph of bracing",
}


class BlockItemInputResolver:
    """Apply verified static item sources that use block-specific stacking.

    Sturdy is a sequential percentage modifier. Glyph of Bracing is a flat
    reduction and therefore enters the block-cost pipeline before percentage
    modifiers. These rules deliberately bypass the generic stat-effect path.
    """

    @staticmethod
    def _apply_sturdy(result: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        modifiers = list(result.core.block_cost.sequential_modifiers)
        unresolved = list(result.unresolved)
        applied = result.applied_effect_count

        for slot_name, entry in build.Armor.items():
            if str(entry.get("Trait", "") or "").strip().casefold() != "sturdy":
                continue

            level = str(entry.get("Level", "") or "").strip()
            quality = str(entry.get("Quality", "") or "").strip()
            if level.casefold() != "cp160":
                unresolved.append(
                    f"{slot_name} Sturdy: needs verified CP160 trait scaling ({level or 'level unset'})"
                )
                continue

            percent = STURDY_PERCENT_BY_QUALITY.get(quality.casefold())
            if percent is None:
                unresolved.append(
                    f"{slot_name} Sturdy: trait value unavailable for quality {quality or 'unset'}"
                )
                continue

            modifiers.append(BlockCostModifier(f"{slot_name}: Sturdy", -percent))
            applied += 1

        return replace(
            result,
            core=replace(
                result.core,
                block_cost=replace(
                    result.core.block_cost,
                    sequential_modifiers=tuple(modifiers),
                ),
            ),
            applied_effect_count=applied,
            unresolved=tuple(unresolved),
        )

    @staticmethod
    def _bracing_reduction(slot_name: str, slot: GearSlot, unresolved: list[str]) -> tuple[float, str]:
        level = str(slot.Level or "").strip()
        tier = str(slot.EnchantTier or "").strip()
        if level.casefold() != "cp160" or tier.casefold() != "truly superb":
            unresolved.append(
                f"{slot_name} Block Cost: needs verified CP160/Truly Superb scaling "
                f"({level or 'level unset'}, {tier or 'tier unset'})"
            )
            return 0.0, ""

        multiplier = 1.0
        suffix = ""
        if str(slot.Trait or "").strip().casefold() == "infused":
            quality = str(slot.Quality or "").strip()
            infused = JEWELRY_INFUSED_PERCENT_BY_QUALITY.get(quality.casefold())
            if infused is None:
                unresolved.append(
                    f"{slot_name}: Infused jewelry value unavailable for quality {quality or 'unset'}"
                )
                return 0.0, ""
            multiplier += infused
            suffix = f" (Infused +{infused * 100:g}%)"

        return TRULY_SUPERB_BRACING_REDUCTION * multiplier, suffix

    @classmethod
    def _apply_bracing(cls, result: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        reductions = list(result.core.block_cost.flat_reductions)
        unresolved = list(result.unresolved)
        applied = result.applied_effect_count

        for slot_name, slot in (
            ("Necklace", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
        ):
            enchant = str(slot.Enchant or "").strip().casefold()
            if enchant not in _BRACING_ENCHANT_NAMES:
                continue

            reduction, suffix = cls._bracing_reduction(slot_name, slot, unresolved)
            if reduction <= 0.0:
                continue

            reductions.append((f"{slot_name}: Glyph of Bracing{suffix}", reduction))
            applied += 1

        return replace(
            result,
            core=replace(
                result.core,
                block_cost=replace(
                    result.core.block_cost,
                    flat_reductions=tuple(reductions),
                ),
            ),
            applied_effect_count=applied,
            unresolved=tuple(unresolved),
        )

    def apply(self, result: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        result = self._apply_sturdy(result, build)
        return self._apply_bracing(result, build)
