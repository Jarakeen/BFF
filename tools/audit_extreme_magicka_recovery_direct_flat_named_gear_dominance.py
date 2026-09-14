from __future__ import annotations

"""Constrained upper-bound audit for direct flat Magicka Recovery named-gear challengers.

The special named-gear denominator is already classified. This pass handles only
branches whose direct Recovery upside can be represented by a finite flat ceiling.
Percentage, named-buff, and search-state mutations remain explicit survivors for a
separate proof because they act on a broader Recovery reference state.

For every flat challenger we first compute a deliberately loose abstract topology
upper bound. The challenger consumes one matching piece-count partition and every
remaining partition is awarded the best ordinary score for that count, even if that
reuses the same set identity and ignores all physical slot conflicts. If that
impossible-best case still loses, the branch is dominated without an expensive
physical search. Only abstract survivors reach the constrained physical solver.

For physical survivors we require the named set, externalize its special pair,
search the best ordinary effective-Recovery structure that can coexist with it,
then add a deliberately generous special ceiling:

* all positive mapped flat Magicka Recovery from the candidate;
* the larger of the triaged flat ceiling and the sum of description-classified flat
  ceilings across active set bonuses;
* the full remaining Enlivening headroom when the same pair also has a Max Magicka
  special route.

Mapped and description-derived flats can overlap. Keeping both is intentional: this
is an upper-bound dominance proof, so overcounting is safe while undercounting is not.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from minmax.stat_ids import StatId
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
    ExtremeRecoverySpecialBranchKind,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialNamedGearBranchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from tools.audit_extreme_magicka_recovery_armor_mundus_frontier import (
    _same_build_max_magicka_for_weight_types,
)
from tools.audit_extreme_magicka_recovery_max_magicka_only_named_gear_dominance import (
    _constrained_effective_recovery_search,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    RECOVERY_MULTIPLIER,
    _EffectiveRecoveryOrdinarySearch,
    build_pair_scores,
)
from tools.audit_extreme_magicka_recovery_same_build_enlivening import exact_enlivening_value
from tools.audit_extreme_magicka_recovery_special_named_gear_triage import _triage_pair


_NONFLAT_KINDS = frozenset(
    {
        ExtremeRecoverySpecialBranchKind.CONDITIONAL_PERCENT,
        ExtremeRecoverySpecialBranchKind.NAMED_BUFF,
        ExtremeRecoverySpecialBranchKind.SEARCH_STATE_MUTATION,
    }
)


@dataclass(frozen=True)
class DirectFlatUpperBound:
    mapped_flat: float
    triaged_flat: float
    description_flat: float
    max_magicka_recovery_ceiling: float
    total_special_ceiling: float
    pending_nonflat: tuple[str, ...] = ()


@dataclass(frozen=True)
class DirectFlatDominanceRow:
    set_id: int
    set_name: str
    piece_count: int
    structural_ordinary_score: float | None
    special_flat_upper_bound: float
    optimistic_total: float | None
    incumbent: float
    physically_available: bool
    bound_kind: str = "constrained_physical"

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


def _mapped_positive_flat(evidence) -> float:
    return sum(
        float(effect.value)
        for effect in getattr(evidence.candidate, "source_effects", ())
        if effect.stat is StatId.MAGICKA_RECOVERY
        and effect.operation is EffectOperation.ADD
        and float(effect.value) > 0.0
    )


def _description_branches(evidence):
    rows = []
    for bonus in getattr(evidence.candidate, "source_bonuses", ()):
        description = str(getattr(bonus, "description", "") or "").strip()
        if not description:
            continue
        branch = ExtremeGearSetRecoverySpecialBranchService.classify(
            set_name=str(evidence.set_name),
            piece_count=int(evidence.piece_count),
            description=description,
            objective_key=OBJECTIVE,
        )
        if branch is not None:
            rows.append(branch)
    return tuple(rows)


def direct_flat_upper_bound(challenger, recovery_evidence) -> DirectFlatUpperBound:
    pending: list[str] = []
    triaged_percent = challenger.recovery_percent_ceiling
    if triaged_percent is not None:
        pending.append(f"triaged percentage Recovery ceiling={float(triaged_percent):.3f}%")
    if str(challenger.recovery_kind or "") in {
        "named_buff",
        "search_state_mutation",
        "mapped_conditional_percent",
        "mapped_conditional_bundle",
        "conditional_percent",
    }:
        pending.append(f"triaged non-flat kind={challenger.recovery_kind}")

    description_branches = _description_branches(recovery_evidence)
    description_flat = 0.0
    for branch in description_branches:
        if branch.kind in _NONFLAT_KINDS or branch.percent_ceiling is not None or branch.search_state_rule:
            pending.append(
                f"description non-flat kind={branch.kind.value} condition={branch.condition or branch.search_state_rule}"
            )
            continue
        if branch.can_raise_self and branch.flat_ceiling is not None:
            description_flat += max(0.0, float(branch.flat_ceiling))

    mapped_flat = _mapped_positive_flat(recovery_evidence)
    triaged_flat = max(0.0, float(challenger.recovery_flat_ceiling or 0.0))
    direct_special = mapped_flat + max(triaged_flat, description_flat)
    max_magicka_ceiling = max(0.0, float(challenger.max_magicka_recovery_ceiling or 0.0))
    return DirectFlatUpperBound(
        mapped_flat=mapped_flat,
        triaged_flat=triaged_flat,
        description_flat=description_flat,
        max_magicka_recovery_ceiling=max_magicka_ceiling,
        total_special_ceiling=direct_special + max_magicka_ceiling,
        pending_nonflat=tuple(dict.fromkeys(pending)),
    )


def abstract_topology_structural_upper_bound(challenger, pair_scores, topology_catalog) -> float | None:
    """Impossible-best ordinary coexistence bound before physical realization.

    A matching count slot is consumed by the special challenger. Every remaining
    count slot receives the best ordinary score available for that count. Set
    identities may be reused and physical eligibility is ignored, both of which can
    only raise the result. Therefore the returned value is a safe structural upper
    bound for dominance pruning.
    """
    challenger_id = int(challenger.set_id)
    required_count = int(challenger.piece_count)
    best_by_count: dict[int, float] = {}
    for (set_id, count), score in pair_scores.items():
        if int(set_id) == challenger_id or not score.ordinary:
            continue
        value = max(0.0, float(score.optimistic_effective_recovery))
        count = int(count)
        if value > best_by_count.get(count, 0.0):
            best_by_count[count] = value

    best: float | None = None
    for topology in topology_catalog.topologies:
        counts = list(int(value) for value in topology.counts)
        if required_count not in counts:
            continue
        counts.remove(required_count)
        score = sum(best_by_count.get(count, 0.0) for count in counts)
        if best is None or score > best:
            best = score
    return best


def dominance_row(
    *,
    challenger,
    structural_score: float | None,
    special_ceiling: float,
    incumbent: float,
    bound_kind: str = "constrained_physical",
):
    available = structural_score is not None
    optimistic = None if structural_score is None else float(structural_score) + float(special_ceiling)
    return DirectFlatDominanceRow(
        set_id=int(challenger.set_id),
        set_name=str(challenger.set_name),
        piece_count=int(challenger.piece_count),
        structural_ordinary_score=(None if structural_score is None else float(structural_score)),
        special_flat_upper_bound=float(special_ceiling),
        optimistic_total=optimistic,
        incumbent=float(incumbent),
        physically_available=available,
        bound_kind=str(bound_kind),
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
    pair_scores, merged = build_pair_scores(
        recovery,
        max_magicka,
        max_magicka_to_recovery=0.0051,
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
    direct = tuple(row for row in triage if row.direct_recovery_challenger)

    candidates = []
    pending = []
    for challenger in direct:
        evidence = recovery_by.get((int(challenger.set_id), int(challenger.piece_count)))
        if evidence is None:
            pending.append((challenger, ("missing canonical Recovery evidence",)))
            continue
        upper = direct_flat_upper_bound(challenger, evidence)
        if upper.pending_nonflat:
            pending.append((challenger, upper.pending_nonflat))
            continue
        candidates.append((challenger, upper))

    rows: list[DirectFlatDominanceRow] = []
    search_unresolved: list[str] = []
    abstract_pruned = 0
    physical_search_candidates = 0
    for challenger, upper in candidates:
        abstract_structural = abstract_topology_structural_upper_bound(
            challenger,
            pair_scores,
            topology,
        )
        abstract_row = dominance_row(
            challenger=challenger,
            structural_score=abstract_structural,
            special_ceiling=upper.total_special_ceiling,
            incumbent=incumbent,
            bound_kind="abstract_topology_upper",
        )
        if abstract_row.dominated:
            rows.append(abstract_row)
            abstract_pruned += 1
            continue

        physical_search_candidates += 1
        constrained, unresolved = _constrained_effective_recovery_search(
            challenger=challenger,
            topology=topology,
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            merged=merged,
            pair_scores=pair_scores,
        )
        if unresolved:
            search_unresolved.extend(
                f"{challenger.set_name} ({challenger.piece_count}): {item}"
                for item in unresolved
            )
        structural = None
        if constrained is not None and constrained.winner_found:
            structural = constrained.best_exact_flat_delta
        rows.append(
            dominance_row(
                challenger=challenger,
                structural_score=structural,
                special_ceiling=upper.total_special_ceiling,
                incumbent=incumbent,
                bound_kind="constrained_physical",
            )
        )

    rows.sort(
        key=lambda row: (
            -(row.optimistic_total if row.optimistic_total is not None else float("-inf")),
            row.piece_count,
            row.set_id,
        )
    )
    dominated = tuple(row for row in rows if row.dominated)
    survivors = tuple(row for row in rows if not row.dominated)
    flat_branch_closed = bool(
        filtered.denominator_proven
        and ordinary_search.ordinary_denominator_proven
        and not unresolved_triage
        and not max_magicka_unresolved
        and not search_unresolved
        and rows
    )

    print("EXTREME MAGICKA RECOVERY DIRECT-FLAT NAMED-GEAR DOMINANCE")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print(f"ordinary_incumbent_prepercent_recovery={incumbent:.3f}")
    print(f"ordinary_incumbent_final_recovery_gain={incumbent * RECOVERY_MULTIPLIER:.3f}")
    print(f"direct_recovery_challengers={len(direct)}")
    print(f"flat_upper_bound_candidates={len(candidates)}")
    print(f"nonflat_or_search_state_pending={len(pending)}")
    print(f"abstract_topology_pruned={abstract_pruned}")
    print(f"physical_search_candidates={physical_search_candidates}")
    print()
    print("DIRECT-FLAT UPPER BOUNDS")
    for row in rows:
        if not row.physically_available:
            print(
                f"set={row.set_name!r} pieces={row.piece_count} bound_kind={row.bound_kind!r} "
                "physically_available=False dominated=True reason='no compatible count topology or legal constrained witness'"
            )
            continue
        assert row.optimistic_total is not None and row.margin is not None
        print(
            f"set={row.set_name!r} pieces={row.piece_count} bound_kind={row.bound_kind!r} "
            f"structural_upper={row.structural_ordinary_score:.3f} "
            f"special_flat_upper_bound={row.special_flat_upper_bound:.3f} "
            f"optimistic_total={row.optimistic_total:.3f} margin_to_incumbent={row.margin:.3f} "
            f"dominated={row.dominated}"
        )
    print()
    print("SURVIVORS")
    for row in survivors:
        print(
            f"survivor: set={row.set_name!r} pieces={row.piece_count} bound_kind={row.bound_kind!r} "
            f"optimistic_total={row.optimistic_total:.3f} margin_to_incumbent={row.margin:.3f}"
        )
    for challenger, reasons in pending:
        print(
            f"pending_nonflat: set={challenger.set_name!r} pieces={challenger.piece_count} reasons={reasons!r}"
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
    print(f"flat_candidates_dominated={len(dominated)}")
    print(f"flat_candidates_surviving={len(survivors)}")
    print(f"direct_flat_named_gear_branch_closed={flat_branch_closed}")
    if flat_branch_closed:
        print(
            "NEXT_STEP=resolve only surviving flat challengers plus the explicitly pending percentage, named-buff, and search-state branches"
        )
    else:
        print("NEXT_STEP=close only the reported direct-flat dominance blockers")
    return 0 if flat_branch_closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
