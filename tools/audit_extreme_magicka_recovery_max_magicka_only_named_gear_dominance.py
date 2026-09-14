from __future__ import annotations

"""Prove Max-Magicka-only special named gear cannot beat the ordinary Recovery winner.

The ordinary Extreme Magicka Recovery gear frontier is already closed at an
optimistic effective pre-percent Recovery gain.  This audit takes only special
pairs whose sole positive Recovery route is through Max Magicka -> Enlivening
Overflow.  For each pair it requires that set physically, externalizes the special
mechanic, searches the best ordinary effective-Recovery loadout that can coexist
with it, then grants the branch the *entire remaining Enlivening headroom*.

Because that headroom is an absolute cap, the resulting score is a proof-safe upper
bound even when the exact conditional Max Magicka mechanic would provide less.
Search-state mutations that can directly raise Recovery (for example a second
Mundus) are deliberately excluded by triage and must be handled as direct Recovery
challengers instead.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_externalized_named_gear_constraint_search_service import (
    ExtremeExternalizedNamedGearConstraintSearchService,
    ExtremeExternalizedNamedGearSemantic,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_constrained_named_gear_exact_flat_search_service import (
    ExtremeNamedGearRequirement,
)
from tools.audit_extreme_magicka_recovery_armor_mundus_frontier import (
    _same_build_max_magicka_for_weight_types,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    RECOVERY_MULTIPLIER,
    _EffectiveRecoveryOrdinarySearch,
    build_pair_scores,
)
from tools.audit_extreme_magicka_recovery_same_build_enlivening import exact_enlivening_value
from tools.audit_extreme_magicka_recovery_special_named_gear_triage import (
    _triage_pair,
)
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialNamedGearBranchService,
)


@dataclass(frozen=True)
class DominanceRow:
    set_id: int
    set_name: str
    piece_count: int
    structural_ordinary_score: float | None
    absolute_enlivening_ceiling: float
    optimistic_total: float | None
    incumbent: float
    physically_available: bool

    @property
    def margin(self) -> float | None:
        if self.optimistic_total is None:
            return None
        return float(self.incumbent) - float(self.optimistic_total)

    @property
    def dominated(self) -> bool:
        if not self.physically_available:
            return True
        return self.optimistic_total is not None and self.optimistic_total < self.incumbent - 1e-9


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def dominance_row(
    *,
    set_id: int,
    set_name: str,
    piece_count: int,
    structural_score: float | None,
    enlivening_ceiling: float,
    incumbent: float,
) -> DominanceRow:
    available = structural_score is not None
    optimistic = None if structural_score is None else float(structural_score) + float(enlivening_ceiling)
    return DominanceRow(
        set_id=int(set_id),
        set_name=str(set_name),
        piece_count=int(piece_count),
        structural_ordinary_score=(None if structural_score is None else float(structural_score)),
        absolute_enlivening_ceiling=float(enlivening_ceiling),
        optimistic_total=optimistic,
        incumbent=float(incumbent),
        physically_available=available,
    )


def main() -> int:
    database = Path(_parser().parse_args().database)
    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    raw_eligibility = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database,
        raw_eligibility,
        required_armor_weight="Light",
    )

    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    max_magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)

    base_max_magicka, max_magicka_unresolved = _same_build_max_magicka_for_weight_types(database, 1)
    base_enlivening = exact_enlivening_value(base_max_magicka)
    remaining_headroom = max(0.0, 150.0 - base_enlivening)
    conversion = 0.0051

    pair_scores, merged = build_pair_scores(
        recovery,
        max_magicka,
        max_magicka_to_recovery=conversion,
    )
    ordinary_search = _EffectiveRecoveryOrdinarySearch(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=merged,
        pair_scores=pair_scores,
    ).search(topology)
    incumbent = max(
        (
            float(row.best_exact_flat_delta)
            for row in ordinary_search.topologies
            if row.winner_found and row.best_exact_flat_delta is not None
        ),
        default=0.0,
    )

    recovery_by = {(int(row.set_id), int(row.piece_count)): row for row in recovery.evidence}
    magicka_by = {(int(row.set_id), int(row.piece_count)): row for row in max_magicka.evidence}
    max_magicka_service = ExtremeMaxResourceSpecialNamedGearBranchService(max_magicka)

    triage = tuple(
        _triage_pair(
            pair,
            recovery_by=recovery_by,
            magicka_by=magicka_by,
            max_magicka_service=max_magicka_service,
            remaining_enlivening_headroom=remaining_headroom,
        )
        for pair in ordinary_search.special_or_nonflat_pairs
    )
    unresolved_triage = tuple(row for row in triage if row.unresolved)
    max_only = tuple(row for row in triage if row.max_magicka_only_challenger)

    rows: list[DominanceRow] = []
    search_unresolved: list[str] = []
    for challenger in max_only:
        requirement = ExtremeNamedGearRequirement(challenger.set_name, challenger.piece_count)
        external = ExtremeExternalizedNamedGearSemantic(challenger.set_name, challenger.piece_count)
        constrained = ExtremeExternalizedNamedGearConstraintSearchService.search(
            topology_catalog=topology,
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            relevance=merged,
            requirements=(requirement,),
            externalized=(external,),
        )
        if constrained.unresolved:
            search_unresolved.extend(
                f"{challenger.set_name} ({challenger.piece_count}): {item}"
                for item in constrained.unresolved
            )
        structural = None
        if constrained.search is not None and constrained.winner_found:
            structural = constrained.search.best_exact_flat_delta
        rows.append(
            dominance_row(
                set_id=challenger.set_id,
                set_name=challenger.set_name,
                piece_count=challenger.piece_count,
                structural_score=structural,
                enlivening_ceiling=challenger.max_magicka_recovery_ceiling,
                incumbent=incumbent,
            )
        )

    rows.sort(
        key=lambda row: (
            -(row.optimistic_total if row.optimistic_total is not None else float("-inf")),
            row.piece_count,
            row.set_id,
        )
    )
    all_dominated = bool(rows) and all(row.dominated for row in rows)
    closed = bool(
        filtered.denominator_proven
        and ordinary_search.ordinary_denominator_proven
        and not unresolved_triage
        and not max_magicka_unresolved
        and not search_unresolved
        and all_dominated
    )

    print("EXTREME MAGICKA RECOVERY MAX-MAGICKA-ONLY NAMED-GEAR DOMINANCE")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print(f"ordinary_incumbent_prepercent_recovery={incumbent:.3f}")
    print(f"ordinary_incumbent_final_recovery_gain={incumbent * RECOVERY_MULTIPLIER:.3f}")
    print(f"same_build_max_magicka_before_named_gear={base_max_magicka:.3f}")
    print(f"base_enlivening={base_enlivening:.3f}")
    print(f"absolute_remaining_enlivening_headroom={remaining_headroom:.3f}")
    print(f"max_magicka_only_challengers={len(max_only)}")
    print()
    print("CONSTRAINED UPPER BOUNDS")
    for row in rows:
        if not row.physically_available:
            print(
                f"set={row.set_name!r} pieces={row.piece_count} physically_available=False "
                "dominated=True reason='no legal constrained Light-armor witness'"
            )
            continue
        assert row.optimistic_total is not None and row.margin is not None
        print(
            f"set={row.set_name!r} pieces={row.piece_count} "
            f"structural_ordinary={row.structural_ordinary_score:.3f} "
            f"granted_full_enlivening_headroom={row.absolute_enlivening_ceiling:.3f} "
            f"optimistic_total={row.optimistic_total:.3f} margin_to_incumbent={row.margin:.3f} "
            f"dominated={row.dominated}"
        )
    print()
    print("PROOF GATES")
    print(f"light_armor_physical_filter_proven={filtered.denominator_proven}")
    print(f"ordinary_denominator_prerequisite_proven={ordinary_search.ordinary_denominator_proven}")
    print(f"triage_unresolved_count={len(unresolved_triage)}")
    print(f"max_magicka_witness_unresolved_count={len(max_magicka_unresolved)}")
    print(f"constrained_search_unresolved_count={len(search_unresolved)}")
    for item in search_unresolved:
        print(f"  unresolved: {item}")
    print(f"all_max_magicka_only_challengers_dominated={all_dominated}")
    print(f"max_magicka_only_named_gear_closed={closed}")
    if closed:
        print(
            "NEXT_STEP=run constrained dominance over the direct-Recovery special named-gear queue, "
            "including second-Mundus and named-buff/search-state branches"
        )
    else:
        print("NEXT_STEP=close only the reported Max-Magicka-only dominance blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
