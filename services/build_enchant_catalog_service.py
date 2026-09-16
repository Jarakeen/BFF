from __future__ import annotations

from pathlib import Path

from minmax.armor_glyph_repository import ArmorGlyphEffectRepository
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.weapon_enchantment_repository import WeaponEnchantmentRepository


_ARMOR_LEGACY_LABELS = {
    "glyph of health": "Max Health",
    "glyph of magicka": "Max Magicka",
    "glyph of stamina": "Max Stamina",
    "glyph of prismatic defense": "Prismatic Defense",
}

_JEWELRY_LEGACY_LABELS = {
    "glyph of health recovery": "Health Recovery",
    "glyph of magicka recovery": "Magicka Recovery",
    "glyph of stamina recovery": "Stamina Recovery",
    "glyph of increase physical harm": "Weapon Damage",
    "glyph of increase magical harm": "Spell Damage",
    "glyph of bracing": "Block Cost",
}


class BuildEnchantCatalogService:
    """Expose canonical enchant choices by equipment family for the Build Editor.

    The ESO repositories remain the source of truth. Known legacy Build labels are
    retained only as display/storage compatibility aliases; every other canonical
    glyph/enchantment name is surfaced verbatim instead of being omitted from a
    hand-maintained UI list.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.armor = ArmorGlyphEffectRepository(self.database_path)
        self.jewelry = JewelryGlyphEffectRepository(self.database_path)
        self.weapon = WeaponEnchantmentRepository(self.database_path)

    @staticmethod
    def _display_choices(
        names: tuple[str, ...],
        aliases: dict[str, str],
    ) -> tuple[str, ...]:
        values: list[str] = [""]
        seen: set[str] = {""}
        for raw in names:
            canonical = " ".join(str(raw or "").strip().split())
            if not canonical:
                continue
            display = aliases.get(canonical.casefold(), canonical)
            key = display.casefold()
            if key in seen:
                continue
            seen.add(key)
            values.append(display)
        return tuple(values)

    def armor_choices(self) -> tuple[str, ...]:
        return self._display_choices(self.armor.list_names(), _ARMOR_LEGACY_LABELS)

    def jewelry_choices(self) -> tuple[str, ...]:
        return self._display_choices(self.jewelry.list_names(), _JEWELRY_LEGACY_LABELS)

    def weapon_choices(self) -> tuple[str, ...]:
        names = tuple(name for _item_id, name in self.weapon.list_items())
        return self._display_choices(names, {})


__all__ = ["BuildEnchantCatalogService"]
