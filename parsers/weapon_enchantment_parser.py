from __future__ import annotations

import json
import re
from pathlib import Path


class WeaponEnchantmentParser:

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

    @staticmethod
    def _duration(
        text: str,
    ) -> tuple[float | None, str | None]:

        match = re.search(
            r"for\s+(-?\d+(?:\.\d+)?)\s*(seconds?|s)\b",
            text,
            re.IGNORECASE,
        )

        if not match:
            return None, None

        return float(match.group(1)), "seconds"

    @staticmethod
    def _effect(
        effect_type: str,
        text: str,
        *,
        damage_type: str | None = None,
        target: str | None = None,
        scaling_type: str | None = None,
    ) -> dict:

        value_min, value_max = (
            WeaponEnchantmentParser._parse_range(text)
        )

        duration_value, duration_unit = (
            WeaponEnchantmentParser._duration(text)
        )

        return {
            "effect_type": effect_type,
            "damage_type": damage_type,
            "target": target,
            "value_min": value_min,
            "value_max": value_max,
            "unit": "flat",
            "duration_value": duration_value,
            "duration_unit": duration_unit,
            "scaling_type": scaling_type,
            "description": text.strip(),
        }

    @classmethod
    def _parse_line(
        cls,
        line: str,
    ) -> list[dict]:

        effects = []

        # --------------------------------------------------
        # Damage + restoration effects
        # --------------------------------------------------

        damage_patterns = [
            ("Frost Damage", "frost"),
            ("Poison Damage", "poison"),
            ("Disease Damage", "disease"),
            ("Shock Damage", "shock"),
            ("Flame Damage", "flame"),
            ("Magic Damage", "magic"),
            ("Physical Damage", "physical"),
        ]

        for phrase, damage_type in damage_patterns:

            if re.search(
                phrase,
                line,
                re.IGNORECASE,
            ):
                effects.append(
                    cls._effect(
                        "damage",
                        line,
                        damage_type=damage_type,
                    )
                )

                break

        # --------------------------------------------------
        # Restoration can occur on the SAME line as damage.
        # --------------------------------------------------

        restore_patterns = [
            (r"restores\s+.*?Health", "health_restore"),
            (r"restores\s+.*?Magicka", "magicka_restore"),
            (r"restores\s+.*?Stamina", "stamina_restore"),
        ]

        for pattern, effect_type in restore_patterns:

            match = re.search(
                pattern,
                line,
                re.IGNORECASE,
            )

            if not match:
                continue

            # Extract only the restoration clause.
            clause = line[match.start():]

            # Stop at another "and" clause where appropriate.
            split = re.split(
                r"\s+and\s+(?=\d)",
                clause,
                maxsplit=1,
                flags=re.IGNORECASE,
            )

            clause = split[0]

            effects.append(
                cls._effect(
                    effect_type,
                    clause,
                )
            )

        # --------------------------------------------------
        # Prismatic Onslaught has:
        # Magic Damage
        # Health
        # Magicka
        # Stamina
        # --------------------------------------------------

        if re.search(
            r"restores\s+.*Health.*Magicka.*Stamina",
            line,
            re.IGNORECASE,
        ):

            # Rebuild the resource clauses individually.
            health = re.search(
                r"restores\s+.*?Health",
                line,
                re.IGNORECASE,
            )

            if health:
                effects = [
                    e for e in effects
                    if e["effect_type"] != "health_restore"
                ]

                effects.append(
                    cls._effect(
                        "health_restore",
                        health.group(0),
                    )
                )

            magicka = re.search(
                r"and\s+(\d+(?:\.\d+)?-\d+(?:\.\d+)?)\s+Magicka",
                line,
                re.IGNORECASE,
            )

            if magicka:
                effects.append(
                    cls._effect(
                        "magicka_restore",
                        magicka.group(0),
                    )
                )

            stamina = re.search(
                r"and\s+(\d+(?:\.\d+)?-\d+(?:\.\d+)?)\s+Stamina",
                line,
                re.IGNORECASE,
            )

            if stamina:
                effects.append(
                    cls._effect(
                        "stamina_restore",
                        stamina.group(0),
                    )
                )

        # --------------------------------------------------
        # Damage shield
        # --------------------------------------------------

        if re.search(
            r"Damage Shield",
            line,
            re.IGNORECASE,
        ):
            effects.append(
                cls._effect(
                    "damage_shield",
                    line,
                )
            )

        # --------------------------------------------------
        # Weapon / Spell Damage increase
        # --------------------------------------------------

        if re.search(
            r"Increase your Weapon Damage and Spell Damage",
            line,
            re.IGNORECASE,
        ):
            effects.append(
                cls._effect(
                    "weapon_spell_damage",
                    line,
                )
            )

        # --------------------------------------------------
        # Weapon / Spell Damage reduction
        # --------------------------------------------------

        if re.search(
            r"Reduce target Weapon Damage and Spell Damage",
            line,
            re.IGNORECASE,
        ):
            effects.append(
                cls._effect(
                    "weapon_spell_damage_reduction",
                    line,
                    target="target",
                )
            )

        # --------------------------------------------------
        # Physical / Spell Resistance reduction
        # --------------------------------------------------

        if re.search(
            r"Reduce the target's Physical and Spell Resistance",
            line,
            re.IGNORECASE,
        ):
            effects.append(
                cls._effect(
                    "physical_spell_resistance_reduction",
                    line,
                    target="target",
                )
            )

        # --------------------------------------------------
        # Decrease Health scaling statement.
        #
        # This statement contains no numeric range. It is
        # metadata for the following Oblivion damage line.
        # --------------------------------------------------

        if re.search(
            r"Oblivion Damage based on a portion of the enemy's Max Health",
            line,
            re.IGNORECASE,
        ):
            effects.append(
                {
                    "effect_type": "scaling_marker",
                    "damage_type": "oblivion",
                    "target": "target",
                    "value_min": None,
                    "value_max": None,
                    "unit": "flat",
                    "duration_value": None,
                    "duration_unit": None,
                    "scaling_type": "target_max_health",
                    "description": line.strip(),
                }
            )

        return effects

    @classmethod
    def _parse_effects(
        cls,
        description: str,
    ) -> list[dict]:

        description = cls._strip_color_codes(
            description
        )

        lines = [
            line.strip()
            for line in description.splitlines()
            if line.strip()
        ]

        effects = []

        pending_scaling = None

        for line in lines:

            parsed = cls._parse_line(line)

            # A scaling marker is not itself a gameplay effect.
            scaling_markers = [
                e for e in parsed
                if e["effect_type"] == "scaling_marker"
            ]

            parsed = [
                e for e in parsed
                if e["effect_type"] != "scaling_marker"
            ]

            if scaling_markers:
                pending_scaling = (
                    scaling_markers[0]["scaling_type"]
                )

            if pending_scaling:

                for effect in parsed:

                    if (
                        effect["effect_type"] == "damage"
                        and effect["damage_type"] == "oblivion"
                    ):
                        effect["scaling_type"] = (
                            pending_scaling
                        )

                        pending_scaling = None

            effects.extend(parsed)

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
