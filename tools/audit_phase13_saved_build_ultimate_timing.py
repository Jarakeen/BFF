from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.rotation_plan import RotationActionKind
from models.build_model import PlayerBuild
from services.rotation_duration_analysis_service import RotationDurationAnalysisService
from services.rotation_duration_refinement_service import RotationDurationRefinementService
from services.rotation_ultimate_service import RotationUltimateService
from ui.rotation_duration_evidence_support import RotationDurationEvidenceSupport
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationSupport,
)


def _load_build(path: Path, build_name: str, character_name: str | None = None) -> PlayerBuild:
    payload = json.loads(path.read_text(encoding="utf-8"))
    members = payload.get("Members", [])
    target_build = str(build_name or "").strip().casefold()
    target_character = str(character_name or "").strip().casefold()

    matches: list[PlayerBuild] = []
    for member in members:
        candidate_build = str(member.get("BuildName", "") or "").strip()
        candidate_character = str(member.get("Name", "") or "").strip()
        if candidate_build.casefold() != target_build:
            continue
        if target_character and candidate_character.casefold() != target_character:
            continue
        matches.append(PlayerBuild.from_dict(member))

    if not matches:
        if target_character:
            raise ValueError(
                f"Saved build not found: character={character_name!r} build={build_name!r}"
            )
        raise ValueError(f"Saved build not found: {build_name}")
    if len(matches) > 1:
        raise ValueError(
            f"Saved build name is ambiguous: {build_name!r}; supply --character"
        )
    return matches[0]


def _slot_six(build: PlayerBuild, bar: str) -> str:
    values = (
        getattr(build, "FrontBarSkills", [])
        if bar == "front"
        else getattr(build, "BackBarSkills", [])
    )
    skills = list(values or [])
    if len(skills) < 6:
        return ""
    return str(skills[5] or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Phase 13 real saved-build Ultimate generation and placement"
    )
    parser.add_argument("--build", required=True)
    parser.add_argument("--character")
    parser.add_argument("--ultimate-bar", choices=("front", "back"), default="front")
    parser.add_argument("--starting-ultimate", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument(
        "--no-combat-attack-generation",
        action="store_true",
        help="Do not treat scheduled light/heavy attacks as successful damaging attacks",
    )
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--builds", default=str(ROOT / "data" / "builds.json"))
    args = parser.parse_args()

    database_path = Path(args.database)
    build = _load_build(Path(args.builds), args.build, args.character)
    selected_bar = str(args.ultimate_bar).casefold()
    selected_ultimate = _slot_six(build, selected_bar)

    support = RotationGenerationSupport(
        duration_refinement=RotationDurationRefinementService(database_path),
        duration_evidence=RotationDurationEvidenceSupport(
            RotationDurationAnalysisService(database_path)
        ),
        ultimate_service=RotationUltimateService(database_path),
    )
    result = support.generate_with_evidence(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=float(args.duration),
            rotation_type="Semi-static",
            weave_light_attacks=True,
            ultimate_bar=selected_bar,
            starting_ultimate=float(args.starting_ultimate),
            use_scheduled_combat_attacks_for_ultimate=not args.no_combat_attack_generation,
        ),
    )

    print("=" * 62)
    print(" PHASE 13 SAVED-BUILD ULTIMATE TIMING AUDIT")
    print("=" * 62)
    print(f"Character:              {result.plan.character_name}")
    print(f"Build:                  {result.plan.build_name}")
    print(f"Duration:               {result.plan.duration_seconds:g}s")
    print(f"Selected ultimate bar:  {selected_bar}")
    print(f"Saved slot-6 ultimate:  {selected_ultimate or 'none'}")
    print(f"Starting Ultimate:      {float(args.starting_ultimate):g}")
    print(
        "Combat attack source:   "
        + ("enabled" if not args.no_combat_attack_generation else "disabled")
    )
    print(
        "Boundary:               scheduled light/heavy attacks count as damaging hits only when enabled"
    )
    print()

    projection = result.ultimate_projection
    if projection is None:
        print("ULTIMATE PROJECTION")
        print("-------------------")
        print("none")
    else:
        print("ULTIMATE PROJECTION")
        print("-------------------")
        if projection.rules:
            for rule in projection.rules:
                times = ", ".join(f"{value:g}s" for value in rule.available_at_seconds) or "none"
                print(f"Ability:                {rule.skill_name}")
                print(f"Canonical cost:         {rule.cost:g}")
                print(f"Affordability times:    {times}")
        else:
            print("No schedulable ultimate rule was produced.")

        if projection.resource_projections:
            resource = projection.resource_projections[0][1]
            print(f"Ending Ultimate:        {resource.ending_amount:g}")
            print(f"Resource points:        {len(resource.points)}")
            print()
            print("RESOURCE TRACE")
            print("--------------")
            for point in resource.points:
                print(f"{point.time_seconds:>5.1f}s  {point.amount:>7.1f}  {point.source}")

    print()
    print("SCHEDULED ULTIMATES")
    print("-------------------")
    ultimate_actions = [
        action
        for action in result.plan.actions
        if action.kind is RotationActionKind.ULTIMATE
    ]
    if ultimate_actions:
        for action in ultimate_actions:
            print(
                f"{action.time_seconds:>5.1f}s  {(action.bar or 'unknown').title():<5}  {action.name}"
            )
    else:
        print("none")

    print()
    print("UNRESOLVED")
    print("----------")
    if result.plan.unresolved:
        for item in result.plan.unresolved:
            print(item)
    else:
        print("none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
