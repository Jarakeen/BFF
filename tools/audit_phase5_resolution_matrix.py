from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.build_service import BuildService
from services.saved_build_capability_service import SavedBuildCapabilityService


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _has_identity(build) -> bool:
    return bool(_clean(build.Name) or _clean(build.Gamertag) or _clean(build.BuildName))


def _is_template_build(build) -> bool:
    """Identify obvious bundled/sample build rows without mutating them.

    Explicit --build selection may still audit these rows. The automatic
    roster-wide closeout path excludes them so sample/template residue does not
    count as unresolved evidence for authoritative user builds.
    """
    labels = {
        _clean(getattr(build, "Name", "")).casefold(),
        _clean(getattr(build, "BuildName", "")).casefold(),
    }
    labels.discard("")
    if not labels:
        return False
    known = {
        "your tank build",
        "your healer build",
        "your dd build",
        "your dps build",
    }
    if labels & known:
        return True
    return any(
        label.startswith("template ")
        or label.endswith(" template")
        or (label.startswith("your ") and label.endswith(" build"))
        for label in labels
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trace real saved builds through the current Phase 5 resolution matrix."
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--build", help="Saved build name or character name.")
    selection.add_argument(
        "--all",
        action="store_true",
        help="Audit every authoritative non-empty saved build without mutating the roster.",
    )
    parser.add_argument(
        "--include-templates",
        action="store_true",
        help="With --all, include obvious sample/template builds in diagnostic totals.",
    )
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


def _print_build_matrix(*, build, service, database: Path) -> int:
    progression = service.progression.resolve(build)
    audit = service.audit_build(build)

    print("=" * 88)
    print(" PHASE 5 REAL-BUILD RESOLUTION MATRIX")
    print("=" * 88)
    print(f"Character:    {build.Name or '(unnamed)'}")
    print(f"Build:        {build.BuildName or '(unnamed)'}")
    print(f"Character ID: {progression.character_id or '(unresolved)'}")
    print(f"Race/Class:   {build.Race or '(none)'} / {build.EsoClass or '(none)'}")
    print(f"Database:     {database}")
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
    return len(audit.unresolved)


def main() -> int:
    args = _parser().parse_args()
    build_service = BuildService(args.builds)
    roster = build_service.load()

    skipped_templates = []
    if args.all:
        candidates = [build for build in roster.Members if _has_identity(build)]
        if args.include_templates:
            builds = candidates
        else:
            builds = [build for build in candidates if not _is_template_build(build)]
            skipped_templates = [build for build in candidates if _is_template_build(build)]
        if not builds:
            print("No authoritative non-empty saved builds found.")
            if skipped_templates:
                print(f"Template/sample builds excluded: {len(skipped_templates)}")
            return 2
    else:
        requested = _clean(args.build).casefold()
        builds = [
            build
            for build in roster.Members
            if _clean(build.BuildName).casefold() == requested
            or _clean(build.Name).casefold() == requested
        ]
        if len(builds) != 1:
            print(f"Expected exactly one saved build/character matching {args.build!r}; found {len(builds)}")
            return 2

    service = SavedBuildCapabilityService(build_service, args.database)

    unresolved_by_build: list[tuple[str, str, int]] = []
    for index, build in enumerate(builds):
        if index:
            print("\n\n")
        unresolved_count = _print_build_matrix(
            build=build,
            service=service,
            database=args.database,
        )
        unresolved_by_build.append((build.Name, build.BuildName, unresolved_count))

    if args.all:
        print("\n" + "#" * 88)
        print(" PHASE 5 ROSTER SUMMARY")
        print("#" * 88)
        total = 0
        for character_name, build_name, unresolved_count in unresolved_by_build:
            total += unresolved_count
            label = f"{character_name or '(unnamed)'} | {build_name or '(unnamed build)'}"
            print(f"  {label}: genuine unresolved={unresolved_count}")
        if skipped_templates:
            print("  EXCLUDED TEMPLATE/SAMPLE BUILDS:")
            for build in skipped_templates:
                label = f"{build.Name or '(unnamed)'} | {build.BuildName or '(unnamed build)'}"
                print(f"    • {label}")
            print("  Re-run with --include-templates to include those diagnostic samples.")
        print(f"  TOTAL GENUINE UNRESOLVED: {total}")
        print("#" * 88)
        return 1 if total else 0

    return 1 if unresolved_by_build[0][2] else 0


if __name__ == "__main__":
    raise SystemExit(main())
