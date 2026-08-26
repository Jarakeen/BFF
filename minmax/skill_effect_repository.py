from __future__ import annotations

import sqlite3
from pathlib import Path

from .character_build.effect_instance import EffectVariant
from .character_build.effect_layer import EffectLayer
from .support_effect_category import SupportEffectCategory
from services.skill_bar_eligibility import is_eligible

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


class SkillEffectRepository:
    """Resolve imported player abilities into linked effect variants."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)

    def available_skills(
        self,
        character_class: object | None = None,
        limit: int | None = 5000,
    ) -> tuple[tuple[int, str], ...]:
        """Return combat-bar abilities allowed for the selected class.

        The picker is deliberately narrower than the full ability database:
        passive, crafted and non-combat lines are excluded. Morphs remain
        distinct because selection is keyed by base ability + morph rather
        than display name.
        """
        if not self.database_path.exists():
            return ()

        selected_class = getattr(character_class, "value", character_class)
        with sqlite3.connect(self.database_path) as db:
            rows = db.execute(
                """
                SELECT ability_id, name, class_type, skill_line,
                       base_ability_id, rank, morph, base_mechanic,
                       is_passive, is_player, is_crafted
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
            # A normal active slot and the ultimate slot together define the
            # complete six-slot choice universe.
            if not (
                is_eligible(skill, character_class=selected_class, slot_index=0)
                or is_eligible(skill, character_class=selected_class, slot_index=5)
            ):
                continue

            base_key = int(base_id or ability_id)
            morph_key = int(morph or 0)
            rank_value = int(rank or 0)
            key = (base_key, morph_key)
            existing = selected.get(key)
            # Lower rank is the base ability record; preserve one record per
            # base/morph identity rather than collapsing morphs by name.
            if existing is None or rank_value < existing[2]:
                selected[key] = (int(ability_id), str(name).strip(), rank_value)

        values = sorted(
            selected.values(),
            key=lambda value: (value[1].casefold(), value[0]),
        )
        if limit is not None:
            values = values[:limit]
        return tuple((ability_id, name) for ability_id, name, _rank in values)

    def resolve(self, ability_id: int) -> tuple[EffectVariant, ...]:
        if not self.database_path.exists():
            return ()

        with sqlite3.connect(self.database_path) as db:
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
                (ability_id,),
            ).fetchall()

        variants: list[EffectVariant] = []
        seen: set[tuple[str, str, str]] = set()
        for ability_name, target, duration, variant_id, effect_name, category, variant_type, source_name, condition in rows:
            key = (str(effect_name), str(source_name or ability_name), str(condition or ""))
            if key in seen:
                continue
            seen.add(key)
            variants.append(EffectVariant(
                name=str(effect_name).strip().casefold().replace(" ", "_"),
                layer=EffectLayer.CAST,
                source=str(source_name or ability_name),
                duration=float(duration) if duration is not None and duration >= 0 else None,
                condition=condition,
                target_type=self._target_type(target),
                category=self._category(category),
            ))
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
