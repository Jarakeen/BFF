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
from minmax.healing_scaling_diagnostic import (
    combat_prayer_investigation_scenarios,
    evaluate_healing_scenario,
)
from minmax.race_repository import RaceRepository
from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare observed healing tooltip against auditable Phase 3 scenarios.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--entity", default="combat_prayer")
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    parser.add_argument("--observed-tooltip", type=float, required=True)
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

    resolution = SkillCoefficientRepository(args.database).resolve_entity_id(
        ability_entity_id(args.entity)
    )
    if resolution.rank is None:
        for message in resolution.unresolved:
            print(message)
        return 2
    active = [c for c in resolution.rank.coefficients if str(c.type).strip() == "8"]
    if len(active) != 1:
        print(f"Expected one active type-8 coefficient for diagnostic; found {len(active)}")
        return 3

    coefficient = active[0]
    derived = context.core_state.derived
    weapon = derived[StatId.WEAPON_DAMAGE].final_value
    spell = derived[StatId.SPELL_DAMAGE].final_value
    base_power = max(float(weapon), float(spell))
    healing_trace = derived[StatId.HEALING_DONE]

    ritual_bonus = 0.0
    powered_bonus = 0.0
    for label, operation, value, _result in healing_trace.steps:
        if operation != "add":
            continue
        key = label.casefold()
        if "mundus: the ritual" in key:
            ritual_bonus += float(value)
        if "powered" in key:
            powered_bonus += float(value)

    max_stat = max(
        float(context.character_state.max_magicka),
        float(context.character_state.max_stamina),
    )

    print("========================================")
    print(" PHASE 3 HEALING TOOLTIP DIAGNOSTIC")
    print("========================================")
    print(f"Character:       {build.Name or '(unnamed)'}")
    print(f"Build:           {build.BuildName or '(unnamed)'}")
    print(f"Skill:           {resolution.rank.name}")
    print(f"Observed:        {args.observed_tooltip:.6f}")
    print(f"Max stat:        {max_stat:.6f}")
    print(f"Base power:      {base_power:.6f}")
    print(f"Ritual trace:    {ritual_bonus:.6f}")
    print(f"Powered trace:   {powered_bonus:.6f} (kept out of tooltip scenarios pending current validation)")
    print()

    results = []
    for scenario in combat_prayer_investigation_scenarios(ritual_bonus=ritual_bonus):
        result = evaluate_healing_scenario(
            coefficient,
            max_stat=max_stat,
            base_power=base_power,
            scenario=scenario,
        )
        delta = float(args.observed_tooltip) - result.tooltip_value
        results.append((abs(delta), scenario.name, result.tooltip_value, delta, result))

    for _abs_delta, name, value, delta, result in results:
        print(f"{name}: {value:.6f} | observed delta {delta:+.6f}")
        print(f"  effective power: {result.effective_power:.6f}")
        print(f"  coefficient before tooltip Healing Done: {result.base_coefficient_value:.6f}")
        for note in result.scenario.notes:
            print(f"  - {note}")

    best = min(results, key=lambda row: row[0])
    print()
    print(f"Closest diagnostic scenario: {best[1]} ({best[2]:.6f}, delta {best[3]:+.6f})")
    print("This is a diagnostic comparison, not a promoted production formula.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
