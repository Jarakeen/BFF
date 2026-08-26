from __future__ import annotations

import sqlite3
from pathlib import Path

from services.skill_bar_eligibility import filter_skill_choices


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


def load_skill_choices(database_path: str | Path = DEFAULT_DATABASE) -> list[dict]:
    """Load one representative rank for each base/morph skill choice.

    The database keeps every rank and coefficient. The skill-bar UI does not
    expose rank progression, so this returns one representative record for
    each (base_ability_id, morph) pair while preserving the exact ability_id
    used by the effect resolver. Morphs remain separate choices.
    """
    path = Path(database_path)
    if not path.exists():
        return []

    with sqlite3.connect(path) as db:
        rows = db.execute(
            """
            SELECT
                sr.ability_id,
                s.base_ability_id,
                COALESCE(NULLIF(sr.raw_name, ''), s.name) AS name,
                s.index_name,
                COALESCE(NULLIF(sr.raw_description, ''), s.description) AS description,
                COALESCE(NULLIF(a.texture, ''), s.texture) AS texture,
                s.class_type,
                s.skill_line,
                s.target,
                s.skill_type,
                s.is_passive,
                s.is_player,
                s.is_crafted,
                s.crafted_id,
                sr.rank,
                sr.morph,
                COALESCE(a.base_mechanic, 0) AS base_mechanic,
                sr.cost,
                sr.duration,
                sr.raw_tooltip,
                sr.raw_coef,
                sr.coef_types
            FROM skill_rank sr
            JOIN skill s ON s.id = sr.skill_id
            LEFT JOIN ability a ON a.ability_id = sr.ability_id
            WHERE sr.id IN (
                SELECT MIN(sr2.id)
                FROM skill_rank sr2
                WHERE sr2.skill_id = sr.skill_id
                GROUP BY sr2.skill_id, COALESCE(sr2.morph, 0)
            )
            AND COALESCE(NULLIF(sr.raw_name, ''), s.name) IS NOT NULL
            AND TRIM(COALESCE(NULLIF(sr.raw_name, ''), s.name)) <> ''
            ORDER BY COALESCE(NULLIF(sr.raw_name, ''), s.name) COLLATE NOCASE,
                     s.base_ability_id,
                     COALESCE(sr.morph, 0)
            """
        ).fetchall()

        columns = {str(column[1]) for column in db.execute("PRAGMA table_info(skill_rank)").fetchall()}

    if not {"morph", "ability_id"}.issubset(columns):
        return []

    names = [
        "ability_id", "base_ability_id", "name", "index_name", "description",
        "texture", "class_type", "skill_line", "target", "skill_type",
        "is_passive", "is_player", "is_crafted", "crafted_id", "rank", "morph",
        "base_mechanic", "cost", "duration", "raw_tooltip", "raw_coef", "coef_types",
    ]
    return [dict(zip(names, row)) for row in rows]


def eligible_skill_choices(
    database_path: str | Path = DEFAULT_DATABASE,
    *,
    character_class: str | None,
    slot_index: int,
    vampire: bool = False,
    werewolf: bool = False,
    transformed_form: str | None = None,
) -> list[dict]:
    return filter_skill_choices(
        load_skill_choices(database_path),
        character_class=character_class,
        slot_index=slot_index,
        vampire=vampire,
        werewolf=werewolf,
        transformed_form=transformed_form,
    )


def available_skill_pairs(
    database_path: str | Path = DEFAULT_DATABASE,
    character_class: str | None = None,
) -> tuple[tuple[int, str], ...]:
    """Return the same alphabetical base/morph choices used by the UI."""
    records: list[dict] = []
    for slot in range(6):
        records.extend(
            eligible_skill_choices(
                database_path,
                character_class=character_class,
                slot_index=slot,
            )
        )

    selected: dict[tuple[int, int], dict] = {}
    for record in records:
        key = (
            int(record.get("base_ability_id") or record.get("ability_id") or 0),
            int(record.get("morph") or 0),
        )
        selected[key] = record

    ordered = sorted(
        selected.values(),
        key=lambda record: (
            str(record.get("name") or "").casefold(),
            int(record.get("base_ability_id") or record.get("ability_id") or 0),
            int(record.get("morph") or 0),
        ),
    )
    return tuple(
        (int(record["ability_id"]), str(record["name"]))
        for record in ordered
    )
