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
            "Show reviewed pure-class Class Mastery routes and conservative reviewed subclass lower bounds."
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
    subclass_lower_bounds = [
        row
        for row in result.routes
        if row.route_kind is ExtremeClassRouteKind.SUBCLASS
        and row.projected_delta is not None
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
    print(f"Subclass routes with reviewed single-line lower bounds: {len(subclass_lower_bounds)}")
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
        print("No reviewed subclass class-line lower bound is currently numeric for this objective.")
    else:
        print("Top reviewed subclass lower bounds:")
        for row in sorted(
            subclass_lower_bounds,
            key=lambda item: (
                -(item.projected_delta or 0.0),
                item.base_class.value,
                item.equipped_skill_lines,
            ),
        )[:12]:
            lines = ", ".join(row.equipped_skill_lines)
            reviewed = ", ".join(row.reviewed_line_ids) or "none"
            print(
                f"  {row.base_class.value:13s} | delta >= {row.projected_delta:g} | "
                f"reviewed {reviewed} | {lines}"
            )

    print()
    print(
        "Boundary: pure deltas cover only reviewed Class Mastery contributions. Subclass numeric values are "
        "conservative single-line lower bounds, not final scores: BFF does not yet sum competing active-bar "
        "slot effects or assume unreviewed lines contribute zero. Every subclass route therefore remains "
        "globally unresolved until the full borrowed-line skill/passive search is complete."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
