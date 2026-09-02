from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .skill_component_source_stat_rule import (
    SkillComponentSourceStatRule,
    extract_source_mapped_stat_rule,
)


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "eso.db"


class SkillComponentSourceStatRuleRepository:
    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _table_exists(db: sqlite3.Connection, name: str) -> bool:
        return db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone() is not None

    @staticmethod
    def _columns(db: sqlite3.Connection, table: str) -> set[str]:
        return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})")}

    def resolve(
        self,
        skill_rank_id: int,
        coefficient_number: int,
    ) -> tuple[SkillComponentSourceStatRule, ...]:
        if not self.database_path.exists():
            return ()

        with sqlite3.connect(self.database_path) as db:
            if not all(self._table_exists(db, name) for name in ("skill_rank", "ability")):
                return ()
            ability_columns = self._columns(db, "ability")
            required = {"coef_description", "raw_description"}
            if not required.issubset(ability_columns):
                return ()
            raw_json_expr = "a.raw_json" if "raw_json" in ability_columns else "NULL"
            row = db.execute(
                f"""
                SELECT a.coef_description, a.raw_description, {raw_json_expr}
                FROM skill_rank sr
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE sr.id = ?
                """,
                (int(skill_rank_id),),
            ).fetchone()
            if row is None:
                return ()

        desc_header = ""
        if row[2]:
            try:
                payload = json.loads(str(row[2]))
                if isinstance(payload, dict):
                    desc_header = str(payload.get("descHeader") or "")
            except (TypeError, ValueError, json.JSONDecodeError):
                desc_header = ""

        return extract_source_mapped_stat_rule(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            raw_description=str(row[1] or ""),
            coef_description=str(row[0] or ""),
            desc_header=desc_header,
        )
