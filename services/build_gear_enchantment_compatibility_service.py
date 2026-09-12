from __future__ import annotations

from dataclasses import replace

from models.build_model import ARMOR_SLOTS, BuildRoster, GearSlot, PlayerBuild


class BuildGearEnchantmentCompatibilityService:
    """Normalize source-backed impossible gear-level/enchantment-tier pairs.

    ESO's ``Truly Superb`` glyph tier is the CP160 potency tier. A saved item that
    claims a Truly Superb glyph while also claiming a lower item level cannot exist
    in game. FoundryDock previously allowed those two editor fields to drift
    independently, producing states such as ``CP70 + Truly Superb``.

    This service performs the narrowest safe repair: when a slot explicitly records
    ``Truly Superb``, the item level is canonicalized to CP160. It does not invent
    scaling for lower glyph tiers, reinterpret enchantment values, or touch slots
    whose enchantment tier is blank/unknown.
    """

    TRULY_SUPERB_TIER = "truly superb"
    TRULY_SUPERB_LEVEL = "CP160"

    @classmethod
    def normalize_slot(cls, slot: GearSlot) -> GearSlot:
        tier = str(slot.EnchantTier or "").strip().casefold()
        if tier != cls.TRULY_SUPERB_TIER:
            return slot
        if str(slot.Level or "").strip().casefold() == cls.TRULY_SUPERB_LEVEL.casefold():
            return slot
        return replace(slot, Level=cls.TRULY_SUPERB_LEVEL)

    @classmethod
    def normalize_armor_entry(cls, entry: dict[str, str]) -> dict[str, str]:
        normalized = {str(key): str(value or "") for key, value in dict(entry or {}).items()}
        tier = str(normalized.get("EnchantTier", "") or "").strip().casefold()
        if tier == cls.TRULY_SUPERB_TIER:
            normalized["Level"] = cls.TRULY_SUPERB_LEVEL
        return normalized

    @classmethod
    def normalize_build(cls, build: PlayerBuild) -> PlayerBuild:
        armor = {
            slot_name: cls.normalize_armor_entry(build.Armor.get(slot_name, {}))
            for slot_name in ARMOR_SLOTS
        }
        return replace(
            build,
            Armor=armor,
            FrontBarWeapon=cls.normalize_slot(build.FrontBarWeapon),
            FrontBarOffHand=cls.normalize_slot(build.FrontBarOffHand),
            BackBarWeapon=cls.normalize_slot(build.BackBarWeapon),
            BackBarOffHand=cls.normalize_slot(build.BackBarOffHand),
            Necklace=cls.normalize_slot(build.Necklace),
            Ring1=cls.normalize_slot(build.Ring1),
            Ring2=cls.normalize_slot(build.Ring2),
        )

    @classmethod
    def normalize_roster(cls, roster: BuildRoster) -> BuildRoster:
        return BuildRoster(
            Members=[cls.normalize_build(member) for member in roster.Members]
        )


__all__ = ["BuildGearEnchantmentCompatibilityService"]
