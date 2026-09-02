from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_text_evidence import extract_component_text_evidence
from tools.audit_phase6_component_gaps import load_phase6_gap_matrix

DEFAULT_DATABASE = ROOT / "data" / "eso.db"
_COLOR_TAG_RE = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")


@dataclass(frozen=True)
class PestilentParserRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    name: str
    source_text: str
    fragment: str
    effect_kind: str | None
    damage_type: str | None


def _normalize(value: object) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    text = _COLOR_TAG_RE.sub("", text)
    return " ".join(text.split())


def load_pestilent_parser_rows(database_path: str | Path) -> tuple[PestilentParserRow, ...]:
    path = Path(database_path)
    gaps = [
        row
        for row in load_phase6_gap_matrix(path)
        if row.disposition == "parser_coverage" and row.name.casefold() == "pestilent colossus"
    ]
    if not gaps:
        return ()

    rank_ids = sorted({row.skill_rank_id for row in gaps})
    placeholders = ",".join("?" for _ in rank_ids)
    with sqlite3.connect(path) as db:
        source_by_rank = {
            int(row[0]): _normalize(row[1])
            for row in db.execute(
                f"""
                SELECT sr.id, a.coef_description
                FROM skill_rank sr
                JOIN ability a ON a.ability_id = sr.ability_id
                WHERE sr.id IN ({placeholders})
                """,
                tuple(rank_ids),
            ).fetchall()
        }

    results: list[PestilentParserRow] = []
    for gap in gaps:
        source_text = source_by_rank.get(gap.skill_rank_id, "")
        evidence = extract_component_text_evidence(source_text, gap.coefficient_number)
        results.append(
            PestilentParserRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                name=gap.name,
                source_text=source_text,
                fragment=evidence.fragment,
                effect_kind=evidence.effect_kind,
                damage_type=evidence.damage_type,
            )
        )
    return tuple(results)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit remaining Pestilent Colossus Phase 6 parser rows.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    args = parser.parse_args()

    rows = load_pestilent_parser_rows(args.database)
    print("\n========================================")
    print(" PHASE 6 PESTILENT COLOSSUS PARSER")
    print("========================================")
    print(f"Database: {args.database}")
    print(f"Rows:     {len(rows)}")
    for row in rows:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.name}"
        )
        print(f"effect_kind={row.effect_kind or '-'} damage_type={row.damage_type or '-'}")
        print(f"fragment={row.fragment or '-'}")
        print(f"source={row.source_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
