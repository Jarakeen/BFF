from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from models.build_model import PlayerBuild

DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _load_saved_build(path: Path, requested: str) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    members = payload.get("Members") if isinstance(payload, dict) else None
    if not isinstance(members, list):
        raise ValueError(f"Unsupported saved-build format in {path}; expected Members")

    key = requested.strip().casefold()
    matches = [
        PlayerBuild.from_dict(entry)
        for entry in members
        if isinstance(entry, dict)
        and str(entry.get("BuildName", "")).strip().casefold() == key
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one saved build named {requested!r}; found {len(matches)}"
        )
    return matches[0]


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def audit(*, database_path: Path, builds_path: Path, build_name: str) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1
    if not builds_path.exists():
        print(f"Saved builds not found: {builds_path}")
        return 2

    try:
        saved = _load_saved_build(builds_path, build_name)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(exc)
        return 3

    repository = ChampionPointStaticRepository(database_path)

    print("========================================")
    print(" PHASE 5 DYNAMIC CP EVIDENCE AUDIT")
    print("========================================")
    print(f"Database:     {database_path}")
    print(f"Saved builds: {builds_path}")
    print(f"Character:    {saved.Name or '(unnamed)'}")
    print(f"Build:        {saved.BuildName or '(unnamed)'}")
    print()

    dynamic_entries: list[tuple[int, object, object]] = []
    for index, entry in enumerate(saved.ChampionPoints, start=1):
        name = str(entry.Name or "").strip()
        if not name:
            continue
        record = repository.get(name)
        if record is None:
            continue
        try:
            points = int(str(entry.Points or "0").strip() or 0)
        except ValueError:
            continue
        effects, unresolved = repository.resolve(name, points)
        if not effects and unresolved:
            dynamic_entries.append((index, entry, record))

    print(f"Saved CP entries:              {len(saved.ChampionPoints)}")
    print(f"Dynamic/unmapped CP entries:  {len(dynamic_entries)}")
    print()

    if not dynamic_entries:
        print("No dynamic/unmapped saved Champion Point entries found.")
        return 0

    with sqlite3.connect(database_path) as db:
        columns = {
            str(row[1])
            for row in db.execute("PRAGMA table_info(champion_point)").fetchall()
        }
        description_expr = (
            "COALESCE(min_description, max_description, description, '')"
            if {"min_description", "max_description", "description"}.issubset(columns)
            else "COALESCE(description, '')"
            if "description" in columns
            else "''"
        )

        for ordinal, (saved_index, entry, record) in enumerate(dynamic_entries, start=1):
            name = str(entry.Name or "").strip()
            points = str(entry.Points or "").strip()
            row = db.execute(
                f"SELECT {description_expr} FROM champion_point WHERE name = ?",
                (name,),
            ).fetchone()
            description = _clean(row[0]) if row else ""

            kind = "non-slottable" if record.is_non_slottable else "slottable"
            print("----------------------------------------")
            print(f"{ordinal}. {name}")
            print("----------------------------------------")
            print(
                f"saved_entry={saved_index} | saved_points={points or '(empty)'} | "
                f"{kind} | skill_type={record.skill_type} | max_points={record.max_points}"
            )
            print(f"jump_points={record.jump_points or '(none)'}")
            print(f"description={description or '(empty)'}")
            print()

    print("Interpretation boundary:")
    print("  - This tool prints imported CP source text only.")
    print("  - It does not create EffectVariants or infer support mechanics.")
    print("  - Static sheet effects remain owned by StaticBuildInputResolver.")
    print()
    print("Audit only: no database or saved-build data were changed.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print source descriptions for saved CP stars that the static CP repository leaves dynamic/unmapped."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(
        audit(
            database_path=args.database,
            builds_path=args.builds,
            build_name=args.build,
        )
    )
