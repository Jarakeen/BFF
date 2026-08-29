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
    StatId.CRITICAL_RESISTANCE: "critical_resistance",
    StatId.HEALING_DONE: "healing_done",
    StatId.HEALING_TAKEN: "healing_taken",
}

RATIO_POINT_STATS = {
    StatId.CRITICAL_DAMAGE,
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

        weapon = build.FrontBarWeapon if active_bar.casefold() == "front" else build.BackBarWeapon
        for name in cls._slot_names(weapon):
            counts[name] += 1
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
    def _armor_glyph_multiplier(slot_name: str, entry: dict[str, str], unresolved: list[str]) -> tuple[float, str]:
        slot_key = str(slot_name or "").strip().casefold()
        if slot_key in ARMOR_MAJOR_ENCHANT_SLOTS:
            multiplier = 1.0
            labels: list[str] = []
        elif slot_key in ARMOR_MINOR_ENCHANT_SLOTS:
            multiplier = 0.4
            labels = ["minor slot 40%"]
        else:
            unresolved.append(f"{slot_name} armor enchantment slot size is unknown")
            return 0.0, ""

        trait = str(entry.get("Trait", "") or "").strip()
        if trait.casefold() == "infused":
            quality = str(entry.get("Quality", "") or "").strip()
            percent = ARMOR_INFUSED_PERCENT_BY_QUALITY.get(quality.casefold())
            if percent is None:
                unresolved.append(
                    f"{slot_name} Infused: enchantment value unavailable for quality {quality or 'unset'}"
                )
                return 0.0, ""
            multiplier *= 1.0 + (percent / 100.0)
            labels.append(f"Infused +{percent:g}%")

        suffix = f" ({', '.join(labels)})" if labels else ""
        return multiplier, suffix

    def _apply_armor_glyphs(self, result: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        if self.armor_glyph_repository is None:
            return result

        unresolved = list(result.unresolved)
        applied = result.applied_effect_count

        for slot_name, entry in build.Armor.items():
            enchant = str(entry.get("Enchant", "") or "").strip()
            if not enchant:
                continue

            glyph_name = ARMOR_ENCHANT_TO_GLYPH.get(enchant.casefold())
            if glyph_name is None:
                unresolved.append(f"{slot_name} enchant not yet resolved: {enchant}")
                continue

            level = str(entry.get("Level", "") or "").strip()
            tier = str(entry.get("EnchantTier", "") or "").strip()
            if level.casefold() != "cp160" or tier.casefold() != "truly superb":
                unresolved.append(
                    f"{slot_name} {enchant}: needs verified level/tier scaling ({level or 'level unset'}, {tier or 'tier unset'})"
                )
                continue

            multiplier, slot_label = self._armor_glyph_multiplier(slot_name, entry, unresolved)
            if multiplier == 0.0:
                continue

            effects = self.armor_glyph_repository.get_armor_glyph_effect_by_name(glyph_name, use_max_value=True)
            if not effects:
                unresolved.append(f"{slot_name} glyph not found: {glyph_name}")
                continue

            for base_effect in effects:
                stat = base_effect.stat
                resource_field = RESOURCE_STATS.get(stat) if stat is not None else None
                if not resource_field:
                    unresolved.append(f"{slot_name} unsupported armor glyph effect: {stat.value if stat else 'unknown'}")
                    continue
                effect = replace(base_effect, value=float(base_effect.value) * multiplier)
                before = getattr(result, resource_field)
                source = f"{slot_name}: {base_effect.source}{slot_label}"
                after = self._resource_item_add(before, effect, source=source)
                if after != before:
                    result = replace(result, **{resource_field: after})
                    applied += 1

        return replace(result, applied_effect_count=applied, unresolved=tuple(unresolved))

    def _apply_jewelry_traits(self, result: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        unresolved = list(result.unresolved)
        applied = result.applied_effect_count
        slots = (
            ("Necklace", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
        )

        for slot_name, slot in slots:
            trait = str(slot.Trait or "").strip()
            trait_key = trait.casefold()
            if not trait or trait_key == "infused":
                continue

            if trait_key not in STATIC_JEWELRY_TRAITS:
                unresolved.append(f"{slot_name} jewelry trait not yet resolved: {trait}")
                continue

            if self.jewelry_trait_repository is None:
                unresolved.append(f"{slot_name}: jewelry trait repository unavailable for {trait}")
                continue

            quality = str(slot.Quality or "").strip()
            level = str(slot.Level or "").strip()
            if level.casefold() != "cp160" or not quality:
                unresolved.append(
                    f"{slot_name} {trait}: needs verified max-level quality ({level or 'level unset'}, {quality or 'quality unset'})"
                )
                continue

            effects = self.jewelry_trait_repository.get_static_effects(
                trait,
                quality=quality,
                level=level,
            )
            if not effects:
                unresolved.append(f"{slot_name} {trait}: no matching static trait effects found")
                continue

            for effect in effects:
                stat = effect.stat
                if stat is None:
                    continue
                source = f"{slot_name}: {trait}"
                resource_field = RESOURCE_STATS.get(stat)
                if resource_field:
                    before = getattr(result, resource_field)
                    after = self._resource_item_add(before, effect, source=source)
                    if after != before:
                        result = replace(result, **{resource_field: after})
                        applied += 1
                    continue
                if stat in CORE_FIELDS:
                    new_core = self._core_add(result.core, stat, effect, source=source)
                    if new_core != result.core:
                        result = replace(result, core=new_core)
                        applied += 1
                    continue
                unresolved.append(f"{slot_name} unsupported jewelry trait effect: {stat.value}")

        return replace(result, applied_effect_count=applied, unresolved=tuple(unresolved))

    def _jewelry_effect_multiplier(self, slot_name: str, slot: GearSlot, unresolved: list[str]) -> tuple[float, str]:
        trait = str(slot.Trait or "").strip()
        if trait.casefold() != "infused":
            return 1.0, ""

        if self.jewelry_trait_repository is None:
            unresolved.append(f"{slot_name}: Infused jewelry trait repository unavailable")
            return 0.0, ""

        quality = str(slot.Quality or "").strip()
        percent = self.jewelry_trait_repository.get_infused_enchantment_percent(quality)
        if percent is None:
            unresolved.append(f"{slot_name}: Infused jewelry value unavailable for quality {quality or 'unset'}")
            return 0.0, ""

        return 1.0 + (percent / 100.0), f" (Infused +{percent:g}%)"

    def _apply_jewelry_glyphs(self, result: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        if self.jewelry_glyph_repository is None:
            return result

        unresolved = list(result.unresolved)
        applied = result.applied_effect_count
        slots = (
            ("Necklace", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
        )

        for slot_name, slot in slots:
            enchant = str(slot.Enchant or "").strip()
            if not enchant:
                continue

            glyph_name = JEWELRY_ENCHANT_TO_GLYPH.get(enchant.casefold())
            if glyph_name is None:
                unresolved.append(f"{slot_name} enchant not yet resolved: {enchant}")
                continue

            level = str(slot.Level or "").strip()
            tier = str(slot.EnchantTier or "").strip()
            if level.casefold() != "cp160" or tier.casefold() != "truly superb":
                unresolved.append(
                    f"{slot_name} {enchant}: needs verified level/tier scaling ({level or 'level unset'}, {tier or 'tier unset'})"
                )
                continue

            multiplier, trait_label = self._jewelry_effect_multiplier(slot_name, slot, unresolved)
            if multiplier == 0.0:
                continue

            effects = self.jewelry_glyph_repository.get_jewelry_glyph_effect_by_name(glyph_name, use_max_value=True)
            if not effects:
                unresolved.append(f"{slot_name} glyph not found: {glyph_name}")
                continue

            for base_effect in effects:
                stat = base_effect.stat
                if stat is None:
                    unresolved.append(f"{slot_name} unsupported jewelry glyph effect: unknown")
                    continue

                effect = replace(base_effect, value=float(base_effect.value) * multiplier)
                source = f"{slot_name}: {base_effect.source}{trait_label}"
                resource_field = RESOURCE_STATS.get(stat)
                if resource_field:
                    before = getattr(result, resource_field)
                    after = self._resource_item_add(before, effect, source=source)
                    if after != before:
                        result = replace(result, **{resource_field: after})
                        applied += 1
                    continue

                if stat in CORE_FIELDS:
                    new_core = self._core_add(result.core, stat, effect, source=source)
                    if new_core != result.core:
                        result = replace(result, core=new_core)
                        applied += 1
                    continue

                unresolved.append(f"{slot_name} unsupported jewelry glyph effect: {stat.value}")

        return replace(result, applied_effect_count=applied, unresolved=tuple(unresolved))

    def resolve(self, build: PlayerBuild, *, active_bar: str = "front") -> GearCalculationInputs:
        result = GearCalculationInputs()
        counts = self.equipped_set_counts(build, active_bar=active_bar)
        result = replace(result, set_counts=tuple(sorted(counts.items())))
        unresolved: list[str] = []
        applied = 0

        for set_name, piece_count in counts.items():
            gear_set = self.repository.get_set(set_name)
            if gear_set is None:
                unresolved.append(f"Unknown set: {set_name}")
                continue

            effects = self.service.resolve_effects(gear_set.id, piece_count)
            for effect in effects:
                if effect.condition:
                    continue
                stat = effect.stat
                if stat is None:
                    continue

                resource_field = RESOURCE_STATS.get(stat)
                if resource_field:
                    before = getattr(result, resource_field)
                    after = self._resource_add(before, effect)
                    if after != before:
                        result = replace(result, **{resource_field: after})
                        applied += 1
                    continue

                if stat is StatId.CRITICAL_CHANCE and effect.operation is EffectOperation.ADD:
                    ratio = self.critical_rating_to_ratio(effect.value)
                    for target in (StatId.WEAPON_CRITICAL, StatId.SPELL_CRITICAL):
                        current: DerivedStatInputs = getattr(result.core, CORE_FIELDS[target])
                        contribution = StatContribution(f"{effect.source} (critical rating)", ratio)
                        updated = replace(current, additive_after_percent=current.additive_after_percent + (contribution,))
                        result = replace(result, core=replace(result.core, **{CORE_FIELDS[target]: updated}))
                    applied += 2
                    continue

                if stat in CORE_FIELDS:
                    new_core = self._core_add(result.core, stat, effect)
                    if new_core != result.core:
                        result = replace(result, core=new_core)
                        applied += 1
                    continue

                unresolved.append(f"Unsupported static effect: {set_name}: {stat.value}")

        result = replace(result, applied_effect_count=applied, unresolved=tuple(unresolved))
        result = self._apply_armor_glyphs(result, build)
        result = self._apply_jewelry_traits(result, build)
        return self._apply_jewelry_glyphs(result, build)
