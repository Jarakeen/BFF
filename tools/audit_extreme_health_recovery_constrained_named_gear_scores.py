from __future__ import annotations

"""Score seven-Heavy Ultimate-source loadouts through shared named-gear search.

The comparison is intentionally relative.  Shared race/class/passive/Mundus/trait/
jewelry/runtime components cancel between the ordinary incumbent and a constrained
Ultimate-source branch.  This audit therefore measures the exact-flat named-gear
Health Recovery displaced by each required source loadout and compares that loss to
the +330 Strategic Reserve gain from moving 390 -> 500 stored Ultimate.

Conditional/non-flat named-gear branches and stochastic/action-runtime obligations
remain explicit proof gates; this audit never promotes them to deterministic truth.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.gear_set_repository import GearSetRepository
from services.extreme_armor_weight_filtered_slot_eligibility_service import (
    ExtremeArmorWeightFilteredSlotEligibilityService,
)
from services.extreme_constrained_named_gear_exact_flat_search_service import (
    ExtremeConstrainedNamedGearExactFlatSearchService,
    ExtremeNamedGearRequirement,
)
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceService
from services.extreme_gear_set_topology_catalog_service import (
    ACTIVE_SNAPSHOT_SET_UNITS,
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalogService,
)
from services.extreme_named_gear_armor_weight_realization_service import (
    ExtremeNamedGearArmorWeightRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.ultimate_source_loadout_combination_service import (
    UltimateSourceLoadoutCandidate,
    UltimateSourceLoadoutCombination,
    UltimateSourceLoadoutCombinationService,
)
from services.ultimate_source_reference_frontier_service import (
    UltimateSourceReferenceFrontierService,
    UltimateSourceRouteStatus,
)
from services.ultimate_source_runtime_legality_service import (
    UltimateSourceRuntimeLegalityService,
    UltimateSourceRuntimeStatus,
)
from tools.audit_extreme_health_recovery_ultimate_source_frontier import (
    DEFAULT_SOURCE,
    _ACTION_PROOF_SOURCE_IDS,
    _SET_REQUIREMENTS,
    _STOCHASTIC_SOURCE_IDS,
    _TRIGGER_WITNESSES,
    _canonical_matches,
)


OBJECTIVE = "health_recovery"
STRATEGIC_RESERVE_GAIN = 330.0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    return parser


def _heavy_compatible_loadouts(
    database: Path,
    source: Path,
):
    frontier_rows = UltimateSourceReferenceFrontierService.parse(
        source.read_text(encoding="utf-8", errors="replace")
    )
    review_candidates = tuple(
        row
        for row in frontier_rows
        if row.route_status
        in {
            UltimateSourceRouteStatus.SEARCH_STATE_MUTATION,
            UltimateSourceRouteStatus.EXACT_REVIEW_REQUIRED,
        }
    )
    reviews = tuple(
        (
            row,
            UltimateSourceRuntimeLegalityService.review(
                row.source_id,
                canonical_records=_canonical_matches(database, row.label, row.source_id),
                trigger_seconds=_TRIGGER_WITNESSES.get(row.source_id, ()),
            ),
        )
        for row in review_candidates
    )
    review_by_id = {row.source_id: review for row, review in reviews}
    reviewed_increment = sum(
        review.generated_ultimate_ceiling
        for _row, review in reviews
        if review.status is UltimateSourceRuntimeStatus.COMPATIBLE_INCREMENT
    )
    remaining_gap = max(0.0, 114.0 - reviewed_increment)
    surviving_rows = tuple(
        row
        for row, review in reviews
        if review.status
        in {
            UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION,
            UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
        }
        and row.source_id != "exhilarating_drain"
    )
    candidates = tuple(
        UltimateSourceLoadoutCandidate(
            source_id=row.source_id,
            label=row.label,
            generated_ultimate_ceiling=review_by_id[row.source_id].generated_ultimate_ceiling,
            required_set_name=_SET_REQUIREMENTS.get(row.source_id, (None, 0))[0],
            required_set_pieces=_SET_REQUIREMENTS.get(row.source_id, (None, 0))[1],
            stochastic=row.source_id in _STOCHASTIC_SOURCE_IDS,
            action_proof_required=row.source_id in _ACTION_PROOF_SOURCE_IDS,
        )
        for row in surviving_rows
    )

    named_catalog = ExtremeNamedGearSetSlotEligibilityService(database).build()
    combination_catalog = UltimateSourceLoadoutCombinationService.search(
        candidates,
        named_catalog.sets,
        required_ultimate_gap=remaining_gap,
    )
    heavy_service = ExtremeNamedGearArmorWeightRealizationService(database)
    compatible: list[UltimateSourceLoadoutCombination] = []
    unresolved: list[str] = []

    for loadout in combination_catalog.gap_closing_combinations:
        if loadout.required_set_units == 0:
            compatible.append(loadout)
            continue
        if loadout.witness is None:
            unresolved.append(
                f"{loadout.source_ids!r}: physical named-set witness missing before Heavy review"
            )
            continue
        named_rows = tuple(named_catalog.by_set_id(set_id) for set_id in loadout.witness.set_ids)
        if any(row is None for row in named_rows):
            unresolved.append(
                f"{loadout.source_ids!r}: named-set eligibility missing after combination proof"
            )
            continue
        topology = ExtremeGearSetCountTopology(
            counts=loadout.witness.counts,
            unused_units=ACTIVE_SNAPSHOT_SET_UNITS - sum(loadout.witness.counts),
            total_units=ACTIVE_SNAPSHOT_SET_UNITS,
        )
        result = heavy_service.find_witness(
            topology,
            tuple(row for row in named_rows if row is not None),
            required_armor_weight="Heavy",
        )
        if result.unresolved:
            unresolved.extend(
                f"{loadout.source_ids!r}: {reason}" for reason in result.unresolved
            )
        elif result.compatible:
            compatible.append(loadout)

    return tuple(compatible), named_catalog, remaining_gap, tuple(dict.fromkeys(unresolved))


def _requirements(loadout: UltimateSourceLoadoutCombination) -> tuple[ExtremeNamedGearRequirement, ...]:
    rows: list[ExtremeNamedGearRequirement] = []
    for source_id in loadout.source_ids:
        set_name, piece_count = _SET_REQUIREMENTS.get(source_id, (None, 0))
        if set_name and int(piece_count) > 0:
            rows.append(
                ExtremeNamedGearRequirement(
                    set_name=str(set_name),
                    piece_count=int(piece_count),
                )
            )
    return tuple(rows)


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    source = Path(args.source)
    if not source.is_file():
        print(f"source_missing={source}")
        return 2

    heavy_loadouts, raw_eligibility, remaining_gap, loadout_unresolved = (
        _heavy_compatible_loadouts(database, source)
    )
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(
        database,
        raw_eligibility,
        required_armor_weight="Heavy",
    )

    gear_repository = GearSetRepository(database)
    topology_catalog = ExtremeGearSetTopologyCatalogService(gear_repository).build()
    breakpoints = ExtremeGearSetBonusBreakpointService(gear_repository).build()
    relevance = ExtremeGearSetObjectiveRelevanceService(gear_repository).build(
        OBJECTIVE,
        breakpoints,
    )

    print("EXTREME HEALTH RECOVERY CONSTRAINED NAMED-GEAR SCORE AUDIT")
    print(f"database={database}")
    print(f"source={source}")
    print("objective=health_recovery")
    print("required_armor_weight=Heavy")
    print(f"remaining_ultimate_gap={remaining_gap:.3f}")
    print(f"seven_heavy_gap_closing_loadouts={len(heavy_loadouts)}")
    print(f"armor_weight_filter_denominator_proven={filtered.denominator_proven}")
    for problem in filtered.unresolved:
        print(f"  armor_weight_unresolved={problem}")
    for problem in loadout_unresolved:
        print(f"  loadout_unresolved={problem}")

    if not filtered.denominator_proven or loadout_unresolved:
        print("NEXT_STEP=close armor-weight/loadout evidence before constrained scoring")
        return 2

    incumbent_search = ExtremeConstrainedNamedGearExactFlatSearchService(
        breakpoints=breakpoints,
        eligibility=filtered.catalog,
        relevance=relevance,
        requirements=(),
    ).search(topology_catalog)
    incumbent = incumbent_search.best_exact_flat_delta
    print()
    print("SEVEN-HEAVY ORDINARY EXACT-FLAT INCUMBENT")
    print(f"incumbent_score={incumbent!r}")
    print(f"incumbent_witnesses={len(incumbent_search.realizations)}")
    print(f"special_or_nonflat_pairs={len(incumbent_search.special_or_nonflat_pairs)}")
    print(f"ordinary_exact_flat_branch_proven={incumbent_search.exact_flat_branch_proven}")

    rows: list[tuple[float, UltimateSourceLoadoutCombination, object]] = []
    unresolved_count = 0
    print()
    print("CONSTRAINED ULTIMATE-SOURCE LOADOUT SCORES")
    for loadout in heavy_loadouts:
        requirements = _requirements(loadout)
        search = ExtremeConstrainedNamedGearExactFlatSearchService(
            breakpoints=breakpoints,
            eligibility=filtered.catalog,
            relevance=relevance,
            requirements=requirements,
        ).search(topology_catalog)
        if search.best_exact_flat_delta is None or incumbent is None:
            unresolved_count += 1
            print(
                f"  unresolved: sources={loadout.source_ids!r} "
                f"requirements={tuple((r.set_name, r.piece_count) for r in requirements)!r} "
                f"reasons={search.unresolved!r}"
            )
            continue
        displaced = float(incumbent) - float(search.best_exact_flat_delta)
        net = STRATEGIC_RESERVE_GAIN - displaced
        rows.append((net, loadout, search))
        print(
            f"  scored: sources={loadout.source_ids!r} "
            f"gear_score={float(search.best_exact_flat_delta):.3f} "
            f"displaced_recovery={displaced:.3f} "
            f"strategic_reserve_gain={STRATEGIC_RESERVE_GAIN:.3f} "
            f"net_vs_ordinary_incumbent={net:.3f} "
            f"stochastic={loadout.stochastic} "
            f"action_proof_required={loadout.action_proof_required} "
            f"runtime_proven={loadout.runtime_proven}"
        )

    rows.sort(key=lambda item: (-item[0], item[1].source_ids))
    print()
    print("RANKED EXACT-FLAT BRANCH")
    for net, loadout, search in rows:
        print(
            f"  rank: net={net:.3f} sources={loadout.source_ids!r} "
            f"gear_score={float(search.best_exact_flat_delta or 0.0):.3f} "
            f"stochastic={loadout.stochastic} "
            f"action_proof_required={loadout.action_proof_required}"
        )

    dominated = tuple(
        loadout.source_ids
        for net, loadout, _search in rows
        if net < -1e-9
    )
    positive = tuple(
        loadout.source_ids
        for net, loadout, _search in rows
        if net > 1e-9
    )
    tied = tuple(
        loadout.source_ids
        for net, loadout, _search in rows
        if abs(net) <= 1e-9
    )
    special_pairs = tuple(incumbent_search.special_or_nonflat_pairs)

    print()
    print(f"scored_loadouts={len(rows)}")
    print(f"unresolved_loadouts={unresolved_count}")
    print(f"ordinary_branch_dominated_loadouts={len(dominated)}")
    print(f"ordinary_branch_positive_loadouts={len(positive)}")
    print(f"ordinary_branch_tied_loadouts={len(tied)}")
    print(f"special_nonflat_named_gear_pairs_pending={len(special_pairs)}")
    print("ultimate_source_numeric_legality_proven=False")
    print("whole_build_health_recovery_scoring_pending=" + str(bool(special_pairs or unresolved_count)))

    if unresolved_count:
        print("NEXT_STEP=close constrained named-set objective semantics that failed exact-flat scoring")
        return 2
    if special_pairs:
        print(
            "NEXT_STEP=compose the existing Health Recovery special/non-flat named-gear "
            "branches against these constrained exact-flat winners before final route dominance"
        )
        return 2
    print(
        "NEXT_STEP=apply stochastic/action-runtime proof to the exact-flat surviving routes "
        "and close final Health Recovery route dominance"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
