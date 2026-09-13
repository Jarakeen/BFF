from __future__ import annotations

"""Audit runtime compatibility of the dominant Health Recovery route and gear frontier."""

import argparse
from collections import Counter
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
)
from services.extreme_health_recovery_runtime_compatibility_service import (
    ExtremeHealthRecoveryRuntimeCompatibilityService,
    ExtremeHealthRecoveryRuntimeState,
)

OBJECTIVE = "health_recovery"
_UNRESOLVED_ROW = re.compile(
    r"^(?P<name>.+?) \((?P<count>\d+)\): active set bonus is not yet mechanic-mapped: (?P<description>.*)$",
    re.DOTALL,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _special_catalog(database: Path):
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    rows: list[tuple[str, int, str]] = []
    unresolved: list[str] = []
    for item in relevance.unresolved:
        match = _UNRESOLVED_ROW.match(str(item))
        if match is None:
            unresolved.append(str(item))
            continue
        rows.append((match.group("name"), int(match.group("count")), match.group("description")))
    catalog = ExtremeGearSetRecoverySpecialBranchService.build(tuple(rows), objective_key=OBJECTIVE)
    return catalog, tuple(dict.fromkeys((*unresolved, *catalog.unresolved)))


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    catalog, semantic_unresolved = _special_catalog(database)

    state = ExtremeHealthRecoveryRuntimeState()
    assessments = ExtremeHealthRecoveryRuntimeCompatibilityService.build(
        catalog.positive_challengers,
        state,
    )
    counts = Counter(row.status.value for row in assessments)

    print("EXTREME HEALTH RECOVERY RUNTIME COMPATIBILITY")
    print(f"database={database}")
    print("mode=dominant_route_shared_state_plus_special_branch_compatibility")
    print()
    print("DOMINANT ROUTE / SHARED STATE")
    print("race='Khajiit' racial_flat=90")
    print("class='Dragonknight' route=('draconic_power',) mastery='booming_voice'")
    print("class_flat_ceiling=1950")
    print(f"low_health_boundary={state.low_health_boundary}")
    print(f"booming_voice_window={state.booming_voice_window}")
    print(f"home_keeps={state.home_keeps}")
    print(f"continuous_attack_active={state.continuous_attack_active}")
    print(f"heavy_armor_pieces={state.heavy_armor_pieces}")
    print(f"major_fortitude_active={state.major_fortitude_active}")
    print(f"provisioning_kind={state.provisioning_kind!r}")
    print(f"dominant_shared_state_compatible={state.dominant_shared_state_compatible}")
    print()

    print("SPECIAL GEAR COMPATIBILITY")
    print(f"positive_special_challengers={len(catalog.positive_challengers)}")
    print("status_counts=" + ", ".join(f"{key}:{value}" for key, value in sorted(counts.items())))
    for row in assessments:
        branch = row.branch
        print(
            f"  {branch.set_name} {branch.piece_count}pc status={row.status.value} "
            f"flat={branch.flat_ceiling!r} percent={branch.percent_ceiling!r} "
            f"reason={row.reason}"
        )

    unresolved = list(semantic_unresolved)
    if not state.dominant_shared_state_compatible:
        unresolved.append("Dominant Dragonknight/shared runtime state is internally incompatible")
    print()
    print(f"runtime_compatibility_unresolved_count={len(unresolved)}")
    for item in unresolved:
        print(f"  unresolved: {item}")

    if unresolved:
        print("NEXT_STEP=close runtime compatibility blockers before numeric equipment scoring")
        return 2
    print("runtime_compatibility_denominator_closed=True")
    print(
        "NEXT_STEP=score ordinary equipment/jewelry/CP and the compatible special branches; "
        "rescore Green Pact with food and keep search-state mutations separate"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
