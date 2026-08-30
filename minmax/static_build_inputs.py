from __future__ import annotations

from dataclasses import replace

from models.build_model import PlayerBuild

from .base_character_state import ResourceInputs
from .champion_point_static_repository import ChampionPointStaticRepository
from .derived_stats import StatContribution
from .effects import Effect, EffectOperation, EffectUnit
from .gear_stat_inputs import CORE_FIELDS, RESOURCE_STATS, RATIO_POINT_STATS, GearCalculationInputs
from .mundus_repository import MundusRepository
from .provisioning_static_repository import ProvisioningStaticRepository
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
    """Apply permanent/static build choices after the gear input layer."""

    MAX_LEVEL_EFFECTIVE_LEVEL = 66.0
    _RESOLVED_DIVINES_WARNING = "Divines: requires Mundus Stone resolution"

    def __init__(
        self,
        mundus_repository: MundusRepository | None = None,
        champion_point_repository: ChampionPointStaticRepository | None = None,
        provisioning_repository: ProvisioningStaticRepository | None = None,
    ) -> None:
        self.mundus_repository = mundus_repository
        self.champion_point_repository = champion_point_repository
        self.provisioning_repository = provisioning_repository

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
    def _resource_add(inputs: ResourceInputs, effect: Effect, bucket: str) -> ResourceInputs:
        if effect.operation is EffectOperation.ADD:
            value = float(effect.value)
            if bucket == "mundus":
                return replace(inputs, mundus_flat=inputs.mundus_flat + value)
            if bucket == "food":
                return replace(inputs, food_flat=inputs.food_flat + value)
            if bucket == "champion":
                return replace(inputs, champion_flat=inputs.champion_flat + value)
            return replace(inputs, other_flat=inputs.other_flat + value)
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

    @staticmethod
    def _apply_block_effect(result: GearCalculationInputs, effect: Effect) -> GearCalculationInputs:
        if effect.stat is StatId.BLOCK_COST and effect.operation is EffectOperation.ADD:
            block_cost = replace(
                result.core.block_cost,
                flat_reductions=result.core.block_cost.flat_reductions
                + ((effect.source, float(effect.value)),),
            )
            return replace(
                result,
                core=replace(result.core, block_cost=block_cost),
                applied_effect_count=result.applied_effect_count + 1,
            )

        if effect.stat is StatId.BLOCK_MITIGATION and effect.operation is EffectOperation.ADD_PERCENT:
            decimal = float(effect.value) / 100.0 if effect.unit is EffectUnit.PERCENT else float(effect.value)
            block_mitigation = replace(
                result.core.block_mitigation,
                amount_blocked_modifiers=result.core.block_mitigation.amount_blocked_modifiers
                + ((effect.source, decimal),),
            )
            return replace(
                result,
                core=replace(result.core, block_mitigation=block_mitigation),
                applied_effect_count=result.applied_effect_count + 1,
            )

        return result

    def _apply_effect(self, result: GearCalculationInputs, effect: Effect, *, resource_bucket: str) -> GearCalculationInputs:
        if effect.stat is None:
            return result
        if effect.stat in {StatId.BLOCK_COST, StatId.BLOCK_MITIGATION}:
            return self._apply_block_effect(result, effect)
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
            after = self._resource_add(before, effect, resource_bucket)
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

    def _apply_mundus(self, result: GearCalculationInputs, build: PlayerBuild, active_bar: str) -> GearCalculationInputs:
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
            result = self._apply_effect(result, effect, resource_bucket="mundus")
        return replace(result, unresolved=tuple(unresolved))

    def _apply_non_slottable_champion_points(self, result: GearCalculationInputs) -> GearCalculationInputs:
        """Apply the temporary profile assumption that passive CP stars are maxed when CP data is available."""

        if self.champion_point_repository is None:
            return result

        unresolved = list(result.unresolved)
        effects, passive_unresolved = self.champion_point_repository.resolve_all_non_slottable_maxed()
        unresolved.extend(passive_unresolved)
        for effect in effects:
            result = self._apply_effect(result, effect, resource_bucket="champion")
        return replace(result, unresolved=tuple(unresolved))

    def _apply_champion_points(self, result: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        entries = [entry for entry in build.ChampionPoints if str(entry.Name or "").strip()]
        if not entries:
            return result
        unresolved = list(result.unresolved)
        if self.champion_point_repository is None:
            unresolved.append("Champion Points selected but static CP repository unavailable")
            return replace(result, unresolved=tuple(unresolved))

        for entry in entries:
            record = self.champion_point_repository.get(entry.Name)
            if record is not None and record.is_non_slottable:
                # Passive stars were already applied at max rank above. Ignore a
                # legacy saved entry so the same passive cannot be counted twice.
                continue
            try:
                points = int(str(entry.Points or "0").strip() or 0)
            except (TypeError, ValueError):
                unresolved.append(f"Champion Point has invalid allocation: {entry.Name}: {entry.Points}")
                continue
            effects, cp_unresolved = self.champion_point_repository.resolve(entry.Name, points)
            unresolved.extend(cp_unresolved)
            for effect in effects:
                result = self._apply_effect(result, effect, resource_bucket="champion")
        return replace(result, unresolved=tuple(unresolved))

    def _apply_food(self, result: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        food_name = str(build.Food or "").strip()
        if not food_name:
            return result
        unresolved = list(result.unresolved)
        if self.provisioning_repository is None:
            unresolved.append(f"Food/Drink selected but provisioning repository unavailable: {food_name}")
            return replace(result, unresolved=tuple(unresolved))
        effects, food_unresolved = self.provisioning_repository.resolve(food_name)
        unresolved.extend(food_unresolved)
        for effect in effects:
            result = self._apply_effect(result, effect, resource_bucket="food")
        return replace(result, unresolved=tuple(unresolved))

    @staticmethod
    def _mark_unresolved_potion(result: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        potion_name = str(build.Potion or "").strip()
        if not potion_name:
            return result
        message = f"Potion selected but potion effects are not yet modeled: {potion_name}"
        if message in result.unresolved:
            return result
        return replace(result, unresolved=result.unresolved + (message,))

    def apply(self, result: GearCalculationInputs, build: PlayerBuild, *, active_bar: str = "front") -> GearCalculationInputs:
        # BaseItemStatResolver predates the DB-backed Mundus layer and emits a
        # placeholder warning for Divines. Divines itself has no sheet effect
        # without a Mundus; with one selected, this resolver applies it below.
        # Either way that old placeholder no longer represents unresolved math.
        result = replace(
            result,
            unresolved=tuple(
                message
                for message in result.unresolved
                if self._RESOLVED_DIVINES_WARNING not in message
            ),
        )
        result = self._apply_non_slottable_champion_points(result)
        result = self._apply_champion_points(result, build)
        result = self._apply_mundus(result, build, active_bar)
        result = self._apply_food(result, build)
        return self._mark_unresolved_potion(result, build)
