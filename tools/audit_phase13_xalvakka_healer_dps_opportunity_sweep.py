from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from minmax.rotation_opportunity_band import (
    RotationOpportunitySample,
    classify_rotation_opportunity_bands,
)
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
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from tools.audit_phase13_xalvakka_healer_threshold_rotation import (
    _DEMAND_NAME,
    _DEMAND_PRIORITIES,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _action_signature(plan) -> tuple[tuple[float, str, str, str], ...]:
    return tuple(
        (
            float(action.time_seconds),
            str(action.kind.value),
            str(action.bar or ""),
            str(action.name or ""),
        )
        for action in plan.actions
    )


def _skill_times(plan, skill_name: str) -> tuple[float, ...]:
    target = skill_name.casefold()
    return tuple(
        float(action.time_seconds)
        for action in plan.actions
        if action.name and action.name.casefold() == target
    )


def _nearest_time(times: tuple[float, ...], target: float) -> float | None:
    if not times:
        return None
    return min(times, key=lambda value: (abs(value - target), value))


def _dps_values(start: float, stop: float, step: float) -> tuple[float, ...]:
    if start <= 0 or stop <= 0 or step <= 0:
        raise ValueError("DPS sweep start, stop, and step must be positive")
    if stop < start:
        raise ValueError("DPS sweep stop must be greater than or equal to start")
    values = []
    current = float(start)
    epsilon = abs(step) * 1e-9
    while current <= float(stop) + epsilon:
        values.append(current)
        current += float(step)
    return tuple(values)


def _outcome_label(*, minimum_delta: int, ending_delta: int, waits_delta: int) -> str:
    if minimum_delta == 0 and ending_delta == 0 and waits_delta == 0:
        return "neutral"
    if minimum_delta >= 0 and ending_delta >= 0 and (minimum_delta > 0 or ending_delta > 0):
        return "helpful"
    if minimum_delta <= 0 and ending_delta <= 0 and (minimum_delta < 0 or ending_delta < 0):
        return "harmful"
    return "mixed"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep caller-supplied raid DPS and show where Xalvakka's projected 70% "
            "Phase 2 window does or does not create a useful DF Healer anticipation opportunity."
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
    parser.add_argument("--dps-start", type=float, default=1_200_000.0)
    parser.add_argument("--dps-stop", type=float, default=2_400_000.0)
    parser.add_argument("--dps-step", type=float, default=100_000.0)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--lead-seconds", type=float, default=3.0)
    parser.add_argument("--window-seconds", type=float, default=2.0)
    parser.add_argument("--anticipation-seconds", type=float, default=3.0)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    if float(args.duration) <= 0:
        raise ValueError("--duration must be positive")
    if float(args.lead_seconds) < 0:
        raise ValueError("--lead-seconds must be non-negative")
    if float(args.window_seconds) <= 0:
        raise ValueError("--window-seconds must be positive")
    if float(args.anticipation_seconds) < 0:
        raise ValueError("--anticipation-seconds must be non-negative")

    dps_values = _dps_values(args.dps_start, args.dps_stop, args.dps_step)
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
    base_signature = _action_signature(base_plan)
    base_metrics = _plan_metrics(
        build=build,
        plan=base_plan,
        database_path=database_path,
    )
    base_seed_times = _skill_times(base_plan, "Budding Seeds")
    band_samples: list[RotationOpportunitySample[float, tuple[str, bool]]] = []

    print("=" * 126)
    print(" PHASE 13 XALVAKKA HEALER DPS OPPORTUNITY-BAND SWEEP")
    print("=" * 126)
    print(f"Character:    {args.character} | Build: {args.build}")
    print(f"Encounter:    {guide.name} ({guide.encounter_id}) | Difficulty: {args.difficulty}")
    print(
        f"DPS sweep:    {dps_values[0]:,.0f} to {dps_values[-1]:,.0f} by {float(args.dps_step):,.0f}"
    )
    print(
        f"Policy:       70% threshold, {float(args.lead_seconds):g}s prep lead, "
        f"{float(args.window_seconds):g}s post-threshold window, Budding Seeds up to "
        f"{float(args.anticipation_seconds):g}s early"
    )
    print(
        "Boundary:     raid DPS and healer anticipation are audit assumptions; threshold and boss health remain canonical"
    )
    print()
    print(
        "RAID DPS   | 70% TIME | PREP WINDOW       | PLAN | BUDDING SEEDS | MIN MAG Δ | END MAG Δ | WAITS Δ"
    )
    print(
        "-----------+----------+-------------------+------+---------------+-----------+-----------+--------"
    )

    for raid_dps in dps_values:
        thresholds = EncounterHealthThresholdProjectionService().project(
            guide=guide,
            difficulty=args.difficulty,
            damage_segments=(
                RaidDamageSegment(
                    0.0,
                    None,
                    float(raid_dps),
                    "caller-supplied constant raid DPS sweep assumption",
                ),
            ),
        )
        phase_2 = next(
            (
                point
                for point in thresholds.points
                if point.fact_key == "phase_2"
                and abs(point.threshold_fraction - 0.70) <= 1e-9
            ),
            None,
        )
        if phase_2 is None or not phase_2.resolved or phase_2.time_seconds is None:
            print(f"{raid_dps:10,.0f} | unresolved")
            continue

        demand_projection = EncounterThresholdRotationDemandService().project(
            thresholds=thresholds,
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
            print(f"{raid_dps:10,.0f} | {float(phase_2.time_seconds):8.2f}s | unresolved demand")
            continue
        demand = demand_projection.demands[0]

        demand_plan = refinement_service.refine(
            seed_plan,
            priorities=priority_projection.priority_list,
            demands=(demand,),
            demand_refresh_leads=refresh_leads,
        ).plan
        metrics = _plan_metrics(
            build=build,
            plan=demand_plan,
            database_path=database_path,
        )
        changed = _action_signature(demand_plan) != base_signature
        demand_seed_times = _skill_times(demand_plan, "Budding Seeds")
        event_time = float(phase_2.time_seconds)
        base_nearest = _nearest_time(base_seed_times, event_time)
        demand_nearest = _nearest_time(demand_seed_times, event_time)
        if base_nearest is None or demand_nearest is None:
            seed_text = "unresolved"
        elif abs(base_nearest - demand_nearest) <= 1e-9:
            seed_text = f"{demand_nearest:4.0f}s same"
        else:
            seed_text = f"{base_nearest:4.0f}->{demand_nearest:2.0f}s"

        minimum_delta = int(metrics["minimum_magicka"]) - int(base_metrics["minimum_magicka"])
        ending_delta = int(metrics["ending_magicka"]) - int(base_metrics["ending_magicka"])
        waits_delta = int(metrics["waits"]) - int(base_metrics["waits"])
        outcome = _outcome_label(
            minimum_delta=minimum_delta,
            ending_delta=ending_delta,
            waits_delta=waits_delta,
        )
        band_samples.append(
            RotationOpportunitySample(
                value=float(raid_dps),
                signature=(outcome, changed),
            )
        )

        print(
            f"{raid_dps:10,.0f} | {event_time:8.2f}s | "
            f"{demand.start_seconds:6.2f}-{demand.end_seconds:6.2f}s | "
            f"{'YES' if changed else ' no':4s} | {seed_text:13s} | "
            f"{minimum_delta:+9d} | {ending_delta:+9d} | {waits_delta:+6d}"
        )

    bands = classify_rotation_opportunity_bands(band_samples)
    if bands:
        print()
        print("OPPORTUNITY BANDS")
        print("-----------------")
        print("DPS RANGE              | OUTCOME  | PLAN CHANGED | SAMPLES")
        print("-----------------------+----------+--------------+--------")
        for band in bands:
            outcome, changed = band.signature
            if band.start_value == band.end_value:
                dps_range = f"{band.start_value:,.0f}"
            else:
                dps_range = f"{band.start_value:,.0f}-{band.end_value:,.0f}"
            print(
                f"{dps_range:23s}| {outcome:8s} | "
                f"{'yes' if changed else 'no':12s} | {band.sample_count:7d}"
            )

    print()
    print(
        "Interpretation: contiguous rows with the same outcome and plan-change state form one "
        "opportunity band. Abrupt changes show where the moving health-triggered mechanic crosses "
        "a discrete rotation boundary such as a bar swap, due-refresh seam, or legal anticipation slot."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
