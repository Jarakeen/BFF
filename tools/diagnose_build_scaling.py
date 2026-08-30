from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_repository import GearSetRepository
from minmax.race_repository import RaceRepository
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _load_builds(path: Path) -> list[PlayerBuild]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("Members"), list):
        return [PlayerBuild.from_dict(entry) for entry in payload["Members"] if isinstance(entry, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("builds"), list):
        builds: list[PlayerBuild] = []
        for entry in payload["builds"]:
            if not isinstance(entry, dict):
                continue
            legacy = entry.get("legacy")
            builds.append(PlayerBuild.from_dict(legacy if isinstance(legacy, dict) else entry))
        return builds
    raise ValueError(f"Unsupported saved-build format in {path}")


def _find_build(builds: list[PlayerBuild], requested: str) -> PlayerBuild:
    key = str(requested or "").strip().casefold()
    matches = [build for build in builds if build.BuildName.strip().casefold() == key]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one saved build named {requested!r}; found {len(matches)}")
    return matches[0]


def _progression(build: PlayerBuild) -> CharacterProgression:
    return CharacterProgression(
        attributes=AttributeAllocation(
            health=build.AttributeHealth,
            magicka=build.AttributeMagicka,
            stamina=build.AttributeStamina,
        )
    )


def _print_trace(label: str, trace) -> None:
    print(f"\n{label}: {trace.final_value:.6f}")
    for step_label, operation, value, result in trace.steps:
        print(f"  {step_label}: {operation} {value:.6f} -> {result:.6f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace saved-build scaling stats used by Phase 3 skill math.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    args = parser.parse_args()

    build = _find_build(_load_builds(args.builds), args.build)
    context = BuildCalculationContextFactory(
        race_repository=RaceRepository(args.database),
        gear_set_repository=GearSetRepository(args.database),
    ).build(
        character_id=build.Name.strip() or build.Gamertag.strip() or "saved-character",
        build_id=build.BuildName.strip() or "saved-build",
        build=build,
        progression=_progression(build),
        active_bar=args.active_bar,
    )

    if context.core_state is None:
        print("core_state unavailable")
        return 1

    print("========================================")
    print(" PHASE 3 BUILD SCALING TRACE")
    print("========================================")
    print(f"Character:  {build.Name or '(unnamed)'}")
    print(f"Build:      {build.BuildName or '(unnamed)'}")
    print(f"Active bar: {args.active_bar}")
    print(f"Potion:     {build.Potion or '(none)'}")
    print(f"Mundus:     {build.Mundus or '(none)'}")

    for stat, label in (
        (StatId.WEAPON_DAMAGE, "Weapon Damage"),
        (StatId.SPELL_DAMAGE, "Spell Damage"),
        (StatId.HEALING_DONE, "Healing Done"),
    ):
        trace = context.core_state.derived.get(stat)
        if trace is not None:
            _print_trace(label, trace)

    print("\nUnresolved build effects:")
    if context.unresolved_gear_effects:
        for message in context.unresolved_gear_effects:
            print(f"  - {message}")
    else:
        print("  (none)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
