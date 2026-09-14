from __future__ import annotations

"""Resolve the finite special named-gear survivor queue for Extreme Stamina Recovery.

The ordinary seven-Medium frontier is closed at 1166 effective pre-percent Recovery.
A proof-safe capacity screen reduced 28 special/non-flat pairs to five exact-search
survivors plus Oakensoul, Twice-Born Star, and Bastion of the Draoife. This audit
resolves that complete queue without reopening already-dominated branches.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from minmax.mundus_repository import MundusRepository
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_constrained_named_gear_exact_flat_search_service import (
    ExtremeConstrainedNamedGearExactFlatSearchService,
    ExtremeNamedGearRequirement,
)
from services.extreme_externalized_named_gear_constraint_search_service import (
    ExtremeExternalizedNamedGearConstraintSearchService,
    ExtremeExternalizedNamedGearSemantic,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialNamedGearBranchService,
)
from services.extreme_mundus_objective_service import ExtremeMundusObjectiveService
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
    ExtremeRecoverySpecialBranchKind,
)
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import (
    distinct_set_capacity_upper_bound,
)
from tools.audit_extreme_stamina_recovery_exact_enlivening_and_ordinary_gear import (
    OBJECTIVE,
    RESOURCE_OBJECTIVE,
    PairScore,
    _Search,
    _pair_scores,
)
from tools.audit_extreme_stamina_recovery_special_named_gear_triage import (
    BASE_ENLIVENING,
    ENLIVENING_CAP,
    ORDINARY_INCUMBENT,
    _triage,
)

EXACT_NAMES = (
    "Torc of Tonal Constancy",
    "Prowler's Talisman",
    "Lustrous Soulwell",
    "Death Dealer's Fete",
    "Shapeshifter's Chain",
)


class _ConstrainedSearch(ExtremeConstrainedNamedGearExactFlatSearchService):
    """Audit-local constrained adapter for merged Stamina Recovery + Max Magicka."""

    SUPPORTED_OBJECTIVES = frozenset(
        (*ExtremeConstrainedNamedGearExactFlatSearchService.SUPPORTED_OBJECTIVES, OBJECTIVE)
    )

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
            ("stamina_recovery", round(row.direct_recovery, 9)),
            ("max_magicka", round(row.max_magicka_flat, 9)),
        )


@dataclass(frozen=True)
class ExactRow:
    set_name: str
    piece_count: int
    structural: float | None
    special_ceiling: float
    optimistic_total: float | None
    dominated: bool
    witness_sets: tuple[tuple[str, int], ...] = ()


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _exact_structural(
    *,
    challenger,
    topology,
    breakpoints,
    eligibility,
    merged,
    pair_scores,
):
    external = ExtremeExternalizedNamedGearSemantic(challenger.set_name, challenger.piece_count)
    derived, errors = ExtremeExternalizedNamedGearConstraintSearchService._derived_relevance(
        merged,
        eligibility,
        (external,),
    )
    if derived is None:
        return None, (), tuple(errors)
    search = _ConstrainedSearch(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=derived,
        requirements=(ExtremeNamedGearRequirement(challenger.set_name, challenger.piece_count),),
        pair_scores=pair_scores,
    ).search(topology)
    if search.unresolved:
        return None, (), tuple(search.unresolved)
    if not search.winner_found or search.best_exact_flat_delta is None:
        return None, (), ()
    witness = search.realizations[0]
    return (
        float(search.best_exact_flat_delta),
        tuple((name, int(count)) for name, count in zip(witness.set_names, witness.counts)),
        (),
    )


def _bastion_ceiling() -> float | None:
    tooltip = (
        "Blocking an attack grants you a stack of Inflection for 10 seconds, up to 3 stacks max. "
        "You can gain up to 1 stack every 0.5 seconds. Increase your Magicka and Stamina Recovery "
        "by 106 per stack of Inflection."
    )
    branch = ExtremeGearSetRecoverySpecialBranchService.classify(
        set_name="Bastion of the Draoife",
        piece_count=5,
        description=tooltip,
        objective_key=OBJECTIVE,
    )
    if branch is None or branch.kind is not ExtremeRecoverySpecialBranchKind.STACKED_FLAT:
        return None
    return branch.flat_ceiling


def main() -> int:
    database = Path(_parser().parse_args().database)
    unresolved: list[str] = []

    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    raw = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database, raw, required_armor_weight="Medium"
    )
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)
    pair_scores, merged = _pair_scores(recovery, magicka, 0.0051)
    ordinary = _Search(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=merged,
        pair_scores=pair_scores,
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
    unresolved.extend(
        f"{row.set_name} ({row.piece_count}): {item}"
        for row in triage
        for item in row.unresolved
    )
    by_name = {row.set_name: row for row in triage}

    exact_rows: list[ExactRow] = []
    for name in EXACT_NAMES:
        challenger = by_name.get(name)
        if challenger is None:
            unresolved.append(f"missing triage row: {name}")
            continue
        structural, witness_sets, errors = _exact_structural(
            challenger=challenger,
            topology=topology,
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            merged=merged,
            pair_scores=pair_scores,
        )
        unresolved.extend(f"{name}: {item}" for item in errors)
        special = float(challenger.flat or 0.0) + float(challenger.max_magicka_recovery_ceiling)
        optimistic = None if structural is None else structural + special
        exact_rows.append(
            ExactRow(
                set_name=name,
                piece_count=challenger.piece_count,
                structural=structural,
                special_ceiling=special,
                optimistic_total=optimistic,
                dominated=(structural is None or optimistic is None or optimistic < ORDINARY_INCUMBENT - 1e-9),
                witness_sets=witness_sets,
            )
        )

    # Oakensoul's Minor Endurance duplicates the already-proven Arcanist's Domain
    # carrier, so its incremental named-buff contribution is zero. Even before the
    # one-bar penalty, its generous distinct-set capacity bound is below incumbent.
    oak = by_name.get("Oakensoul Ring")
    oak_upper = None if oak is None else distinct_set_capacity_upper_bound(oak, pair_scores)
    if oak is None:
        unresolved.append("missing Oakensoul triage row")
    oak_duplicate_named_buff = bool(
        oak is not None
        and oak.recovery_kind == "search_state_mutation"
        and oak.condition == "minor_endurance"
        and abs(float(oak.percent or 0.0) - 15.0) <= 1e-9
    )
    oak_dominated = bool(
        oak_duplicate_named_buff
        and oak_upper is not None
        and oak_upper < ORDINARY_INCUMBENT - 1e-9
    )

    # Twice-Born Star can add a second, distinct Mundus. Canonical U50 data has
    # The Serpent as the only direct Stamina Recovery stone, so every distinct
    # second stone contributes 0 direct Stamina Recovery. We still grant the set
    # the entire remaining Enlivening headroom to cover a Max-Magicka second stone.
    tbs = by_name.get("Twice-Born Star")
    tbs_upper = None if tbs is None else distinct_set_capacity_upper_bound(tbs, pair_scores)
    if tbs is None:
        unresolved.append("missing Twice-Born Star triage row")
    mundus_rows = ExtremeMundusObjectiveService.candidates_for_objective(
        MundusRepository(database, initialize=False),
        OBJECTIVE,
        multiplier=1.637,
    )
    non_serpent_direct = max(
        (
            float(row.projected_delta or 0.0)
            for row in mundus_rows
            if row.mundus_name != "The Serpent" and row.projected_delta is not None
        ),
        default=0.0,
    )
    tbs_total_upper = None if tbs_upper is None else tbs_upper + non_serpent_direct + headroom
    tbs_dominated = bool(
        tbs is not None
        and tbs.condition == "second_mundus"
        and non_serpent_direct <= 1e-9
        and tbs_total_upper is not None
        and tbs_total_upper < ORDINARY_INCUMBENT - 1e-9
    )

    bastion = by_name.get("Bastion of the Draoife")
    bastion_upper = None if bastion is None else distinct_set_capacity_upper_bound(bastion, pair_scores)
    bastion_stack = _bastion_ceiling()
    if bastion is None:
        unresolved.append("missing Bastion triage row")
    if bastion_stack is None:
        unresolved.append("Bastion reviewed three-stack ceiling unresolved")
    bastion_total = None if bastion_upper is None or bastion_stack is None else bastion_upper + bastion_stack
    bastion_dominated = bool(
        bastion_total is not None and bastion_total < ORDINARY_INCUMBENT - 1e-9
    )

    exact_rows.sort(key=lambda row: (-(row.optimistic_total or -1e30), row.set_name.casefold()))
    exact_all_dominated = bool(exact_rows) and all(row.dominated for row in exact_rows)
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = bool(
        filtered.denominator_proven
        and ordinary.ordinary_denominator_proven
        and exact_all_dominated
        and oak_dominated
        and tbs_dominated
        and bastion_dominated
        and not unique_unresolved
    )

    print("EXTREME STAMINA RECOVERY SPECIAL NAMED-GEAR EXACT SURVIVORS")
    print(f"database={database}")
    print(f"ordinary_incumbent_prepercent={ORDINARY_INCUMBENT:.3f}")
    print(f"remaining_enlivening_headroom={headroom:.3f}")
    print()
    print("EXACT CONSTRAINED SURVIVORS")
    for row in exact_rows:
        print(
            f"set={row.set_name!r} pieces={row.piece_count} structural={row.structural!r} "
            f"special_ceiling={row.special_ceiling:.3f} optimistic_total={row.optimistic_total!r} "
            f"dominated={row.dominated} witness_sets={row.witness_sets!r}"
        )
    print()
    print("SEARCH-STATE / FORMULA CLOSURES")
    print(f"oakensoul_capacity_upper={float(oak_upper or 0.0):.3f}")
    print(f"oakensoul_minor_endurance_duplicate={oak_duplicate_named_buff}")
    print(f"oakensoul_dominated={oak_dominated}")
    print(f"twice_born_capacity_upper={float(tbs_upper or 0.0):.3f}")
    print(f"twice_born_second_mundus_direct_stamina_recovery={non_serpent_direct:.3f}")
    print(f"twice_born_granted_full_enlivening_headroom={headroom:.3f}")
    print(f"twice_born_optimistic_total={float(tbs_total_upper or 0.0):.3f}")
    print(f"twice_born_dominated={tbs_dominated}")
    print(f"bastion_capacity_upper={float(bastion_upper or 0.0):.3f}")
    print(f"bastion_three_stack_ceiling={float(bastion_stack or 0.0):.3f}")
    print(f"bastion_optimistic_total={float(bastion_total or 0.0):.3f}")
    print(f"bastion_dominated={bastion_dominated}")
    print()
    print("PROOF GATES")
    print(f"medium_armor_physical_filter_proven={filtered.denominator_proven}")
    print(f"ordinary_denominator_prerequisite_proven={ordinary.ordinary_denominator_proven}")
    print(f"exact_survivors_all_dominated={exact_all_dominated}")
    print(f"oakensoul_closed={oak_dominated}")
    print(f"twice_born_star_closed={tbs_dominated}")
    print(f"bastion_closed={bastion_dominated}")
    print(f"audit_unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"special_named_gear_denominator_closed={closed}")
    print(
        "NEXT_STEP=compose the Stamina Recovery active-bar/context frontier with Major Endurance, "
        "Continuous Attack, Battle Rush, and Domination"
        if closed
        else "NEXT_STEP=close only the reported exact-survivor blockers"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
