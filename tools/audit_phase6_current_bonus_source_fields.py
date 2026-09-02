from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_DATABASE = ROOT / "data" / "eso.db"
TARGET_RANKS = (
    5617, 5618, 5621, 5622, 5623, 5624, 5636, 5637, 5644, 5645, 5646,
    5729, 5730, 6199, 6200, 6568, 6569, 7072, 7073, 7621, 7622, 7627, 7628,
)


@dataclass(frozen=True)
class CurrentBonusSourceRow:
    skill_rank_id: int
    ability_id: int
    name: str
    populated_fields: tuple[str, ...]
    relevant_fields: tuple[str, ...]
    values: tuple[tuple[str, str], ...]


def _table_columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in db.execute(f"PRAGMA table_info({table})").fetchall()}


def _normalize(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _json_strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        results: list[str] = []
        for item in value.values():
            results.extend(_json_strings(item))
        return tuple(results)
    if isinstance(value, list):
        results: list[str] = []
        for item in value:
            results.extend(_json_strings(item))
        return tuple(results)
    return ()


def _looks_relevant(text: str) -> bool:
    lower = text.casefold()
    return (
        "current bonus" in lower
        or "current amount" in lower
        or "$1" in lower
        or "$2" in lower
        or "$3" in lower
        or "per piece" in lower
        or "for each" in lower
        or "slotted" in lower
        or "equipped" in lower
        or "wearing" in lower
        or "armor" in lower
        or "resistance" in lower
        or "critical" in lower
        or "recovery" in lower
        or "health" in lower
        or "magicka" in lower
        or "stamina" in lower
        or "damage" in lower
    )


def load_current_bonus_source_rows(
    database_path: str | Path,
    *,
    skill_rank_ids: tuple[int, ...] = TARGET_RANKS,
) -> tuple[CurrentBonusSourceRow, ...]:
    path = Path(database_path)
    if not path.exists():
        raise FileNotFoundError(path)

    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        ability_columns = _table_columns(db, "ability")
        rank_columns = _table_columns(db, "skill_rank")

        candidate_fields: list[tuple[str, str]] = []
        for column in (
            "name",
            "description",
            "coef_description",
            "raw_description",
            "raw_tooltip",
            "raw_coef",
            "coef_types",
            "raw_json",
        ):
            if column in ability_columns:
                candidate_fields.append((f"ability.{column}", f"a.{column}"))
        for column in (
            "raw_description",
            "raw_tooltip",
            "raw_coef",
            "coef_types",
            "raw_name",
        ):
            if column in rank_columns:
                candidate_fields.append((f"skill_rank.{column}", f"sr.{column}"))

        selects = [f"{expr} AS '{label}'" for label, expr in candidate_fields]
        placeholders = ",".join("?" for _ in skill_rank_ids)
        rows = db.execute(
            f"""
            SELECT sr.id AS skill_rank_id, sr.ability_id,
                   COALESCE(NULLIF(a.name, ''), '') AS canonical_name,
                   {', '.join(selects)}
            FROM skill_rank sr
            JOIN ability a ON a.ability_id = sr.ability_id
            WHERE sr.id IN ({placeholders})
            ORDER BY sr.id
            """,
            tuple(int(value) for value in skill_rank_ids),
        ).fetchall()

    results: list[CurrentBonusSourceRow] = []
    for row in rows:
        populated: list[str] = []
        relevant: list[str] = []
        values: list[tuple[str, str]] = []
        for label, _expr in candidate_fields:
            raw_value = row[label]
            text = _normalize(raw_value)
            if not text:
                continue
            populated.append(label)
            display = text
            if label == "ability.raw_json":
                try:
                    parsed = json.loads(str(raw_value))
                except (TypeError, ValueError, json.JSONDecodeError):
                    parsed = None
                strings = tuple(_normalize(item) for item in _json_strings(parsed) if _normalize(item))
                matches = tuple(item for item in strings if _looks_relevant(item))
                if matches:
                    relevant.append(label)
                    display = " | ".join(matches)
                else:
                    display = f"<json strings={len(strings)}>"
            elif _looks_relevant(text):
                relevant.append(label)
            values.append((label, display))

        results.append(
            CurrentBonusSourceRow(
                skill_rank_id=int(row["skill_rank_id"]),
                ability_id=int(row["ability_id"]),
                name=str(row["canonical_name"] or ""),
                populated_fields=tuple(populated),
                relevant_fields=tuple(relevant),
                values=tuple(values),
            )
        )
    return tuple(results)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit canonical source fields behind Phase 6 Current bonus parser gaps."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    args = parser.parse_args()

    rows = load_current_bonus_source_rows(args.database)
    print("\n========================================")
    print(" PHASE 6 CURRENT BONUS SOURCE FIELDS")
    print("========================================")
    print(f"Database: {args.database}")
    print(f"Ranks:    {len(rows)}")
    print("NOTE: Undaunted Command contributes three coefficient rows per rank; this audit prints each rank once.")

    for row in rows:
        print("\n----------------------------------------")
        print(f"rank={row.skill_rank_id} ability={row.ability_id} name={row.name}")
        print(f"populated={','.join(row.populated_fields) or '-'}")
        print(f"relevant_fields={','.join(row.relevant_fields) or '-'}")
        for label, value in row.values:
            if label == "ability.raw_json" and value.startswith("<json strings="):
                print(f"{label}: {value}")
                continue
            print(f"{label}: {value[:1400]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
