from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class ComponentEvidenceRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    name: str
    target: str | None
    duration: float | None
    tick_time: float | None
    radius: float | None
    is_channeled: bool
    coef_description: str | None
    raw_description: str | None
    raw_tooltip: str | None

    @property
    def has_target_evidence(self) -> bool:
        return bool(str(self.target or "").strip())

    @property
    def has_timing_evidence(self) -> bool:
        return any(value not in (None, 0, 0.0) for value in (self.duration, self.tick_time))

    @property
    def has_radius_evidence(self) -> bool:
        return self.radius not in (None, 0, 0.0)

    @property
    def has_text_evidence(self) -> bool:
        return any(
            bool(str(value or "").strip())
            for value in (self.coef_description, self.raw_description, self.raw_tooltip)
        )


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def load_component_evidence(
    database_path: str | Path,
    *,
    skill_rank_id: int | None = None,
    ability_id: int | None = None,
    limit: int | None = None,
) -> tuple[ComponentEvidenceRow, ...]:
    """Read classification evidence without interpreting it as mechanics.

    This deliberately returns source facts only. A non-zero duration does not
    prove DoT, a radius does not by itself prove AoE damage, and target text does
    not prove a coefficient's effect kind. Those conclusions belong in a later
    verified mapping/import layer.
    """

    path = Path(database_path)
    if not path.exists():
        raise FileNotFoundError(path)

    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        required = {"skill_rank", "skill_coefficient", "ability"}
        missing = sorted(name for name in required if not _table_exists(db, name))
        if missing:
            raise RuntimeError("Required tables are missing: " + ", ".join(missing))

        where: list[str] = []
        params: list[object] = []
        if skill_rank_id is not None:
            where.append("sr.id = ?")
            params.append(int(skill_rank_id))
        if ability_id is not None:
            where.append("sr.ability_id = ?")
            params.append(int(ability_id))

        sql = """
            SELECT
                sr.id AS skill_rank_id,
                sc.coefficient_number,
                sr.ability_id,
                COALESCE(NULLIF(a.name, ''), NULLIF(sr.raw_name, ''), '') AS name,
                a.target,
                a.duration,
                a.tick_time,
                a.radius,
                COALESCE(a.is_channeled, 0) AS is_channeled,
                a.coef_description,
                a.raw_description,
                a.raw_tooltip
            FROM skill_rank sr
            JOIN skill_coefficient sc ON sc.skill_rank_id = sr.id
            LEFT JOIN ability a ON a.ability_id = sr.ability_id
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY sr.id, sc.coefficient_number"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(0, int(limit)))

        rows = db.execute(sql, tuple(params)).fetchall()

    return tuple(
        ComponentEvidenceRow(
            skill_rank_id=int(row["skill_rank_id"]),
            coefficient_number=int(row["coefficient_number"]),
            ability_id=int(row["ability_id"]),
            name=str(row["name"] or ""),
            target=row["target"],
            duration=float(row["duration"]) if row["duration"] is not None else None,
            tick_time=float(row["tick_time"]) if row["tick_time"] is not None else None,
            radius=float(row["radius"]) if row["radius"] is not None else None,
            is_channeled=bool(row["is_channeled"]),
            coef_description=row["coef_description"],
            raw_description=row["raw_description"],
            raw_tooltip=row["raw_tooltip"],
        )
        for row in rows
    )


def summarize(rows: tuple[ComponentEvidenceRow, ...]) -> dict[str, int]:
    return {
        "components": len(rows),
        "target": sum(row.has_target_evidence for row in rows),
        "timing": sum(row.has_timing_evidence for row in rows),
        "radius": sum(row.has_radius_evidence for row in rows),
        "channeled": sum(row.is_channeled for row in rows),
        "text": sum(row.has_text_evidence for row in rows),
    }


def _clean(value: object, *, max_len: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit raw evidence available for per-coefficient skill classification."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--skill-rank-id", type=int)
    parser.add_argument("--ability-id", type=int)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--samples", type=int, default=12)
    args = parser.parse_args()

    rows = load_component_evidence(
        args.database,
        skill_rank_id=args.skill_rank_id,
        ability_id=args.ability_id,
        limit=args.limit,
    )
    counts = summarize(rows)

    print("\n========================================")
    print(" PHASE 3 SKILL COMPONENT EVIDENCE AUDIT")
    print("========================================")
    print(f"Database:    {args.database}")
    print(f"Components:  {counts['components']}")
    print(f"Target text: {counts['target']}")
    print(f"Timing:      {counts['timing']}")
    print(f"Radius:      {counts['radius']}")
    print(f"Channeled:   {counts['channeled']}")
    print(f"Raw text:    {counts['text']}")
    print()
    print("NOTE: these are evidence fields, not inferred mechanics.")
    print("Duration != DoT, radius != AoE damage, and target != effect kind.")

    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.name}"
        )
        print(
            f"target={_clean(row.target)} duration={row.duration} "
            f"tick={row.tick_time} radius={row.radius} channeled={row.is_channeled}"
        )
        if row.coef_description:
            print(f"coef_description: {_clean(row.coef_description)}")
        if row.raw_description:
            print(f"raw_description:  {_clean(row.raw_description)}")
        if row.raw_tooltip:
            print(f"raw_tooltip:      {_clean(row.raw_tooltip)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
