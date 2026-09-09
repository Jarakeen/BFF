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
from services.extreme_maximum_heal_unresolved_relevance_service import (
    ExtremeMaximumHealUnresolvedRelevanceService,
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


def _decisive_blockers(entries, omitted_scope):
    """Return unresolved mechanics/search gaps that can still change the leader."""
    priorities = (
        (
            "winner magnitude",
            "Blood of the Elder Dragon maximum-event scaling requires component-specific missing-Health proof for the winning recipient",
        ),
    )
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for label, needle in priorities:
        if any(needle in tuple(entry.unresolved) for entry in entries):
            key = (label, needle)
            if key not in seen:
                seen.add(key)
                found.append(key)

    boundary_priorities = (
        "proof that a lower baseline family within an already represented source kind cannot overtake after whole-build mutation",
        "whole-build optimization outside the selected Stage-2 finalist families/routes",
        "base-class change",
    )
    for boundary in boundary_priorities:
        if boundary in tuple(omitted_scope):
            key = ("search proof", boundary)
            if key not in seen:
                seen.add(key)
                found.append(key)
    return tuple(found)


def _setup_prerequisites(entries, relevance):
    values: list[str] = []
    for entry in entries:
        values.extend(relevance.classify(entry.unresolved).setup_prerequisites)
    return tuple(dict.fromkeys(values))


def _format_objective_entry(entry, *, index: int, relevance):
    classified = relevance.classify(entry.unresolved)
    ambient = set(classified.ambient)
    prerequisites = set(classified.setup_prerequisites)
    lines = []
    for line in _format_entry(entry, index=index):
        stripped = line.strip()
        if stripped.startswith("unresolved:"):
            message = stripped.split("unresolved:", 1)[1].strip()
            if message in ambient or message in prerequisites:
                continue
        if stripped.startswith("evidence:"):
            lines.append(
                f"     objective evidence: {'complete' if classified.objective_complete else 'incomplete'}"
            )
            continue
        lines.append(line)
    for prerequisite in classified.setup_prerequisites:
        lines.append(f"     setup prerequisite: {prerequisite}")
    if classified.ambient:
        lines.append(f"     ambient diagnostics omitted: {len(classified.ambient)}")
    return tuple(lines)


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
    relevance = ExtremeMaximumHealUnresolvedRelevanceService()

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
        leader_relevance = relevance.classify(leader.unresolved)
        print(f"  {leader.source_name}")
        print(f"  Modeled event: {float(leader.event_value):.3f} ({leader.event_kind})")
        print(f"  Objective evidence complete: {'YES' if leader_relevance.objective_complete else 'NO'}")
        if leader_relevance.setup_prerequisites:
            print(
                "  Achievable setup prerequisites: "
                + str(len(leader_relevance.setup_prerequisites))
            )
        if leader_relevance.ambient:
            print(f"  Ambient build diagnostics ignored for this objective: {len(leader_relevance.ambient)}")
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
    threat_families: dict[tuple, tuple[object, object, int]] = {}
    if leader_value is not None:
        for entry in result.entries:
            bound = bounds.bound(entry)
            if (
                bound.lower_bound is not None
                and bound.upper_bound is not None
                and bound.upper_bound > bound.lower_bound + 1e-9
                and bound.upper_bound > float(leader_value) + 1e-9
            ):
                key = (
                    entry.source_kind,
                    entry.source_name.casefold(),
                    float(bound.lower_bound),
                    float(bound.upper_bound),
                    str(bound.reason or ""),
                )
                if key in threat_families:
                    original_entry, original_bound, count = threat_families[key]
                    threat_families[key] = (original_entry, original_bound, count + 1)
                else:
                    threat_families[key] = (entry, bound, 1)
    if not threat_families:
        print("  None among the optimized finalists with currently modeled numeric bounds.")
    else:
        for entry, bound, route_count in threat_families.values():
            suffix = f" across {route_count} optimized routes" if route_count > 1 else ""
            print(
                f"  - {entry.source_name}: modeled {bound.lower_bound:.3f}; "
                f"source-supported ceiling {bound.upper_bound:.3f}{suffix}"
            )
            if bound.reason:
                print(f"    reason: {bound.reason}")
        print("  Result: current numeric leader cannot yet be proven against these ceilings.")

    prerequisites = _setup_prerequisites(result.entries, relevance)
    print("\nACHIEVABLE SETUP PREREQUISITES")
    if not prerequisites:
        print("  None among currently modeled finalists.")
    else:
        for message in prerequisites:
            print(f"  - {message}")
        print("  These are setup requirements for an Extreme achievable maximum, not live-snapshot proof blockers.")

    blockers = _decisive_blockers(result.entries, result.omitted_scope)
    print("\nDECISIVE PROOF BLOCKERS")
    if not blockers:
        print("  None among currently modeled finalist mechanics and search boundaries.")
    else:
        for label, message in blockers:
            print(f"  - [{label}] {message}")

    if result.errors:
        print("\nFINALIST ERRORS")
        for message in result.errors:
            print(f"  - {message}")

    print("\nTOP OPTIMIZED FINALISTS")
    for index, entry in enumerate(result.entries[: max(0, int(top))], 1):
        for line in _format_objective_entry(entry, index=index, relevance=relevance):
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
