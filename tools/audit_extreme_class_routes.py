from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.extreme_class_route_comparison_service import (
    ExtremeClassRouteComparisonService,
    ExtremeClassRouteKind,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Show reviewed pure-class Class Mastery routes and canonical-bar-backed subclass lower bounds."
        )
    )
    parser.add_argument("objective")
    parser.add_argument("--reference-value", type=float, default=None)
    parser.add_argument("--higher-max-resource", type=float, default=None)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    result = ExtremeClassRouteComparisonService(args.database).compare(
        args.objective,
        reference_value=args.reference_value,
        higher_max_resource=args.higher_max_resource,
    )

    pure = [row for row in result.routes if row.route_kind is ExtremeClassRouteKind.PURE_MASTERY]
    subclasses = [row for row in result.routes if row.route_kind is ExtremeClassRouteKind.SUBCLASS]
    subclass_lower_bounds = [row for row in subclasses if row.projected_delta is not None]
    pending_bar = [
        row for row in subclasses
        if row.score_status == "pending_canonical_bar_materialization"
    ]

    print("=" * 100)
    print(" EXTREME BUILD CLASS ROUTE REVIEW")
    print("=" * 100)
    print(f"Objective: {result.objective_key}")
    print(f"Reference value: {args.reference_value if args.reference_value is not None else 'not supplied'}")
    print(
        "Higher Max Magicka/Stamina: "
        f"{args.higher_max_resource if args.higher_max_resource is not None else 'not supplied'}"
    )
    print(f"Reviewed pure-class routes with numeric deltas: {len(pure)}")
    print(f"Subclass routes with canonical materialized lower bounds: {len(subclass_lower_bounds)}")
    print(f"Reviewed allocations blocked by canonical bar materialization: {len(pending_bar)}")
    print(f"Legal subclass routes still globally unresolved: {result.unresolved_subclass_count}")
    print(f"Global winner allowed: {'yes' if result.can_declare_global_winner else 'NO'}")
    print()

    if not pure:
        print("No reviewed Class Mastery route currently produces a numeric delta for this objective.")
    else:
        print("Reviewed pure-class routes:")
        for row in sorted(pure, key=lambda item: (-(item.projected_delta or 0.0), item.base_class.value)):
            masteries = " + ".join(row.mastery_names) or "none"
            boundary = row.boundary.value if row.boundary is not None else "unresolved"
            print(
                f"  {row.base_class.value:13s} | delta {row.projected_delta:g} | "
                f"{boundary:27s} | {masteries}"
            )

    print()
    if not subclass_lower_bounds:
        print("No reviewed subclass lower bound currently has a canonical six-slot bar for this objective.")
    else:
        print("Top reviewed subclass lower bounds with concrete bars:")
        for row in sorted(
            subclass_lower_bounds,
            key=lambda item: (
                -(item.projected_delta or 0.0),
                item.base_class.value,
                item.equipped_skill_lines,
                item.slot_counts,
                item.skill_bar_names,
            ),
        )[:12]:
            lines = ", ".join(row.equipped_skill_lines)
            slots = ", ".join(f"{line}={count}" for line, count in row.slot_counts if count) or "none"
            sources = "; ".join(row.reviewed_sources) or "none"
            bar = " | ".join(row.skill_bar_names) or "unmaterialized"
            print(
                f"  {row.base_class.value:13s} | delta >= {row.projected_delta:g} | "
                f"slots {slots} | {sources} | {lines}"
            )
            print(f"      bar: {bar}")

    print()
    print(
        "Boundary: subclass numeric values now require both a reviewed six-slot allocation and a concrete "
        "canonical skill bar with five distinct non-Ultimate base families plus one Ultimate. The displayed "
        "bar proves equipability only; its morph choices are deterministic representatives, not yet an "
        "objective-optimal skill-effect search. Unreviewed skills/passives are still not assumed to contribute "
        "zero, so every subclass route remains globally unresolved until the full borrowed-line effect search "
        "is complete."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
