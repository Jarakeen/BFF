from __future__ import annotations

import sqlite3
from pathlib import Path

from .character_build.effect_instance import EffectVariant
from .character_build.effect_layer import EffectLayer
from .skill_known_effects import verified_skill_effects
from .support_effect_category import SupportEffectCategory
from services.skill_bar_eligibility import is_eligible

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


class SkillEffectRepository:
    """Resolve imported player abilities into linked and verified effects.

    Imported ``ability_effect_link`` rows remain the primary source. A small
    audited supplemental registry fills only mechanics that source ability
    records prove but the imported link table omitted.
    """

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)
        self._resolve_cache: dict[int, tuple[EffectVariant, ...]] = {}

    @staticmethod
    def _ability_columns(db: sqlite3.Connection) -> set[str]:
        return {str(row[1]) for row in db.execute("PRAGMA table_info(ability)").fetchall()}

    @staticmethod
    def _duration_seconds(value: object) -> float | None:
        """Normalize imported ability duration from milliseconds to seconds.

        The ``ability.duration`` column is imported in ESO API milliseconds.
        CharacterBuild/EffectVariant duration values are canonical seconds.
        Supplemental verified effects are authored directly as EffectVariants
        and therefore already use seconds; only linked DB ability rows pass
        through this conversion boundary.
        """
        if value is None:
            return None
        try:
            milliseconds = float(value)
        except (TypeError, ValueError):
            return None
        if milliseconds < 0:
            return None
        return milliseconds / 1000.0

    def available_skills(self, character_class: object | None = None, limit: int | None = 5000) -> tuple[tuple[int, str], ...]:
        """Return combat-bar abilities allowed for the selected class.

        Production has the full imported schema; small fixtures may omit
        optional columns, so those columns receive neutral defaults here.
        """
        if not self.database_path.exists():
            return ()

        selected_class = getattr(character_class, "value", character_class)
        with sqlite3.connect(self.database_path) as db:
            columns = self._ability_columns(db)
            required = {"ability_id", "name", "class_type", "skill_line", "base_ability_id", "rank", "morph"}
            if not required.issubset(columns):
                return ()

            optional = {
                "base_mechanic": "0",
                "is_passive": "0",
                "is_player": "1",
                "is_crafted": "0",
            }
            select_columns = [
                "ability_id", "name", "class_type", "skill_line",
                "base_ability_id", "rank", "morph",
            ]
            select_columns.extend(
                column if column in columns else f"{default} AS {column}"
                for column, default in optional.items()
            )
            rows = db.execute(
                f"""
                SELECT {', '.join(select_columns)}
                FROM ability
                WHERE name IS NOT NULL AND TRIM(name) <> ''
                ORDER BY base_ability_id, morph, rank, ability_id
                """
            ).fetchall()

        selected: dict[tuple[int, int], tuple[int, str, int]] = {}
        for row in rows:
            ability_id, name, class_type, skill_line, base_id, rank, morph, base_mechanic, is_passive, is_player, is_crafted = row
            skill = {
                "ability_id": ability_id,
                "name": name,
                "class_type": class_type,
                "skill_line": skill_line,
                "base_ability_id": base_id,
                "rank": rank,
                "morph": morph,
                "base_mechanic": base_mechanic,
                "is_passive": is_passive,
                "is_player": is_player,
                "is_crafted": is_crafted,
            }
            if not (
                is_eligible(skill, character_class=selected_class, slot_index=0)
                or is_eligible(skill, character_class=selected_class, slot_index=5)
            ):
                continue

            key = (int(base_id or ability_id), int(morph or 0))
            rank_value = int(rank or 0)
            existing = selected.get(key)
            if existing is None or rank_value < existing[2]:
                selected[key] = (int(ability_id), str(name).strip(), rank_value)

        values = sorted(selected.values(), key=lambda value: (value[1].casefold(), value[0]))
        if limit is not None:
            values = values[:limit]
        return tuple((ability_id, name) for ability_id, name, _rank in values)

    def resolve(self, ability_id: int) -> tuple[EffectVariant, ...]:
        cache_key = int(ability_id)
        if cache_key in self._resolve_cache:
            return self._resolve_cache[cache_key]
        if not self.database_path.exists():
            self._resolve_cache[cache_key] = ()
            return ()

        with sqlite3.connect(self.database_path) as db:
            columns = self._ability_columns(db)
            if "ability_id" not in columns:
                self._resolve_cache[cache_key] = ()
                return ()

            metadata_columns = ["name"]
            metadata_columns.append(
                "base_ability_id" if "base_ability_id" in columns else "ability_id AS base_ability_id"
            )
            metadata_columns.append("morph" if "morph" in columns else "0 AS morph")
            metadata = db.execute(
                f"SELECT {', '.join(metadata_columns)} FROM ability WHERE ability_id = ?",
                (cache_key,),
            ).fetchone()
            if metadata is None:
                self._resolve_cache[cache_key] = ()
                return ()

            ability_name, base_ability_id, morph = metadata

            tables = {
                str(row[0])
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            required_link_tables = {
                "ability_effect_link",
                "effect_variant",
                "effect",
            }
            if required_link_tables.issubset(tables):
                rows = db.execute(
                    """
                    SELECT a.name, a.target, a.duration, ev.id, e.name,
                           e.category, ev.type, es.source_name, es.condition
                    FROM ability a
                    JOIN ability_effect_link ael ON ael.ability_id = a.ability_id
                    JOIN effect_variant ev ON ev.id = ael.effect_variant_id
                    JOIN effect e ON e.id = ev.effect_id
                    LEFT JOIN effect_source es ON es.id = ael.effect_source_id
                    WHERE a.ability_id = ?
                    ORDER BY ev.id, es.id
                    """,
                    (cache_key,),
                ).fetchall()
            else:
                rows = []

        variants: list[EffectVariant] = []
        seen: set[tuple[str, str, str]] = set()
        for linked_ability_name, target, duration, variant_id, effect_name, category, variant_type, source_name, condition in rows:
            key = (
                str(effect_name).strip().casefold().replace(" ", "_"),
                str(source_name or linked_ability_name),
                str(condition or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            variants.append(EffectVariant(
                name=key[0],
                layer=EffectLayer.CAST,
                source=str(source_name or linked_ability_name),
                duration=self._duration_seconds(duration),
                condition=condition,
                target_type=self._target_type(target),
                category=self._category(category),
            ))

        for supplemental in verified_skill_effects(
            int(base_ability_id or cache_key),
            int(morph or 0),
        ):
            key = (
                supplemental.name,
                supplemental.source,
                str(supplemental.condition or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            variants.append(supplemental)

        result = tuple(variants)
        self._resolve_cache[cache_key] = result
        return result

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
