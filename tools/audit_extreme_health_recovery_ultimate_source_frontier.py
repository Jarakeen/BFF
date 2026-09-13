from __future__ import annotations

"""Inventory the U50 Ultimate-generation source frontier for the Health Recovery route."""

import argparse
from collections import Counter
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ultimate_source_reference_frontier_service import (
    UltimateSourceReferenceFrontierService,
    UltimateSourceRouteStatus,
)


DEFAULT_SOURCE = ROOT / "math" / "ESO Ultimate Generation Calculator _ U50 _ Hyperioxes.htm"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    return parser


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _canonical_matches(database: Path, label: str) -> tuple[str, ...]:
    if not database.is_file():
        return ()
    matches: list[str] = []
    with sqlite3.connect(database) as db:
        skill_columns = _columns(db, "skill")
        if {"name", "description"}.issubset(skill_columns):
            class_expr = "COALESCE(class_type, '')" if "class_type" in skill_columns else "''"
            line_expr = "COALESCE(skill_line, '')" if "skill_line" in skill_columns else "''"
            rows = db.execute(
                f"""
                SELECT name, {class_expr}, {line_expr}, COALESCE(description, '')
                FROM skill
                WHERE LOWER(COALESCE(name, '')) = LOWER(?)
                ORDER BY id
                """,
                (label,),
            ).fetchall()
            matches.extend(
                f"skill name={name!r} class={class_name!r} line={line!r} description={description!r}"
                for name, class_name, line, description in rows
            )

        gear_columns = _columns(db, "gear_set")
        bonus_columns = _columns(db, "gear_set_bonus")
        if {"id", "name"}.issubset(gear_columns) and {"set_id", "piece_count", "description"}.issubset(bonus_columns):
            rows = db.execute(
                """
                SELECT gs.name, gsb.piece_count, gsb.description
                FROM gear_set gs JOIN gear_set_bonus gsb ON gsb.set_id = gs.id
                WHERE LOWER(COALESCE(gs.name, '')) = LOWER(?)
                ORDER BY gsb.piece_count, gsb.id
                """,
                (label,),
            ).fetchall()
            matches.extend(
                f"gear name={name!r} pieces={pieces} description={description!r}"
                for name, pieces, description in rows
            )
    return tuple(matches)


def main() -> int:
    args = _parser().parse_args()
    database, source = Path(args.database), Path(args.source)
    if not source.is_file():
        print(f"source_missing={source}")
        return 2

    rows = UltimateSourceReferenceFrontierService.parse(
        source.read_text(encoding="utf-8", errors="replace")
    )
    counts = Counter(row.route_status.value for row in rows)

    print("EXTREME HEALTH RECOVERY ULTIMATE SOURCE FRONTIER")
    print(f"database={database}")
    print(f"source={source}")
    print("route=Khajiit pure Dragonknight with Booming Voice")
    print("required_additional_ultimate=114.000")
    print(f"reference_sources_reviewed={len(rows)}")
    print("status_counts=" + ", ".join(f"{key}:{value}" for key, value in sorted(counts.items())))
    print()

    for row in rows:
        print(
            f"{row.source_id}: label={row.label!r} category={row.category!r} "
            f"displayed_rate={row.displayed_rate!r} status={row.route_status.value}"
        )
        print(f"  reason={row.reason}")
        if row.route_status in {
            UltimateSourceRouteStatus.SEARCH_STATE_MUTATION,
            UltimateSourceRouteStatus.EXACT_REVIEW_REQUIRED,
        }:
            matches = _canonical_matches(database, row.label)
            if matches:
                for match in matches:
                    print(f"  canonical={match}")
            else:
                print("  canonical=<no exact name match in reviewed skill/gear tables>")

    candidates = tuple(
        row for row in rows
        if row.route_status in {
            UltimateSourceRouteStatus.SEARCH_STATE_MUTATION,
            UltimateSourceRouteStatus.EXACT_REVIEW_REQUIRED,
        }
    )
    print()
    print(f"remaining_route_candidates={len(candidates)}")
    print("remaining_candidate_ids=" + repr(tuple(row.source_id for row in candidates)))
    print("ultimate_source_denominator_discovered=True")
    print("ultimate_source_numeric_legality_proven=False")
    print(
        "NEXT_STEP=review exact canonical trigger/cadence/self-targeting and "
        "equipment or Vampire tradeoffs for the remaining route candidates"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
