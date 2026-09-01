from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
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
    adaptation = SavedBuildCharacterAdapter(database_path).adapt(saved)

    print("========================================")
    print(" PHASE 5 CHAMPION POINT AUDIT")
    print("========================================")
    print(f"Database:     {database_path}")
    print(f"Saved builds: {builds_path}")
    print(f"Character:    {saved.Name or '(unnamed)'}")
    print(f"Build:        {saved.BuildName or '(unnamed)'}")
    print()

    canonical_count = (
        len(adaptation.build.champion_points)
        if adaptation.build is not None
        else 0
    )
    print(f"Saved CP entries:     {len(saved.ChampionPoints)}")
    print(f"Canonical CP entries: {canonical_count}")
    print()

    if not saved.ChampionPoints:
        print("No saved Champion Point entries.")
        return 0

    for index, entry in enumerate(saved.ChampionPoints, start=1):
        name = str(entry.Name or "").strip()
        raw_points = str(entry.Points or "").strip()
        print(f"{index}. {name or '(unnamed)'} | saved_points={raw_points or '(empty)'}")

        if not name:
            print("   record: unresolved (missing name)")
            continue

        record = repository.get(name)
        if record is None:
            print("   record: not found in champion_point table")
            continue

        kind = "non-slottable" if record.is_non_slottable else "slottable"
        print(
            f"   record: {kind} | skill_type={record.skill_type} | "
            f"max_points={record.max_points} | jump_points={record.jump_points or '(none)'}"
        )

        try:
            points = int(raw_points or 0)
        except ValueError:
            print("   resolution: invalid saved point allocation")
            continue

        effects, unresolved = repository.resolve(name, points)
        if effects:
            print("   resolved static effects:")
            for effect in effects:
                stat = effect.stat.value if effect.stat is not None else "(none)"
                print(
                    f"     - stat={stat} | operation={effect.operation.value} | "
                    f"value={effect.value} | unit={effect.unit.value}"
                )
        else:
            print("   resolved static effects: none")

        if unresolved:
            print("   unresolved mechanics:")
            for message in unresolved:
                print(f"     - {message}")
        else:
            print("   unresolved mechanics: none")

    print()
    if adaptation.unresolved:
        print("Adapter diagnostics unrelated to CP may still be present:")
        for message in adaptation.unresolved:
            print(f"  - {message}")
    else:
        print("Adapter diagnostics: none")

    print()
    print("Audit only: no database or saved-build data were changed.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit saved Champion Point selections against the current static CP repository and canonical adapter."
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
