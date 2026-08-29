from __future__ import annotations

from dataclasses import replace

from models.build_model import GearSlot, PlayerBuild

from .derived_stats import DerivedStatInputs, StatContribution
from .gear_stat_inputs import GearCalculationInputs


# CP160 Legendary armor values from the mined ESO item catalog. Values are the
# untraited baseline endpoints; Reinforced and Nirnhoned are applied later as
# trait effects rather than being baked into the base item value.
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


class BaseItemStatResolver:
    """Apply deterministic CP160 Legendary armor and weapon base stats.

    This layer intentionally does not apply traits. It establishes the item
    value those traits modify, keeping base items and trait math independently
    inspectable in the final calculation trace.
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
    def _armor_equipped(entry: dict[str, str]) -> bool:
        return bool(
            str(entry.get("Set", "") or "").strip()
            or str(entry.get("Set2", "") or "").strip()
            or str(entry.get("Weight", "") or "").strip()
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

            if level.casefold() != "cp160" or quality.casefold() != "gold":
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

        return replace(result, core=core, applied_effect_count=applied, unresolved=tuple(unresolved))

    @staticmethod
    def _weapon_equipped(slot: GearSlot) -> bool:
        return bool(
            str(slot.Set or "").strip()
            or str(slot.Set2 or "").strip()
            or str(getattr(slot, "WeaponType", "") or "").strip()
        )

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

        if level.casefold() != "cp160" or quality.casefold() != "gold":
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
