from __future__ import annotations

import json
import re
from pathlib import Path


class ArmorGlyphParser:

    @staticmethod
    def _strip_color_codes(text: str) -> str:
        return re.sub(
            r"\|c[0-9A-Fa-f]{6}|\|r",
            "",
            text or "",
        )

    @staticmethod
    def _parse_range(
        text: str,
    ) -> tuple[float | None, float | None]:

        match = re.search(
            r"(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)",
            text,
        )

        if match:
            return (
                float(match.group(1)),
                float(match.group(2)),
            )

        single = re.search(
            r"(?<![\w.])(-?\d+(?:\.\d+)?)",
            text,
        )

        if single:
            value = float(single.group(1))
            return value, value

        return None, None

    @classmethod
    def _parse_effects(
        cls,
        description: str,
    ) -> list[dict]:

        description = cls._strip_color_codes(
            description
        )

        effects = []

        for raw_line in description.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            value_min, value_max = cls._parse_range(
                line
            )

            effect_type = None

            if re.search(
                r"Maximum Health",
                line,
                re.IGNORECASE,
            ):
                effect_type = "maximum_health"

            elif re.search(
                r"Maximum Magicka",
                line,
                re.IGNORECASE,
            ):
                effect_type = "maximum_magicka"

            elif re.search(
                r"Maximum Stamina",
                line,
                re.IGNORECASE,
            ):
                effect_type = "maximum_stamina"

            if effect_type is None:
                continue

            effects.append(
                {
                    "effect_type": effect_type,
                    "value_min": value_min,
                    "value_max": value_max,
                    "unit": "flat",
                    "description": line,
                }
            )

        return effects

    @classmethod
    def parse(
        cls,
        path: Path,
    ) -> list[dict]:

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        records = data.get(
            "minedItemSummary",
            []
        )

        results = []

        for record in records:

            description = (
                record.get(
                    "enchantDesc",
                    ""
                )
                or ""
            )

            results.append(
                {
                    "item_id": int(
                        record["itemId"]
                    ),

                    "name": record.get(
                        "name",
                        ""
                    ),

                    "icon": record.get(
                        "icon",
                        ""
                    ),

                    "level_range": record.get(
                        "level",
                        ""
                    ),

                    "quality_range": record.get(
                        "quality",
                        ""
                    ),

                    "value_range": record.get(
                        "value",
                        ""
                    ),

                    "enchant_name": record.get(
                        "enchantName",
                        ""
                    ),

                    "enchant_description": description,

                    "glyph_min_level": record.get(
                        "glyphMinLevel",
                        ""
                    ),

                    "craft_skill_rank": (
                        int(record["craftSkillRank"])
                        if str(
                            record.get(
                                "craftSkillRank",
                                ""
                            )
                        ).isdigit()
                        else None
                    ),

                    "default_enchant_id": (
                        int(record["defaultEnchantId"])
                        if str(
                            record.get(
                                "defaultEnchantId",
                                ""
                            )
                        ).isdigit()
                        else None
                    ),

                    "craft_type": (
                        int(record["craftType"])
                        if str(
                            record.get(
                                "craftType",
                                ""
                            )
                        ).isdigit()
                        else None
                    ),

                    "effects": cls._parse_effects(
                        description
                    ),
                }
            )

        return results
