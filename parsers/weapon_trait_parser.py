from __future__ import annotations

import json
import re
from pathlib import Path


class WeaponTraitParser:

    @staticmethod
    def _strip_color_codes(text: str) -> str:
        return re.sub(
            r"\|c[0-9A-Fa-f]{6}|\|r",
            "",
            text or "",
        )

    @staticmethod
    def _number(text: str) -> float | None:
        match = re.search(
            r"(-?\d+(?:\.\d+)?)",
            text,
        )

        if not match:
            return None

        return float(match.group(1))

    @classmethod
    def _parse_effects(
        cls,
        description: str,
    ) -> list[dict]:

        description = cls._strip_color_codes(
            description
        ).strip()

        effects = []

        if description.startswith(
            "Increases weapon enchantment effect"
        ):
            match = re.search(
                r"effect by\s+(\d+(?:\.\d+)?)%",
                description,
                re.IGNORECASE,
            )

            if match:
                effects.append(
                    {
                        "effect_type": (
                            "weapon_enchantment_effect"
                        ),
                        "value": float(
                            match.group(1)
                        ),
                        "secondary_value": None,
                        "unit": "percent",
                        "description": description,
                    }
                )

            match = re.search(
                r"reduces enchantment cooldown by\s+(\d+(?:\.\d+)?)%",
                description,
                re.IGNORECASE,
            )

            if match:
                effects.append(
                    {
                        "effect_type": (
                            "enchantment_cooldown_reduction"
                        ),
                        "value": float(
                            match.group(1)
                        ),
                        "secondary_value": None,
                        "unit": "percent",
                        "description": description,
                    }
                )

            return effects

        if re.search(
            r"Physical and Spell Resistance",
            description,
            re.IGNORECASE,
        ):
            effects.append(
                {
                    "effect_type": (
                        "physical_spell_resistance"
                    ),
                    "value": cls._number(description),
                    "secondary_value": None,
                    "unit": "flat",
                    "description": description,
                }
            )

            return effects

        if re.search(
            r"Weapon and Spell Critical",
            description,
            re.IGNORECASE,
        ):
            effects.append(
                {
                    "effect_type": (
                        "weapon_spell_critical"
                    ),
                    "value": cls._number(description),
                    "secondary_value": None,
                    "unit": "percent",
                    "description": description,
                }
            )

            return effects

        if re.search(
            r"gain Ultimate",
            description,
            re.IGNORECASE,
        ):
            chance = cls._number(description)

            effects.append(
                {
                    "effect_type": (
                        "ultimate_gain_chance"
                    ),
                    "value": chance,
                    "secondary_value": 1.0,
                    "unit": "percent",
                    "description": description,
                }
            )

            return effects

        if re.search(
            r"Physical and Spell Penetration",
            description,
            re.IGNORECASE,
        ):
            effects.append(
                {
                    "effect_type": (
                        "physical_spell_penetration"
                    ),
                    "value": cls._number(description),
                    "secondary_value": None,
                    "unit": "flat",
                    "description": description,
                }
            )

            return effects

        if re.search(
            r"experience gained from kills",
            description,
            re.IGNORECASE,
        ):
            effects.append(
                {
                    "effect_type": "kill_experience",
                    "value": cls._number(description),
                    "secondary_value": None,
                    "unit": "percent",
                    "description": description,
                }
            )

            return effects

        if re.search(
            r"healing done",
            description,
            re.IGNORECASE,
        ):
            effects.append(
                {
                    "effect_type": "healing_done",
                    "value": cls._number(description),
                    "secondary_value": None,
                    "unit": "percent",
                    "description": description,
                }
            )

            return effects

        if re.search(
            r"chance to apply status effects",
            description,
            re.IGNORECASE,
        ):
            effects.append(
                {
                    "effect_type": (
                        "status_effect_chance"
                    ),
                    "value": cls._number(description),
                    "secondary_value": None,
                    "unit": "percent",
                    "description": description,
                }
            )

            return effects

        if re.search(
            r"Increases Damage of this weapon",
            description,
            re.IGNORECASE,
        ):
            effects.append(
                {
                    "effect_type": "weapon_damage",
                    "value": cls._number(description),
                    "secondary_value": None,
                    "unit": "percent",
                    "description": description,
                }
            )

            return effects

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
                    "traitDesc",
                    ""
                )
                or ""
            )

            results.append(
                {
                    "item_id": int(
                        record["itemId"]
                    ),
                    "material_name": record.get(
                        "name",
                        ""
                    ),
                    "description": description,
                    "effects": cls._parse_effects(
                        description
                    ),
                }
            )

        return results
