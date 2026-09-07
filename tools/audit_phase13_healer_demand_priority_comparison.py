from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.healer_ability_priority import (
    HealerDemandTagPriorities,
    HealerTagPriority,
)
from minmax.healer_rotation_policy import HealerRotationTag
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.healer_rotation_priority_service import HealerRotationPriorityService
from services.rotation_duration_refinement_service import RotationDurationRefinementService
from tools.audit_phase13_healer_priority_comparison import (
    _BASE_PRIORITIES,
    _audit_policy_set,
    _plan_metrics,
)
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"
_DEMAND_NAME = "Synthetic Burst Healing Window"
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
        reason="audit-only burst-healing demand override",
    ),
)


def _window_actions(plan, *, start: float, end: float):
    return tuple(
        action
        for action in plan.actions
        if start <= float(action.time_seconds) < end
        and action.kind.value in {"skill", "wait", "heavy_attack", "bar_swap"}
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare one real saved healer rotation using fixed base priorities versus "
            "the same priorities with an explicit synthetic burst-demand override."
        )
    )
    parser.add_argument("--character", default="Magrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--demand-start", type=float, default=24.0)
    parser.add_argument("--demand-end", type=float, default=30.0)
    args = parser.parse_args()

    demand = RotationDemandWindow(
        name=_DEMAND_NAME,
        start_seconds=float(args.demand_start),
        end_seconds=float(args.demand_end),
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    build = _load_saved_build(
        Path(args.builds),
        character=args.character,
        build_name=args.build,
    )
    database_path = Path(args.database)
    policy_set = _audit_policy_set(build, database_path=database_path)
    projection = HealerRotationPriorityService().project(
        policy_set=policy_set,
        base_priorities=_BASE_PRIORITIES,
        demand_priorities=_DEMAND_PRIORITIES,
    )

    refinement_service = RotationDurationRefinementService(database_path=database_path)
    generator = RotationGenerationSupport(duration_refinement=refinement_service)
    request = RotationGenerationRequest(
        duration_seconds=float(args.duration),
        ability_priorities=projection.entries,
    )
    definition = generator.build_definition(build=build, request=request)
    seed_plan = generator.planner.build_plan(definition, build)

    base_plan = refinement_service.refine(
        seed_plan,
        priorities=projection.priority_list,
    ).plan
    demand_plan = refinement_service.refine(
        seed_plan,
        priorities=projection.priority_list,
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

    print("=" * 94)
    print(" PHASE 13 REAL HEALER DEMAND-PRIORITY COMPARISON")
    print("=" * 94)
    print(f"Character: {args.character}")
    print(f"Build:     {args.build}")
    print(f"Duration:  {float(args.duration):g}s")
    print(
        f"Demand:    {_DEMAND_NAME} | {demand.start_seconds:g}s to {demand.end_seconds:g}s"
    )
    print("Boundary:  synthetic audit window and explicit audit-only healer tags; not encounter truth")
    print()

    print("DEMAND PRIORITY EFFECT")
    print("----------------------")
    base_resolved = {
        item.entry.skill_name: item.effective_priority
        for item in projection.priority_list.resolve()
    }
    demand_resolved = {
        item.entry.skill_name: item.effective_priority
        for item in projection.priority_list.resolve(demand)
    }
    for item in projection.priority_list.resolve(demand):
        before = base_resolved[item.entry.skill_name]
        after = demand_resolved[item.entry.skill_name]
        marker = "*" if before != after else " "
        print(
            f"{marker} {item.entry.bar:5s} slot {item.entry.slot} | "
            f"{item.entry.skill_name:28s} | {before:2d} -> {after:2d}"
        )
    print()

    print("METRIC                     | BASE PRIORITY | DEMAND-AWARE | DELTA")
    print("---------------------------+---------------+--------------+----------")
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
        print(f"{label:27s}| {before:13d} | {after:12d} | {after - before:+8d}")
    print()

    context_start = max(0.0, demand.start_seconds - 2.0)
    context_end = min(float(args.duration) + 0.001, demand.end_seconds + 3.0)
    print(f"ACTIONS {context_start:g}s-{context_end:g}s")
    print("-" * 94)
    print("BASE PRIORITY")
    for action in _window_actions(base_plan, start=context_start, end=context_end):
        print(
            f"  {float(action.time_seconds):5.1f}s | {(action.bar or '-'):5s} | "
            f"{action.kind.value:12s} | {action.name or ''}"
        )
    print("DEMAND-AWARE")
    for action in _window_actions(demand_plan, start=context_start, end=context_end):
        print(
            f"  {float(action.time_seconds):5.1f}s | {(action.bar or '-'):5s} | "
            f"{action.kind.value:12s} | {action.name or ''}"
        )

    print()
    print(
        "Interpretation: the demand-aware plan should differ only where an active, named "
        "window changes explicit priority. The audit does not claim this synthetic burst "
        "window corresponds to a real encounter mechanic."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
