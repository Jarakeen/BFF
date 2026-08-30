from __future__ import annotations

from dataclasses import replace
from math import floor

from models.build_model import GearSlot, PlayerBuild

from .base_character_state import FlatContribution, ResourceInputs
from .derived_stats import DerivedStatInputs, StatContribution
from .gear_stat_inputs import GearCalculationInputs


ARMOR_BASE_CP160_GOLD: dict[str, dict[str, float]] = {
    "Head": {"Light": 1221.0, "Medium": 1823.0, "Heavy": 2425.0},
    "Shoulders": {"Light": 1221.0, "Medium": 1823.0, "Heavy": 2425.0},
    "Chest": {"Light": 1396.0, "Medium": 2084.0, "Heavy": 2772.0},
    "Hands": {"Light": 698.0, "Medium": 1042.0, "Heavy": 1386.0},
    "Waist": {"Light": 523.0, "Medium": 781.0, "Heavy": 1039.0},
    "Legs": {"Light": 1221.0, "Medium": 1823.0, "Heavy": 2425.0},
    "Feet": {"Light": 1221.0, "Medium": 1823.0, "Heavy": 2425.0},
}

WEAPON_POWER_CP160_GOLD: dict[str, float] = {
    "Bow": 1335.0,
    "Inferno Staff": 1335.0,
    "Lightning Staff": 1335.0,
    "Ice Staff": 1335.0,
    "Restoration Staff": 1335.0,
    "Sword": 1335.0,
    "Axe": 1335.0,
    "Mace": 1335.0,
    "Dagger": 1335.0,
    "One Hand and Shield": 1335.0,
    "Two-Handed": 1571.0,
}

NAKED_LEVEL_50_POWER = 1000.0
SHIELD_ARMOR_CP160_GOLD = 1720.0
DUAL_WIELD_OFFHAND_POWER_RATIO = 0.177

ARMOR_REINFORCED_PERCENT_GOLD = 0.16
ARMOR_NIRNHONED_RESISTANCE_GOLD = 253.0
ARMOR_IMPENETRABLE_CRITICAL_RESISTANCE_GOLD = 132.0
ARMOR_INVIGORATING_RECOVERY_GOLD = 16.0

WEAPON_NIRNHONED_PERCENT_GOLD = 0.15
WEAPON_PRECISE_CRIT_GOLD = 0.036
WEAPON_SHARPENED_PENETRATION_GOLD = 1638.0
WEAPON_POWERED_HEALING_GOLD = 0.045
WEAPON_DEFENDING_RESISTANCE_GOLD = 1638.0

TWO_SLOT_WEAPON_TYPES = {
    "Bow",
    "Inferno Staff",
    "Lightning Staff",
    "Ice Staff",
    "Restoration Staff",
    "Two-Handed",
}
ONE_HANDED_WEAPON_TYPES = {"Sword", "Axe", "Mace", "Dagger"}


class BaseItemStatResolver:
    """Apply deterministic CP160 Legendary base item stats and static traits."""

    @staticmethod
    def _core_flat(core, field_name: str, label: str, amount: float):
        current: DerivedStatInputs = getattr(core, field_name)
        updated = replace(current, flat=current.flat + (StatContribution(label, float(amount)),))
        return replace(core, **{field_name: updated})

    @staticmethod
    def _core_additive_after_percent(core, field_name: str, label: str, amount: float):
        current: DerivedStatInputs = getattr(core, field_name)
        updated = replace(
            current,
            additive_after_percent=current.additive_after_percent + (StatContribution(label, float(amount)),),
        )
        return replace(core, **{field_name: updated})

    @staticmethod
    def _resource_item_flat(inputs: ResourceInputs, label: str, amount: float) -> ResourceInputs:
        value = float(amount)
        return replace(
            inputs,
            item_flat=inputs.item_flat + value,
            item_contributions=inputs.item_contributions + (FlatContribution(label, value),),
        )

    @staticmethod
    def _armor_equipped(entry: dict[str, str]) -> bool:
        return bool(
            str(entry.get("Set", "") or "").strip()
            or str(entry.get("Set2", "") or "").strip()
            or str(entry.get("Weight", "") or "").strip()
        )

    @staticmethod
    def _weapon_equipped(slot: GearSlot) -> bool:
        return bool(
            str(slot.Set or "").strip()
            or str(slot.Set2 or "").strip()
            or str(slot.WeaponType or "").strip()
        )

    @staticmethod
    def _gold_cp160(level: str, quality: str) -> bool:
        return str(level or "").strip().casefold() == "cp160" and str(quality or "").strip().casefold() == "gold"

    def _apply_armor_trait(
        self,
        *,
        core,
        slot_name: str,
        trait: str,
        rating: float,
        applied: int,
        unresolved: list[str],
    ):
        trait_key = trait.casefold()
        if not trait_key:
            return core, applied
        if trait_key == "reinforced":
            reinforced_rating = float(floor(rating * (1.0 + ARMOR_REINFORCED_PERCENT_GOLD)))
            bonus = reinforced_rating - rating
            label = f"{slot_name}: Reinforced armor ({rating:g} -> {reinforced_rating:g})"
            core = self._core_flat(core, "physical_resistance", label, bonus)
            core = self._core_flat(core, "spell_resistance", label, bonus)
            return core, applied + 2
        if trait_key == "nirnhoned":
            label = f"{slot_name}: Nirnhoned (+253 resistance)"
            core = self._core_flat(core, "physical_resistance", label, ARMOR_NIRNHONED_RESISTANCE_GOLD)
            core = self._core_flat(core, "spell_resistance", label, ARMOR_NIRNHONED_RESISTANCE_GOLD)
            return core, applied + 2
        if trait_key == "impenetrable":
            label = f"{slot_name}: Impenetrable (+132 Critical Resistance)"
            core = self._core_flat(core, "critical_resistance", label, ARMOR_IMPENETRABLE_CRITICAL_RESISTANCE_GOLD)
            return core, applied + 1
        if trait_key in {"invigorating", "infused"}:
            return core, applied
        if trait_key == "divines":
            unresolved.append(f"{slot_name} Divines: requires Mundus Stone resolution")
        elif trait_key in {"sturdy", "well-fitted", "training"}:
            unresolved.append(f"{slot_name} armor trait not yet resolved: {trait}")
        else:
            unresolved.append(f"{slot_name} unsupported armor trait: {trait}")
        return core, applied

    def _apply_invigorating(self, result: GearCalculationInputs, label: str) -> GearCalculationInputs:
        return replace(
            result,
            health_recovery=self._resource_item_flat(result.health_recovery, label, ARMOR_INVIGORATING_RECOVERY_GOLD),
            magicka_recovery=self._resource_item_flat(result.magicka_recovery, label, ARMOR_INVIGORATING_RECOVERY_GOLD),
            stamina_recovery=self._resource_item_flat(result.stamina_recovery, label, ARMOR_INVIGORATING_RECOVERY_GOLD),
        )

    def _apply_armor(self, result: GearCalculationInputs, build: PlayerBuild) -> GearCalculationInputs:
        unresolved = list(result.unresolved)
        applied = result.applied_effect_count
        core = result.core
        for slot_name, entry in build.Armor.items():
            if not self._armor_equipped(entry):
                continue
            level = str(entry.get("Level", "") or "").strip()
            quality = str(entry.get("Quality", "") or "").strip()
            weight = str(entry.get("Weight", "") or "").strip()
            trait = str(entry.get("Trait", "") or "").strip()
            if not self._gold_cp160(level, quality):
                unresolved.append(
                    f"{slot_name} armor base: CP160 Gold required ({level or 'level unset'}, {quality or 'quality unset'})"
                )
                continue
            slot_values = ARMOR_BASE_CP160_GOLD.get(slot_name)
            rating = slot_values.get(weight) if slot_values else None
            if rating is None:
                unresolved.append(f"{slot_name} armor base: weight missing or unsupported ({weight or 'unset'})")
                continue
            label = f"{slot_name}: {weight} armor base"
            core = self._core_flat(core, "physical_resistance", label, rating)
            core = self._core_flat(core, "spell_resistance", label, rating)
            applied += 2
            core, applied = self._apply_armor_trait(
                core=core,
                slot_name=slot_name,
                trait=trait,
                rating=rating,
                applied=applied,
                unresolved=unresolved,
            )
            if trait.casefold() == "invigorating":
                result = self._apply_invigorating(result, f"{slot_name}: Invigorating (+16 recovery)")
                applied += 3
        return replace(result, core=core, applied_effect_count=applied, unresolved=tuple(unresolved))

    @staticmethod
    def _weapon_trait_multiplier(weapon_type: str) -> float:
        return 2.0 if weapon_type in TWO_SLOT_WEAPON_TYPES else 1.0

    def _apply_weapon_trait(
        self,
        *,
        core,
        slot_name: str,
        weapon_type: str,
        trait: str,
        power: float,
        applied: int,
        unresolved: list[str],
        nirnhoned_scale: float = 1.0,
    ):
        trait_key = trait.casefold()
        if not trait_key:
            return core, applied
        if trait_key == "nirnhoned":
            nirn_power = float(floor(power * (1.0 + WEAPON_NIRNHONED_PERCENT_GOLD)))
            bonus = (nirn_power - power) * nirnhoned_scale
            label = f"{slot_name}: Nirnhoned weapon power ({power:g} -> {nirn_power:g})"
            core = self._core_flat(core, "weapon_damage", label, bonus)
            core = self._core_flat(core, "spell_damage", label, bonus)
            return core, applied + 2
        multiplier = self._weapon_trait_multiplier(weapon_type)
        if trait_key == "precise":
            amount = WEAPON_PRECISE_CRIT_GOLD * multiplier
            label = f"{slot_name}: Precise (+{amount * 100:g}% critical)"
            core = self._core_additive_after_percent(core, "weapon_critical", label, amount)
            core = self._core_additive_after_percent(core, "spell_critical", label, amount)
            return core, applied + 2
        if trait_key == "sharpened":
            amount = WEAPON_SHARPENED_PENETRATION_GOLD * multiplier
            label = f"{slot_name}: Sharpened (+{amount:g} penetration)"
            core = self._core_flat(core, "physical_penetration", label, amount)
            core = self._core_flat(core, "spell_penetration", label, amount)
            return core, applied + 2
        if trait_key == "powered":
            amount = WEAPON_POWERED_HEALING_GOLD * multiplier
            label = f"{slot_name}: Powered (+{amount * 100:g}% healing done)"
            core = self._core_additive_after_percent(core, "healing_done", label, amount)
            return core, applied + 1
        if trait_key == "defending":
            amount = WEAPON_DEFENDING_RESISTANCE_GOLD * multiplier
            label = f"{slot_name}: Defending (+{amount:g} resistance)"
            core = self._core_flat(core, "physical_resistance", label, amount)
            core = self._core_flat(core, "spell_resistance", label, amount)
            return core, applied + 2
        if trait_key == "infused":
            # Infused changes the weapon enchantment, not the static sheet by itself.
            return core, applied
        if trait_key == "charged":
            unresolved.append(f"{slot_name} Charged: requires status-effect chance model")
        elif trait_key == "decisive":
            unresolved.append(f"{slot_name} Decisive: requires Ultimate generation model")
        elif trait_key == "training":
            unresolved.append(f"{slot_name} Training: non-combat experience trait")
        else:
            unresolved.append(f"{slot_name} unsupported weapon trait: {trait}")
        return core, applied

    def _apply_shield(
        self,
        result: GearCalculationInputs,
        slot: GearSlot,
        *,
        slot_name: str,
    ) -> GearCalculationInputs:
        unresolved = list(result.unresolved)
        applied = result.applied_effect_count
        core = result.core
        if not self._gold_cp160(slot.Level, slot.Quality):
            unresolved.append(
                f"{slot_name} shield base: CP160 Gold required ({slot.Level or 'level unset'}, {slot.Quality or 'quality unset'})"
            )
            return replace(result, unresolved=tuple(unresolved))
        rating = SHIELD_ARMOR_CP160_GOLD
        core = self._core_flat(core, "physical_resistance", f"{slot_name}: Shield armor base", rating)
        core = self._core_flat(core, "spell_resistance", f"{slot_name}: Shield armor base", rating)
        applied += 2
        core, applied = self._apply_armor_trait(
            core=core,
            slot_name=slot_name,
            trait=str(slot.Trait or "").strip(),
            rating=rating,
            applied=applied,
            unresolved=unresolved,
        )
        if str(slot.Trait or "").strip().casefold() == "invigorating":
            result = self._apply_invigorating(result, f"{slot_name}: Invigorating (+16 recovery)")
            applied += 3
        return replace(result, core=core, applied_effect_count=applied, unresolved=tuple(unresolved))

    def _apply_weapon(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str,
    ) -> GearCalculationInputs:
        unresolved = list(result.unresolved)
        applied = result.applied_effect_count
        core = result.core
        is_front = active_bar.casefold() == "front"
        bar_name = "Front Bar" if is_front else "Back Bar"
        main, offhand = build.active_weapon_slots(active_bar)

        if not self._weapon_equipped(main):
            return result
        if not self._gold_cp160(main.Level, main.Quality):
            unresolved.append(
                f"{bar_name} weapon base: CP160 Gold required ({main.Level or 'level unset'}, {main.Quality or 'quality unset'})"
            )
            return replace(result, unresolved=tuple(unresolved))

        main_type = str(main.WeaponType or "").strip()
        if main_type.casefold() == "dual wield" and offhand.is_empty:
            unresolved.append(f"{bar_name} weapon base: legacy Dual Wield needs explicit main/off-hand weapons")
            return replace(result, unresolved=tuple(unresolved))

        main_power = WEAPON_POWER_CP160_GOLD.get(main_type)
        if main_power is None:
            unresolved.append(f"{bar_name} weapon base: weapon type missing or unsupported ({main_type or 'unset'})")
            return replace(result, unresolved=tuple(unresolved))

        explicit_offhand = not offhand.is_empty
        off_type = str(offhand.WeaponType or "").strip() if explicit_offhand else ""
        dual_wield = explicit_offhand and main_type in ONE_HANDED_WEAPON_TYPES and off_type in ONE_HANDED_WEAPON_TYPES
        sword_board = explicit_offhand and main_type in ONE_HANDED_WEAPON_TYPES and off_type == "Shield"

        if explicit_offhand and not (dual_wield or sword_board):
            unresolved.append(f"{bar_name} weapon base: unsupported main/off-hand combination ({main_type or 'unset'} + {off_type or 'unset'})")
            return replace(result, unresolved=tuple(unresolved))

        adjustment = main_power - NAKED_LEVEL_50_POWER
        core = self._core_flat(core, "weapon_damage", f"{bar_name}: {main_type} base weapon power ({main_power:g})", adjustment)
        core = self._core_flat(core, "spell_damage", f"{bar_name}: {main_type} base weapon power ({main_power:g})", adjustment)
        applied += 2
        core, applied = self._apply_weapon_trait(
            core=core,
            slot_name=bar_name,
            weapon_type=main_type,
            trait=str(main.Trait or "").strip(),
            power=main_power,
            applied=applied,
            unresolved=unresolved,
        )

        if dual_wield:
            if not self._gold_cp160(offhand.Level, offhand.Quality):
                unresolved.append(
                    f"{bar_name} Off Hand weapon base: CP160 Gold required ({offhand.Level or 'level unset'}, {offhand.Quality or 'quality unset'})"
                )
            else:
                off_power = WEAPON_POWER_CP160_GOLD.get(off_type)
                if off_power is None:
                    unresolved.append(f"{bar_name} Off Hand weapon type unsupported: {off_type or 'unset'}")
                else:
                    contribution = float(floor(off_power * DUAL_WIELD_OFFHAND_POWER_RATIO))
                    label = f"{bar_name} Off Hand: {off_type} contribution ({DUAL_WIELD_OFFHAND_POWER_RATIO * 100:g}% of {off_power:g})"
                    core = self._core_flat(core, "weapon_damage", label, contribution)
                    core = self._core_flat(core, "spell_damage", label, contribution)
                    applied += 2
                    core, applied = self._apply_weapon_trait(
                        core=core,
                        slot_name=f"{bar_name} Off Hand",
                        weapon_type=off_type,
                        trait=str(offhand.Trait or "").strip(),
                        power=off_power,
                        applied=applied,
                        unresolved=unresolved,
                        nirnhoned_scale=DUAL_WIELD_OFFHAND_POWER_RATIO,
                    )

        result = replace(result, core=core, applied_effect_count=applied, unresolved=tuple(unresolved))
        if sword_board:
            result = self._apply_shield(result, offhand, slot_name=f"{bar_name} Shield")
        return result

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
    ) -> GearCalculationInputs:
        result = self._apply_armor(result, build)
        return self._apply_weapon(result, build, active_bar=active_bar)
