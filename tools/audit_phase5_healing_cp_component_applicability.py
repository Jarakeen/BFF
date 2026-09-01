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
from minmax.champion_point_skill_repository import ChampionPointSkillRepository
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
        raise ValueError(f"Expected exactly one saved build named {requested!r}; found {len(matches)}")
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


def _skill_identity(db: sqlite3.Connection, name: str) -> tuple[int, int] | None:
    row = db.execute(
        """
        SELECT sr.id, sr.skill_id
        FROM ability a
        JOIN skill_rank sr ON sr.ability_id = a.ability_id
        WHERE LOWER(TRIM(a.name)) = LOWER(TRIM(?))
        ORDER BY COALESCE(sr.rank, 0) DESC, sr.id DESC
        LIMIT 1
        """,
        (name,),
    ).fetchone()
    return (int(row[0]), int(row[1])) if row is not None else None


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

    relationship_repository = ChampionPointSkillRepository(database_path)
    if not relationship_repository.available():
        print()
        print("Explicit CP -> skill applicability:")
        print("  champion_point_skill tables unavailable")
        print("  No CP -> skill relationships will be inferred from component semantics.")
        return 4

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
            return 5

        found = 0
        for name in skill_names:
            identity = _skill_identity(db, name)
            if identity is None:
                continue
            skill_rank_id, skill_id = identity
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

            relationships = relationship_repository.get_for_skill_rank(skill_rank_id)
            explicit = {
                relationship.champion_point_name.casefold(): relationship
                for relationship in relationships
            }
            found += 1
            print()
            print(f"  {name} | skill_id={skill_id} | skill_rank_id={skill_rank_id}")
            relevant_relationships = [
                relationship
                for relationship in relationships
                if relationship.champion_point_name in _CP_NAMES
            ]
            if relevant_relationships:
                print("    ESO-Hub explicit CP links:")
                for relationship in relevant_relationships:
                    scope = "rank-specific" if relationship.skill_rank_id is not None else "legacy base-skill fallback"
                    condition = f" | condition={relationship.condition}" if relationship.condition else ""
                    source = f" | source={relationship.source}" if relationship.source else ""
                    print(f"      - {relationship.champion_point_name} | scope={scope}{condition}{source}")
            else:
                print("    ESO-Hub explicit CP links: none of the audited healing CPs")

            for coefficient_number, _kind, is_dot, is_aoe, can_crit, source, confidence in heal_rows:
                hot = None if is_dot is None else bool(is_dot)
                aoe = None if is_aoe is None else bool(is_aoe)
                applies: list[str] = []

                has_rejuvenator = "rejuvenator" in explicit
                has_swift = "swift renewal" in explicit
                has_soothing = "soothing tide" in explicit

                if rejuvenator and has_rejuvenator:
                    applies.append("Rejuvenator")
                if swift and has_swift and hot is True:
                    applies.append("Swift Renewal")
                if soothing and has_soothing and aoe is True:
                    applies.append("Soothing Tide")
                if swift and has_swift and hot is None:
                    applies.append("Swift Renewal unresolved: periodicity unknown")
                if soothing and has_soothing and aoe is None:
                    applies.append("Soothing Tide unresolved: target shape unknown")

                rejected: list[str] = []
                if rejuvenator and not has_rejuvenator:
                    rejected.append("Rejuvenator: no explicit ESO-Hub link")
                if swift and not has_swift:
                    rejected.append("Swift Renewal: no explicit ESO-Hub link")
                if soothing and not has_soothing:
                    rejected.append("Soothing Tide: no explicit ESO-Hub link")

                print(
                    "    - coef #{coef} | periodicity={periodicity} | target_shape={shape} | "
                    "can_crit={crit} | applies={applies} | rejected={rejected} | "
                    "component_source={source} | confidence={confidence}".format(
                        coef=coefficient_number,
                        periodicity="hot" if hot is True else "direct" if hot is False else "unknown",
                        shape="aoe" if aoe is True else "single_target" if aoe is False else "unknown",
                        crit="yes" if can_crit else "no" if can_crit == 0 else "unknown",
                        applies=", ".join(applies) or "none",
                        rejected=", ".join(rejected) or "none",
                        source=source or "(none)",
                        confidence=confidence if confidence is not None else "(none)",
                    )
                )

    if not found:
        print("  (no classified healing components found on saved bars)")

    print()
    print("Interpretation boundary:")
    print("  - Rank/morph-specific ESO-Hub links win when available.")
    print("  - Legacy base-skill links are fallback evidence only.")
    print("  - skill_component_classification may narrow an explicit relationship to qualifying components.")
    print("  - Component semantics never invent a CP -> skill relationship absent from the ESO-Hub harvest.")
    print("  - Rejuvenator changes healing-ability coefficient power, not standing Weapon/Spell Damage.")
    print("  - This audit does not alter calculations or database rows.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit saved healing CP applicability through explicit ESO-Hub skill links and Phase 3 component semantics."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(audit(database_path=args.database, builds_path=args.builds, build_name=args.build))
