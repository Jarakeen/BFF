from __future__ import annotations

import sqlite3
from pathlib import Path


class SkillLineRepository:
    """Resolve canonical skill-line and passive metadata from eso.db."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._skill_line_cache: dict[tuple[str, str], str | None] = {}
        self._passive_max_rank_cache: dict[str, int | None] = {}
        self._preload_complete = False

    @staticmethod
    def _lookup_key(value: str) -> str:
        """Mirror SQLite LOWER(TRIM(...)) lookup semantics for cache keys."""
        return str(value or "").strip().casefold()

    def preload_all_static(self) -> None:
        """Warm instance-local canonical skill/passive lookup caches in one read.

        This changes only when immutable metadata is loaded. Ordinary lookups retain
        their existing SQL fallback, and a new repository instance always observes a
        fresh database state.
        """
        if self._preload_complete or not self.database_path.exists():
            return

        with sqlite3.connect(self.database_path) as db:
            ability_columns = {
                str(row[1]) for row in db.execute("PRAGMA table_info(ability)").fetchall()
            }
            if {"name", "skill_line"}.issubset(ability_columns):
                class_expr = (
                    "TRIM(COALESCE(class_type, ''))" if "class_type" in ability_columns else "''"
                )
                passive_clause = (
                    "AND COALESCE(is_passive, 0) = 0" if "is_passive" in ability_columns else ""
                )
                rows = db.execute(
                    f"""
                    SELECT
                        TRIM(COALESCE(name, '')),
                        {class_expr},
                        TRIM(COALESCE(skill_line, ''))
                    FROM ability
                    WHERE TRIM(COALESCE(name, '')) <> ''
                      AND TRIM(COALESCE(skill_line, '')) <> ''
                      {passive_clause}
                    ORDER BY name COLLATE NOCASE, skill_line COLLATE NOCASE
                    """
                ).fetchall()

                grouped: dict[tuple[str, str], set[str]] = {}
                for name, class_name, skill_line in rows:
                    clean_name = str(name or "").strip()
                    clean_class = str(class_name or "").strip()
                    clean_line = str(skill_line or "").strip()
                    if not clean_name or not clean_line:
                        continue
                    grouped.setdefault(
                        (self._lookup_key(clean_name), self._lookup_key(clean_class)), set()
                    ).add(clean_line)
                    # Calls without a class filter are legal only when the ability
                    # name resolves to one unambiguous canonical skill line.
                    grouped.setdefault((self._lookup_key(clean_name), ""), set()).add(clean_line)

                for cache_key, lines in grouped.items():
                    self._skill_line_cache[cache_key] = (
                        next(iter(lines)) if len(lines) == 1 else None
                    )

            skill_columns = {
                str(row[1]) for row in db.execute("PRAGMA table_info(skill)").fetchall()
            }
            rank_columns = {
                str(row[1]) for row in db.execute("PRAGMA table_info(skill_rank)").fetchall()
            }
            if {"id", "name", "is_passive"}.issubset(skill_columns) and {
                "skill_id",
                "rank",
            }.issubset(rank_columns):
                rows = db.execute(
                    """
                    SELECT TRIM(COALESCE(s.name, '')), MAX(sr.rank)
                    FROM skill s
                    JOIN skill_rank sr ON sr.skill_id = s.id
                    WHERE COALESCE(s.is_passive, 0) = 1
                      AND TRIM(COALESCE(s.name, '')) <> ''
                    GROUP BY LOWER(TRIM(s.name))
                    """
                ).fetchall()
                for name, rank in rows:
                    result: int | None = None
                    if rank is not None:
                        try:
                            value = int(rank)
                        except (TypeError, ValueError):
                            value = 0
                        if value > 0:
                            result = value
                    self._passive_max_rank_cache[self._lookup_key(name)] = result

        self._preload_complete = True

    def skill_line_for_ability_name(self, ability_name: str, *, class_name: str = "") -> str | None:
        name = str(ability_name or "").strip()
        if not name:
            return None

        cache_key = (self._lookup_key(name), self._lookup_key(class_name))
        if cache_key in self._skill_line_cache:
            return self._skill_line_cache[cache_key]
        if not self.database_path.exists():
            return None

        with sqlite3.connect(self.database_path) as db:
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)").fetchall()}
            required = {"name", "skill_line"}
            if not required.issubset(columns):
                self._skill_line_cache[cache_key] = None
                return None

            clauses = ["LOWER(TRIM(name)) = LOWER(TRIM(?))"]
            params: list[str] = [name]
            if class_name.strip() and "class_type" in columns:
                clauses.append("LOWER(TRIM(COALESCE(class_type, ''))) = LOWER(TRIM(?))")
                params.append(class_name.strip())
            if "is_passive" in columns:
                clauses.append("COALESCE(is_passive, 0) = 0")

            rows = db.execute(
                f"""
                SELECT DISTINCT TRIM(COALESCE(skill_line, ''))
                FROM ability
                WHERE {' AND '.join(clauses)}
                  AND TRIM(COALESCE(skill_line, '')) <> ''
                ORDER BY 1
                """,
                params,
            ).fetchall()

        lines = [str(row[0]).strip() for row in rows if str(row[0] or "").strip()]
        result = lines[0] if len(lines) == 1 else None
        self._skill_line_cache[cache_key] = result
        return result

    def passive_max_rank(self, passive_name: str) -> int | None:
        """Return the highest canonical rank recorded for one player passive."""
        name = str(passive_name or "").strip()
        if not name:
            return None

        cache_key = self._lookup_key(name)
        if cache_key in self._passive_max_rank_cache:
            return self._passive_max_rank_cache[cache_key]
        if not self.database_path.exists():
            return None

        with sqlite3.connect(self.database_path) as db:
            skill_columns = {str(row[1]) for row in db.execute("PRAGMA table_info(skill)").fetchall()}
            rank_columns = {str(row[1]) for row in db.execute("PRAGMA table_info(skill_rank)").fetchall()}
            if not {"id", "name", "is_passive"}.issubset(skill_columns):
                self._passive_max_rank_cache[cache_key] = None
                return None
            if not {"skill_id", "rank"}.issubset(rank_columns):
                self._passive_max_rank_cache[cache_key] = None
                return None
            row = db.execute(
                """
                SELECT MAX(sr.rank)
                FROM skill s
                JOIN skill_rank sr ON sr.skill_id = s.id
                WHERE COALESCE(s.is_passive, 0) = 1
                  AND LOWER(TRIM(s.name)) = LOWER(TRIM(?))
                """,
                (name,),
            ).fetchone()

        result: int | None = None
        if row is not None and row[0] is not None:
            try:
                value = int(row[0])
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                result = value

        self._passive_max_rank_cache[cache_key] = result
        return result
