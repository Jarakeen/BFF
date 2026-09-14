from __future__ import annotations

"""Prove seven-Heavy compatibility for gap-closing Health Recovery Ultimate loadouts."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_gear_set_topology_catalog_service import (
    ACTIVE_SNAPSHOT_SET_UNITS,
    ExtremeGearSetCountTopology,
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    return parser


def _minimal(
    rows: tuple[UltimateSourceLoadoutCombination, ...],
) -> tuple[UltimateSourceLoadoutCombination, ...]:
    output: list[UltimateSourceLoadoutCombination] = []
    for row in rows:
        row_ids = frozenset(row.source_ids)
        if any(frozenset(other.source_ids) < row_ids for other in rows):
            continue
        output.append(row)
    return tuple(output)


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)
    source = Path(args.source)
    if not source.is_file():
        print(f"source_missing={source}")
        return 2

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

    # The preceding frontier audit proves Exhilarating Drain dominated for this
    # Health Recovery route because Vampire stage 1's global recovery penalty is
    # already larger than the best-case Strategic Reserve gain.
    dominated_ids = {"exhilarating_drain"}
    surviving_rows = tuple(
        row
        for row, review in reviews
        if review.status
        in {
            UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION,
            UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED,
        }
        and row.source_id not in dominated_ids
    )

    loadout_candidates = tuple(
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
    loadout_catalog = UltimateSourceLoadoutCombinationService.search(
        loadout_candidates,
        named_catalog.sets,
        required_ultimate_gap=remaining_gap,
    )
    heavy_service = ExtremeNamedGearArmorWeightRealizationService(database)

    heavy_compatible: list[UltimateSourceLoadoutCombination] = []
    heavy_incompatible: list[UltimateSourceLoadoutCombination] = []
    heavy_unresolved: list[tuple[UltimateSourceLoadoutCombination, tuple[str, ...]]] = []

    for loadout in loadout_catalog.gap_closing_combinations:
        if loadout.required_set_units == 0:
            heavy_compatible.append(loadout)
            continue
        if loadout.witness is None:
            heavy_unresolved.append(
                (loadout, ("Physical loadout witness missing for named-set requirement",))
            )
            continue

        named_rows = tuple(
            named_catalog.by_set_id(set_id) for set_id in loadout.witness.set_ids
        )
        if any(row is None for row in named_rows):
            heavy_unresolved.append(
                (loadout, ("Named-set eligibility disappeared after physical witness",))
            )
            continue

        topology = ExtremeGearSetCountTopology(
            counts=loadout.witness.counts,
            unused_units=(
                ACTIVE_SNAPSHOT_SET_UNITS - sum(loadout.witness.counts)
            ),
            total_units=ACTIVE_SNAPSHOT_SET_UNITS,
        )
        result = heavy_service.find_witness(
            topology,
            tuple(row for row in named_rows if row is not None),
            required_armor_weight="Heavy",
        )
        if result.unresolved:
            heavy_unresolved.append((loadout, result.unresolved))
        elif result.compatible:
            heavy_compatible.append(loadout)
        else:
            heavy_incompatible.append(loadout)

    compatible_rows = tuple(heavy_compatible)
    minimal_compatible = _minimal(compatible_rows)
    heavy_denominator_proven = (
        loadout_catalog.physical_set_slot_denominator_proven
        and not heavy_unresolved
    )

    print("EXTREME HEALTH RECOVERY SEVEN-HEAVY ULTIMATE LOADOUT AUDIT")
    print(f"database={database}")
    print(f"source={source}")
    print("required_armor_weight=Heavy")
    print(f"remaining_ultimate_gap={remaining_gap:.3f}")
    print(f"gap_closing_loadouts={len(loadout_catalog.gap_closing_combinations)}")
    print(f"seven_heavy_compatible_loadouts={len(compatible_rows)}")
    print(f"seven_heavy_incompatible_loadouts={len(heavy_incompatible)}")
    print(f"seven_heavy_unresolved_loadouts={len(heavy_unresolved)}")
    print(f"minimal_seven_heavy_gap_closers={len(minimal_compatible)}")

    for row in minimal_compatible:
        print(
            "  heavy_minimal_closer: "
            f"sources={row.source_ids!r} "
            f"ultimate_ceiling={row.total_ultimate_ceiling:.3f} "
            f"set_units={row.required_set_units} "
            f"stochastic={row.stochastic} "
            f"action_proof_required={row.action_proof_required} "
            f"runtime_proven={row.runtime_proven}"
        )

    for row in heavy_incompatible:
        print(
            "  heavy_rejected: "
            f"sources={row.source_ids!r} set_names={row.required_set_names!r}"
        )
    for row, reasons in heavy_unresolved:
        for reason in reasons:
            print(
                "  heavy_unresolved: "
                f"sources={row.source_ids!r} reason={reason}"
            )

    print(
        "seven_heavy_named_set_legality_proven="
        f"{heavy_denominator_proven}"
    )
    print("whole_build_health_recovery_scoring_pending=True")
    print("ultimate_source_numeric_legality_proven=False")
    print(
        "NEXT_STEP=score whole-build Health Recovery for seven-Heavy-compatible "
        "gap-closing loadouts, including displaced incumbent gear bonuses and "
        "stochastic/action-runtime proof obligations"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
