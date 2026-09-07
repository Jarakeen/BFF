from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.resource_costs import ResourceType
from minmax.rotation_resource_reserve import resource_amount_before
from services.encounter_boss_guide import EncounterBossGuideService
from services.healer_rotation_priority_service import HealerRotationPriorityService
from services.rotation_duration_refinement_service import RotationDurationRefinementService
from services.rotation_sustain_service import RotationSustainService
from tools.audit_phase13_healer_priority_comparison import _BASE_PRIORITIES, _audit_policy_set
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from tools.audit_phase13_xalvakka_healer_band_cost_diagnosis import _project_plan
from tools.audit_phase13_xalvakka_healer_threshold_rotation import _DEMAND_NAME, _DEMAND_PRIORITIES
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _floor_values(start: int, stop: int, step: int) -> tuple[int, ...]:
    if step <= 0:
        raise ValueError("--reserve-step must be positive")
    if start < 0 or stop < 0:
        raise ValueError("reserve floors cannot be negative")
    if stop < start:
        raise ValueError("--reserve-stop must be at least --reserve-start")
    return tuple(range(start, stop + 1, step))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep caller-supplied mechanic-entry Magicka reserve floors for baseline and "
            "encounter-aware DF Healer plans at representative Xalvakka raid-DPS values."
        )
    )
    parser.add_argument("--character", default="Magrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--encounter", default="xalvakka")
    parser.add_argument(
        "--difficulty",
        choices=("normal", "veteran", "hardmode"),
        default="hardmode",
    )
    parser.add_argument(
        "--raid-dps",
        type=float,
        nargs="+",
        default=(1_300_000.0, 1_500_000.0, 2_000_000.0),
    )
    parser.add_argument("--reserve-start", type=int, default=14_000)
    parser.add_argument("--reserve-stop", type=int, default=24_000)
    parser.add_argument("--reserve-step", type=int, default=1_000)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--lead-seconds", type=float, default=3.0)
    parser.add_argument("--window-seconds", type=float, default=2.0)
    parser.add_argument("--anticipation-seconds", type=float, default=3.0)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    if any(float(value) <= 0 for value in args.raid_dps):
        raise ValueError("all --raid-dps values must be positive")
    floors = _floor_values(args.reserve_start, args.reserve_stop, args.reserve_step)

    database_path = Path(args.database)
    build = _load_saved_build(
        Path(args.builds),
        character=args.character,
        build_name=args.build,
    )
    guide = EncounterBossGuideService(database_path).get(args.encounter)
    policy_set = _audit_policy_set(build, database_path=database_path)
    priority_projection = HealerRotationPriorityService().project(
        policy_set=policy_set,
        base_priorities=_BASE_PRIORITIES,
        demand_priorities=_DEMAND_PRIORITIES,
    )
    refresh_leads = (
        DemandRefreshLead(
            demand_name=_DEMAND_NAME,
            bar="front",
            skill_name="Budding Seeds",
            lead_seconds=float(args.anticipation_seconds),
        ),
    )

    refinement_service = RotationDurationRefinementService(database_path=database_path)
    generator = RotationGenerationSupport(duration_refinement=refinement_service)
    request = RotationGenerationRequest(
        duration_seconds=float(args.duration),
        ability_priorities=priority_projection.entries,
    )
    definition = generator.build_definition(build=build, request=request)
    seed_plan = generator.planner.build_plan(definition, build)
    base_plan = refinement_service.refine(
        seed_plan,
        priorities=priority_projection.priority_list,
    ).plan

    sustain_service = RotationSustainService(database_path=database_path)
    base_sustain = sustain_service.evaluate(
        build=build,
        plan=base_plan,
        resource=ResourceType.MAGICKA,
    )

    print("=" * 118)
    print(" PHASE 13 XALVAKKA HEALER MECHANIC-ENTRY RESERVE-FLOOR SWEEP")
    print("=" * 118)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Encounter: {guide.name} ({guide.encounter_id}) | Difficulty: {args.difficulty}")
    print(
        f"Reserve sweep: {floors[0]:,} to {floors[-1]:,} Magicka by {args.reserve_step:,}; "
        "all floors are caller-supplied diagnostic policies"
    )
    print(
        "Boundary: reserve is measured immediately before the projected prep-window start; "
        "this tool does not claim any swept floor is the correct Xalvakka requirement"
    )

    for raid_dps in args.raid_dps:
        phase_2, demand, aware_plan = _project_plan(
            raid_dps=float(raid_dps),
            guide=guide,
            difficulty=args.difficulty,
            seed_plan=seed_plan,
            refinement_service=refinement_service,
            priorities=priority_projection.priority_list,
            refresh_leads=refresh_leads,
            lead_seconds=float(args.lead_seconds),
            window_seconds=float(args.window_seconds),
        )
        aware_sustain = sustain_service.evaluate(
            build=build,
            plan=aware_plan,
            resource=ResourceType.MAGICKA,
        )
        base_entry = resource_amount_before(base_sustain.run.timeline, demand.start_seconds)
        aware_entry = resource_amount_before(aware_sustain.run.timeline, demand.start_seconds)

        print()
        print("-" * 118)
        print(
            f"{float(raid_dps):,.0f} RAID DPS | 70% at {float(phase_2.time_seconds):.2f}s | "
            f"prep {demand.start_seconds:.2f}-{demand.end_seconds:.2f}s | "
            f"entry Mag baseline {base_entry:,}, aware {aware_entry:,}"
        )
        print("RESERVE FLOOR | BASELINE | AWARE | BASE MARGIN | AWARE MARGIN")
        print("--------------+----------+-------+-------------+-------------")
        for floor in floors:
            base_margin = base_entry - floor
            aware_margin = aware_entry - floor
            print(
                f"{floor:12,d} | {'PASS' if base_margin >= 0 else 'FAIL':8s} | "
                f"{'PASS' if aware_margin >= 0 else 'FAIL':5s} | "
                f"{base_margin:+11,d} | {aware_margin:+11,d}"
            )

        if base_entry == aware_entry:
            print(
                "Reserve boundary: both plans cross at the same floor because their resource "
                "timelines are identical before this demand begins."
            )
        else:
            better = "encounter-aware" if aware_entry > base_entry else "baseline"
            print(
                f"Reserve boundary: {better} enters with {abs(aware_entry - base_entry):,} more Magicka; "
                "reserve policy can therefore distinguish the plans before the mechanic."
            )

    print()
    print(
        "Interpretation: reserve eligibility changes only when the caller-supplied floor exceeds the "
        "Magicka actually available immediately before demand entry. A later schedule improvement "
        "cannot repair an entry reserve that was already missing."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
