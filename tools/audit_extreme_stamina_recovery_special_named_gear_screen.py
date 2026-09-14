from __future__ import annotations

"""Proof-safe capacity screen for Extreme Stamina Recovery special named gear."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_armor_weight_filtered_slot_eligibility_service import ExtremeArmorWeightFilteredSlotEligibilityService
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_special_named_gear_branch_service import ExtremeMaxResourceSpecialNamedGearBranchService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import distinct_set_capacity_upper_bound
from tools.audit_extreme_stamina_recovery_exact_enlivening_and_ordinary_gear import OBJECTIVE, RESOURCE_OBJECTIVE, _Search, _pair_scores
from tools.audit_extreme_stamina_recovery_special_named_gear_triage import (
    BASE_ENLIVENING,
    ENLIVENING_CAP,
    ORDINARY_INCUMBENT,
    _triage,
)


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def main() -> int:
    database = Path(_parser().parse_args().database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    raw = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database, raw, required_armor_weight="Medium"
    )
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)
    scores, merged = _pair_scores(recovery, magicka, 0.0051)
    ordinary = _Search(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=merged,
        pair_scores=scores,
    ).search(topology)

    recovery_by = {(int(row.set_id), int(row.piece_count)): row for row in recovery.evidence}
    magicka_by = {(int(row.set_id), int(row.piece_count)): row for row in magicka.evidence}
    max_service = ExtremeMaxResourceSpecialNamedGearBranchService(magicka)
    headroom = max(0.0, ENLIVENING_CAP - BASE_ENLIVENING)
    triage = tuple(
        _triage(
            pair,
            recovery_by=recovery_by,
            magicka_by=magicka_by,
            max_service=max_service,
            headroom=headroom,
        )
        for pair in ordinary.special_or_nonflat_pairs
    )

    unresolved = tuple(row for row in triage if row.unresolved)
    flat_rows = []
    pending = []
    for row in triage:
        if row.unresolved:
            continue
        structural = distinct_set_capacity_upper_bound(row, scores)
        if row.can_raise and row.flat is not None and row.percent is None:
            special = float(row.flat) + float(row.max_magicka_recovery_ceiling)
        elif (not row.can_raise) and row.max_magicka_kind is not None:
            special = float(row.max_magicka_recovery_ceiling)
        else:
            if row.can_raise:
                pending.append(row)
            continue
        optimistic = None if structural is None else float(structural) + special
        dominated = structural is None or (optimistic is not None and optimistic < ORDINARY_INCUMBENT - 1e-9)
        flat_rows.append((row, structural, special, optimistic, dominated))

    flat_rows.sort(key=lambda item: (-(item[3] if item[3] is not None else -1e30), item[0].piece_count, item[0].set_id))
    dominated = tuple(item for item in flat_rows if item[4])
    survivors = tuple(item for item in flat_rows if not item[4])

    print("EXTREME STAMINA RECOVERY SPECIAL NAMED-GEAR CAPACITY SCREEN")
    print(f"database={database}")
    print(f"ordinary_incumbent_prepercent={ORDINARY_INCUMBENT:.3f}")
    print(f"special_pair_count={len(triage)}")
    print(f"triage_unresolved_count={len(unresolved)}")
    print(f"screenable_flat_or_maxmagicka_pairs={len(flat_rows)}")
    print(f"pending_nonflat_or_search_state_pairs={len(pending)}")
    print()
    print("CAPACITY BOUNDS")
    for row, structural, special, optimistic, is_dominated in flat_rows:
        if structural is None or optimistic is None:
            print(f"set={row.set_name!r} pieces={row.piece_count} compatible_capacity=False dominated=True")
            continue
        print(
            f"set={row.set_name!r} pieces={row.piece_count} structural_upper={structural:.3f} "
            f"special_upper={special:.3f} optimistic_total={optimistic:.3f} "
            f"margin_to_incumbent={optimistic - ORDINARY_INCUMBENT:.3f} dominated={is_dominated}"
        )
    print()
    print("SURVIVORS")
    for row, _structural, _special, optimistic, _dominated in survivors:
        print(f"survivor: set={row.set_name!r} pieces={row.piece_count} optimistic_total={optimistic:.3f}")
    for row in pending:
        print(
            f"pending_nonflat: set={row.set_name!r} pieces={row.piece_count} "
            f"kind={row.recovery_kind!r} flat={row.flat!r} percent={row.percent!r} condition={row.condition!r}"
        )
    print()
    closed = bool(
        filtered.denominator_proven
        and ordinary.ordinary_denominator_proven
        and not unresolved
        and flat_rows
    )
    print("PROOF GATES")
    print(f"medium_armor_physical_filter_proven={filtered.denominator_proven}")
    print(f"ordinary_denominator_prerequisite_proven={ordinary.ordinary_denominator_proven}")
    print(f"all_special_pairs_classified={not unresolved}")
    print(f"capacity_screen_dominated={len(dominated)}")
    print(f"capacity_screen_survivors={len(survivors)}")
    print(f"pending_nonflat_or_search_state={len(pending)}")
    print(f"special_named_gear_capacity_screen_closed={closed}")
    print("NEXT_STEP=exactly resolve only capacity survivors and pending non-flat/search-state branches, then compose contextual Recovery stack")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
