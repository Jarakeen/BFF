from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.ability_cost_repository import AbilityCostRepository
from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.build_sustain import evaluate_named_build_sustain
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_repository import GearSetRepository
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.race_repository import RaceRepository
from minmax.resource_costs import ResourceType
from minmax.saved_build_activity import create_saved_bar_activity_plan
from models.build_model import PlayerBuild

DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _load_saved_builds(path: Path) -> list[PlayerBuild]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("Members"), list):
        return [PlayerBuild.from_dict(entry) for entry in payload["Members"] if isinstance(entry, dict)]
    raise ValueError(f"Unsupported saved-build format in {path}; expected Members")


def _find_build(builds: list[PlayerBuild], requested: str) -> PlayerBuild:
    key = str(requested or "").strip().casefold()
    matches = [build for build in builds if build.BuildName.strip().casefold() == key]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous build name: {requested!r}")
    raise ValueError(f"Saved build not found: {requested!r}")


def _audit_progression(build: PlayerBuild) -> CharacterProgression:
    # The canonical character catalog does not yet persist skill-line ownership.
    # For this read-only audit, infer only armor lines visibly represented by the
    # equipped build so their current standing passives can be exercised. The
    # assumption is printed in the audit output and is not written anywhere.
    armor_lines = {
        f"{str(entry.get('Weight', '') or '').strip().title()} Armor"
        for entry in build.Armor.values()
        if str(entry.get("Weight", "") or "").strip().casefold() in {"light", "medium", "heavy"}
    }
    return CharacterProgression(
        attributes=AttributeAllocation(
            health=build.AttributeHealth,
            magicka=build.AttributeMagicka,
            stamina=build.AttributeStamina,
        ),
        owned_skill_lines=tuple(sorted(armor_lines)),
    )


def audit_saved_build_sustain(
    *,
    database_path: Path,
    builds_path: Path,
    build_name: str,
    active_bar: str,
    resource: ResourceType,
    duration_seconds: float,
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

    progression = _audit_progression(build)
    factory = BuildCalculationContextFactory(
        race_repository=RaceRepository(database_path),
        gear_set_repository=GearSetRepository(database_path),
    )
    context = factory.build(
        character_id=build.Name.strip() or build.Gamertag.strip() or "saved-character",
        build_id=build.BuildName.strip() or "saved-build",
        build=build,
        progression=progression,
        active_bar=active_bar,
        fight_duration=duration_seconds,
    )

    plan = create_saved_bar_activity_plan(
        build,
        active_bar=active_bar,
        duration_seconds=duration_seconds,
    )
    cost_modifier_resolver = BuildActionCostModifierResolver(
        JewelryCostModifierRepository(database_path),
        JewelryTraitRepository(database_path),
    )
    run = evaluate_named_build_sustain(
        build=build,
        context=context,
        resource=resource,
        duration_seconds=duration_seconds,
        actions=plan.actions,
        ability_cost_repository=AbilityCostRepository(database_path),
        cost_modifier_resolver=cost_modifier_resolver,
    )

    pool = {
        ResourceType.HEALTH: (context.character_state.max_health, context.character_state.health_recovery),
        ResourceType.MAGICKA: (context.character_state.max_magicka, context.character_state.magicka_recovery),
        ResourceType.STAMINA: (context.character_state.max_stamina, context.character_state.stamina_recovery),
    }[resource]

    print()
    print("========================================")
    print(" PHASE 4 SAVED-BUILD SUSTAIN AUDIT")
    print("========================================")
    print(f"Database:       {database_path}")
    print(f"Saved builds:   {builds_path}")
    print(f"Character:      {build.Name or '(unnamed)'}")
    print(f"Build:          {build.BuildName or '(unnamed)'}")
    print(f"Class/Race:     {build.EsoClass or '(unset)'} / {build.Race or '(unset)'}")
    print(f"Active bar:     {active_bar}")
    print(f"Resource:       {resource.value}")
    print(f"Window:         {duration_seconds:g}s")
    print(f"Max resource:   {pool[0]}")
    print(f"Recovery/tick:  {pool[1]}")
    print(
        "Audit progression assumption: "
        + (", ".join(progression.owned_skill_lines) if progression.owned_skill_lines else "no armor lines inferred")
    )
    print()

    print("Deterministic saved-bar activity plan:")
    if not plan.actions:
        print("  (no ordinary skills on active bar)")
    for action in plan.actions:
        print(f"  {action.time_seconds:5.1f}s  {action.skill_name}")

    print()
    print("Resolved resource cost events:")
    if not run.action_cost_events:
        print("  (none for requested resource)")
    for event in run.action_cost_events:
        print(f"  {event.time_seconds:5.1f}s  -{event.amount:5d}  {event.source}")

    print()
    print("Recovery ticks:")
    for event in run.recovery_ticks:
        print(
            f"  {event.time_seconds:5.1f}s  +{event.tick.restored_amount:5d}  "
            f"base={event.tick.displayed_recovery} bonus={event.tick.additive_recovery_bonus} "
            f"suppressed={event.tick.suppressed}"
        )

    sustain = run.sustain
    print()
    print("Sustain result:")
    print(f"  Sustains:              {sustain.sustains}")
    print(f"  Starting resource:     {sustain.starting_amount}")
    print(f"  Ending resource:       {sustain.ending_amount}")
    print(f"  Minimum resource:      {sustain.minimum_amount}")
    print(f"  Total cost attempted:  {sustain.total_cost_attempted}")
    print(f"  Total cost paid:       {sustain.total_cost_paid}")
    print(f"  Restoration applied:   {sustain.total_restoration_applied}")
    print(f"  Restoration wasted:    {sustain.total_restoration_wasted}")
    if sustain.first_failure is not None:
        failure = sustain.first_failure
        print(
            f"  First failure:         {failure.time_seconds:g}s {failure.source} "
            f"shortfall={failure.shortfall} before={failure.resource_before} "
            f"cost={failure.attempted_cost}"
        )

    unresolved = tuple(context.unresolved_gear_effects) + tuple(run.unresolved)
    print()
    print("Unresolved:")
    if unresolved:
        for message in unresolved:
            print(f"  - {message}")
    else:
        print("  (none)")
    print()

    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a deterministic Phase 4 sustain audit against one real saved build."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    parser.add_argument(
        "--resource",
        choices=("health", "magicka", "stamina"),
        default="magicka",
    )
    parser.add_argument("--duration", type=float, default=20.0)
    return parser


if __name__ == "__main__":
    arguments = _parser().parse_args()
    raise SystemExit(
        audit_saved_build_sustain(
            database_path=arguments.database,
            builds_path=arguments.builds,
            build_name=arguments.build,
            active_bar=arguments.active_bar,
            resource=ResourceType(arguments.resource),
            duration_seconds=arguments.duration,
        )
    )
