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
from models.build_model import PlayerBuild

DEFAULT_BUILDS = get_data_dir() / "builds.json"
_CP_NAMES = ("Swift Renewal", "Soothing Tide", "Rejuvenator")


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


def _cp_points(saved: PlayerBuild) -> dict[str, int]:
    result: dict[str, int] = {}
    for entry in saved.ChampionPoints:
        name = str(entry.Name or "").strip()
        if name not in _CP_NAMES:
            continue
        try:
            result[name] = int(str(entry.Points or "0").strip() or 0)
        except (TypeError, ValueError):
            continue
    return result


def _stage_count(points: int) -> int:
    return sum(1 for threshold in (10, 20, 30, 40, 50) if points >= threshold)


def _skill_rank_id(db: sqlite3.Connection, name: str) -> int | None:
    row = db.execute(
        """
        SELECT sr.id
        FROM ability a
        JOIN skill_rank sr ON sr.ability_id = a.ability_id
        WHERE LOWER(TRIM(a.name)) = LOWER(TRIM(?))
        ORDER BY COALESCE(sr.rank, 0) DESC, sr.id DESC
        LIMIT 1
        """,
        (name,),
    ).fetchone()
    return int(row[0]) if row is not None else None


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

    cp = _cp_points(saved)
    swift = _stage_count(cp.get("Swift Renewal", 0)) * 2
    soothing = _stage_count(cp.get("Soothing Tide", 0)) * 2
    rejuvenator = _stage_count(cp.get("Rejuvenator", 0)) * 41

    print("========================================")
    print(" PHASE 5 HEALING CP COMPONENT AUDIT")
    print("========================================")
    print(f"Database:     {database_path}")
    print(f"Saved builds: {builds_path}")
    print(f"Character:    {saved.Name or '(unnamed)'}")
    print(f"Build:        {saved.BuildName or '(unnamed)'}")
    print()
    print("Saved CP modifiers at current allocation:")
    print(f"  Swift Renewal: {cp.get('Swift Renewal', 0)} points -> +{swift}% HoT Healing Done")
    print(f"  Soothing Tide: {cp.get('Soothing Tide', 0)} points -> +{soothing}% AoE Healing Done")
    print(f"  Rejuvenator:   {cp.get('Rejuvenator', 0)} points -> +{rejuvenator} healing-ability Weapon/Spell Damage")

    skill_names = [
        str(name).strip()
        for name in tuple(saved.FrontBarSkills) + tuple(saved.BackBarSkills)
        if str(name or "").strip()
    ]

    print()
    print("Saved skill healing components:")
    with sqlite3.connect(database_path) as db:
        tables = {
            str(row[0])
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "skill_component_classification" not in tables:
            print("  skill_component_classification table unavailable")
            return 4

        found = 0
        for name in skill_names:
            skill_rank_id = _skill_rank_id(db, name)
            if skill_rank_id is None:
                continue
            rows = db.execute(
                """
                SELECT coefficient_number, effect_kind, is_dot, is_aoe, can_crit,
                       source, confidence
                FROM skill_component_classification
                WHERE skill_rank_id = ?
                ORDER BY coefficient_number
                """,
                (skill_rank_id,),
            ).fetchall()
            heal_rows = [row for row in rows if str(row[1] or "").strip().casefold() == "heal"]
            if not heal_rows:
                continue
            found += 1
            print()
            print(f"  {name} | skill_rank_id={skill_rank_id}")
            for coefficient_number, _kind, is_dot, is_aoe, can_crit, source, confidence in heal_rows:
                hot = None if is_dot is None else bool(is_dot)
                aoe = None if is_aoe is None else bool(is_aoe)
                applies: list[str] = ["Rejuvenator"] if rejuvenator else []
                if hot is True and swift:
                    applies.append("Swift Renewal")
                if aoe is True and soothing:
                    applies.append("Soothing Tide")
                if hot is None:
                    applies.append("Swift Renewal unresolved: periodicity unknown")
                if aoe is None:
                    applies.append("Soothing Tide unresolved: target shape unknown")
                print(
                    "    - coef #{coef} | periodicity={periodicity} | target_shape={shape} | "
                    "can_crit={crit} | applies={applies} | source={source} | confidence={confidence}".format(
                        coef=coefficient_number,
                        periodicity="hot" if hot is True else "direct" if hot is False else "unknown",
                        shape="aoe" if aoe is True else "single_target" if aoe is False else "unknown",
                        crit="yes" if can_crit else "no" if can_crit == 0 else "unknown",
                        applies=", ".join(applies) or "none",
                        source=source or "(none)",
                        confidence=confidence if confidence is not None else "(none)",
                    )
                )

    if not found:
        print("  (no classified healing components found on saved bars)")

    print()
    print("Interpretation boundary:")
    print("  - Rejuvenator applies only to healing ability calculations, not the standing Weapon/Spell Damage sheet stat.")
    print("  - Swift Renewal requires a classified healing-over-time component.")
    print("  - Soothing Tide requires a classified AoE healing component.")
    print("  - This audit does not alter calculations or database rows.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit saved healing CP applicability against persisted Phase 3 skill-component semantics."
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
