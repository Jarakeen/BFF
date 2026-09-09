from __future__ import annotations

"""Stage-2 targeted whole-build audit for Extreme maximum-heal finalists.

Stage 1 exhaustively screens legal route/heal/slot combinations on the saved
build with zero mutation passes. This command then selects a route-diverse set
of top healing-event families and runs the expensive whole-build optimizer only
on those concrete screened entries. It is read-only and remains a lower-bound
shortlist search rather than a global-proof claim.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.build_service import BuildService
from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogService,
)
from services.extreme_baseline_canonical_actual_heal_optimization_service import (
    ExtremeBaselineCanonicalActualHealOptimizationService,
)
from services.extreme_baseline_route_aware_max_health_optimization_service import (
    ExtremeBaselineRouteAwareMaxHealthOptimizationService,
)
from services.extreme_maximum_healing_event_class_route_catalog_service import (
    ExtremeMaximumHealingEventClassRouteCatalogService,
)
from services.extreme_maximum_healing_event_finalist_optimization_service import (
    ExtremeMaximumHealingEventFinalistOptimizationService,
)
from services.extreme_maximum_healing_event_uncertainty_bound_service import (
    ExtremeMaximumHealingEventUncertaintyBoundService,
)
from services.extreme_sorcerer_blood_magic_actual_heal_service import (
    ExtremeSorcererBloodMagicActualHealService,
)
from services.extreme_sorcerer_blood_magic_class_route_catalog_service import (
    ExtremeSorcererBloodMagicClassRouteCatalogService,
)
from tools.audit_extreme_maximum_healing_event import _find_build, _format_entry

DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _screen(build, *, database_path: Path, builds_path: Path, active_bar: str, include_base_class_changes: bool):
    ordinary = ExtremeActualHealClassRouteCatalogService(
        database_path=database_path,
        optimizer=ExtremeBaselineCanonicalActualHealOptimizationService(),
    )
    blood_magic = ExtremeSorcererBloodMagicClassRouteCatalogService(
        database_path=database_path,
        blood_magic=ExtremeSorcererBloodMagicActualHealService(
            optimizer=ExtremeBaselineRouteAwareMaxHealthOptimizationService(
                database_path=database_path,
                builds_path=builds_path,
            )
        ),
    )
    service = ExtremeMaximumHealingEventClassRouteCatalogService(
        ordinary=ordinary,
        blood_magic=blood_magic,
    )
    return service.rank(
        build,
        active_bar=active_bar,
        max_passes=0,
        include_base_class_changes=include_base_class_changes,
    )


def audit(
    *,
    build_name: str,
    database_path: Path,
    builds_path: Path,
    active_bar: str,
    include_base_class_changes: bool,
    max_passes: int,
    max_families: int,
    routes_per_family: int,
    top: int,
) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1
    if not builds_path.exists():
        print(f"Build file not found: {builds_path}")
        return 1

    try:
        build = _find_build(tuple(BuildService(builds_path).load().Members), build_name)
    except ValueError as exc:
        print(str(exc))
        return 2

    print("STAGE 1: screening legal route/heal/slot candidates...")
    screening = _screen(
        build,
        database_path=database_path,
        builds_path=builds_path,
        active_bar=active_bar,
        include_base_class_changes=include_base_class_changes,
    )

    full_ordinary = ExtremeActualHealClassRouteCatalogService(database_path=database_path)
    full_blood = ExtremeSorcererBloodMagicClassRouteCatalogService(database_path=database_path)
    service = ExtremeMaximumHealingEventFinalistOptimizationService(
        ordinary=full_ordinary,
        blood_magic=full_blood,
    )

    print(
        "STAGE 2: optimizing route-diverse finalists "
        f"(families={max_families}, routes/family={routes_per_family}, passes={max_passes})..."
    )

    def _progress(index, total, finalist):
        route = ", ".join(finalist.route.equipped_skill_lines)
        print(
            f"  [{index}/{total}] {finalist.source_name} | "
            f"{finalist.source_kind} | route: {route} | slot {finalist.slotted_index + 1}",
            flush=True,
        )

    result = service.optimize(
        build,
        screening,
        active_bar=active_bar,
        max_passes=max_passes,
        max_families=max_families,
        routes_per_family=routes_per_family,
        progress=_progress,
    )
    bounds = ExtremeMaximumHealingEventUncertaintyBoundService()

    print("====================================================")
    print(" EXTREME MAXIMUM HEALING EVENT - STAGE 2")
    print("====================================================")
    print(f"Character: {build.Name or '(unnamed)'}")
    print(f"Build: {build.BuildName or '(unnamed)'}")
    print(f"Active bar: {active_bar}")
    print("Boundary: targeted shortlist whole-build optimization; NOT a global maximum proof")
    print(f"Stage-1 scored entries: {result.selection.screened_scored_entries}")
    print(f"Exact duplicates removed: {result.selection.exact_duplicates_removed}")
    print(f"Represented heal families: {result.selection.represented_families}")
    print(f"Selected finalists: {len(result.selection.finalists)}")
    print(f"Successfully optimized finalists: {len(result.entries)}")
    print("Global maximum proven: NO")

    leader = result.best_scored
    print("\nCURRENT NUMERIC LEADER")
    if leader is None or leader.event_value is None:
        print("  No Stage-2 finalist produced a scored maximum-event value.")
    else:
        print(f"  {leader.source_name}")
        print(f"  Modeled event: {float(leader.event_value):.3f} ({leader.event_kind})")
        print(f"  Evidence complete: {'YES' if leader.mechanic_complete else 'NO'}")
        print(f"  Route: {', '.join(leader.route.equipped_skill_lines)}")
        print(f"  Active-bar slot: {leader.slotted_index + 1}")
        if leader.trace.recipient_scopes or leader.trace.recipient_keys:
            print(
                "  Recipient: "
                + ", ".join(leader.trace.recipient_scopes)
                + " / "
                + ", ".join(leader.trace.recipient_keys)
            )
        if leader.trace.event_keys:
            print("  Event identity: " + ", ".join(leader.trace.event_keys))

    print("\nUNRESOLVED CEILING THREATS")
    leader_value = None if leader is None else leader.event_value
    threats = []
    if leader_value is not None:
        for entry in result.entries:
            bound = bounds.bound(entry)
            if (
                bound.lower_bound is not None
                and bound.upper_bound is not None
                and bound.upper_bound > bound.lower_bound + 1e-9
                and bound.upper_bound > float(leader_value) + 1e-9
            ):
                threats.append((entry, bound))
    if not threats:
        print("  None among the optimized finalists with currently modeled numeric bounds.")
    else:
        for entry, bound in threats:
            print(
                f"  - {entry.source_name}: modeled {bound.lower_bound:.3f}; "
                f"source-supported ceiling {bound.upper_bound:.3f}"
            )
            if bound.reason:
                print(f"    reason: {bound.reason}")
        print("  Result: current numeric leader cannot yet be proven against these ceilings.")

    if result.errors:
        print("\nFINALIST ERRORS")
        for message in result.errors:
            print(f"  - {message}")

    print("\nTOP OPTIMIZED FINALISTS")
    for index, entry in enumerate(result.entries[: max(0, int(top))], 1):
        for line in _format_entry(entry, index=index):
            print(line)
        bound = bounds.bound(entry)
        if (
            bound.lower_bound is not None
            and bound.upper_bound is not None
            and bound.upper_bound > bound.lower_bound + 1e-9
        ):
            print(f"     source-supported ceiling: {bound.upper_bound:.3f}")

    print("\nREMAINING BOUNDARIES")
    for item in result.omitted_scope:
        print(f"  - {item}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, help="Saved BuildName to audit")
    parser.add_argument("--database", type=Path, default=Path(DEFAULT_DATABASE))
    parser.add_argument("--builds", type=Path, default=Path(DEFAULT_BUILDS))
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    parser.add_argument("--include-base-class-changes", action="store_true")
    parser.add_argument("--max-passes", type=int, default=4)
    parser.add_argument("--families", type=int, default=5)
    parser.add_argument("--routes-per-family", type=int, default=3)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()
    return audit(
        build_name=args.build,
        database_path=args.database,
        builds_path=args.builds,
        active_bar=args.active_bar,
        include_base_class_changes=args.include_base_class_changes,
        max_passes=max(1, args.max_passes),
        max_families=max(1, args.families),
        routes_per_family=max(1, args.routes_per_family),
        top=max(0, args.top),
    )


if __name__ == "__main__":
    raise SystemExit(main())
