from __future__ import annotations

"""Fast baseline screen for Extreme maximum single-healing-event contenders.

This command exhaustively scores legal route/heal/slot combinations on the
supplied saved build, but intentionally performs zero whole-build mutation
passes. Use it to identify serious finalists before running expensive build
optimization. It is read-only and never claims a global maximum.
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
from services.extreme_sorcerer_blood_magic_actual_heal_service import (
    ExtremeSorcererBloodMagicActualHealService,
)
from services.extreme_sorcerer_blood_magic_class_route_catalog_service import (
    ExtremeSorcererBloodMagicClassRouteCatalogService,
)
from tools.audit_extreme_maximum_healing_event import _find_build, format_report

DEFAULT_BUILDS = get_data_dir() / "builds.json"


def audit(
    *,
    build_name: str,
    database_path: Path,
    builds_path: Path,
    active_bar: str,
    include_base_class_changes: bool,
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

    ordinary_optimizer = ExtremeBaselineCanonicalActualHealOptimizationService()
    ordinary = ExtremeActualHealClassRouteCatalogService(
        database_path=database_path,
        optimizer=ordinary_optimizer,
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
    result = service.rank(
        build,
        active_bar=active_bar,
        max_passes=0,
        include_base_class_changes=include_base_class_changes,
    )

    # Screening deliberately omits whole-build optimization even if every
    # baseline mechanic is otherwise complete. Make that boundary impossible
    # for downstream reporting to mistake for a proof claim.
    result = type(result)(
        entries=result.entries,
        best_scored=result.best_scored,
        best_complete=result.best_complete,
        ordinary=result.ordinary,
        blood_magic=result.blood_magic,
        search_scope=(
            "STAGE 1 SCREEN: exhaustive legal route/heal/slot baseline scoring",
            "zero whole-build mutation passes",
            *result.search_scope,
        ),
        omitted_scope=(
            "whole-build optimization for screened contenders",
            *result.omitted_scope,
        ),
    )

    print("SCREENING MODE: baseline route/heal/slot ranking; NOT a global maximum proof")
    print(format_report(result, build=build, active_bar=active_bar, top=top))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, help="Saved BuildName to audit")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_DATABASE),
        help="Path to eso.db (default: canonical data/eso.db)",
    )
    parser.add_argument(
        "--builds",
        type=Path,
        default=Path(DEFAULT_BUILDS),
        help="Path to builds.json",
    )
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    parser.add_argument("--include-base-class-changes", action="store_true")
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()
    return audit(
        build_name=args.build,
        database_path=args.database,
        builds_path=args.builds,
        active_bar=args.active_bar,
        include_base_class_changes=args.include_base_class_changes,
        top=args.top,
    )


if __name__ == "__main__":
    raise SystemExit(main())
