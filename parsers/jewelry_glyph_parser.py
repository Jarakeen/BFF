from __future__ import annotations

import json
import re
from pathlib import Path


class JewelryGlyphParser:

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

        # Handle fixed values such as:
        # "Adds 10 Stamina Recovery."
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

        description = cls._strip_color_codes(description)

        effects = []

        for raw_line in description.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            value_min, value_max = cls._parse_range(line)

            effect_type = None
            unit = "flat"

            if re.search(r"Weapon and Spell Damage", line, re.I):
                effect_type = "weapon_spell_damage"

            elif re.search(r"Stamina Recovery", line, re.I):
                effect_type = "stamina_recovery"

            elif re.search(r"Magicka Recovery", line, re.I):
                effect_type = "magicka_recovery"

            elif re.search(r"Health Recovery", line, re.I):
                effect_type = "health_recovery"

            elif re.search(r"Frost Resistance", line, re.I):
                effect_type = "frost_resistance"

            elif re.search(r"Fire Resistance", line, re.I):
                effect_type = "flame_resistance"

            elif re.search(r"Shock Resistance", line, re.I):
                effect_type = "shock_resistance"

            elif re.search(r"Poison Resistance", line, re.I):
                effect_type = "poison_resistance"

            elif re.search(r"Disease Resistance", line, re.I):
                effect_type = "disease_resistance"

            elif re.search(r"Physical Resistance", line, re.I):
                effect_type = "physical_resistance"

            elif re.search(r"Spell Resistance", line, re.I):
                effect_type = "spell_resistance"

            elif re.search(r"Reduce Magicka cost", line, re.I):
                effect_type = "magicka_cost_reduction"

            elif re.search(r"Reduce Stamina cost", line, re.I):
                effect_type = "stamina_cost_reduction"

            elif re.search(
                r"Reduce Health, Magicka, and Stamina cost",
                line,
                re.I,
            ):
                effect_type = "resource_cost_reduction"

            elif re.search(r"Bash attacks", line, re.I):
                effect_type = "bash_damage"

            elif re.search(r"cost of Block", line, re.I):
                effect_type = "block_cost_reduction"

            elif re.search(
                r"duration of beneficial potion effects",
                line,
                re.I,
            ):
                effect_type = "potion_duration"

            elif re.search(r"cooldown of potions", line, re.I):
                effect_type = "potion_cooldown_reduction"

            if effect_type is None:
                continue

            if "%" in line:
                unit = "percent"
            elif "second" in line.lower():
                unit = "seconds"

            effects.append(
                {
                    "effect_type": effect_type,
                    "value_min": value_min,
                    "value_max": value_max,
                    "unit": unit,
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
            path.read_text(encoding="utf-8")
        )

        records = data.get(
            "minedItemSummary",
            []
        )

        results = []

        for record in records:

            description = (
                record.get("enchantDesc", "")
                or ""
            )

            results.append(
                {
                    "item_id": int(record["itemId"]),
                    "name": record.get("name", ""),
                    "icon": record.get("icon", ""),
                    "level_range": record.get("level", ""),
                    "quality_range": record.get("quality", ""),
                    "value_range": record.get("value", ""),
                    "enchant_name": record.get("enchantName", ""),
                    "enchant_description": description,
                    "glyph_min_level": record.get(
                        "glyphMinLevel", ""
                    ),
                    "craft_skill_rank": (
                        int(record["craftSkillRank"])
                        if str(
                            record.get("craftSkillRank", "")
                        ).isdigit()
                        else None
                    ),
                    "default_enchant_id": (
                        int(record["defaultEnchantId"])
                        if str(
                            record.get("defaultEnchantId", "")
                        ).isdigit()
                        else None
                    ),
                    "craft_type": (
                        int(record["craftType"])
                        if str(
                            record.get("craftType", "")
                        ).isdigit()
                        else None
                    ),
                    "effects": cls._parse_effects(
                        description
                    ),
                }
            )

        return results
