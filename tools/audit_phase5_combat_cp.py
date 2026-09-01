from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from services.build_service import BuildService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter
from services.saved_build_capability_service import SavedBuildCapabilityService


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect purchased non-slottable CP that Phase 5 does not map into standing core stats."
    )
    parser.add_argument("--build", required=True, help="Saved build or character name.")
    parser.add_argument("--builds", type=Path, default=get_data_dir() / "builds.json")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    return parser


def _discipline(database: Path, name: str) -> int | None:
    try:
        with sqlite3.connect(database) as db:
            row = db.execute(
                "SELECT discipline_id FROM champion_point WHERE lower(trim(name)) = lower(trim(?)) LIMIT 1",
                (name,),
            ).fetchone()
        return int(row[0]) if row and row[0] is not None else None
    except sqlite3.Error:
        return None


def main() -> int:
    args = _parser().parse_args()
    build_service = BuildService(args.builds)
    roster = build_service.load()
    requested = _clean(args.build).casefold()
    build = next(
        (
            candidate
            for candidate in roster.Members
            if _clean(candidate.BuildName).casefold() == requested
            or _clean(candidate.Name).casefold() == requested
        ),
        None,
    )
    if build is None:
        print(f"No saved build matched: {args.build}")
        return 2

    progression = MinmaxCharacterProgressionAdapter(
        build_service.canonical.catalog_service
    ).resolve(build)
    repository = ChampionPointStaticRepository(args.database)

    print("=" * 72)
    print(" PHASE 5 COMBAT CHAMPION POINT DIAGNOSTIC")
    print("=" * 72)
    print(f"Character: {build.Name}")
    print(f"Build:     {build.BuildName}")
    print(f"Database:  {args.database}")
    print()

    genuine_count = 0
    deferred_count = 0
    noncombat_count = 0
    for name, points in sorted(
        (progression.progression.passive_cp_points or {}).items(),
        key=lambda item: item[0].casefold(),
    ):
        if int(points) <= 0:
            continue
        record = repository.get(name)
        if record is None or not record.is_non_slottable:
            continue
        _effects, unresolved = repository.resolve(name, int(points))
        if not unresolved:
            continue

        discipline = _discipline(args.database, record.name)
        reason = SavedBuildCapabilityService.CP_DEFERRED_BOUNDARY_REASONS.get(
            record.name.casefold()
        )
        if discipline == 3:
            classification = "non-combat boundary"
            noncombat_count += 1
        elif reason:
            classification = f"deferred boundary: {reason}"
            deferred_count += 1
        else:
            classification = "genuine unmapped"
            genuine_count += 1

        print("-" * 72)
        print(f"{record.name}")
        print(f"Allocated:      {points}/{record.max_points}")
        print(f"Jump points:    {record.jump_points or '(none)'}")
        print(f"Classification: {classification}")
        print(f"Description:    {record.description or '(blank)'}")
        print(f"Resolver:       {'; '.join(unresolved)}")

    print()
    print("=" * 72)
    print(f"GENUINE UNMAPPED:       {genuine_count}")
    print(f"DEFERRED COMBAT:        {deferred_count}")
    print(f"NON-COMBAT BOUNDARIES:  {noncombat_count}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
