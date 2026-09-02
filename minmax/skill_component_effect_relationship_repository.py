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

    The repository joins coefficient-local UESP tooltip evidence with the
    canonical named-effect vocabulary already present in the database. The
    specialized ``combat_effect`` table remains preferred, while the broader
    ``effect`` table supplements names that are canonical EffectVariant
    identities but have not been duplicated into ``combat_effect``.

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
        names: set[str] = set()
        for table in ("combat_effect", "effect"):
            if not self._table_exists(db, table):
                continue
            for row in db.execute(
                f"SELECT name FROM {table} WHERE name IS NOT NULL AND TRIM(name) <> ''"
            ):
                name = str(row[0]).strip()
                if name:
                    names.add(name)
        return tuple(sorted(names, key=str.casefold))

    def resolve(
        self,
        skill_rank_id: int,
        coefficient_number: int,
    ) -> tuple[SkillComponentEffectRelationship, ...]:
        if not self.database_path.exists():
            return ()

        with sqlite3.connect(self.database_path) as db:
            if not all(self._table_exists(db, name) for name in ("skill_rank", "ability")):
                return ()
            if not any(self._table_exists(db, name) for name in ("combat_effect", "effect")):
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
