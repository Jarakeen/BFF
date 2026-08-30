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

PRIMARY_STATS = (
    (StatId.MAX_HEALTH, "Max Health"),
    (StatId.MAX_MAGICKA, "Max Magicka"),
    (StatId.MAX_STAMINA, "Max Stamina"),
    (StatId.HEALTH_RECOVERY, "Health Recovery"),
    (StatId.MAGICKA_RECOVERY, "Magicka Recovery"),
    (StatId.STAMINA_RECOVERY, "Stamina Recovery"),
)

DERIVED_STATS = (
    (StatId.WEAPON_DAMAGE, "Weapon Damage"),
    (StatId.SPELL_DAMAGE, "Spell Damage"),
    (StatId.WEAPON_CRITICAL, "Weapon Critical"),
    (StatId.SPELL_CRITICAL, "Spell Critical"),
    (StatId.CRITICAL_DAMAGE, "Critical Damage"),
    (StatId.CRITICAL_HEALING, "Critical Healing"),
    (StatId.CRITICAL_RESISTANCE, "Critical Resistance"),
    (StatId.PHYSICAL_PENETRATION, "Physical Penetration"),
    (StatId.SPELL_PENETRATION, "Spell Penetration"),
    (StatId.PHYSICAL_RESISTANCE, "Physical Resistance"),
    (StatId.SPELL_RESISTANCE, "Spell Resistance"),
    (StatId.HEALING_DONE, "Healing Done"),
    (StatId.HEALING_TAKEN, "Healing Taken"),
)

KNOWN_COVERAGE_GAPS = (
    "Verified standing Warden passives are partially resolved; other class passive families are not yet wired.",
    "Verified Light/Medium armor passives are resolved only when character ownership is explicitly supplied.",
    "Verified Undaunted Mettle is resolved when Undaunted ownership is explicitly supplied; triggered Undaunted Command remains combat-state work.",
    "Verified Mages Guild Magicka Controller and Fighters Guild Slayer are resolved from owned skill lines plus active-bar slot counts; other guild passive effects remain ability-family or combat-state work.",
    "Verified Support Magicka Aid is resolved from Support ownership plus active-bar Support slot counts; Psijic and Assault standing-sheet audits found no generic standing contribution.",
    "Weapon passive effects are classified but do not contribute generic standing sheet stats for Restoration/Destruction Staff.",
    "Selected potions are recorded, but active potion buffs are not yet modeled.",
    "Conditional/proc buffs must remain unresolved unless their active state is explicitly supplied.",
    "Block cost and Block Mitigation are not yet represented as first-class shared stats.",
)


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


def _progression(build: PlayerBuild, *, owned_skill_lines: tuple[str, ...] = ()) -> CharacterProgression:
    return CharacterProgression(
        attributes=AttributeAllocation(
            health=build.AttributeHealth,
            magicka=build.AttributeMagicka,
            stamina=build.AttributeStamina,
        ),
        owned_skill_lines=owned_skill_lines,
    )


def _print_trace(label: str, trace) -> None:
    print(f"\n{label}: {trace.final_value:.6f}")
    for step in trace.steps:
        if hasattr(step, "label"):
            print(f"  {step.label}: {step.operation} {step.value:.6f} -> {step.result:.6f}")
        else:
            step_label, operation, value, result = step
            print(f"  {step_label}: {operation} {value:.6f} -> {result:.6f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace saved-build shared stats used by Phase 2/3 combat math.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    parser.add_argument(
        "--owned-skill-line",
        action="append",
        default=[],
        help="Character-owned/maxed passive skill line to include; repeat for multiple lines.",
    )
    args = parser.parse_args()

    build = _find_build(_load_builds(args.builds), args.build)
    progression = _progression(build, owned_skill_lines=tuple(args.owned_skill_line))
    context = BuildCalculationContextFactory(
        race_repository=RaceRepository(args.database),
        gear_set_repository=GearSetRepository(args.database),
    ).build(
        character_id=build.Name.strip() or build.Gamertag.strip() or "saved-character",
        build_id=build.BuildName.strip() or "saved-build",
        build=build,
        progression=progression,
        active_bar=args.active_bar,
    )

    if context.core_state is None:
        print("core_state unavailable")
        return 1

    print("========================================")
    print(" SHARED BUILD MATH TRACE")
    print("========================================")
    print(f"Character:  {build.Name or '(unnamed)'}")
    print(f"Build:      {build.BuildName or '(unnamed)'}")
    print(f"Role:       {build.Role or '(unset)'}")
    print(f"Class:      {build.EsoClass or '(unset)'}")
    print(f"Race:       {build.Race or '(unset)'}")
    print(f"Active bar: {args.active_bar}")
    print(f"Food:       {build.Food or '(none)'}")
    print(f"Potion:     {build.Potion or '(none)'}")
    print(f"Mundus:     {build.Mundus or '(none)'}")
    print(
        "Owned skill lines: "
        + (", ".join(progression.owned_skill_lines) if progression.owned_skill_lines else "(none supplied)")
    )

    print("\nPRIMARY RESOURCE LAYER")
    for stat, label in PRIMARY_STATS:
        trace = context.character_state.traces.get(stat)
        if trace is not None:
            _print_trace(label, trace)

    print("\nDERIVED COMBAT STAT LAYER")
    for stat, label in DERIVED_STATS:
        trace = context.core_state.derived.get(stat)
        if trace is not None:
            _print_trace(label, trace)

    print("\nUnresolved build effects:")
    if context.unresolved_gear_effects:
        for message in context.unresolved_gear_effects:
            print(f"  - {message}")
    else:
        print("  (none)")

    print("\nKnown shared-pipeline coverage gaps:")
    for message in KNOWN_COVERAGE_GAPS:
        print(f"  - {message}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
