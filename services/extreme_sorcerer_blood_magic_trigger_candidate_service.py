from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from services.extreme_heal_class_route_service import canonical_class_skill_line_id


@dataclass(frozen=True)
class ExtremeSorcererBloodMagicTriggerCandidate:
    name: str
    ability_id: int
    skill_rank_id: int
    rank: int
    morph: int
    base_cost: float
    base_mechanic: int
    skill_line: str


class ExtremeSorcererBloodMagicTriggerCandidateService:
    """Discover reviewed costed Dark Magic casts that can trigger Blood Magic.

    U50 Blood Magic requires casting a Dark Magic ability *with a cost*. Route
    eligibility therefore comes from canonical class-line ownership plus a
    concrete positive ``ability.base_cost`` row. This service does not infer cost
    from names, descriptions, or skill-line membership alone.
    """

    DARK_MAGIC_LINE_ID = "dark_magic"

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def candidates(self) -> tuple[ExtremeSorcererBloodMagicTriggerCandidate, ...]:
        if not self.database_path.exists():
            raise FileNotFoundError(self.database_path)
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                """
                SELECT
                    sr.skill_id,
                    sr.id AS skill_rank_id,
                    sr.ability_id,
                    COALESCE(sr.rank, 0) AS rank,
                    COALESCE(sr.morph, 0) AS morph,
                    COALESCE(NULLIF(a.name, ''), NULLIF(sr.raw_name, ''), s.name, '') AS name,
                    COALESCE(a.skill_line, '') AS skill_line,
                    a.base_cost,
                    a.base_mechanic,
                    COALESCE(a.is_player, 0) AS is_player,
                    COALESCE(a.is_passive, s.is_passive, 0) AS is_passive
                FROM skill_rank sr
                JOIN skill s ON s.id = sr.skill_id
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE COALESCE(a.is_player, 0) = 1
                  AND COALESCE(a.is_passive, s.is_passive, 0) = 0
                  AND a.base_cost IS NOT NULL
                  AND a.base_cost > 0
                  AND a.base_mechanic IS NOT NULL
                ORDER BY sr.skill_id, COALESCE(sr.morph, 0), COALESCE(sr.rank, 0) DESC,
                         sr.ability_id DESC
                """
            ).fetchall()

        grouped: dict[tuple[int, int], sqlite3.Row] = {}
        for row in rows:
            if canonical_class_skill_line_id(row["skill_line"]) != self.DARK_MAGIC_LINE_ID:
                continue
            key = (int(row["skill_id"]), int(row["morph"] or 0))
            grouped.setdefault(key, row)

        return tuple(
            sorted(
                (
                    ExtremeSorcererBloodMagicTriggerCandidate(
                        name=str(row["name"] or "").strip(),
                        ability_id=int(row["ability_id"]),
                        skill_rank_id=int(row["skill_rank_id"]),
                        rank=int(row["rank"] or 0),
                        morph=int(row["morph"] or 0),
                        base_cost=float(row["base_cost"]),
                        base_mechanic=int(row["base_mechanic"]),
                        skill_line=str(row["skill_line"] or "").strip(),
                    )
                    for row in grouped.values()
                    if str(row["name"] or "").strip()
                ),
                key=lambda item: (item.name.casefold(), item.morph, item.ability_id),
            )
        )
