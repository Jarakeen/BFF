from __future__ import annotations

from dataclasses import replace

from models.build_model import PlayerBuild

from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs, GearStatInputResolver
from .item_base_stats import WEAPON_POWER_CP160_GOLD


_ONE_HANDED_TYPES = {"sword", "axe", "mace", "dagger"}
_TWO_HANDED_TYPES = {"greatsword", "battleaxe", "battle axe", "maul"}

# Reviewed U50 max-rank standing-sheet values. These are intentionally limited
# to the branches proven by tools/audit_extreme_weapon_damage_weapon_passive_challengers.py.
_TWIN_BLADE_SWORD_DAMAGE_PER_SWORD = 129.0
_TWIN_BLADE_DAGGER_CRITICAL_RATING_PER_DAGGER = 657.0
_TWIN_BLADE_MACE_PENETRATION_PER_MACE = 1487.0
_HEAVY_WEAPONS_GREATSWORD_DAMAGE = 258.0
_HEAVY_WEAPONS_MAUL_PENETRATION = 2974.0
_AMBIDEXTROUS_OFFHAND_PERCENT = 0.06
_BOW_ACCURACY_CRITICAL_RATING = 1314.0


class WeaponStandingPassiveInputResolver:
    """Apply only reviewed weapon-passive standing-sheet contributions.

    This resolver is deliberately incomplete. It owns the proven static branches
    for Twin Blade and Blunt (swords) and Heavy Weapons (greatsword) and fails
    closed for relevant unreviewed subtype branches. Ability-family, proc,
    status-state, block-state, and sustain semantics remain in their dedicated
    runtime models.
    """

    @staticmethod
    def _active_weapon_types(build: PlayerBuild, active_bar: str) -> tuple[str, str]:
        main, offhand = build.active_weapon_slots(active_bar)
        return (
            " ".join(str(main.WeaponType or "").strip().casefold().split()),
            " ".join(str(offhand.WeaponType or "").strip().casefold().split()),
        )

    @staticmethod
    def _add_critical_rating(
        result: GearCalculationInputs,
        *,
        label: str,
        rating: float,
    ) -> GearCalculationInputs:
        ratio = GearStatInputResolver.critical_rating_to_ratio(float(rating))
        contribution = StatContribution(label, ratio)
        core = result.core
        core = replace(
            core,
            weapon_critical=replace(
                core.weapon_critical,
                additive_after_percent=core.weapon_critical.additive_after_percent
                + (contribution,),
            ),
            spell_critical=replace(
                core.spell_critical,
                additive_after_percent=core.spell_critical.additive_after_percent
                + (contribution,),
            ),
        )
        return replace(
            result,
            core=core,
            applied_effect_count=result.applied_effect_count + 2,
        )

    @staticmethod
    def _add_penetration(
        result: GearCalculationInputs,
        *,
        label: str,
        amount: float,
    ) -> GearCalculationInputs:
        contribution = StatContribution(label, float(amount))
        core = result.core
        core = replace(
            core,
            physical_penetration=replace(
                core.physical_penetration,
                flat=core.physical_penetration.flat + (contribution,),
            ),
            spell_penetration=replace(
                core.spell_penetration,
                flat=core.spell_penetration.flat + (contribution,),
            ),
        )
        return replace(
            result,
            core=core,
            applied_effect_count=result.applied_effect_count + 2,
        )

    @staticmethod
    def _add_flat_damage(
        result: GearCalculationInputs,
        *,
        label: str,
        amount: float,
    ) -> GearCalculationInputs:
        contribution = StatContribution(label, float(amount))
        core = result.core
        core = replace(
            core,
            weapon_damage=replace(
                core.weapon_damage,
                flat=core.weapon_damage.flat + (contribution,),
            ),
            spell_damage=replace(
                core.spell_damage,
                flat=core.spell_damage.flat + (contribution,),
            ),
        )
        return replace(
            result,
            core=core,
            applied_effect_count=result.applied_effect_count + 2,
        )

    def apply(
        self,
        result: GearCalculationInputs,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
        twin_blade_and_blunt_owned: bool = False,
        ambidextrous_owned: bool = False,
        heavy_weapons_owned: bool = False,
        bow_accuracy_owned: bool = False,
    ) -> GearCalculationInputs:
        main_type, offhand_type = self._active_weapon_types(build, active_bar)
        unresolved = list(result.unresolved)

        dual_wield = main_type in _ONE_HANDED_TYPES and offhand_type in _ONE_HANDED_TYPES
        two_handed = main_type in _TWO_HANDED_TYPES and not offhand_type
        bow = main_type == "bow" and not offhand_type

        if bow and bow_accuracy_owned:
            result = self._add_critical_rating(
                result,
                label="Bow: Accuracy (Rank 2)",
                rating=_BOW_ACCURACY_CRITICAL_RATING,
            )

        if dual_wield and twin_blade_and_blunt_owned:
            for hand_label, weapon_type in (
                ("main hand", main_type),
                ("off hand", offhand_type),
            ):
                if weapon_type == "sword":
                    result = self._add_flat_damage(
                        result,
                        label=(
                            "Dual Wield: Twin Blade and Blunt "
                            f"({hand_label} sword)"
                        ),
                        amount=_TWIN_BLADE_SWORD_DAMAGE_PER_SWORD,
                    )
                elif weapon_type == "dagger":
                    result = self._add_critical_rating(
                        result,
                        label=(
                            "Dual Wield: Twin Blade and Blunt "
                            f"({hand_label} dagger)"
                        ),
                        rating=_TWIN_BLADE_DAGGER_CRITICAL_RATING_PER_DAGGER,
                    )
                elif weapon_type == "mace":
                    result = self._add_penetration(
                        result,
                        label=(
                            "Dual Wield: Twin Blade and Blunt "
                            f"({hand_label} mace)"
                        ),
                        amount=_TWIN_BLADE_MACE_PENETRATION_PER_MACE,
                    )
                elif weapon_type == "axe":
                    unresolved.append(
                        "Dual Wield: Twin Blade and Blunt axe Critical Damage "
                        "branch is not yet promoted from current-version evidence"
                    )

        if dual_wield and ambidextrous_owned:
            _main, offhand = build.active_weapon_slots(active_bar)
            offhand_level = str(offhand.Level or "").strip().casefold()
            offhand_quality = str(offhand.Quality or "").strip().casefold()
            offhand_label = " ".join(str(offhand.WeaponType or "").strip().split())
            offhand_power = WEAPON_POWER_CP160_GOLD.get(offhand_label)
            if offhand_level != "cp160" or offhand_quality != "gold":
                unresolved.append(
                    "Dual Wield: Ambidextrous requires verified CP160 Gold off-hand "
                    f"weapon damage ({offhand.Level or 'level unset'}, "
                    f"{offhand.Quality or 'quality unset'})"
                )
            elif offhand_power is None:
                unresolved.append(
                    "Dual Wield: Ambidextrous off-hand weapon damage is unavailable "
                    f"for {offhand_label or 'unknown weapon'}"
                )
            else:
                result = self._add_flat_damage(
                    result,
                    label=(
                        "Dual Wield: Ambidextrous "
                        f"(6% of {offhand_label} {offhand_power:g})"
                    ),
                    amount=float(offhand_power) * _AMBIDEXTROUS_OFFHAND_PERCENT,
                )

        if heavy_weapons_owned:
            if two_handed and main_type == "greatsword":
                result = self._add_flat_damage(
                    result,
                    label="Two Handed: Heavy Weapons (greatsword)",
                    amount=_HEAVY_WEAPONS_GREATSWORD_DAMAGE,
                )
            elif two_handed and main_type == "maul":
                result = self._add_penetration(
                    result,
                    label="Two Handed: Heavy Weapons (maul)",
                    amount=_HEAVY_WEAPONS_MAUL_PENETRATION,
                )
            elif two_handed and main_type in {"battleaxe", "battle axe"}:
                unresolved.append(
                    "Two Handed: Heavy Weapons battle axe Critical Damage "
                    "branch is not yet promoted from current-version evidence"
                )
            elif main_type in {"two-handed", "two handed"}:
                unresolved.append(
                    "Two Handed: Heavy Weapons requires a concrete weapon subtype; "
                    "legacy aggregate Two-Handed identity is insufficient"
                )

        return replace(
            result,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = ["WeaponStandingPassiveInputResolver"]
