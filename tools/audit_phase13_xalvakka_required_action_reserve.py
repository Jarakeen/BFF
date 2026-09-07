from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.resource_costs import ResourceType
from services.rotation_candidate_scorecard_service import RotationDemandActionRequirement
from services.rotation_required_action_reserve_service import RotationRequiredActionReserveService
from services.rotation_sustain_service import RotationSustainService
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from tools.audit_phase13_xalvakka_healer_threshold_rotation import _DEMAND_NAME


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Derive the minimum Magicka needed to pay for the explicit Xalvakka healer "
            "prep action through BFF's canonical Phase 4 action-cost pipeline."
        )
    )
    parser.add_argument("--character", default="Magrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    build = _load_saved_build(
        Path(args.builds),
        character=args.character,
        build_name=args.build,
    )
    requirement = RotationDemandActionRequirement(
        demand_name=_DEMAND_NAME,
        skill_name="Budding Seeds",
        bar="front",
        minimum_casts=1,
    )
    derivation = RotationRequiredActionReserveService(
        RotationSustainService(database_path=Path(args.database))
    ).derive(
        build=build,
        demand_name=_DEMAND_NAME,
        requirements=(requirement,),
        resource=ResourceType.MAGICKA,
    )

    print("=" * 104)
    print(" PHASE 13 XALVAKKA REQUIRED-ACTION RESERVE DERIVATION")
    print("=" * 104)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Demand:    {_DEMAND_NAME}")
    print("Required:  1 front-bar Budding Seeds cast")
    print("Resource:  Magicka")
    print()

    for name, casts, amount in derivation.action_costs:
        print(f"{name}: {casts} required cast(s) -> {amount:,} canonical Magicka")
    print(f"Derived minimum cast-affordability reserve: {derivation.minimum_amount:,} Magicka")

    if derivation.blocking_unresolved:
        print("\nBLOCKING COST EVIDENCE")
        for message in derivation.blocking_unresolved:
            print(f"  - {message}")
        print(
            "\nNo reserve requirement should be promoted from this derivation until the "
            "required action costs resolve cleanly."
        )
        return 1

    print("\nPromotion: canonical required-action cost floor is resolved and may be used as a reserve requirement.")

    if derivation.context_notes:
        print("\nNON-BLOCKING CONTEXT NOTES")
        for message in derivation.context_notes:
            print(f"  - {message}")

    print(
        "\nBoundary: this is only the canonical resource needed to pay for the explicitly "
        "required cast(s). It is not a healer safety margin, emergency follow-up budget, "
        "or universal Xalvakka reserve recommendation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
