from __future__ import annotations

import sqlite3
from pathlib import Path

from .character_build.effect_instance import EffectVariant
from .character_build.effect_layer import EffectLayer
from .support_effect_category import SupportEffectCategory

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


class SkillEffectRepository:
    """Resolve imported player abilities into linked effect variants.

    This is deliberately a read-only bridge over the existing
    ability -> ability_effect_link -> effect_variant -> effect tables.
    It does not invent skill effects when the database has no linkage.
    """

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)

    def available_skills(self, limit: int | None = 5000) -> tuple[tuple[int, str], ...]:
        if not self.database_path.exists():
            return ()
        with sqlite3.connect(self.database_path) as db:
            sql = """
                SELECT ability_id, name
                FROM ability
                WHERE name IS NOT NULL
                  AND TRIM(name) <> ''
                  AND COALESCE(is_player, 0) = 1
                ORDER BY name COLLATE NOCASE, ability_id
            """
            if limit is not None:
                sql += " LIMIT ?"
                rows = db.execute(sql, (limit,)).fetchall()
            else:
                rows = db.execute(sql).fetchall()
        return tuple((int(row[0]), str(row[1])) for row in rows)

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
