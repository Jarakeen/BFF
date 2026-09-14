from __future__ import annotations

"""Close the ordinary named-gear frontier for Extreme Magicka Recovery.

The search objective is deliberately optimistic but additive:

    direct Magicka Recovery + ordinary flat Max Magicka * Enlivening coefficient

The Max Magicka term is converted with the current one-weight Undaunted Mettle
multiplier and is *not* capped during branch-and-bound.  That makes the search
score a proof-safe upper bound.  Winning realizations are then rescored with the
real remaining Enlivening headroom.  If an exact realization reaches the optimistic
bound, the ordinary named-gear branch is globally closed.

Armor legality is projected through the already-locked seven-Light frontier.
Divines and Infused traits remain compatible with arbitrary set identities, so set
placement only needs to preserve Light armor plus canonical slot/weapon legality.
"""

import argparse
from dataclasses import dataclass, replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from minmax.passive_math import undaunted_mettle_resource_percent
from minmax.stat_ids import StatId
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveBreakpointEvidence,
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from tools.audit_extreme_magicka_recovery_armor_mundus_frontier import (
    _same_build_max_magicka_for_weight_types,
)
from tools.audit_extreme_magicka_recovery_same_build_enlivening import exact_enlivening_value

OBJECTIVE = "magicka_recovery"
RESOURCE_OBJECTIVE = "max_magicka"
RECOVERY_MULTIPLIER = 1.81  # locked 53% class route + 28% seven-Light Evocation


@dataclass(frozen=True)
class PairScore:
    direct_recovery: float
    max_magicka_flat: float
    optimistic_effective_recovery: float
    ordinary: bool


class _EffectiveRecoveryOrdinarySearch(ExtremeMaxResourceOrdinaryNamedGearSearchService):
    SUPPORTED_OBJECTIVES = frozenset((*ExtremeMaxResourceOrdinaryNamedGearSearchService.SUPPORTED_OBJECTIVES, OBJECTIVE))

    def __init__(self, *, pair_scores: dict[tuple[int, int], PairScore], **kwargs) -> None:
        super().__init__(**kwargs)
        self.pair_scores = dict(pair_scores)

    def _ordinary_exact_delta(self, evidence, objective_key: str) -> float | None:  # type: ignore[override]
        row = self.pair_scores.get((int(evidence.set_id), int(evidence.piece_count)))
        if row is None or not row.ordinary:
            return None
        return float(row.optimistic_effective_recovery)

    def _objective_effect_signature(self, evidence, objective_key: str):  # type: ignore[override]
        row = self.pair_scores.get((int(evidence.set_id), int(evidence.piece_count)))
        if row is None or not row.ordinary:
            return ()
        return (
            ("magicka_recovery", round(row.direct_recovery, 9)),
            ("max_magicka", round(row.max_magicka_flat, 9)),
        )


def _ordinary_flat(evidence: ExtremeGearSetObjectiveBreakpointEvidence | None, objective_key: str) -> float | None:
    if evidence is None:
        return 0.0
    if evidence.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
        return 0.0
    return ExtremeMaxResourceOrdinaryNamedGearSearchService._ordinary_exact_delta(
        evidence,
        objective_key,
    )


def build_pair_scores(
    recovery: ExtremeGearSetObjectiveRelevanceCatalog,
    max_magicka: ExtremeGearSetObjectiveRelevanceCatalog,
    *,
    max_magicka_to_recovery: float,
) -> tuple[dict[tuple[int, int], PairScore], ExtremeGearSetObjectiveRelevanceCatalog]:
    recovery_by = {(int(row.set_id), int(row.piece_count)): row for row in recovery.evidence}
    magicka_by = {(int(row.set_id), int(row.piece_count)): row for row in max_magicka.evidence}
    pairs = tuple(sorted(set(recovery_by) | set(magicka_by)))

    scores: dict[tuple[int, int], PairScore] = {}
    merged: list[ExtremeGearSetObjectiveBreakpointEvidence] = []
    for pair in pairs:
        r = recovery_by.get(pair)
        m = magicka_by.get(pair)
        direct = _ordinary_flat(r, OBJECTIVE)
        magicka = _ordinary_flat(m, RESOURCE_OBJECTIVE)
        ordinary = direct is not None and magicka is not None
        direct_value = float(direct or 0.0)
        magicka_value = float(magicka or 0.0)
        optimistic = direct_value + magicka_value * float(max_magicka_to_recovery)
        scores[pair] = PairScore(
            direct_recovery=direct_value,
            max_magicka_flat=magicka_value,
            optimistic_effective_recovery=optimistic,
            ordinary=ordinary,
        )

        base = r or m
        assert base is not None
        if ordinary and optimistic > 1e-12:
            status = ExtremeGearSetObjectiveRelevance.RELEVANT
        elif ordinary:
            status = ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
        else:
            status = ExtremeGearSetObjectiveRelevance.UNRESOLVED
        candidate = replace(
            base.candidate,
            objective_key=OBJECTIVE,
            reviewed_delta=optimistic,
            unresolved=(() if ordinary else base.candidate.unresolved),
        )
        merged.append(
            replace(
                base,
                objective_key=OBJECTIVE,
                status=status,
                reviewed_delta=optimistic,
                candidate=candidate,
                search_state_rule=None,
            )
        )

    merged.sort(key=lambda row: (row.set_name.casefold(), row.set_id, row.piece_count))
    return scores, ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key=OBJECTIVE,
        evidence=tuple(merged),
        unresolved=(),
    )


def realization_pair_totals(realization, pair_scores: dict[tuple[int, int], PairScore]) -> tuple[float, float]:
    recovery = 0.0
    magicka = 0.0
    for set_id, count in zip(realization.set_ids, realization.counts):
        row = pair_scores.get((int(set_id), int(count)))
        if row is None:
            continue
        recovery += float(row.direct_recovery)
        magicka += float(row.max_magicka_flat)
    return recovery, magicka


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


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
    enlivening_headroom = max(0.0, 150.0 - base_enlivening)
    undaunted_multiplier = 1.0 + undaunted_mettle_resource_percent(1)
    conversion = 0.005 * undaunted_multiplier

    pair_scores, merged_relevance = build_pair_scores(
        recovery,
        max_magicka,
        max_magicka_to_recovery=conversion,
    )
    search = _EffectiveRecoveryOrdinarySearch(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=merged_relevance,
        pair_scores=pair_scores,
    ).search(topology)

    topology_winners = tuple(
        row for row in search.topologies if row.winner_found and row.best_exact_flat_delta is not None
    )
    optimistic_best = max((float(row.best_exact_flat_delta) for row in topology_winners), default=0.0)
    optimistic_realizations = tuple(
        realization
        for row in topology_winners
        if abs(float(row.best_exact_flat_delta or 0.0) - optimistic_best) <= 1e-9
        for realization in row.realizations
    )

    exact_rows = []
    for realization in optimistic_realizations:
        direct, magicka_flat = realization_pair_totals(realization, pair_scores)
        optimistic_enlivening_gain = magicka_flat * conversion
        exact_enlivening_gain = min(enlivening_headroom, optimistic_enlivening_gain)
        exact_effective = direct + exact_enlivening_gain
        exact_rows.append((exact_effective, direct, magicka_flat, exact_enlivening_gain, realization))
    exact_rows.sort(key=lambda row: (-row[0], row[4].set_ids, row[4].counts))
    exact_winner = exact_rows[0] if exact_rows else None
    exact_best = float(exact_winner[0]) if exact_winner else 0.0
    optimistic_bound_reached = bool(exact_winner and abs(exact_best - optimistic_best) <= 1e-9)

    special_pairs = tuple(search.special_or_nonflat_pairs)
    ordinary_closed = bool(
        filtered.denominator_proven
        and search.ordinary_denominator_proven
        and optimistic_realizations
        and optimistic_bound_reached
        and not max_magicka_unresolved
    )

    names = {int(row.set_id): row.name for row in filtered.catalog.sets}

    print("EXTREME MAGICKA RECOVERY ORDINARY NAMED-GEAR FRONTIER")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print()
    print("CROSS-STAT BOUND")
    print(f"same_build_max_magicka_before_named_gear={base_max_magicka:.3f}")
    print(f"base_enlivening={base_enlivening:.3f}")
    print(f"remaining_enlivening_headroom={enlivening_headroom:.3f}")
    print(f"one_weight_undaunted_multiplier={undaunted_multiplier:.6f}")
    print(f"ordinary_max_magicka_to_recovery_coefficient={conversion:.6f}")
    print(f"locked_recovery_multiplier={RECOVERY_MULTIPLIER:.6f}")
    print()
    print("SEARCH")
    print(f"optimistic_effective_recovery_best={optimistic_best:.3f}")
    print(f"optimistic_winner_realizations={len(optimistic_realizations)}")
    print(f"special_or_nonflat_pairs={len(special_pairs)}")
    for set_id, set_name, count in special_pairs[:20]:
        print(f"  special: set_id={set_id} set={set_name!r} pieces={count}")
    if len(special_pairs) > 20:
        print(f"  ... {len(special_pairs) - 20} more special/non-flat pairs")
    print()
    print("EXACT OPTIMISTIC-WINNER RESCORE")
    for index, row in enumerate(exact_rows[:10], start=1):
        exact_effective, direct, magicka_flat, enlivening_gain, realization = row
        sets = tuple((names.get(int(set_id), str(set_id)), int(count)) for set_id, count in zip(realization.set_ids, realization.counts))
        print(
            f"rank={index} sets={sets!r} direct_recovery={direct:.3f} "
            f"max_magicka_flat={magicka_flat:.3f} enlivening_gain={enlivening_gain:.3f} "
            f"effective_prepercent_recovery={exact_effective:.3f} "
            f"effective_final_recovery_gain={exact_effective * RECOVERY_MULTIPLIER:.3f}"
        )
        print(
            "  assignments="
            + repr(tuple((assignment.slot, names.get(int(assignment.set_id), str(assignment.set_id)), assignment.weapon_type) for assignment in realization.assignments))
        )
    print()
    print("PROOF GATES")
    print(f"light_armor_physical_filter_proven={filtered.denominator_proven}")
    print(f"ordinary_search_denominator_proven={search.ordinary_denominator_proven}")
    print(f"optimistic_winner_found={bool(optimistic_realizations)}")
    print(f"optimistic_bound_reached_by_exact_realization={optimistic_bound_reached}")
    print(f"max_magicka_witness_unresolved_count={len(max_magicka_unresolved)}")
    for item in max_magicka_unresolved:
        print(f"  unresolved: {item}")
    print(f"ordinary_named_gear_frontier_closed={ordinary_closed}")
    print(f"full_named_gear_denominator_closed={ordinary_closed and not special_pairs}")
    if ordinary_closed:
        print(
            "NEXT_STEP=review special/non-flat named-gear pairs separately; ordinary named gear is closed "
            "against the locked 7-Light / 7-Divines / Atronach / three-Infused state"
        )
    else:
        print("NEXT_STEP=close only the reported ordinary named-gear blockers")
    return 0 if ordinary_closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
