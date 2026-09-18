from __future__ import annotations

"""Additively normalize source-backed entity-only ability-altering weapon sets.

The source corpus is produced by the ESO-Hub entity-only gear crawler. This
importer never deletes or replaces existing rows. It defaults to dry-run;
--write is required to insert anything.
"""

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import get_data_dir


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "research" / "raw" / "eso_hub_entity_only_gear_sets.json"
DEFAULT_DATABASE = get_data_dir() / "eso.db"

TWO_HAND_EQUIP_TYPE = 6
ONE_HAND_EQUIP_TYPE = 5
OFF_HAND_EQUIP_TYPE = 7

WEAPON_ROWS_BY_SKILL_LINE: dict[str, tuple[tuple[int, int], ...]] = {
    "bow": ((TWO_HAND_EQUIP_TYPE, 8),),
    "restoration staff": ((TWO_HAND_EQUIP_TYPE, 9),),
    "destruction staff": (
        (TWO_HAND_EQUIP_TYPE, 12),
        (TWO_HAND_EQUIP_TYPE, 13),
        (TWO_HAND_EQUIP_TYPE, 15),
    ),
    "two handed": (
        (TWO_HAND_EQUIP_TYPE, 4),
        (TWO_HAND_EQUIP_TYPE, 5),
        (TWO_HAND_EQUIP_TYPE, 6),
    ),
    "dual wield": (
        (ONE_HAND_EQUIP_TYPE, 1),
        (ONE_HAND_EQUIP_TYPE, 2),
        (ONE_HAND_EQUIP_TYPE, 3),
        (ONE_HAND_EQUIP_TYPE, 11),
    ),
    "one hand and shield": (
        (ONE_HAND_EQUIP_TYPE, 1),
        (ONE_HAND_EQUIP_TYPE, 2),
        (ONE_HAND_EQUIP_TYPE, 3),
        (ONE_HAND_EQUIP_TYPE, 11),
        (OFF_HAND_EQUIP_TYPE, 14),
    ),
}


def _norm(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


@dataclass(frozen=True)
class WeaponSetPlan:
    name: str
    category: str
    location: str
    piece_count: int
    bonus: str
    skill_line: str
    modified_skills: tuple[str, ...]
    weapon_rows: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class NormalizationPlan:
    rows: tuple[WeaponSetPlan, ...]
    unresolved: tuple[str, ...]

    @property
    def proven(self) -> bool:
        return bool(self.rows) and not self.unresolved


def _piece_count(description: str) -> int | None:
    match = re.match(r"^\((\d+)\s+items?\)", str(description or "").strip(), re.I)
    return None if match is None else int(match.group(1))


def _skill_lines_for_names(
    db: sqlite3.Connection,
    skill_names: tuple[str, ...],
) -> tuple[str, ...]:
    found: set[str] = set()
    for name in skill_names:
        rows = db.execute(
            """
            SELECT DISTINCT skill_line
            FROM skill
            WHERE name IS NOT NULL
              AND LOWER(TRIM(name)) = LOWER(TRIM(?))
              AND skill_line IS NOT NULL
              AND TRIM(skill_line) <> ''
            """,
            (name,),
        ).fetchall()
        found.update(str(row[0]).strip() for row in rows if str(row[0] or "").strip())
    return tuple(sorted(found, key=str.casefold))


def build_plan(database: Path, source_json: Path) -> NormalizationPlan:
    payload = json.loads(source_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return NormalizationPlan((), ("source JSON is not a list",))

    unresolved: list[str] = []
    plans: list[WeaponSetPlan] = []

    with sqlite3.connect(database) as db:
        tables = {
            str(row[0])
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        required = {"entity", "gear_set", "gear_set_bonus", "gear_set_piece", "skill"}
        missing = required - tables
        if missing:
            return NormalizationPlan(
                (),
                (f"database missing required table(s): {', '.join(sorted(missing))}",),
            )

        for row in payload:
            name = str(row.get("name") or "").strip()
            category = str(row.get("type") or "").strip()
            location = str(row.get("location") or "").strip()
            bonuses = tuple(str(value).strip() for value in row.get("bonuses") or () if str(value).strip())
            skills = tuple(str(value).strip() for value in row.get("modified_skills") or () if str(value).strip())
            source_unresolved = tuple(str(value) for value in row.get("unresolved") or ())

            if source_unresolved:
                unresolved.append(f"{name}: source evidence unresolved: {source_unresolved}")
                continue
            if not name:
                unresolved.append("source row has blank set name")
                continue
            if category.casefold() not in {"arena", "trial"}:
                unresolved.append(f"{name}: unsupported source type {category!r}")
                continue
            if len(bonuses) != 1:
                unresolved.append(f"{name}: expected exactly one focal bonus, found {len(bonuses)}")
                continue
            count = _piece_count(bonuses[0])
            if count != 2:
                unresolved.append(f"{name}: expected 2-item ability-altering bonus, found {count!r}")
                continue
            if not skills:
                unresolved.append(f"{name}: no modified skills")
                continue

            entity = db.execute(
                """
                SELECT id
                FROM entity
                WHERE entity_type = 'gear_set'
                  AND LOWER(TRIM(name)) = LOWER(TRIM(?))
                """,
                (name,),
            ).fetchall()
            if len(entity) != 1:
                unresolved.append(
                    f"{name}: expected one canonical gear_set entity, found {len(entity)}"
                )
                continue

            existing = db.execute(
                "SELECT id FROM gear_set WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))",
                (name,),
            ).fetchall()
            if existing:
                unresolved.append(
                    f"{name}: gear_set already exists; additive normalizer will not modify it"
                )
                continue

            lines = _skill_lines_for_names(db, skills)
            weapon_lines = tuple(
                line
                for line in lines
                if _norm(line) in WEAPON_ROWS_BY_SKILL_LINE
            )
            if len(weapon_lines) != 1:
                unresolved.append(
                    f"{name}: modified skills resolve to {len(lines)} canonical skill lines "
                    f"{lines}, with {len(weapon_lines)} supported weapon lines {weapon_lines}"
                )
                continue
            skill_line = weapon_lines[0]
            weapon_rows = WEAPON_ROWS_BY_SKILL_LINE[_norm(skill_line)]

            plans.append(
                WeaponSetPlan(
                    name=name,
                    category=category,
                    location=location,
                    piece_count=count,
                    bonus=bonuses[0],
                    skill_line=skill_line,
                    modified_skills=skills,
                    weapon_rows=weapon_rows,
                )
            )

    return NormalizationPlan(
        rows=tuple(sorted(plans, key=lambda item: item.name.casefold())),
        unresolved=tuple(dict.fromkeys(unresolved)),
    )


def apply_plan(database: Path, plan: NormalizationPlan) -> tuple[int, int, int]:
    if not plan.proven:
        raise RuntimeError("normalization plan is not proven; refusing to write")

    with sqlite3.connect(database) as db:
        db.execute("PRAGMA foreign_keys = ON")
        next_set_id = int(
            db.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM gear_set").fetchone()[0]
        )
        set_count = 0
        bonus_count = 0
        piece_count = 0

        for offset, row in enumerate(plan.rows):
            set_id = next_set_id + offset
            existing = db.execute(
                "SELECT id FROM gear_set WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))",
                (row.name,),
            ).fetchone()
            if existing is not None:
                raise RuntimeError(
                    f"{row.name}: gear_set appeared after planning; refusing to overwrite"
                )

            db.execute(
                """
                INSERT INTO gear_set(id, name, category, max_equip_count)
                VALUES (?, ?, ?, 2)
                """,
                (set_id, row.name, row.category),
            )
            set_count += 1

            db.execute(
                """
                INSERT INTO gear_set_bonus(set_id, piece_count, description)
                VALUES (?, ?, ?)
                """,
                (set_id, row.piece_count, row.bonus),
            )
            bonus_count += 1

            for equip_type, weapon_type in row.weapon_rows:
                db.execute(
                    """
                    INSERT INTO gear_set_piece(
                        set_id, equip_type, armor_type, weapon_type
                    )
                    VALUES (?, ?, 0, ?)
                    """,
                    (set_id, equip_type, weapon_type),
                )
                piece_count += 1

        db.commit()
        return set_count, bonus_count, piece_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Additively normalize reviewed entity-only ability-altering weapon sets"
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply additive inserts. Without this flag the command is dry-run only.",
    )
    args = parser.parse_args()

    plan = build_plan(args.database, args.input)

    print("ENTITY-ONLY ABILITY-ALTERING WEAPON SET NORMALIZER")
    print(f"database={args.database}")
    print(f"input={args.input}")
    print(f"candidate_count={len(plan.rows)}")
    print(f"unresolved_count={len(plan.unresolved)}")
    print(f"normalization_plan_proven={plan.proven}")

    line_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for row in plan.rows:
        line_counts[row.skill_line] = line_counts.get(row.skill_line, 0) + 1
        category_counts[row.category] = category_counts.get(row.category, 0) + 1
    print(f"category_counts={dict(sorted(category_counts.items()))}")
    print(f"skill_line_counts={dict(sorted(line_counts.items()))}")

    for issue in plan.unresolved:
        print(f"UNRESOLVED {issue}")

    if not args.write:
        print("WRITE_MODE=False")
        print(
            "NEXT_STEP=review this dry-run. If candidate_count=60 and "
            "unresolved_count=0, rerun with --write to perform additive inserts."
        )
        return 0

    if not plan.proven:
        print("RESULT=REFUSED: unresolved normalization evidence remains")
        return 2

    sets, bonuses, pieces = apply_plan(args.database, plan)
    print("WRITE_MODE=True")
    print(f"inserted_sets={sets}")
    print(f"inserted_bonuses={bonuses}")
    print(f"inserted_piece_rows={pieces}")
    print("RESULT=PASS: additive normalization committed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
