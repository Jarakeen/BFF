from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from minmax.rotation_plan import RotationActionKind
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
from services.rotation_sustain_service import RotationSustainService
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


def _action_rows(plan):
    return tuple(
        (
            float(action.time_seconds),
            action.kind.value,
            str(action.bar or ""),
            str(action.name or ""),
        )
        for action in plan.actions
        if action.kind is not RotationActionKind.LIGHT_ATTACK
    )


def _action_counter(plan) -> Counter[tuple[str, str, str]]:
    return Counter(
        (action.kind.value, str(action.bar or ""), str(action.name or ""))
        for action in plan.actions
        if action.kind is not RotationActionKind.LIGHT_ATTACK
    )


def _skill_times(plan) -> dict[str, tuple[float, ...]]:
    result: dict[str, list[float]] = defaultdict(list)
    for action in plan.actions:
        if action.kind not in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
            continue
        if not action.name:
            continue
        result[str(action.name)].append(float(action.time_seconds))
    return {name: tuple(times) for name, times in result.items()}


def _cost_totals(sustain) -> dict[str, tuple[int, int]]:
    counts: Counter[str] = Counter()
    totals: Counter[str] = Counter()
    for event in sustain.run.action_cost_events:
        counts[event.source] += 1
        totals[event.source] += int(event.amount)
    return {source: (counts[source], totals[source]) for source in sorted(totals)}


def _print_skill_schedule_diff(base_plan, candidate_plan) -> None:
    base = _skill_times(base_plan)
    candidate = _skill_times(candidate_plan)
    names = sorted(set(base) | set(candidate), key=str.casefold)
    changed = [name for name in names if base.get(name, ()) != candidate.get(name, ())]
    if not changed:
        print("  none")
        return
    for name in changed:
        before = ", ".join(f"{value:g}" for value in base.get(name, ())) or "none"
        after = ", ".join(f"{value:g}" for value in candidate.get(name, ())) or "none"
        print(f"  {name}: {before} -> {after}")


def _print_count_diff(base_plan, candidate_plan) -> None:
    base = _action_counter(base_plan)
    candidate = _action_counter(candidate_plan)
    keys = sorted(set(base) | set(candidate))
    changed = [key for key in keys if base[key] != candidate[key]]
    if not changed:
        print("  none")
        return
    for kind, bar, name in changed:
        print(
            f"  {kind:12s} | {bar or '-':5s} | {name or '(unnamed)':28s} | "
            f"{base[(kind, bar, name)]} -> {candidate[(kind, bar, name)]}"
        )


def _print_cost_diff(base_sustain, candidate_sustain) -> None:
    base = _cost_totals(base_sustain)
    candidate = _cost_totals(candidate_sustain)
    names = sorted(set(base) | set(candidate), key=str.casefold)
    changed = [name for name in names if base.get(name, (0, 0)) != candidate.get(name, (0, 0))]
    if not changed:
        print("  none")
        return
    for name in changed:
        b_count, b_cost = base.get(name, (0, 0))
        c_count, c_cost = candidate.get(name, (0, 0))
        print(
            f"  {name:28s} | casts {b_count:2d}->{c_count:2d} | "
            f"Magicka {b_cost:6d}->{c_cost:6d} | delta {c_cost - b_cost:+6d}"
        )


def _first_resource_divergence(base_sustain, candidate_sustain):
    base_events = base_sustain.run.timeline.events
    candidate_events = candidate_sustain.run.timeline.events
    limit = min(len(base_events), len(candidate_events))
    for index in range(limit):
        before = base_events[index]
        after = candidate_events[index]
        signature_before = (
            float(before.time_seconds),
            before.kind.value,
            before.source,
            int(before.after),
        )
        signature_after = (
            float(after.time_seconds),
            after.kind.value,
            after.source,
            int(after.after),
        )
        if signature_before != signature_after:
            return index, before, after
    if len(base_events) != len(candidate_events):
        return limit, None, None
    return None


def _project_plan(
    *,
    raid_dps: float,
    guide,
    difficulty: str,
    seed_plan,
    refinement_service,
    priorities,
    refresh_leads,
    lead_seconds: float,
    window_seconds: float,
):
    thresholds = EncounterHealthThresholdProjectionService().project(
        guide=guide,
        difficulty=difficulty,
        damage_segments=(
            RaidDamageSegment(
                0.0,
                None,
                float(raid_dps),
                "caller-supplied constant raid DPS diagnosis assumption",
            ),
        ),
    )
    phase_2 = next(
        point
        for point in thresholds.points
        if point.fact_key == "phase_2" and abs(point.threshold_fraction - 0.70) <= 1e-9
    )
    demands = EncounterThresholdRotationDemandService().project(
        thresholds=thresholds,
        policies=(
            EncounterThresholdRotationDemandPolicy(
                fact_key="phase_2",
                threshold_fraction=0.70,
                kind=RotationDemandKind.HEALING,
                pattern=RotationDemandPattern.BURST,
                lead_seconds=float(lead_seconds),
                window_seconds=float(window_seconds),
                target_count=12,
                name=_DEMAND_NAME,
            ),
        ),
    )
    if not demands.demands:
        details = "; ".join(demands.unresolved) or "no projected demand"
        raise RuntimeError(f"could not project healer demand at {raid_dps:,.0f} DPS: {details}")
    demand = demands.demands[0]
    plan = refinement_service.refine(
        seed_plan,
        priorities=priorities,
        demands=(demand,),
        demand_refresh_leads=refresh_leads,
    ).plan
    return phase_2, demand, plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose why representative Xalvakka healer opportunity bands change "
            "DF Healer action counts and Magicka differently."
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
        help="representative DPS samples to compare with the same base plan",
    )
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--lead-seconds", type=float, default=3.0)
    parser.add_argument("--window-seconds", type=float, default=2.0)
    parser.add_argument("--anticipation-seconds", type=float, default=3.0)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    if any(float(value) <= 0 for value in args.raid_dps):
        raise ValueError("all --raid-dps values must be positive")

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
    base_metrics = _plan_metrics(build=build, plan=base_plan, database_path=database_path)

    print("=" * 116)
    print(" PHASE 13 XALVAKKA HEALER OPPORTUNITY-BAND COST DIAGNOSIS")
    print("=" * 116)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Encounter: {guide.name} ({guide.encounter_id}) | Difficulty: {args.difficulty}")
    print(
        "Boundary: raid DPS and healer anticipation are audit assumptions; all resource costs "
        "come from the canonical Phase 4 sustain pipeline"
    )

    for raid_dps in args.raid_dps:
        phase_2, demand, plan = _project_plan(
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
        sustain = sustain_service.evaluate(
            build=build,
            plan=plan,
            resource=ResourceType.MAGICKA,
        )
        metrics = _plan_metrics(build=build, plan=plan, database_path=database_path)

        print()
        print("-" * 116)
        print(
            f"{float(raid_dps):,.0f} RAID DPS | 70% at {float(phase_2.time_seconds):.2f}s | "
            f"prep {demand.start_seconds:.2f}-{demand.end_seconds:.2f}s"
        )
        print(
            "Resource delta vs base: "
            f"minimum {int(metrics['minimum_magicka']) - int(base_metrics['minimum_magicka']):+d}, "
            f"ending {int(metrics['ending_magicka']) - int(base_metrics['ending_magicka']):+d}, "
            f"waits {int(metrics['waits']) - int(base_metrics['waits']):+d}"
        )

        print("\nSKILL SCHEDULE CHANGES")
        _print_skill_schedule_diff(base_plan, plan)

        print("\nACTION COUNT CHANGES")
        _print_count_diff(base_plan, plan)

        print("\nMAGICKA COST CHANGES")
        _print_cost_diff(base_sustain, sustain)

        divergence = _first_resource_divergence(base_sustain, sustain)
        print("\nFIRST RESOURCE TIMELINE DIVERGENCE")
        if divergence is None:
            print("  none")
        else:
            index, before, after = divergence
            if before is None or after is None:
                print(f"  event count diverges after shared event index {index}")
            else:
                print(
                    f"  event {index}: base {before.time_seconds:g}s {before.kind.value} "
                    f"{before.source!r} -> {before.after}; candidate "
                    f"{after.time_seconds:g}s {after.kind.value} {after.source!r} -> {after.after}"
                )

    print()
    print(
        "Interpretation: harmful/helpful labels are consequences of the resulting whole action "
        "and cost sequence. This audit shows the concrete cast-count and canonical-cost differences "
        "rather than assigning a fixed penalty or bonus to early refresh itself."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
