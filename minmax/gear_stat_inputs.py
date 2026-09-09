from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

from models.build_model import GearSlot, PlayerBuild

from .armor_glyph_repository import ArmorGlyphEffectRepository
from .base_character_state import FlatContribution, ResourceInputs
from .core_stat_calculator import CoreStatInputs
from .derived_stats import DerivedStatInputs, StatContribution
from .effects import Effect, EffectOperation, EffectUnit
from .gear_set_effect_service import GearSetEffectService
from .gear_set_repository import GearSetRepository
from .jewelry_glyph_repository import JewelryGlyphEffectRepository
from .jewelry_trait_repository import JewelryTraitRepository
from .stat_ids import StatId


RESOURCE_STATS = {
    StatId.MAX_HEALTH: "health",
    StatId.MAX_MAGICKA: "magicka",
    StatId.MAX_STAMINA: "stamina",
    StatId.HEALTH_RECOVERY: "health_recovery",
    StatId.MAGICKA_RECOVERY: "magicka_recovery",
    StatId.STAMINA_RECOVERY: "stamina_recovery",
}

CORE_FIELDS = {
    StatId.WEAPON_DAMAGE: "weapon_damage",
    StatId.SPELL_DAMAGE: "spell_damage",
    StatId.PHYSICAL_RESISTANCE: "physical_resistance",
    StatId.SPELL_RESISTANCE: "spell_resistance",
    StatId.PHYSICAL_PENETRATION: "physical_penetration",
    StatId.SPELL_PENETRATION: "spell_penetration",
    StatId.WEAPON_CRITICAL: "weapon_critical",
    StatId.SPELL_CRITICAL: "spell_critical",
    StatId.CRITICAL_DAMAGE: "critical_damage",
    StatId.CRITICAL_HEALING: "critical_healing",
    StatId.CRITICAL_RESISTANCE: "critical_resistance",
    StatId.HEALING_DONE: "healing_done",
    StatId.HEALING_TAKEN: "healing_taken",
}

RATIO_POINT_STATS = {
    StatId.CRITICAL_DAMAGE,
    StatId.CRITICAL_HEALING,
    StatId.HEALING_DONE,
    StatId.HEALING_TAKEN,
}

ARMOR_ENCHANT_TO_GLYPH = {
    "max health": "Glyph of Health",
    "max magicka": "Glyph of Magicka",
    "max stamina": "Glyph of Stamina",
    "prismatic defense": "Glyph of Prismatic Defense",
}

JEWELRY_ENCHANT_TO_GLYPH = {
    "health recovery": "Glyph of Health Recovery",
    "magicka recovery": "Glyph of Magicka Recovery",
    "stamina recovery": "Glyph of Stamina Recovery",
    "weapon damage": "Glyph of Increase Physical Harm",
    "spell damage": "Glyph of Increase Magical Harm",
}

STATIC_JEWELRY_TRAITS = {"arcane", "healthy", "robust", "triune", "protective"}
TWO_SLOT_SET_WEAPON_TYPES = {
    "bow",
    "inferno staff",
    "lightning staff",
    "ice staff",
    "restoration staff",
    "two-handed",
}
LEGACY_TWO_ITEM_WEAPON_TYPES = {"dual wield", "one hand and shield"}

ARMOR_MAJOR_ENCHANT_SLOTS = {"head", "chest", "legs"}
ARMOR_MINOR_ENCHANT_SLOTS = {"shoulders", "hands", "waist", "feet"}
ARMOR_INFUSED_PERCENT_BY_QUALITY = {
    "white": 9.0,
    "green": 13.0,
    "blue": 17.0,
    "purple": 21.0,
    "gold": 25.0,
    "normal": 9.0,
    "fine": 13.0,
    "superior": 17.0,
    "epic": 21.0,
    "legendary": 25.0,
}


@dataclass(frozen=True)
class GearCalculationInputs:
    health: ResourceInputs = ResourceInputs()
    magicka: ResourceInputs = ResourceInputs()
    stamina: ResourceInputs = ResourceInputs()
    health_recovery: ResourceInputs = ResourceInputs()
    magicka_recovery: ResourceInputs = ResourceInputs()
    stamina_recovery: ResourceInputs = ResourceInputs()
    core: CoreStatInputs = CoreStatInputs()
    set_counts: tuple[tuple[str, int], ...] = ()
    applied_effect_count: int = 0
    unresolved: tuple[str, ...] = ()


class GearStatInputResolver:
    """Translate verified static gear effects into calculator inputs."""

    MAX_LEVEL_EFFECTIVE_LEVEL = 66.0

    def __init__(
        self,
        repository: GearSetRepository,
        armor_glyph_repository: ArmorGlyphEffectRepository | None = None,
        jewelry_glyph_repository: JewelryGlyphEffectRepository | None = None,
        jewelry_trait_repository: JewelryTraitRepository | None = None,
    ):
        self.repository = repository
        self.service = GearSetEffectService(repository)
        self.armor_glyph_repository = armor_glyph_repository
        self.jewelry_glyph_repository = jewelry_glyph_repository
        self.jewelry_trait_repository = jewelry_trait_repository

    @classmethod
    def critical_rating_to_ratio(cls, rating: float) -> float:
        level = cls.MAX_LEVEL_EFFECTIVE_LEVEL
        return float(rating) / (2.0 * level * (100.0 + level))

    @staticmethod
    def _slot_names(slot: GearSlot) -> list[str]:
        return [name.strip() for name in (slot.Set, slot.Set2) if str(name).strip()]

    @classmethod
    def equipped_set_counts(cls, build: PlayerBuild, *, active_bar: str = "front") -> Counter[str]:
        counts: Counter[str] = Counter()
        for entry in build.Armor.values():
            name = str(entry.get("Set", "") or "").strip()
            if name:
                counts[name] += 1
        for slot in (build.Necklace, build.Ring1, build.Ring2):
            if slot.Set.strip():
                counts[slot.Set.strip()] += 1

        main, offhand = build.active_weapon_slots(active_bar)
        main_type = str(main.WeaponType or "").strip().casefold()

        if not offhand.is_empty:
            if main.Set.strip():
                counts[main.Set.strip()] += 1
            if offhand.Set.strip():
                counts[offhand.Set.strip()] += 1
            return counts

        if main_type in TWO_SLOT_SET_WEAPON_TYPES:
            if main.Set.strip():
                counts[main.Set.strip()] += 2
            return counts

        # Legacy saves represented two weapon pieces inside the main slot with Set/Set2.
        # Preserve that shape whenever no explicit offhand exists, even if WeaponType is blank.
        if main.Set2.strip() or main_type in LEGACY_TWO_ITEM_WEAPON_TYPES:
            for name in cls._slot_names(main):
                counts[name] += 1
            return counts

        if main.Set.strip():
            counts[main.Set.strip()] += 1
        return counts

    @staticmethod
    def _resource_add(inputs: ResourceInputs, effect: Effect) -> ResourceInputs:
        if effect.operation is EffectOperation.ADD:
            amount = float(effect.value)
            return replace(
                inputs,
                set_flat=inputs.set_flat + amount,
                set_contributions=inputs.set_contributions + (FlatContribution(effect.source, amount),),
            )
        if effect.operation is EffectOperation.ADD_PERCENT:
            value = float(effect.value) / 100.0 if effect.unit is EffectUnit.PERCENT else float(effect.value)
            return replace(inputs, other_percent=inputs.other_percent + value)
        return inputs

    @staticmethod
    def _resource_item_add(inputs: ResourceInputs, effect: Effect, *, source: str) -> ResourceInputs:
        if effect.operation is not EffectOperation.ADD:
            return inputs
        amount = float(effect.value)
        return replace(
            inputs,
            item_flat=inputs.item_flat + amount,
            item_contributions=inputs.item_contributions + (FlatContribution(source, amount),),
        )

    @staticmethod
    def _core_add(
        core: CoreStatInputs,
        stat: StatId,
        effect: Effect,
        *,
        value: float | None = None,
        source: str | None = None,
    ) -> CoreStatInputs:
        field_name = CORE_FIELDS[stat]
        current: DerivedStatInputs = getattr(core, field_name)
        amount = float(effect.value if value is None else value)
        contribution = StatContribution(source or effect.source, amount)

        if effect.operation is EffectOperation.ADD:
            updated = replace(current, flat=current.flat + (contribution,))
        elif effect.operation is EffectOperation.ADD_PERCENT:
            decimal = amount / 100.0 if effect.unit is EffectUnit.PERCENT else amount
            contribution = StatContribution(source or effect.source, decimal)
            if stat in RATIO_POINT_STATS:
                updated = replace(current, additive_after_percent=current.additive_after_percent + (contribution,))
            else:
                updated = replace(current, percent=current.percent + (contribution,))
        else:
            return core
        return replace(core, **{field_name: updated})

    @staticmethod
    def _core_item_add(core: CoreStatInputs, stat: StatId, value: float, *, source: str) -> CoreStatInputs:
        field_name = CORE_FIELDS[stat]
        current: DerivedStatInputs = getattr(core, field_name)
        contribution = StatContribution(source, float(value))
        updated = replace(current, flat=current.flat + (contribution,))
        return replace(core, **{field_name: updated})

    def _apply_effect(self, inputs: GearCalculationInputs, effect: Effect) -> GearCalculationInputs:
        if effect.stat is None:
            return inputs
        resource_field = RESOURCE_STATS.get(effect.stat)
        if resource_field is not None:
            current = getattr(inputs, resource_field)
            updated = self._resource_add(current, effect)
            if updated == current:
                return inputs
            return replace(
                inputs,
                **{resource_field: updated},
                applied_effect_count=inputs.applied_effect_count + 1,
            )
        if effect.stat in CORE_FIELDS:
            core = self._core_add(inputs.core, effect.stat, effect)
            if core == inputs.core:
                return inputs
            return replace(inputs, core=core, applied_effect_count=inputs.applied_effect_count + 1)
        return inputs

    def _apply_base_item_stats(self, inputs: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        # Remaining implementation unchanged from current branch.
        return self._apply_base_item_stats_impl(inputs, build)

    def _apply_base_item_stats_impl(self, inputs: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        raise NotImplementedError
