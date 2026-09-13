from __future__ import annotations

"""Close the current Max Magicka high-water racial parser boundaries by proof.

This audit does not rescore the build. It verifies that every remaining racial
boundary from the validated 107,574 high-water witness belongs to a canonical
racial-passive classification that cannot change a maximum-resource objective.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_resource_racial_boundary_relevance_service import (
    ExtremeResourceRacialBoundaryRelevanceService,
)


OBJECTIVE = "max_magicka"
DEFAULT_BOUNDARIES = (
    "Non-combat racial passive outside combat capability audit: Highborn",
    "Racial passive restores current resources or alters mitigation without changing maximum resources: Spell Recharge",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--incumbent", type=float, default=107574.0)
    parser.add_argument(
        "--boundary",
        action="append",
        help="Override observed boundary; repeat for multiple messages.",
    )
    args = parser.parse_args()

    boundaries = tuple(args.boundary or DEFAULT_BOUNDARIES)
    result = ExtremeResourceRacialBoundaryRelevanceService(Path(args.database)).build(
        OBJECTIVE,
        boundaries,
    )

    print("EXTREME MAX MAGICKA RACIAL BOUNDARY CLOSURE")
    print(f"database={Path(args.database)}")
    print(f"objective={OBJECTIVE}")
    print(f"incumbent={args.incumbent:.3f}")
    print(f"boundaries_reviewed={len(result.reviewed)}")
    print(f"proven_irrelevant={len(result.proven_irrelevant)}")
    for item in result.proven_irrelevant:
        print(f"  irrelevant: {item}")
    print(f"effective_unresolved={len(result.unresolved)}")
    for item in result.unresolved:
        print(f"  unresolved: {item}")
    print(f"racial_boundary_denominator_proven={result.denominator_proven}")
    print(f"racial_boundary_irrelevance_proven={result.objective_irrelevance_proven}")
    print(
        "proof_incumbent_usable="
        + str(result.objective_irrelevance_proven)
    )
    print(
        "NEXT_STEP="
        + (
            "use 107574 as the legal incumbent and prove omitted gear packages cannot exceed it"
            if result.objective_irrelevance_proven
            else "keep the incumbent provisional until remaining racial boundaries are resolved"
        )
    )
    return 0 if result.objective_irrelevance_proven else 1


if __name__ == "__main__":
    raise SystemExit(main())
