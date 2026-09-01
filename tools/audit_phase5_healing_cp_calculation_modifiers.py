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
from minmax.character_build.champion_points import ChampionPointAllocation
from minmax.healing_champion_point_component_resolver import (
    HealingChampionPointComponentResolver,
)
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from models.build_model import PlayerBuild

DEFAULT_BUILDS = get_data_dir() / "builds.json"
_HEALING_CP_NAMES = {"Rejuvenator", "Soothing Tide", "Swift Renewal"}


def _load_saved_build(path: Path, requested: str) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    members = payload.get("Members") if isinstance(payload, dict) else None
    if not isinstance(members, list):
        raise ValueError(f"Unsupported saved-build format in {path}; expected Members")
    key = str(requested or "").strip().casefold()
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


def _allocations(saved: PlayerBuild) -> tuple[ChampionPointAllocation, ...]:
    result: list[ChampionPointAllocation] = []
    for entry in saved.ChampionPoints:
        name = str(entry.Name or "").strip()
        if name not in _HEALING_CP_NAMES:
            continue
        try:
            points = int(str(entry.Points or "0").strip() or 0)
        except (TypeError, ValueError):
            continue
        result.append(
            ChampionPointAllocation(
                node_id=name.casefold().replace(" ", "_"),
                points=points,
            )
        )
    return tuple(result)


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

    allocations = _allocations(saved)
    coefficient_repository = SkillCoefficientRepository(database_path)
    resolver = HealingChampionPointComponentResolver(database_path)

    print("========================================")
    print(" PHASE 5 HEALING CP CALCULATION AUDIT")
    print("========================================")
    print(f"Database:     {database_path}")
    print(f"Saved builds: {builds_path}")
    print(f"Character:    {saved.Name or '(unnamed)'}")
    print(f"Build:        {saved.BuildName or '(unnamed)'}")
    print()
    print("Canonical healing CP allocations:")
    if allocations:
        for allocation in allocations:
            print(f"  - {allocation.node_id}: {allocation.points}")
    else:
        print("  (none)")

    skill_names = [
        str(name).strip()
        for name in tuple(saved.FrontBarSkills) + tuple(saved.BackBarSkills)
        if str(name or "").strip()
    ]

    printed = 0
    print()
    print("Resolved per-component actual-effect modifiers:")
    with sqlite3.connect(database_path) as db:
        for skill_name in skill_names:
            resolution = coefficient_repository.resolve_name(skill_name)
            if resolution.rank is None:
                continue
            rank = resolution.rank
            rows = db.execute(
                """
                SELECT coefficient_number
                FROM skill_component_classification
                WHERE skill_rank_id = ?
                  AND LOWER(TRIM(effect_kind)) = 'heal'
                ORDER BY coefficient_number
                """,
                (rank.skill_rank_id,),
            ).fetchall()
            coefficient_numbers = tuple(int(row[0]) for row in rows)
            if not coefficient_numbers:
                continue

            modifiers, unresolved = resolver.resolve_for_skill(
                allocations=allocations,
                skill_rank_id=rank.skill_rank_id,
                coefficient_numbers=coefficient_numbers,
                is_slotted=True,
            )
            printed += 1
            print()
            print(
                f"  {rank.name} | skill_rank_id={rank.skill_rank_id} | "
                f"heal_coefficients={coefficient_numbers}"
            )
            by_coefficient = {modifier.coefficient_number: modifier for modifier in modifiers}
            for coefficient_number in coefficient_numbers:
                modifier = by_coefficient.get(coefficient_number)
                if modifier is None:
                    print(f"    - coef #{coefficient_number}: no actual-effect CP modifier")
                    continue
                sources = ", ".join(modifier.sources) or "none"
                print(
                    f"    - coef #{coefficient_number}: power_bonus={modifier.power_bonus:g} | "
                    f"additive_healing_done={modifier.additive_percent:g}% | sources={sources}"
                )
            for message in unresolved:
                print(f"    ! unresolved: {message}")

    if not printed:
        print("  (no classified healing components found on saved bars)")

    print()
    print("Interpretation boundary:")
    print("  - These modifiers are actual-effect-only inputs, not standing sheet stats.")
    print("  - Rejuvenator changes the power input of qualifying healing coefficients.")
    print("  - Swift Renewal / Soothing Tide contribute to one additive healing-done bucket.")
    print("  - Explicit ESO-Hub rank/morph links remain the hard applicability gate.")
    print("  - Source metadata drift is reported unresolved rather than guessed.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit production healing CP component modifiers for one saved build."
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
