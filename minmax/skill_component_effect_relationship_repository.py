from __future__ import annotations

"""Read-only repository for canonical Phase 6 component-to-effect relationships."""

import sqlite3
from pathlib import Path

from .skill_component_effect_relationship import (
    SkillComponentEffectRelationship,
    extract_explicit_effect_applications,
)
from .skill_component_text_evidence import extract_component_text_evidence


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


class SkillComponentEffectRelationshipRepository:
    """Resolve explicit named-effect applications for coefficient components.

    The repository joins two existing sources of truth:

    - coefficient-local UESP tooltip evidence from ``ability.coef_description``;
    - the canonical named-effect vocabulary from ``combat_effect``.

    It never writes rows and never infers chance, cooldown, duration, uptime, or
    current combat state. Those temporal concerns remain outside Phase 6.
    """

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _table_exists(db: sqlite3.Connection, name: str) -> bool:
        return db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone() is not None

    def _known_effect_names(self, db: sqlite3.Connection) -> tuple[str, ...]:
        if not self._table_exists(db, "combat_effect"):
            return ()
        return tuple(
            str(row[0]).strip()
            for row in db.execute(
                "SELECT name FROM combat_effect "
                "WHERE name IS NOT NULL AND TRIM(name) <> '' ORDER BY name"
            )
        )

    def resolve(
        self,
        skill_rank_id: int,
        coefficient_number: int,
    ) -> tuple[SkillComponentEffectRelationship, ...]:
        if not self.database_path.exists():
            return ()

        with sqlite3.connect(self.database_path) as db:
            required = ("skill_rank", "ability", "combat_effect")
            if not all(self._table_exists(db, name) for name in required):
                return ()

            row = db.execute(
                """
                SELECT a.coef_description
                FROM skill_rank sr
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE sr.id = ?
                """,
                (int(skill_rank_id),),
            ).fetchone()
            if row is None:
                return ()

            known_effect_names = self._known_effect_names(db)

        evidence = extract_component_text_evidence(
            row[0],
            int(coefficient_number),
        )
        if not evidence.fragment:
            return ()

        return extract_explicit_effect_applications(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            fragment=evidence.fragment,
            known_effect_names=known_effect_names,
        )
