from __future__ import annotations

import re
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
    "glyph of bashing": "Bashing",
    "glyph of bracing": "Block Cost",
}

_GLYPH_TIER_PREFIXES = (
    "Truly Superb",
    "Monumental",
    "Splendid",
    "Greater",
    "Superb",
    "Average",
    "Moderate",
    "Inferior",
    "Trifling",
    "Strong",
    "Lesser",
    "Slight",
    "Major",
    "Minor",
    "Petty",
)
_TIER_PREFIX_RE = re.compile(
    r"^(?:" + "|".join(re.escape(value) for value in _GLYPH_TIER_PREFIXES) + r")\s+",
    re.IGNORECASE,
)


class BuildEnchantCatalogService:
    """Expose canonical enchant choices by equipment family for the Build Editor.

    The ESO repositories remain the source of truth. Imported glyph tables contain
    item-tier names such as ``Truly Superb Glyph of Bashing``; the editor needs the
    enchant family, not every quality/tier duplicate. Tier prefixes are therefore
    collapsed for presentation only. Known legacy Build labels remain compatibility
    aliases so existing saved builds do not change identity merely because the UI now
    reads the complete canonical catalog.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.armor = ArmorGlyphEffectRepository(self.database_path)
        self.jewelry = JewelryGlyphEffectRepository(self.database_path)
        self.weapon = WeaponEnchantmentRepository(self.database_path)

    @staticmethod
    def _family_name(value: str) -> str:
        normalized = " ".join(str(value or "").strip().split())
        return _TIER_PREFIX_RE.sub("", normalized).strip()

    @classmethod
    def _display_choices(
        cls,
        names: tuple[str, ...],
        aliases: dict[str, str],
    ) -> tuple[str, ...]:
        values: list[str] = [""]
        seen: set[str] = {""}
        for raw in names:
            family = cls._family_name(raw)
            if not family:
                continue
            display = aliases.get(family.casefold(), family)
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
