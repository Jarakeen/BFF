from __future__ import annotations

from dataclasses import replace
from math import floor

from models.build_model import GearSlot, PlayerBuild

from .derived_stats import DerivedStatInputs, StatContribution
from .gear_stat_inputs import GearCalculationInputs


# CP160 Legendary armor values from the mined ESO item catalog. Values are the
# untraited baseline endpoints; Reinforced and Nirnhoned are applied below as
# independently traceable trait effects.
ARMOR_BASE_CP160_GOLD: dict[str, dict[str, float]] = {
    "Head": {"Light": 1221.0, "Medium": 1823.0, "Heavy": 2425.0},
    "Shoulders": {"Light": 1221.0, "Medium": 1823.0, "Heavy": 2425.0},
    "Chest": {"Light": 1396.0, "Medium": 2084.0, "Heavy": 2772.0},
    "Hands": {"Light": 698.0, "Medium": 1042.0, "Heavy": 1386.0},
    "Waist": {"Light": 523.0, "Medium": 781.0, "Heavy": 1039.0},
    "Legs": {"Light": 1221.0, "Medium": 1823.0, "Heavy": 2425.0},
    "Feet": {"Light": 1221.0, "Medium": 1823.0, "Heavy": 2425.0},
}

# CP160 Legendary equipped weapon power. The core calculator already supplies
# the naked level-50 1000 Weapon/Spell Damage baseline, so only the difference
# above that baseline is added to its trace.
WEAPON_POWER_CP160_GOLD: dict[str, float] = {
    "Bow": 1335.0,
    "Inferno Staff": 1335.0,
    "Lightning Staff": 1335.0,
    "Ice Staff": 1335.0,
    "Restoration Staff": 1335.0,
    "One Hand and Shield": 1335.0,
    "Two-Handed": 1571.0,
}

NAKED_LEVEL_50_POWER = 1000.0

# Verified current CP160 Legendary trait endpoints. Item-local traits live here
# because Reinforced and Nirnhoned modify the equipped item's own base value.
ARMOR_REINFORCED_PERCENT_GOLD = 0.16
ARMOR_NIRNHONED_RESISTANCE_GOLD = 253.0
ARMOR_IMPENETRABLE_CRITICAL_RESISTANCE_GOLD = 132.0

WEAPON_NIRNHONED_PERCENT_GOLD = 0.15
WEAPON_PRECISE_CRIT_GOLD = 0.036
WEAPON_SHARPENED_PENETRATION_GOLD = 1638.0
WEAPON_POWERED_HEALING_GOLD = 0.045
WEAPON_DEFENDING_RESISTANCE_GOLD = 1638.0

# Bows and staves occupy two weapon slots just like a melee two-hander. ESO
# doubles character-wide weapon-trait bonuses for two-slot weapons. Nirnhoned
# and Infused are item-local exceptions and do not double.
TWO_SLOT_WEAPON_TYPES = {
    "Bow",
    "Inferno Staff",
    "Lightning Staff",
    "Ice Staff",
    "Restoration Staff",
    "Two-Handed",
}

SUPPORTED_STATIC_ARMOR_TRAITS = {"reinforced", "nirnhoned", "impenetrable"}
SUPPORTED_STATIC_WEAPON_TRAITS = {"nirnhoned", "precise", "sharpened", "powered", "defending"}


class BaseItemStatResolver:
    """Apply deterministic CP160 Legendary base item stats and static traits.

    The resolver only models effects that can be calculated from the equipped
    item itself. Conditional/proc traits stay explicitly unresolved until the
    corresponding combat system exists.
    """

    @staticmethod
    def _core_flat(core, field_name: str, label: str, amount: float):
        current: DerivedStatInputs = getattr(core, field_name)
        updated = replace(
            current,
            flat=current.flat + (StatContribution(label, float(amount)),),
        )
        return replace(core, **{field_name: updated})

    @staticmethod
    def _core_additive_after_percent(core, field_name: str, label: str, amount: float):
        current: DerivedStatInputs = getattr(core, field_name)
        updated = replace(
            current,
            additive_after_percent=current.additive_after_percent
            + (StatContribution(label, float(amount)),),
        )
        return replace(core, **{field_name: updated})

    @staticmethod
    def _armor_equipped(entry: dict[str, str]) -> bool:
        return bool(
            str(entry.get("Set", "") or "").strip()
            or str(entry.get("Set2", "") or "").strip()
            or str(entry.get("Weight", "") or "").strip()
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
            bonus = rating * ARMOR_REINFORCED_PERCENT_GOLD
            label = f"{slot_name}: Reinforced (+16% item armor)"
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
            core = self._core_flat(
                core,
                "critical_resistance",
                label,
                ARMOR_IMPENETRABLE_CRITICAL_RESISTANCE_GOLD,
            )
            return core, applied + 1

        if trait_key == "divines":
            unresolved.append(f"{slot_name} Divines: requires Mundus Stone resolution")
        elif trait_key == "infused":
            unresolved.append(f"{slot_name} Infused: requires armor enchantment potency resolution")
        elif trait_key in {"sturdy", "well-fitted", "training", "invigorating"}:
            unresolved.append(f"{slot_name} armor trait not yet resolved: {trait}")
        else:
            unresolved.append(f"{slot_name} unsupported armor trait: {trait}")
        return core, applied

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
                    f"{slot_name} armor base: CP160 Gold required "
                    f"({level or 'level unset'}, {quality or 'quality unset'})"
                )
                continue

            slot_values = ARMOR_BASE_CP160_GOLD.get(slot_name)
            rating = slot_values.get(weight) if slot_values else None
            if rating is None:
                unresolved.append(
                    f"{slot_name} armor base: weight missing or unsupported ({weight or 'unset'})"
                )
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

        return replace(result, core=core, applied_effect_count=applied, unresolved=tuple(unresolved))

    @staticmethod
    def _weapon_equipped(slot: GearSlot) -> bool:
        return bool(
            str(slot.Set or "").strip()
            or str(slot.Set2 or "").strip()
            or str(getattr(slot, "WeaponType", "") or "").strip()
        )

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
    ):
        trait_key = trait.casefold()
        if not trait_key:
            return core, applied

        if trait_key == "nirnhoned":
            # ESO floors the item tooltip after applying Nirnhoned: 1335 -> 1535,
            # 1571 -> 1806. Add only the item-local difference to the trace.
            nirn_power = float(floor(power * (1.0 + WEAPON_NIRNHONED_PERCENT_GOLD)))
            bonus = nirn_power - power
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
            unresolved.append(f"{slot_name} Infused: requires weapon enchantment resolution")
        elif trait_key == "charged":
            unresolved.append(f"{slot_name} Charged: requires status-effect chance model")
        elif trait_key == "decisive":
            unresolved.append(f"{slot_name} Decisive: requires Ultimate generation model")
        elif trait_key == "training":
            unresolved.append(f"{slot_name} Training: non-combat experience trait")
        else:
            unresolved.append(f"{slot_name} unsupported weapon trait: {trait}")
        return core, applied

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
        slot = build.FrontBarWeapon if is_front else build.BackBarWeapon
        slot_name = "Front Bar" if is_front else "Back Bar"

        if not self._weapon_equipped(slot):
            return result

        level = str(slot.Level or "").strip()
        quality = str(slot.Quality or "").strip()
        weapon_type = str(getattr(slot, "WeaponType", "") or "").strip()
        trait = str(slot.Trait or "").strip()

        if not self._gold_cp160(level, quality):
            unresolved.append(
                f"{slot_name} weapon base: CP160 Gold required "
                f"({level or 'level unset'}, {quality or 'quality unset'})"
            )
            return replace(result, unresolved=tuple(unresolved))

        if weapon_type.casefold() == "dual wield":
            unresolved.append(
                f"{slot_name} weapon base: Dual Wield requires separate main/off-hand modeling"
            )
            return replace(result, unresolved=tuple(unresolved))

        power = WEAPON_POWER_CP160_GOLD.get(weapon_type)
        if power is None:
            unresolved.append(
                f"{slot_name} weapon base: weapon type missing or unsupported ({weapon_type or 'unset'})"
            )
            return replace(result, unresolved=tuple(unresolved))

        adjustment = power - NAKED_LEVEL_50_POWER
        label = f"{slot_name}: {weapon_type} base weapon power ({power:g})"
        core = self._core_flat(core, "weapon_damage", label, adjustment)
        core = self._core_flat(core, "spell_damage", label, adjustment)
        applied += 2

        core, applied = self._apply_weapon_trait(
            core=core,
            slot_name=slot_name,
            weapon_type=weapon_type,
            trait=trait,
            power=power,
            applied=applied,
            unresolved=unresolved,
        )

        return replace(result, core=core, applied_effect_count=applied, unresolved=tuple(unresolved))

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
    ) -> GearCalculationInputs:
        result = self._apply_armor(result, build)
        return self._apply_weapon(result, build, active_bar=active_bar)
