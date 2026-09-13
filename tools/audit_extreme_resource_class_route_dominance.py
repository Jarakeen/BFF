from __future__ import annotations

"""Audit whether one legal Extreme class route dominates the projected route frontier.

This diagnostic consumes the proof-owned class-route projection. It does not infer
new passive mechanics. A dominance candidate exists only when one retained legal
route's reviewed resource-sensitive class-line signature is a superset of every
other retained signature.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_global_search_universe_service import ExtremeGlobalSearchUniverseService
from services.extreme_resource_class_route_projection_service import (
    ExtremeResourceClassRouteProjectionService,
)


OBJECTIVES = ("max_magicka", "max_stamina")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="data/eso.db")
    parser.add_argument("--objective", choices=OBJECTIVES, default="max_magicka")
    return parser


def _identity(route) -> tuple[str, bool, tuple[str, ...]]:
    return (
        str(route.base_class.value),
        bool(route.is_subclassed),
        tuple(route.equipped_skill_lines),
    )


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    key = str(args.objective).strip().casefold()

    universe = ExtremeGlobalSearchUniverseService(database).build()
    projection = ExtremeResourceClassRouteProjectionService(database).build(
        key,
        tuple(universe.class_routes),
    )

    print("EXTREME RESOURCE CLASS ROUTE DOMINANCE")
    print(f"objective={key}")
    print(f"routes_raw={len(universe.class_routes)}")
    print(f"projection_complete={projection.projection_complete}")
    print(f"relevant_class_lines={projection.relevant_class_lines!r}")
    print(f"projected_routes={len(projection.routes)}")
    print(f"projected_signatures={projection.signatures!r}")
    print(f"unresolved={len(projection.unresolved)}")
    if projection.unresolved:
        for message in projection.unresolved:
            print(f"  unresolved: {message}")

    if not projection.projection_complete:
        print("dominance_candidate=False")
        return 0

    rows = tuple(zip(projection.routes, projection.signatures))
    candidates = []
    for route, signature in rows:
        owned = set(signature)
        if all(set(other_signature).issubset(owned) for _, other_signature in rows):
            candidates.append((route, signature))

    candidates.sort(key=lambda row: _identity(row[0]))
    print(f"dominance_candidate={bool(candidates)}")
    print(f"dominance_candidate_count={len(candidates)}")
    if candidates:
        route, signature = candidates[0]
        print(f"dominance_witness_base_class={route.base_class.value}")
        print(f"dominance_witness_subclassed={route.is_subclassed}")
        print(f"dominance_witness_lines={tuple(route.equipped_skill_lines)!r}")
        print(f"dominance_witness_signature={signature!r}")

    print("projected_route_rows=")
    for route, signature in rows:
        print(
            "  "
            f"base={route.base_class.value} subclassed={route.is_subclassed} "
            f"lines={tuple(route.equipped_skill_lines)!r} signature={signature!r}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
