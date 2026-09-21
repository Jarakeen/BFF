from __future__ import annotations

"""Materialize a proven named-set realization onto an ordinary PlayerBuild.

This service does no stat math and invents no gear properties. It writes only the
set identities and weapon types proven by the named realization witness. Traits,
quality, glyphs, armor weights, and inactive-bar gear remain separate Extreme axes.
"""

from models.build_model import PlayerBuild
from services.extreme_named_gear_set_realization_service import ExtremeNamedGearSetRealization


_ARMOR_SLOTS = frozenset({"Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"})


class ExtremeNamedGearBuildMaterializerService:
    """Apply one concrete active-snapshot named gear witness to a build copy."""

    @staticmethod
    def materialize(
        build: PlayerBuild,
        realization: ExtremeNamedGearSetRealization,
        *,
        active_bar: str,
    ) -> PlayerBuild:
        candidate = PlayerBuild.from_dict(build.to_dict())

        # Clear only set identity on shared body/jewelry and the selected weapon
        # bar. Other gear axes remain untouched so later layers may compose them.
        for slot in candidate.Armor.values():
            slot["Set"] = ""
            slot["Set2"] = ""
        for field_name in ("Necklace", "Ring1", "Ring2"):
            slot = getattr(candidate, field_name)
            slot.Set = ""
            slot.Set2 = ""

        normalized_bar = str(active_bar or "front").strip().casefold()
        if normalized_bar not in {"front", "back"}:
            raise ValueError(f"unsupported active bar for Extreme gear materialization: {active_bar!r}")
        selected_main = (
            candidate.FrontBarWeapon
            if normalized_bar == "front"
            else candidate.BackBarWeapon
        )
        selected_offhand = (
            candidate.FrontBarOffHand
            if normalized_bar == "front"
            else candidate.BackBarOffHand
        )
        # Set identity and weapon type belong to this materializer. Preserve
        # trait, enchant, quality, tier, level, and weight because later
        # generated axes own those fields and runtime rematerialization must
        # not erase their selections.
        for weapon_slot in (selected_main, selected_offhand):
            weapon_slot.Set = ""
            weapon_slot.Set2 = ""
            weapon_slot.WeaponType = ""

        for assignment in realization.assignments:
            set_name = str(assignment.set_name or "").strip()
            if not set_name:
                raise ValueError("Extreme named gear assignment has empty set name")
            slot = str(assignment.slot or "").strip()

            if slot in _ARMOR_SLOTS:
                candidate.Armor[slot]["Set"] = set_name
                continue
            if slot == "Necklace":
                candidate.Necklace.Set = set_name
                continue
            if slot == "Ring1":
                candidate.Ring1.Set = set_name
                continue
            if slot == "Ring2":
                candidate.Ring2.Set = set_name
                continue
            if slot not in {"Main Hand", "Off Hand"}:
                raise ValueError(f"unsupported Extreme named gear witness slot: {slot!r}")

            weapon = selected_main if slot == "Main Hand" else selected_offhand
            weapon.Set = set_name
            weapon.Set2 = ""
            weapon.WeaponType = str(assignment.weapon_type or "").strip()

        return candidate
