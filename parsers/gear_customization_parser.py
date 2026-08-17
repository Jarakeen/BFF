# ==================================================
# Black Feather Foundry
#
# File:
# parsers/gear_customization_parser.py
#
# Purpose:
# Parse UESP gear trait and glyph JSON sources.
#
# ==================================================

from __future__ import annotations

import json
from pathlib import Path


class GearCustomizationParser:

    # --------------------------------------------------
    # JSON
    # --------------------------------------------------

    @staticmethod
    def load_json(path: Path) -> list[dict]:

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        records = data.get(
            "minedItemSummary",
            []
        )

        if not isinstance(records, list):
            raise ValueError(
                f"Expected minedItemSummary list in {path}"
            )

        return records

    # --------------------------------------------------
    # Trait materials
    # --------------------------------------------------

    @classmethod
    def parse_traits(
        cls,
        path: Path,
        gear_type: str,
    ) -> list[dict]:

        records = cls.load_json(path)

        results = []

        for row in records:

            trait_id = row.get("trait")

            if trait_id in (None, "", "-1"):
                continue

            results.append(
                {
                    "trait_id": int(trait_id),
                    "gear_type": gear_type,
                    "material_item_id": int(
                        row["itemId"]
                    ),
                    "material_name": row.get(
                        "name",
                        "",
                    ),
                    "material_icon": row.get(
                        "icon",
                        "",
                    ),
                    "description": row.get(
                        "traitDesc",
                        "",
                    ),
                }
            )

        return results

    # --------------------------------------------------
    # Glyphs / enchantments
    # --------------------------------------------------

    @classmethod
    def parse_glyphs(
        cls,
        path: Path,
        gear_type: str,
    ) -> list[dict]:

        records = cls.load_json(path)

        results = []

        for row in records:

            enchant_name = (
                row.get("enchantName") or ""
            ).strip()

            if not enchant_name:
                continue

            default_enchant_id = row.get(
                "defaultEnchantId"
            )

            if default_enchant_id in (
                None,
                "",
                "-1",
            ):
                default_enchant_id = None
            else:
                default_enchant_id = int(
                    default_enchant_id
                )

            results.append(
                {
                    "item_id": int(
                        row["itemId"]
                    ),
                    "gear_type": gear_type,
                    "name": row.get(
                        "name",
                        "",
                    ),
                    "icon": row.get(
                        "icon",
                        "",
                    ),
                    "enchant_name": enchant_name,
                    "enchant_description": row.get(
                        "enchantDesc",
                        "",
                    ),
                    "default_enchant_id":
                        default_enchant_id,
                    "level_range": row.get(
                        "glyphMinLevel",
                        "",
                    ),
                    "quality_range": row.get(
                        "quality",
                        "",
                    ),
                }
            )

        return results

    # --------------------------------------------------
    # Combined parse
    # --------------------------------------------------

    @classmethod
    def parse_all(
        cls,
        raw_dir: Path,
    ) -> dict[str, list[dict]]:

        return {

            "traits": (
                cls.parse_traits(
                    raw_dir / "armor_traits.json",
                    "Armor",
                )
                +
                cls.parse_traits(
                    raw_dir / "weapon_trait.json",
                    "Weapon",
                )
            ),

            "glyphs": (
                cls.parse_glyphs(
                    raw_dir / "armor_glyph.json",
                    "Armor",
                )
                +
                cls.parse_glyphs(
                    raw_dir / "jewelry_glyph.json",
                    "Jewelry",
                )
                +
                cls.parse_glyphs(
                    raw_dir / "weapon_enchantments.json",
                    "Weapon",
                )
            ),
        }