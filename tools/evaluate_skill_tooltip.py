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
from minmax.skill_coefficient_repository import (
    SkillCoefficientRepository,
    ability_entity_id,
)
from minmax.skill_tooltip_calculator import SkillTooltipCalculator
from minmax.source_provenance import SourceProvenanceError, load_source_provenance
from models.build_model import PlayerBuild


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _load_saved_builds(path: Path) -> list[PlayerBuild]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, dict) and isinstance(payload.get("Members"), list):
        return [
            PlayerBuild.from_dict(entry)
            for entry in payload["Members"]
            if isinstance(entry, dict)
        ]

    if isinstance(payload, dict) and isinstance(payload.get("builds"), list):
        builds: list[PlayerBuild] = []
        for entry in payload["builds"]:
            if not isinstance(entry, dict):
                continue
            legacy = entry.get("legacy")
            builds.append(PlayerBuild.from_dict(legacy if isinstance(legacy, dict) else entry))
        return builds

    raise ValueError(
        f"Unsupported saved-build format in {path}; expected Members or builds"
    )


def _find_build(builds: list[PlayerBuild], requested: str) -> PlayerBuild:
    key = str(requested or "").strip().casefold()
    if not key:
        raise ValueError("--build is required")

    matches = [
        build
        for build in builds
        if build.BuildName.strip().casefold() == key
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        owners = ", ".join(
            build.Name.strip() or build.Gamertag.strip() or "(unnamed)"
            for build in matches
        )
        raise ValueError(f"Ambiguous build name {requested!r}; owners: {owners}")

    available = ", ".join(
        sorted(
            {
                build.BuildName.strip()
                for build in builds
                if build.BuildName.strip()
            },
            key=str.casefold,
        )
    )
    raise ValueError(
        f"Saved build not found: {requested!r}. Available builds: {available or '(none)'}"
    )


def _progression(build: PlayerBuild) -> CharacterProgression:
    return CharacterProgression(
        attributes=AttributeAllocation(
            health=build.AttributeHealth,
            magicka=build.AttributeMagicka,
            stamina=build.AttributeStamina,
        )
    )


def evaluate_saved_build(
    *,
    database_path: Path,
    builds_path: Path,
    build_name: str,
    entity_id: str,
    active_bar: str,
) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1
    if not builds_path.exists():
        print(f"Saved builds not found: {builds_path}")
        return 2

    try:
        build = _find_build(_load_saved_builds(builds_path), build_name)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(exc)
        return 3

    factory = BuildCalculationContextFactory(
        race_repository=RaceRepository(database_path),
        gear_set_repository=GearSetRepository(database_path),
    )
    context = factory.build(
        character_id=build.Name.strip() or build.Gamertag.strip() or "saved-character",
        build_id=build.BuildName.strip() or "saved-build",
        build=build,
        progression=_progression(build),
        active_bar=active_bar,
    )

    canonical_entity_id = ability_entity_id(entity_id)
    calculator = SkillTooltipCalculator(
        SkillCoefficientRepository(database_path)
    )
    result = calculator.evaluate_entity_id(canonical_entity_id, context)

    slotted = {
        "front": tuple(
            ability_entity_id(name)
            for name in build.FrontBarSkills
            if str(name).strip()
        ),
        "back": tuple(
            ability_entity_id(name)
            for name in build.BackBarSkills
            if str(name).strip()
        ),
    }
    slotted_bars = tuple(
        bar_name
        for bar_name, skills in slotted.items()
        if canonical_entity_id in skills
    )

    print()
    print("========================================")
    print(" PHASE 3 SAVED-BUILD SKILL TOOLTIP")
    print("========================================")
    print(f"Database:       {database_path}")
    print(f"Saved builds:   {builds_path}")
    print(f"Character:      {build.Name or '(unnamed)'}")
    print(f"Build:          {build.BuildName or '(unnamed)'}")
    print(f"Active bar:     {active_bar}")
    print(f"Entity ID:      {canonical_entity_id}")
    print(f"Slotted on:     {', '.join(slotted_bars) if slotted_bars else '(not slotted)'}")
    try:
        provenance = load_source_provenance("skill_coefficients")
    except (OSError, json.JSONDecodeError, SourceProvenanceError) as exc:
        print(f"Coefficient provenance: unavailable ({exc})")
    else:
        print(
            f"Coefficient source: {provenance.source_system} "
            f"{provenance.export_table} ({provenance.source_kind})"
        )
        print(f"Coefficient export: {provenance.export_url}")
        print(
            "Coefficient provenance: "
            f"records={provenance.record_count or 'unresolved'} | "
            f"game update={provenance.game_update or 'unresolved'} | "
            f"API version={provenance.api_version or 'unresolved'} | "
            f"retrieved at={provenance.retrieved_at or 'unresolved'}"
        )
    print()

    if result.skill is None:
        print("Skill resolution failed:")
        for message in result.unresolved:
            print(f"  - {message}")
        return 4

    skill = result.skill
    print(
        f"Resolved skill: {skill.name} | rank={skill.rank} | morph={skill.morph} | "
        f"source ability={skill.ability_id} | skill_rank={skill.skill_rank_id}"
    )

    scaling = result.scaling
    if scaling is not None:
        print()
        print("Phase 2 scaling inputs:")
        print(f"  Max Health:              {scaling.max_health:.6f}")
        print(f"  Max Magicka:             {scaling.max_magicka:.6f}")
        print(f"  Max Stamina:             {scaling.max_stamina:.6f}")
        print(f"  Highest Max Resource:    {scaling.highest_max_resource:.6f}")
        print(f"  Weapon Damage:           {scaling.weapon_damage:.6f}")
        print(f"  Spell Damage:            {scaling.spell_damage:.6f}")
        print(f"  Highest Offensive Power: {scaling.highest_offensive_power:.6f}")

    print()
    print("Coefficient trace:")
    if not result.components:
        print("  (no evaluated components)")
    for component in result.components:
        print(
            f"  #{component.coefficient_number} type={component.coefficient_type}: "
            f"({component.a:.12g} * {component.max_stat:.6f}) + "
            f"({component.b:.12g} * {component.power:.6f}) + "
            f"{component.c:.12g}"
        )
        print(
            f"     resource={component.resource_term:.6f} | "
            f"power={component.power_term:.6f} | "
            f"constant={component.constant_term:.6f}"
        )
        print(
            f"     before R={component.before_r:.6f} | "
            f"R={component.r:.12g} | raw={component.final_value:.6f}"
        )

    print()
    if result.raw_total is None:
        print("Raw tooltip total: unresolved")
    else:
        print(f"Raw tooltip total: {result.raw_total:.6f}")
        print("Final ESO tooltip rounding: intentionally not applied")

    unresolved = tuple(context.unresolved_gear_effects) + tuple(result.unresolved)
    print()
    print("Unresolved:")
    if unresolved:
        for message in unresolved:
            print(f"  - {message}")
    else:
        print("  (none)")
    print()

    return 0 if result.raw_total is not None else 5


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate one canonical skill entity against a real saved build "
            "through the Phase 2 character-sheet pipeline."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--entity", default="blessing_of_protection")
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    return parser


if __name__ == "__main__":
    arguments = _parser().parse_args()
    raise SystemExit(
        evaluate_saved_build(
            database_path=arguments.database,
            builds_path=arguments.builds,
            build_name=arguments.build,
            entity_id=arguments.entity,
            active_bar=arguments.active_bar,
        )
    )
