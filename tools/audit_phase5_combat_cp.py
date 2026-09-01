from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from services.build_service import BuildService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect saved character combat CP that Phase 5 cannot yet map statically."
    )
    parser.add_argument("--build", required=True, help="Saved build or character name.")
    parser.add_argument("--builds", type=Path, default=get_data_dir() / "builds.json")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    return parser


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

    unresolved_count = 0
    for name, points in sorted(
        (progression.progression.passive_cp_points or {}).items(),
        key=lambda item: item[0].casefold(),
    ):
        if int(points) <= 0:
            continue
        record = repository.get(name)
        if record is None or not record.is_non_slottable:
            continue
        effects, unresolved = repository.resolve(name, int(points))
        if not unresolved:
            continue
        unresolved_count += 1
        print("-" * 72)
        print(f"{record.name}")
        print(f"Allocated:   {points}/{record.max_points}")
        print(f"Jump points: {record.jump_points or '(none)'}")
        print(f"Description: {record.description or '(blank)'}")
        print(f"Resolver:    {'; '.join(unresolved)}")

    print()
    print("=" * 72)
    print(f"UNMAPPED PURCHASED NON-SLOTTABLE CP: {unresolved_count}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
