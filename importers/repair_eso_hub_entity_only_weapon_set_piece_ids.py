from __future__ import annotations

"""Add canonical ESO equip/weapon identity rows to normalized arena weapon sets.

An earlier additive normalizer used stale local numeric identities for two-handed
weapon equip slots and shields. This repair is additive-only: it inserts the
canonical rows that are missing and never deletes the legacy rows, preserving the
user's no-subtractive-database rule.
"""

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import get_data_dir
from importers.import_eso_hub_entity_only_weapon_sets import (
    DEFAULT_INPUT,
    WEAPON_ROWS_BY_SKILL_LINE,
    _norm,
    _skill_lines_for_names,
)

DEFAULT_DATABASE = get_data_dir() / "eso.db"


@dataclass(frozen=True)
class RepairRow:
    set_id: int
    set_name: str
    equip_type: int
    weapon_type: int


@dataclass(frozen=True)
class RepairPlan:
    rows: tuple[RepairRow, ...]
    unresolved: tuple[str, ...]

    @property
    def proven(self) -> bool:
        return not self.unresolved


def build_plan(database: Path, source_json: Path) -> RepairPlan:
    payload = json.loads(source_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return RepairPlan((), ("source JSON is not a list",))

    rows: list[RepairRow] = []
    unresolved: list[str] = []

    with sqlite3.connect(database) as db:
        for source in payload:
            name = str(source.get("name") or "").strip()
            skills = tuple(
                str(value).strip()
                for value in source.get("modified_skills") or ()
                if str(value).strip()
            )
            if not name or not skills:
                unresolved.append(f"{name or '<blank>'}: missing source identity or modified skills")
                continue

            set_rows = db.execute(
                """
                SELECT id
                FROM gear_set
                WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
                """,
                (name,),
            ).fetchall()
            if len(set_rows) != 1:
                unresolved.append(f"{name}: expected one normalized gear_set row, found {len(set_rows)}")
                continue
            set_id = int(set_rows[0][0])

            lines = _skill_lines_for_names(db, skills)
            weapon_lines = tuple(
                line for line in lines if _norm(line) in WEAPON_ROWS_BY_SKILL_LINE
            )
            if len(weapon_lines) != 1:
                unresolved.append(
                    f"{name}: expected one canonical weapon skill line, found {weapon_lines}"
                )
                continue

            for equip_type, weapon_type in WEAPON_ROWS_BY_SKILL_LINE[_norm(weapon_lines[0])]:
                exists = db.execute(
                    """
                    SELECT 1
                    FROM gear_set_piece
                    WHERE set_id = ?
                      AND COALESCE(equip_type, 0) = ?
                      AND COALESCE(armor_type, 0) = 0
                      AND COALESCE(weapon_type, 0) = ?
                    LIMIT 1
                    """,
                    (set_id, int(equip_type), int(weapon_type)),
                ).fetchone()
                if exists is None:
                    rows.append(
                        RepairRow(
                            set_id=set_id,
                            set_name=name,
                            equip_type=int(equip_type),
                            weapon_type=int(weapon_type),
                        )
                    )

    return RepairPlan(
        rows=tuple(sorted(rows, key=lambda row: (row.set_name.casefold(), row.equip_type, row.weapon_type))),
        unresolved=tuple(dict.fromkeys(unresolved)),
    )


def apply_plan(database: Path, plan: RepairPlan) -> int:
    if not plan.proven:
        raise RuntimeError("repair plan is unresolved; refusing to write")

    inserted = 0
    with sqlite3.connect(database) as db:
        for row in plan.rows:
            before = db.total_changes
            db.execute(
                """
                INSERT OR IGNORE INTO gear_set_piece(
                    set_id, equip_type, armor_type, weapon_type
                )
                VALUES (?, ?, 0, ?)
                """,
                (row.set_id, row.equip_type, row.weapon_type),
            )
            if db.total_changes > before:
                inserted += 1
        db.commit()
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add canonical equip/weapon rows to normalized ability-altering weapon sets"
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    plan = build_plan(args.database, args.input)
    print("ENTITY-ONLY WEAPON SET CANONICAL ID REPAIR")
    print(f"database={args.database}")
    print(f"input={args.input}")
    print(f"missing_canonical_piece_row_count={len(plan.rows)}")
    print(f"unresolved_count={len(plan.unresolved)}")
    print(f"repair_plan_proven={plan.proven}")

    for issue in plan.unresolved:
        print(f"UNRESOLVED {issue}")

    if not args.write:
        print("WRITE_MODE=False")
        print("NEXT_STEP=review dry-run; --write only inserts missing canonical rows and deletes nothing")
        return 0

    if not plan.proven:
        print("RESULT=REFUSED: unresolved repair evidence remains")
        return 2

    inserted = apply_plan(args.database, plan)
    print("WRITE_MODE=True")
    print(f"inserted_piece_rows={inserted}")
    print("RESULT=PASS: additive canonical-id repair committed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
