from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path
import sqlite3

from minmax.character_build.character_class import CLASS_SKILL_LINES
from minmax.character_progression import CharacterProgression
from services.extreme_heal_class_route_service import (
    ExtremeHealClassRoute,
    canonical_class_skill_line_id,
)


@lru_cache(maxsize=8)
def _class_passive_max_ranks_for_database(
    database_path: str,
) -> tuple[tuple[str, tuple[tuple[str, int], ...]], ...]:
    """Load immutable class-passive max-rank evidence once per canonical database."""

    path = Path(database_path)
    if not path.exists():
        raise FileNotFoundError(path)

    with sqlite3.connect(path) as db:
        skill_columns = {
            str(row[1])
            for row in db.execute("PRAGMA table_info(skill)").fetchall()
        }
        rank_columns = {
            str(row[1])
            for row in db.execute("PRAGMA table_info(skill_rank)").fetchall()
        }
        required_skill = {"id", "name", "skill_line", "is_passive"}
        required_rank = {"skill_id", "rank"}
        missing = sorted(required_skill - skill_columns)
        if missing or not required_rank.issubset(rank_columns):
            details = []
            if missing:
                details.append("skill: " + ", ".join(missing))
            missing_rank = sorted(required_rank - rank_columns)
            if missing_rank:
                details.append("skill_rank: " + ", ".join(missing_rank))
            raise ValueError(
                "Canonical hypothetical class progression requires columns: "
                + "; ".join(details)
            )

        rows = db.execute(
            """
            SELECT
                s.name,
                COALESCE(s.skill_line, '') AS skill_line,
                MAX(sr.rank) AS max_rank
            FROM skill s
            JOIN skill_rank sr ON sr.skill_id = s.id
            WHERE COALESCE(s.is_passive, 0) != 0
              AND TRIM(COALESCE(s.skill_line, '')) <> ''
            GROUP BY s.id, s.name, s.skill_line
            ORDER BY s.skill_line COLLATE NOCASE, s.name COLLATE NOCASE
            """
        ).fetchall()

    all_class_lines = {
        line
        for lines in CLASS_SKILL_LINES.values()
        for line in lines
    }
    result: dict[str, dict[str, int]] = {}
    for raw_name, raw_line, raw_rank in rows:
        line = canonical_class_skill_line_id(raw_line)
        if line not in all_class_lines:
            continue
        name = str(raw_name or "").strip()
        try:
            rank = int(raw_rank or 0)
        except (TypeError, ValueError):
            rank = 0
        if name and rank > 0:
            result.setdefault(line, {})[name] = rank

    return tuple(
        (line, tuple(sorted(passives.items(), key=lambda item: item[0].casefold())))
        for line, passives in sorted(result.items(), key=lambda item: item[0].casefold())
    )


class ExtremeHypotheticalClassProgressionService:
    """Build a fair fully-leveled class progression snapshot for Extreme routes.

    Extreme build search is not limited to the progression of the saved character.
    For a hypothetical class/class-line route, class skill lines are treated as
    fully leveled and their canonical passive ranks are set to the recorded max.
    Non-class progression, attributes, CP, and explicit non-class passive ranks
    remain inherited from the supplied character snapshot.

    This service changes progression ownership/rank evidence only. It does not
    claim that every passive mechanic is modeled. Unresolved passive effects stay
    unresolved in the shared calculation pipeline.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def normalize(
        self,
        progression: CharacterProgression,
        route: ExtremeHealClassRoute,
    ) -> CharacterProgression:
        class_passives = self._class_passive_max_ranks()
        all_class_lines = {
            line
            for lines in CLASS_SKILL_LINES.values()
            for line in lines
        }
        selected_lines = set(route.equipped_skill_lines)

        inherited_lines = tuple(
            line
            for line in progression.owned_skill_lines
            if canonical_class_skill_line_id(line) not in all_class_lines
        )
        owned_lines = tuple(dict.fromkeys((*inherited_lines, *sorted(selected_lines))))

        passive_ranks = dict(progression.passive_ranks or {})
        class_passive_names = {
            name.casefold()
            for line_passives in class_passives.values()
            for name in line_passives
        }
        passive_ranks = {
            name: rank
            for name, rank in passive_ranks.items()
            if name.casefold() not in class_passive_names
        }
        for line in sorted(selected_lines):
            passive_ranks.update(class_passives.get(line, {}))

        return replace(
            progression,
            owned_skill_lines=owned_lines,
            passive_ranks=passive_ranks,
        )

    def _class_passive_max_ranks(self) -> dict[str, dict[str, int]]:
        evidence = _class_passive_max_ranks_for_database(
            str(self.database_path.resolve())
        )
        return {
            line: dict(passives)
            for line, passives in evidence
        }
