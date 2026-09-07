from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir
from minmax.resource_costs import ResourceType
from services.build_catalog_service import BuildCatalogService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter
from services.rotation_progression_readiness_service import RotationProgressionReadinessService
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build


DEFAULT_BUILDS = get_data_dir() / "builds.json"
DEFAULT_CATALOG = get_data_dir() / "characters.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Show whether canonical character-owned progression is complete enough "
            "to drive rotation action costs without equipment inference."
        )
    )
    parser.add_argument("--character", default="Magrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument(
        "--resource",
        choices=("magicka", "stamina"),
        default="magicka",
    )
    args = parser.parse_args()

    build = _load_saved_build(
        Path(args.builds),
        character=args.character,
        build_name=args.build,
    )
    resource = ResourceType(args.resource)
    catalog = BuildCatalogService(Path(args.catalog))
    readiness = RotationProgressionReadinessService(
        MinmaxCharacterProgressionAdapter(catalog)
    ).assess(
        build=build,
        resource=resource,
    )

    print("=" * 104)
    print(" PHASE 13 ROTATION CANONICAL PROGRESSION READINESS")
    print("=" * 104)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Catalog:   {args.catalog}")
    print(f"Resource:  {resource.value.title()}")
    print(f"Character ID: {readiness.character_id or '(unresolved)'}")
    print()

    print("CANONICAL OWNED SKILL LINES")
    if readiness.canonical_owned_skill_lines:
        for line in readiness.canonical_owned_skill_lines:
            print(f"  - {line}")
    else:
        print("  (none recorded)")

    print("\nEQUIPMENT EVIDENCE")
    if readiness.equipped_armor_skill_lines:
        for line in readiness.equipped_armor_skill_lines:
            print(f"  - current build equips {line}")
    else:
        print("  (no recognized armor weights equipped)")

    print(f"\nCOST-RELEVANT FOR {resource.value.upper()}")
    if readiness.cost_relevant_skill_lines:
        for line in readiness.cost_relevant_skill_lines:
            state = (
                "RECORDED"
                if line not in readiness.missing_cost_relevant_skill_lines
                else "MISSING CANONICAL OWNERSHIP"
            )
            print(f"  - {line}: {state}")
    else:
        print("  (no equipped armor skill line currently changes this resource cost path)")

    if readiness.unresolved:
        print("\nUNRESOLVED")
        for message in readiness.unresolved:
            print(f"  - {message}")

    print("\nREADINESS")
    if readiness.ready:
        print("  READY: canonical progression is sufficient for this resource cost path.")
        return 0

    print("  BLOCKED: canonical progression is not sufficient for this resource cost path.")
    if readiness.missing_cost_relevant_skill_lines:
        print(
            "  Missing cost-relevant canonical ownership: "
            + ", ".join(readiness.missing_cost_relevant_skill_lines)
        )
    print(
        "  Boundary: equipped armor is evidence only. This audit never writes or infers "
        "character-owned progression from the current build."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
