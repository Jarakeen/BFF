from __future__ import annotations

from dataclasses import replace

from models.build_model import PlayerBuild

from .derived_stats import StatContribution
from .gear_stat_inputs import GearCalculationInputs
from .item_base_stats import WEAPON_POWER_CP160_GOLD


_ONE_HANDED_TYPES = {"sword", "axe", "mace", "dagger"}
_TWO_HANDED_TYPES = {"greatsword", "battleaxe", "battle axe", "maul"}

# Reviewed U50 max-rank standing-sheet values. These are intentionally limited
# to the branches proven by tools/audit_extreme_weapon_damage_weapon_passive_challengers.py.
_TWIN_BLADE_SWORD_DAMAGE_PER_SWORD = 64.0
_HEAVY_WEAPONS_GREATSWORD_DAMAGE = 129.0
_AMBIDEXTROUS_OFFHAND_PERCENT = 0.03


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
    ) -> GearCalculationInputs:
        main_type, offhand_type = self._active_weapon_types(build, active_bar)
        unresolved = list(result.unresolved)

        dual_wield = main_type in _ONE_HANDED_TYPES and offhand_type in _ONE_HANDED_TYPES
        two_handed = main_type in _TWO_HANDED_TYPES and not offhand_type

        if dual_wield and twin_blade_and_blunt_owned:
            if main_type == "sword" and offhand_type == "sword":
                result = self._add_flat_damage(
                    result,
                    label="Dual Wield: Twin Blade and Blunt (2 swords)",
                    amount=2.0 * _TWIN_BLADE_SWORD_DAMAGE_PER_SWORD,
                )
            else:
                unresolved.append(
                    "Dual Wield: Twin Blade and Blunt standing effect is not yet "
                    f"modeled for {main_type or 'unknown'} + {offhand_type or 'unknown'}"
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
                        f"(3% of {offhand_label} {offhand_power:g})"
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
            elif two_handed:
                unresolved.append(
                    "Two Handed: Heavy Weapons standing effect is not yet modeled "
                    f"for {main_type}"
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
