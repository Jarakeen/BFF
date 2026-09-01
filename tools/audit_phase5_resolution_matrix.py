from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from minmax.race_repository import RaceRepository
from services.build_service import BuildService
from services.saved_build_capability_service import SavedBuildCapabilityService


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trace one real saved build through the current Phase 5 resolution matrix."
    )
    parser.add_argument("--build", required=True, help="Saved build name or character name.")
    parser.add_argument("--builds", type=Path, default=get_data_dir() / "builds.json")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    return parser


def _effect_text(effect) -> str:
    layer = getattr(getattr(effect, "layer", None), "value", getattr(effect, "layer", ""))
    target = getattr(getattr(effect, "target_type", None), "value", getattr(effect, "target_type", ""))
    category = getattr(getattr(effect, "category", None), "value", getattr(effect, "category", ""))
    extras: list[str] = []
    if getattr(effect, "trigger", None):
        extras.append(f"trigger={effect.trigger}")
    if getattr(effect, "condition", None):
        extras.append(f"condition={effect.condition}")
    suffix = f" | {' | '.join(extras)}" if extras else ""
    return (
        f"{effect.name} | layer={layer or 'unknown'} | target={target or 'unknown'} "
        f"| category={category or 'other'} | source={effect.source}{suffix}"
    )


def main() -> int:
    args = _parser().parse_args()
    build_service = BuildService(args.builds)
    roster = build_service.load()
    requested = _clean(args.build).casefold()
    matches = [
        build
        for build in roster.Members
        if _clean(build.BuildName).casefold() == requested
        or _clean(build.Name).casefold() == requested
    ]
    if len(matches) != 1:
        print(f"Expected exactly one saved build/character matching {args.build!r}; found {len(matches)}")
        return 2

    build = matches[0]
    service = SavedBuildCapabilityService(build_service, args.database)
    service.context_factory = Phase5BuildCalculationContextFactory(
        race_repository=RaceRepository(args.database),
        gear_set_repository=service.gear_repository,
    )
    progression = service.progression.resolve(build)
    audit = service.audit_build(build)

    print("=" * 88)
    print(" PHASE 5 REAL-BUILD RESOLUTION MATRIX")
    print("=" * 88)
    print(f"Character:    {build.Name or '(unnamed)'}")
    print(f"Build:        {build.BuildName or '(unnamed)'}")
    print(f"Character ID: {progression.character_id or '(unresolved)'}")
    print(f"Race/Class:   {build.Race or '(none)'} / {build.EsoClass or '(none)'}")
    print(f"Database:     {args.database}")
    print()

    print("CANONICAL CHARACTER PROGRESSION")
    print(f"  owned skill lines: {len(progression.progression.owned_skill_lines)}")
    print(f"  passive ranks:     {len(progression.progression.passive_ranks or {})}")
    print(f"  passive CP stars:  {len(progression.progression.passive_cp_points or {})}")
    if progression.unresolved:
        for message in progression.unresolved:
            print(f"  ⚠ {message}")
    print()

    for bar in ("front", "back"):
        print("-" * 88)
        print(f"{bar.upper()} BAR GEAR SETS")
        counts = service._active_set_counts(build, bar)
        if not counts:
            print("  (none)")
        for set_name, count in counts.items():
            gear_set = service.gear_repository.get_set(set_name)
            if gear_set is None:
                print(f"  ⚠ {set_name}: not found in canonical gear_set data")
                continue
            variants = service.gear_effects.resolve(gear_set.id, count)
            print(
                f"  {gear_set.name}: pieces={count} | category={gear_set.category or '(unset)'} "
                f"| max_equip={gear_set.max_equip_count or '(unset)'} | variants={len(variants)}"
            )
            for effect in variants:
                print(f"    ✓ {_effect_text(effect)}")
            if not variants:
                print("    • no verified EffectVariant mapping at the active piece count")

        print()
        print(f"{bar.upper()} BAR SKILLS")
        skills = build.FrontBarSkills if bar == "front" else build.BackBarSkills
        any_skill = False
        for raw_name in skills:
            name = _clean(raw_name)
            if not name:
                continue
            any_skill = True
            ability_id = service._ability_id(name, build.EsoClass)
            if ability_id is None:
                print(f"  ⚠ {name}: canonical ability not found")
                continue
            variants = service.skill_effects.resolve(ability_id)
            print(f"  {name}: ability_id={ability_id} | variants={len(variants)}")
            for effect in variants:
                print(f"    ✓ {_effect_text(effect)}")
            if not variants:
                print("    • no verified support EffectVariant mapping")
        if not any_skill:
            print("  (none)")
        print()

    print("POTION AVAILABILITY")
    potion_name = _clean(build.Potion)
    if not potion_name:
        print("  (none selected)")
    else:
        potion = service.potions.resolve(potion_name)
        print(
            f"  {potion_name}: formulas={len(potion.formulas)} | variants={len(potion.effects)} "
            f"| resolved={'yes' if potion.resolved else 'no'}"
        )
        for effect in potion.effects:
            print(f"    ✓ {_effect_text(effect)}")
        for message in potion.unresolved:
            print(f"    ⚠ {message}")
    print()

    print("CAPABILITY SUMMARY")
    print(f"  unique resolved EffectVariants: {len(audit.resolved_effects)}")
    print(f"  sources: {', '.join(audit.resolved_sources) if audit.resolved_sources else '(none)'}")
    print(f"  conditional sources: {', '.join(audit.conditional_sources) if audit.conditional_sources else '(none)'}")
    print(f"  intentional boundaries: {len(audit.boundaries)}")
    print(f"  genuine unresolved: {len(audit.unresolved)}")
    for message in audit.boundaries:
        print(f"    • {message}")
    for message in audit.unresolved:
        print(f"    ⚠ {message}")

    print()
    print("=" * 88)
    print(f"PHASE 5 GENUINE UNRESOLVED: {len(audit.unresolved)}")
    print("=" * 88)
    return 1 if audit.unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
