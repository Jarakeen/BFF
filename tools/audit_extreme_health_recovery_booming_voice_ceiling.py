from __future__ import annotations

"""Inspect canonical evidence needed to bound Booming Voice Health Recovery.

Booming Voice inherits The Storm Voice's ``Ultimate spent`` event.  This audit keeps
stored Ultimate separate from the cost of the Ultimate ability actually cast, prints
the canonical passive evidence, and enumerates the base-cost frontier of Ultimates a
pure Dragonknight can legally own from native or shared combat skill lines.

It deliberately does not treat the 500 stored-Ultimate cap as the spend value.
"""

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.class_mastery_repository import ClassMasteryRepository
from services.eso_character_progression_contract import ULTIMATE_RULES


_DK_NATIVE_LINES = frozenset({"ardent flame", "draconic power", "earthen heart"})
_EXCLUDED_SHARED_LINES = frozenset(
    {
        "class mastery",
        "crafting",
        "racial",
        "excavation",
        "legerdemain",
        "scrying",
        "thieves guild",
        "dark brotherhood",
    }
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def _select_existing(columns: set[str], names: tuple[str, ...], *, prefix: str = "") -> list[str]:
    result: list[str] = []
    for name in names:
        if name in columns:
            source = f"{prefix}.{name}" if prefix else name
            result.append(f"{source} AS {prefix + '_' if prefix else ''}{name}")
    return result


def _key(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _pure_dk_ultimate_candidate(row: sqlite3.Row) -> bool:
    owner = _key(row["s_class_type"] if "s_class_type" in row.keys() else "")
    line = _key(row["s_skill_line"] if "s_skill_line" in row.keys() else "")
    if owner:
        return owner == "dragonknight" and line in _DK_NATIVE_LINES
    return bool(line and line not in _EXCLUDED_SHARED_LINES)


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    mastery = tuple(
        row
        for row in ClassMasteryRepository(database).all()
        if row.name.casefold() == "booming voice"
    )

    print("EXTREME HEALTH RECOVERY BOOMING VOICE CEILING EVIDENCE")
    print(f"database={database}")
    print("mode=canonical_cost_frontier_not_stored_ultimate_assumption")
    print()
    print("ULTIMATE CONTRACT")
    print(f"maximum_resource={ULTIMATE_RULES.maximum_resource}")
    print(f"one_ultimate_per_bar={ULTIMATE_RULES.one_ultimate_per_bar}")
    print(f"normal_cast_consumes_accumulated_resource={ULTIMATE_RULES.normal_cast_consumes_accumulated_resource}")
    print("stored_resource_is_not_assumed_spend_value=True")
    print()

    print("CLASS MASTERY ROW")
    if not mastery:
        print("  <missing Booming Voice Class Mastery row>")
    for row in mastery:
        print(
            f"  class={row.class_name!r} skill_id={row.skill_id} base_ability_id={row.base_ability_id} "
            f"name={row.name!r}"
        )
        print(f"  description={row.description!r}")
    print()

    if not database.is_file():
        print("database_missing=True")
        return 2

    ultimate_candidates: list[sqlite3.Row] = []
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        skill_cols = _columns(db, "skill")
        rank_cols = _columns(db, "skill_rank")
        ability_cols = _columns(db, "ability")

        print("MATCHING SKILL ROWS")
        skill_select = _select_existing(
            skill_cols,
            (
                "id", "base_ability_id", "name", "class_type", "skill_line", "skill_type",
                "description", "is_passive", "is_player", "is_crafted",
            ),
            prefix="s",
        )
        if skill_select:
            text_parts = [
                part for part in (
                    "LOWER(COALESCE(s.name, ''))",
                    "LOWER(COALESCE(s.description, ''))" if "description" in skill_cols else "''",
                )
            ]
            rows = db.execute(
                f"SELECT {', '.join(skill_select)} FROM skill s "
                f"WHERE {' OR '.join(f'{part} LIKE ?' for part in text_parts for _ in (0, 1))} "
                "ORDER BY LOWER(COALESCE(s.name, '')), s.id",
                tuple(value for _part in text_parts for value in ("%storm voice%", "%booming voice%")),
            ).fetchall()
            if not rows:
                print("  <none>")
            for row in rows:
                print("  " + repr(dict(row)))
        else:
            print("  <skill schema unavailable>")
        print()

        print("MATCHING SKILL RANK / ABILITY ROWS")
        if {"skill_id", "ability_id"}.issubset(rank_cols) and "id" in skill_cols:
            select = []
            select.extend(_select_existing(skill_cols, ("id", "name", "class_type", "skill_line"), prefix="s"))
            select.extend(_select_existing(rank_cols, ("ability_id", "rank", "morph", "cost", "raw_name", "raw_description"), prefix="sr"))
            select.extend(_select_existing(ability_cols, ("name", "base_mechanic", "description"), prefix="a"))
            ability_join = "LEFT JOIN ability a ON a.ability_id = sr.ability_id" if "ability_id" in ability_cols else ""
            predicates = ["LOWER(COALESCE(s.name, '')) LIKE ?"]
            params: list[str] = ["%storm voice%"]
            if "raw_name" in rank_cols:
                predicates.append("LOWER(COALESCE(sr.raw_name, '')) LIKE ?")
                params.append("%storm voice%")
            if "raw_description" in rank_cols:
                predicates.append("LOWER(COALESCE(sr.raw_description, '')) LIKE ?")
                params.append("%storm voice%")
            if "name" in ability_cols:
                predicates.append("LOWER(COALESCE(a.name, '')) LIKE ?")
                params.append("%storm voice%")
            if "description" in ability_cols:
                predicates.append("LOWER(COALESCE(a.description, '')) LIKE ?")
                params.append("%storm voice%")
            rows = db.execute(
                f"SELECT {', '.join(select)} FROM skill_rank sr "
                "JOIN skill s ON s.id = sr.skill_id "
                f"{ability_join} "
                f"WHERE {' OR '.join(predicates)} "
                "ORDER BY s.id, COALESCE(sr.rank, 0), COALESCE(sr.morph, 0), sr.ability_id",
                tuple(params),
            ).fetchall()
            if not rows:
                print("  <none>")
            for row in rows:
                print("  " + repr(dict(row)))
        else:
            print("  <rank schema unavailable>")
        print()

        print("PURE DRAGONKNIGHT ULTIMATE BASE-COST FRONTIER")
        required_rank = {"skill_id", "ability_id", "cost"}
        if required_rank.issubset(rank_cols) and {"id", "class_type", "skill_line", "is_passive", "is_player"}.issubset(skill_cols) and {"ability_id", "base_mechanic"}.issubset(ability_cols):
            rows = db.execute(
                """
                SELECT
                    s.id AS s_id,
                    s.name AS s_name,
                    s.class_type AS s_class_type,
                    s.skill_line AS s_skill_line,
                    s.base_ability_id AS s_base_ability_id,
                    sr.ability_id AS sr_ability_id,
                    sr.rank AS sr_rank,
                    COALESCE(sr.morph, 0) AS sr_morph,
                    sr.cost AS sr_cost,
                    COALESCE(NULLIF(sr.raw_name, ''), NULLIF(a.name, ''), s.name) AS resolved_name,
                    a.base_mechanic AS a_base_mechanic
                FROM skill_rank sr
                JOIN skill s ON s.id = sr.skill_id
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE COALESCE(s.is_player, 0) != 0
                  AND COALESCE(s.is_passive, 0) = 0
                  AND COALESCE(a.base_mechanic, 0) = 8
                  AND sr.cost IS NOT NULL
                ORDER BY CAST(sr.cost AS REAL) DESC, LOWER(COALESCE(NULLIF(sr.raw_name, ''), NULLIF(a.name, ''), s.name)), sr.ability_id
                """
            ).fetchall()
            ultimate_candidates = [row for row in rows if _pure_dk_ultimate_candidate(row)]
            if not ultimate_candidates:
                print("  <no cost-bearing ultimate candidates>")
            for row in ultimate_candidates:
                print("  " + repr(dict(row)))
        else:
            print("  <ultimate cost schema unavailable>")

    print()
    numeric_costs: list[float] = []
    for row in ultimate_candidates:
        try:
            numeric_costs.append(float(row["sr_cost"]))
        except (TypeError, ValueError):
            continue
    max_cost = max(numeric_costs) if numeric_costs else None
    print(f"ultimate_candidates_reviewed={len(ultimate_candidates)}")
    print(f"maximum_legal_base_ultimate_cost={max_cost if max_cost is not None else '<unresolved>'}")
    if max_cost is not None:
        print(f"booming_voice_flat_ceiling_if_cost_semantics={max_cost * 5.0:.3f}")
        print("NEXT_STEP=confirm cost semantics against The Storm Voice event contract, then wire this proven cost ceiling into route dominance")
    else:
        print("NEXT_STEP=resolve missing Ultimate cost evidence before assigning Booming Voice a numeric ceiling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
