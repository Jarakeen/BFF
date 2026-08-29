from __future__ import annotations

from dataclasses import replace

from models.build_model import GearSlot, PlayerBuild

from .base_character_state import ResourceInputs
from .derived_stats import StatContribution
from .effects import Effect, EffectOperation, EffectUnit
from .gear_stat_inputs import CORE_FIELDS, RESOURCE_STATS, RATIO_POINT_STATS, GearCalculationInputs
from .mundus_repository import MundusRepository
from .stat_ids import StatId


DIVINES_PERCENT_BY_QUALITY = {
    "white": 5.1,
    "normal": 5.1,
    "green": 6.1,
    "fine": 6.1,
    "blue": 7.1,
    "superior": 7.1,
    "purple": 8.1,
    "epic": 8.1,
    "gold": 9.1,
    "legendary": 9.1,
}


class StaticBuildInputResolver:
    """Apply non-gear permanent build choices after the gear input layer."""

    MAX_LEVEL_EFFECTIVE_LEVEL = 66.0

    def __init__(self, mundus_repository: MundusRepository | None = None) -> None:
        self.mundus_repository = mundus_repository

    @classmethod
    def critical_rating_to_ratio(cls, rating: float) -> float:
        level = cls.MAX_LEVEL_EFFECTIVE_LEVEL
        return float(rating) / (2.0 * level * (100.0 + level))

    @staticmethod
    def _divines_from_slot(label: str, trait: str, quality: str, unresolved: list[str]) -> float:
        if str(trait or "").strip().casefold() != "divines":
            return 0.0
        percent = DIVINES_PERCENT_BY_QUALITY.get(str(quality or "").strip().casefold())
        if percent is None:
            unresolved.append(f"{label} Divines: quality required to resolve Mundus amplification")
            return 0.0
        return percent / 100.0

    def _mundus_multiplier(self, build: PlayerBuild, active_bar: str, unresolved: list[str]) -> float:
        bonus = 0.0
        for slot_name, entry in build.Armor.items():
            bonus += self._divines_from_slot(
                slot_name,
                str(entry.get("Trait", "") or ""),
                str(entry.get("Quality", "") or ""),
                unresolved,
            )

        _main, offhand = build.active_weapon_slots(active_bar)
        if str(offhand.WeaponType or "").strip().casefold() == "shield":
            bonus += self._divines_from_slot(
                f"{active_bar.title()} Bar Shield",
                offhand.Trait,
                offhand.Quality,
                unresolved,
            )
        return 1.0 + bonus

    @staticmethod
    def _resource_mundus_add(inputs: ResourceInputs, effect: Effect) -> ResourceInputs:
        if effect.operation is EffectOperation.ADD:
            return replace(inputs, mundus_flat=inputs.mundus_flat + float(effect.value))
        if effect.operation is EffectOperation.ADD_PERCENT:
            decimal = float(effect.value) / 100.0 if effect.unit is EffectUnit.PERCENT else float(effect.value)
            return replace(inputs, other_percent=inputs.other_percent + decimal)
        return inputs

    @staticmethod
    def _core_add(result: GearCalculationInputs, effect: Effect) -> GearCalculationInputs:
        if effect.stat not in CORE_FIELDS:
            return result
        field_name = CORE_FIELDS[effect.stat]
        current = getattr(result.core, field_name)
        amount = float(effect.value)
        contribution = StatContribution(effect.source, amount)
        if effect.operation is EffectOperation.ADD:
            updated = replace(current, flat=current.flat + (contribution,))
        elif effect.operation is EffectOperation.ADD_PERCENT:
            decimal = amount / 100.0 if effect.unit is EffectUnit.PERCENT else amount
            contribution = StatContribution(effect.source, decimal)
            if effect.stat in RATIO_POINT_STATS:
                updated = replace(current, additive_after_percent=current.additive_after_percent + (contribution,))
            else:
                updated = replace(current, percent=current.percent + (contribution,))
        else:
            return result
        return replace(result, core=replace(result.core, **{field_name: updated}))

    def _apply_effect(self, result: GearCalculationInputs, effect: Effect) -> GearCalculationInputs:
        if effect.stat is None:
            return result
        if effect.stat is StatId.CRITICAL_CHANCE:
            ratio = self.critical_rating_to_ratio(effect.value)
            contribution = StatContribution(effect.source, ratio)
            core = result.core
            return replace(
                result,
                core=replace(
                    core,
                    weapon_critical=replace(
                        core.weapon_critical,
                        additive_after_percent=core.weapon_critical.additive_after_percent + (contribution,),
                    ),
                    spell_critical=replace(
                        core.spell_critical,
                        additive_after_percent=core.spell_critical.additive_after_percent + (contribution,),
                    ),
                ),
                applied_effect_count=result.applied_effect_count + 2,
            )

        resource_field = RESOURCE_STATS.get(effect.stat)
        if resource_field:
            before = getattr(result, resource_field)
            after = self._resource_mundus_add(before, effect)
            if after != before:
                return replace(
                    result,
                    **{resource_field: after, "applied_effect_count": result.applied_effect_count + 1},
                )
            return result

        updated = self._core_add(result, effect)
        if updated != result:
            return replace(updated, applied_effect_count=result.applied_effect_count + 1)
        return result

    def apply(self, result: GearCalculationInputs, build: PlayerBuild, *, active_bar: str = "front") -> GearCalculationInputs:
        mundus_name = str(build.Mundus or "").strip()
        if not mundus_name:
            return result

        unresolved = list(result.unresolved)
        if self.mundus_repository is None:
            unresolved.append(f"Mundus selected but repository unavailable: {mundus_name}")
            return replace(result, unresolved=tuple(unresolved))

        multiplier = self._mundus_multiplier(build, active_bar, unresolved)
        effects, mundus_unresolved = self.mundus_repository.get_effects(mundus_name, multiplier=multiplier)
        unresolved.extend(mundus_unresolved)
        if not effects and not mundus_unresolved:
            unresolved.append(f"Mundus not found for active game update: {mundus_name}")

        for effect in effects:
            result = self._apply_effect(result, effect)
        return replace(result, unresolved=tuple(unresolved))
