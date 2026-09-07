from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.healer_ability_priority import HealerDemandTagPriorities, HealerTagPriority
from minmax.healer_rotation_policy import HealerRotationTag
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.encounter_boss_guide import EncounterBossGuideService
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjectionService,
)
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
    EncounterThresholdRotationDemandService,
)
from services.healer_rotation_priority_service import HealerRotationPriorityService
from services.rotation_duration_refinement_service import RotationDurationRefinementService
from tools.audit_phase13_healer_priority_comparison import (
    _BASE_PRIORITIES,
    _audit_policy_set,
    _plan_metrics,
)
from tools.audit_phase13_healer_demand_priority_comparison import _window_actions
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"
_DEMAND_NAME = "Xalvakka Phase 2 healing prep"
_DEMAND_PRIORITIES = (
    HealerDemandTagPriorities(
        demand_name=_DEMAND_NAME,
        priorities=(
            HealerTagPriority(HealerRotationTag.CRITICAL_HEALING, 0),
            HealerTagPriority(HealerRotationTag.BURST_PREPARATION, 0),
            HealerTagPriority(HealerRotationTag.SUSTAINED_HEALING, 2),
            HealerTagPriority(HealerRotationTag.SUPPORT_MAINTENANCE, 6),
            HealerTagPriority(HealerRotationTag.MOVEMENT_UTILITY, 7),
            HealerTagPriority(HealerRotationTag.DISCRETIONARY_FILLER, 9),
        ),
        reason="audit-only projected Xalvakka phase-transition healing preparation",
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare DF Healer base-priority scheduling with a healer demand window "
            "derived from Xalvakka's reviewed 70% health threshold under an explicit raid-DPS assumption."
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
    parser.add_argument("--raid-dps", type=float, default=1_500_000.0)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--lead-seconds", type=float, default=3.0)
    parser.add_argument("--window-seconds", type=float, default=2.0)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    if float(args.raid_dps) <= 0:
        raise ValueError("--raid-dps must be positive")
    if float(args.duration) <= 0:
        raise ValueError("--duration must be positive")

    database_path = Path(args.database)
    build = _load_saved_build(
        Path(args.builds),
        character=args.character,
        build_name=args.build,
    )
    guide = EncounterBossGuideService(database_path).get(args.encounter)
    threshold_projection = EncounterHealthThresholdProjectionService().project(
        guide=guide,
        difficulty=args.difficulty,
        damage_segments=(
            RaidDamageSegment(
                0.0,
                None,
                float(args.raid_dps),
                "caller-supplied constant raid DPS audit assumption",
            ),
        ),
    )
    demand_projection = EncounterThresholdRotationDemandService().project(
        thresholds=threshold_projection,
        policies=(
            EncounterThresholdRotationDemandPolicy(
                fact_key="phase_2",
                threshold_fraction=0.70,
                kind=RotationDemandKind.HEALING,
                pattern=RotationDemandPattern.BURST,
                lead_seconds=float(args.lead_seconds),
                window_seconds=float(args.window_seconds),
                target_count=12,
                name=_DEMAND_NAME,
            ),
        ),
    )
    if not demand_projection.demands:
        details = "; ".join(demand_projection.unresolved) or "no demand was projected"
        raise RuntimeError(f"Xalvakka Phase 2 demand is unavailable: {details}")
    demand = demand_projection.demands[0]

    policy_set = _audit_policy_set(build, database_path=database_path)
    priority_projection = HealerRotationPriorityService().project(
        policy_set=policy_set,
        base_priorities=_BASE_PRIORITIES,
        demand_priorities=_DEMAND_PRIORITIES,
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
    demand_plan = refinement_service.refine(
        seed_plan,
        priorities=priority_projection.priority_list,
        demands=(demand,),
    ).plan

    base_metrics = _plan_metrics(
        build=build,
        plan=base_plan,
        database_path=database_path,
    )
    demand_metrics = _plan_metrics(
        build=build,
        plan=demand_plan,
        database_path=database_path,
    )

    phase_2 = next(
        point
        for point in threshold_projection.points
        if point.fact_key == "phase_2" and abs(point.threshold_fraction - 0.70) <= 1e-9
    )

    print("=" * 104)
    print(" PHASE 13 XALVAKKA PROJECTED-THRESHOLD HEALER ROTATION COMPARISON")
    print("=" * 104)
    print(f"Character:       {args.character}")
    print(f"Build:           {args.build}")
    print(f"Encounter:       {guide.name} ({guide.encounter_id})")
    print(f"Difficulty:      {args.difficulty}")
    print(f"Boss health:     {threshold_projection.maximum_health:,}")
    print(f"Raid DPS:        {float(args.raid_dps):,.0f} (caller supplied)")
    print(f"70% projection:  {float(phase_2.time_seconds):.2f}s")
    print(
        f"Healer prep:     {demand.start_seconds:.2f}s to {demand.end_seconds:.2f}s "
        f"({float(args.lead_seconds):g}s lead)"
    )
    print(
        "Boundary:        encounter threshold and boss health are canonical; clock time is conditional on the supplied DPS; healer policy is audit-only"
    )
    print()

    print("METRIC                     | BASE PRIORITY | XALVAKKA-AWARE | DELTA")
    print("---------------------------+---------------+----------------+----------")
    for key, label in (
        ("refresh_claims", "Refresh claims"),
        ("premature_waits", "Premature-recast waits"),
        ("waits", "WAIT actions"),
        ("displaced_beyond", "Displaced beyond horizon"),
        ("minimum_magicka", "Minimum Magicka"),
        ("ending_magicka", "Ending Magicka"),
        ("shortfall", "Total shortfall"),
    ):
        before = int(base_metrics[key])
        after = int(demand_metrics[key])
        print(f"{label:27s}| {before:13d} | {after:14d} | {after - before:+8d}")
    print()

    context_start = max(0.0, demand.start_seconds - 3.0)
    context_end = min(float(args.duration) + 0.001, demand.end_seconds + 4.0)
    print(f"ACTIONS {context_start:.2f}s-{context_end:.2f}s")
    print("-" * 104)
    print("BASE PRIORITY")
    for action in _window_actions(base_plan, start=context_start, end=context_end):
        print(
            f"  {float(action.time_seconds):5.1f}s | {(action.bar or '-'):5s} | "
            f"{action.kind.value:12s} | {action.name or ''}"
        )
    print("XALVAKKA-AWARE")
    for action in _window_actions(demand_plan, start=context_start, end=context_end):
        print(
            f"  {float(action.time_seconds):5.1f}s | {(action.bar or '-'):5s} | "
            f"{action.kind.value:12s} | {action.name or ''}"
        )

    print()
    print(
        "Interpretation: any schedule difference is caused by an explicit healer-priority override "
        "during a window whose placement comes from Xalvakka's reviewed 70% threshold plus the supplied raid-DPS trajectory."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
