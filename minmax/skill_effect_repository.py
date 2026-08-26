from __future__ import annotations

import sqlite3
from pathlib import Path

from .character_build.effect_instance import EffectVariant
from .character_build.effect_layer import EffectLayer
from .character_build.character_class import CLASS_SKILL_LINES, CharacterClass
from .support_effect_category import SupportEffectCategory

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


class SkillEffectRepository:
    """Resolve imported player abilities into linked effect variants."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)

    def available_skills(
        self,
        character_class: CharacterClass | str | None = None,
        limit: int | None = 5000,
    ) -> tuple[tuple[int, str], ...]:
        """Return selectable active combat skills for a class.

        Class skills are restricted to the selected character's three class
        lines. Non-class player skills are also exposed, including weapon,
        armor, guild, alliance, world and other universal combat lines. This
        keeps the picker faithful to the database instead of silently
        limiting the roster lab to class abilities.
        """
        if not self.database_path.exists() or character_class is None:
            return ()

        if isinstance(character_class, CharacterClass):
            selected_class = character_class
        else:
            try:
                selected_class = CharacterClass(str(character_class).strip().casefold())
            except ValueError:
                return ()

        selected_lines = CLASS_SKILL_LINES[selected_class]
        selected_class_name = selected_class.value

        with sqlite3.connect(self.database_path) as db:
            rows = db.execute(
                """
                SELECT
                    ability_id,
                    name,
                    class_type,
                    skill_line,
                    base_ability_id,
                    rank,
                    morph,
                    is_passive,
                    is_player,
                    is_crafted
                FROM ability
                WHERE name IS NOT NULL
                  AND TRIM(name) <> ''
                  AND COALESCE(is_player, 0) = 1
                  AND COALESCE(is_passive, 0) = 0
                  AND COALESCE(is_crafted, 0) = 0
                ORDER BY base_ability_id, morph, rank, ability_id
                """
            ).fetchall()

        selected: dict[tuple[int, int], tuple[int, str, int]] = {}
        for row in rows:
            ability_id, name, class_type, skill_line, base_id, rank, morph, *_ = row
            owner = str(class_type or "").strip().casefold()
            line = str(skill_line or "").strip().casefold().replace(" ", "_")

            # A non-empty class_type belongs to a specific class. Only the
            # selected class may contribute those class-line abilities.
            # Empty class_type denotes shared/universal combat lines.
            if owner:
                if owner != selected_class_name:
                    continue
                if line not in selected_lines:
                    continue

            base_key = int(base_id or ability_id)
            morph_key = int(morph or 0)
            key = (base_key, morph_key)
            rank_value = int(rank or 0)
            existing = selected.get(key)
            if existing is None or rank_value < existing[2]:
                selected[key] = (int(ability_id), str(name).strip(), rank_value)

        values = sorted(
            selected.items(),
            key=lambda item: (item[0][0], item[0][1], item[1][2], item[1][0]),
        )
        if limit is not None:
            values = values[:limit]
        return tuple((value[0], value[1]) for _key, value in values)

    def resolve(self, ability_id: int) -> tuple[EffectVariant, ...]:
        if not self.database_path.exists():
            return ()

        with sqlite3.connect(self.database_path) as db:
            rows = db.execute(
                """
                SELECT
                    a.name,
                    a.target,
                    a.duration,
                    ev.id,
                    e.name,
                    e.category,
                    ev.type,
                    es.source_name,
                    es.condition
                FROM ability a
                JOIN ability_effect_link ael
                  ON ael.ability_id = a.ability_id
                JOIN effect_variant ev
                  ON ev.id = ael.effect_variant_id
                JOIN effect e
                  ON e.id = ev.effect_id
                LEFT JOIN effect_source es
                  ON es.id = ael.effect_source_id
                WHERE a.ability_id = ?
                ORDER BY ev.id, es.id
                """,
                (ability_id,),
            ).fetchall()

        variants: list[EffectVariant] = []
        seen: set[tuple[str, str, str]] = set()
        for ability_name, target, duration, variant_id, effect_name, category, variant_type, source_name, condition in rows:
            key = (str(effect_name), str(source_name or ability_name), str(condition or ""))
            if key in seen:
                continue
            seen.add(key)
            variants.append(
                EffectVariant(
                    name=str(effect_name).strip().casefold().replace(" ", "_"),
                    layer=EffectLayer.CAST,
                    source=str(source_name or ability_name),
                    duration=float(duration) if duration is not None and duration >= 0 else None,
                    condition=condition,
                    target_type=self._target_type(target),
                    category=self._category(category),
                )
            )
        return tuple(variants)

    @staticmethod
    def _category(value: str | None) -> SupportEffectCategory:
        text = (value or "").strip().casefold()
        if "debuff" in text:
            return SupportEffectCategory.DEBUFF
        if "buff" in text:
            return SupportEffectCategory.BUFF
        if "status" in text:
            return SupportEffectCategory.STATUS
        return SupportEffectCategory.OTHER

    @staticmethod
    def _target_type(value: str | None):
        from .support_target_type import SupportTargetType
        text = (value or "").strip().casefold()
        if "enemy" in text or "target" in text:
            return SupportTargetType.ENEMY
        if "group" in text:
            return SupportTargetType.GROUP
        if "ally" in text or "friendly" in text:
            return SupportTargetType.ALLY
        return SupportTargetType.SELF
