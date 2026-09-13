from __future__ import annotations

"""Inventory canonical Health Recovery equipment, jewelry, Mundus, and CP frontiers.

This is a proof-frontier audit, not whole-record scoring. It compares the reviewed
Heavy-Armor trait/Mundus states, resolves the strongest Health Recovery jewelry
glyph with Gold Infused scaling, and projects canonical Champion Point candidates.
Unsupported CP mechanics are screened by direct Health Recovery relevance, then
relevant conditional mechanics receive individual numeric ceilings. Champion Bar
loadout legality remains a separate proof obligation.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.item_base_stats import ARMOR_INVIGORATING_RECOVERY_GOLD
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from minmax.passive_math import heavy_armor_constitution_health_recovery_percent
from services.extreme_champion_point_objective_service import (
    ExtremeChampionPointObjectiveService,
)
from services.extreme_divines_mundus_objective_service import (
    ExtremeDivinesMundusObjectiveService,
)
from services.extreme_health_recovery_champion_point_branch_service import (
    ExtremeHealthRecoveryChampionPointBranchService,
)
from services.extreme_health_recovery_champion_point_screening_service import (
    ExtremeHealthRecoveryChampionPointScreeningService,
)
from services.extreme_health_recovery_jewelry_projection_service import (
    ExtremeHealthRecoveryJewelryProjectionService,
)


OBJECTIVE = "health_recovery"
HEAVY_PIECES = 7
ARMOR_TRAIT_SOURCES = 7


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _screen_unresolved_cp(repository, candidates):
    relevant = []
    irrelevant = []
    missing = []
    for candidate in candidates:
        record = repository.get(candidate.name)
        if record is None:
            missing.append(candidate)
            continue
        screening = ExtremeHealthRecoveryChampionPointScreeningService.screen(record)
        if screening.relevant:
            relevant.append((candidate, screening))
        else:
            irrelevant.append((candidate, screening))
    return tuple(relevant), tuple(irrelevant), tuple(missing)


def _classify_screened(rows):
    return tuple(
        (
            candidate,
            screening,
            ExtremeHealthRecoveryChampionPointBranchService.classify(screening.record),
        )
        for candidate, screening in rows
    )


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    print("EXTREME HEALTH RECOVERY EQUIPMENT FRONTIER")
    print(f"database={database}")
    print("mode=canonical_equipment_frontier_plus_cp_semantic_branches")
    print()

    print("HEAVY ARMOR / MUNDUS TRAIT FRONTIER")
    constitution = heavy_armor_constitution_health_recovery_percent(HEAVY_PIECES)
    print(f"heavy_armor_pieces={HEAVY_PIECES}")
    print(f"constitution_percent={constitution * 100:.3f}")
    print(f"invigorating_flat_per_armor_piece={ARMOR_INVIGORATING_RECOVERY_GOLD:.3f}")

    mundus_repository = MundusRepository(database)
    armor_rows: list[tuple[float, int, int, float, float]] = []
    for divines_count in range(ARMOR_TRAIT_SOURCES + 1):
        invigorating_count = ARMOR_TRAIT_SOURCES - divines_count
        mundus = ExtremeDivinesMundusObjectiveService.candidate_for_name(
            mundus_repository,
            "The Steed",
            OBJECTIVE,
            armor_divines_count=divines_count,
            shield_divines=False,
        )
        mundus_delta = mundus.projected_delta
        if mundus_delta is None:
            print(
                f"  armor_divines={divines_count} unresolved_mundus="
                + "; ".join(mundus.mundus.unresolved)
            )
            continue
        invigorating_flat = invigorating_count * float(ARMOR_INVIGORATING_RECOVERY_GOLD)
        direct_flat = float(mundus_delta) + invigorating_flat
        armor_rows.append(
            (direct_flat, divines_count, invigorating_count, float(mundus_delta), invigorating_flat)
        )
        print(
            f"  armor_divines={divines_count} armor_invigorating={invigorating_count} "
            f"steed_delta={float(mundus_delta):.3f} invigorating_flat={invigorating_flat:.3f} "
            f"direct_flat={direct_flat:.3f}"
        )

    armor_rows.sort(key=lambda row: (-row[0], -row[1]))
    best_armor = armor_rows[0] if armor_rows else None
    if best_armor is None:
        print("best_armor_trait_state=<unresolved>")
    else:
        print(
            f"best_armor_trait_state=divines:{best_armor[1]},invigorating:{best_armor[2]} "
            f"steed_delta={best_armor[3]:.3f} invigorating_flat={best_armor[4]:.3f} "
            f"direct_flat={best_armor[0]:.3f}"
        )
    print("shield_trait_state=separate_weapon_legality_axis_not_claimed_here")
    print()

    print("JEWELRY GLYPH / TRAIT FRONTIER")
    jewelry = ExtremeHealthRecoveryJewelryProjectionService(
        JewelryGlyphEffectRepository(database),
        JewelryTraitRepository(database),
    ).build()
    print(f"glyphs_reviewed={jewelry.glyphs_reviewed}")
    print(f"relevant_glyphs={jewelry.relevant_glyphs!r}")
    print(f"strongest_glyph_name={jewelry.strongest_glyph_name!r}")
    print(f"base_flat_per_slot={jewelry.base_flat_per_slot!r}")
    print(f"gold_infused_percent={jewelry.infused_percent!r}")
    print(f"infused_flat_per_slot={jewelry.infused_flat_per_slot!r}")
    print(f"three_slot_infused_flat={jewelry.three_slot_infused_flat!r}")
    print(f"jewelry_denominator_proven={jewelry.denominator_proven}")
    for problem in jewelry.unresolved:
        print(f"  jewelry_unresolved: {problem}")
    print()

    print("CHAMPION POINT FRONTIER")
    cp_repository = ChampionPointStaticRepository(database)
    baseline = ExtremeChampionPointObjectiveService.non_slottable_baseline_for_objective(
        cp_repository,
        OBJECTIVE,
    )
    slottable = ExtremeChampionPointObjectiveService.slottable_candidates_for_objective(
        cp_repository,
        OBJECTIVE,
    )
    positive_slottable = tuple(
        row
        for row in slottable
        if row.reviewed_delta is not None and float(row.reviewed_delta) > 0.0
    )
    unresolved_slottable = tuple(row for row in slottable if row.reviewed_delta is None)

    relevant_non_slottable, irrelevant_non_slottable, missing_non_slottable = _screen_unresolved_cp(
        cp_repository,
        baseline.unresolved_candidates,
    )
    relevant_slottable, irrelevant_slottable, missing_slottable = _screen_unresolved_cp(
        cp_repository,
        unresolved_slottable,
    )
    classified_non_slottable = _classify_screened(relevant_non_slottable)
    classified_slottable = _classify_screened(relevant_slottable)
    incomplete_branches = tuple(
        row
        for row in (*classified_non_slottable, *classified_slottable)
        if not row[2].complete
    )

    print(f"non_slottable_candidates_reviewed={len(baseline.resolved_candidates) + len(baseline.unresolved_candidates)}")
    print(f"non_slottable_reviewed_lower_bound={baseline.reviewed_lower_bound:.3f}")
    print(f"non_slottable_raw_unresolved={len(baseline.unresolved_candidates)}")
    print(f"non_slottable_relevance_pruned={len(irrelevant_non_slottable)}")
    print(f"non_slottable_health_recovery_relevant={len(relevant_non_slottable)}")
    for row in baseline.resolved_candidates:
        if float(row.reviewed_delta or 0.0) > 0.0:
            print(f"  non_slottable_positive: {row.name} delta={float(row.reviewed_delta):.3f}")
    for candidate, screening, branch in classified_non_slottable:
        print(
            f"  non_slottable_branch: {candidate.name} kind={branch.kind.value} "
            f"flat_ceiling={branch.flat_ceiling!r} stages={branch.stages!r} "
            f"condition={branch.condition or '<none>'} complete={branch.complete}"
        )
        for problem in branch.unresolved:
            print(f"    unresolved: {problem}")
    for candidate in missing_non_slottable:
        print(f"  non_slottable_screening_missing_record: {candidate.name}")

    print(f"slottable_candidates_reviewed={len(slottable)}")
    print(f"positive_slottable_candidates={len(positive_slottable)}")
    for row in positive_slottable:
        print(f"  slottable_positive: {row.name} delta={float(row.reviewed_delta):.3f}")
    print(f"slottable_raw_unresolved={len(unresolved_slottable)}")
    print(f"slottable_relevance_pruned={len(irrelevant_slottable)}")
    print(f"slottable_health_recovery_relevant={len(relevant_slottable)}")
    for candidate, screening, branch in sorted(
        classified_slottable,
        key=lambda row: (-(row[2].flat_ceiling or 0.0), row[0].name.casefold()),
    ):
        print(
            f"  slottable_branch: {candidate.name} kind={branch.kind.value} "
            f"flat_ceiling={branch.flat_ceiling!r} stages={branch.stages!r} "
            f"condition={branch.condition or '<none>'} complete={branch.complete}"
        )
        for problem in branch.unresolved:
            print(f"    unresolved: {problem}")
    for candidate in missing_slottable:
        print(f"  slottable_screening_missing_record: {candidate.name}")
    print()

    cp_semantic_relevance_denominator_screened = not missing_non_slottable and not missing_slottable
    cp_individual_branch_denominator_proven = (
        cp_semantic_relevance_denominator_screened and not incomplete_branches
    )
    cp_loadout_legality_pending = bool(positive_slottable or classified_slottable)
    print(f"cp_semantic_relevance_denominator_screened={cp_semantic_relevance_denominator_screened}")
    print(f"cp_individual_branch_denominator_proven={cp_individual_branch_denominator_proven}")
    print(f"cp_loadout_legality_pending={cp_loadout_legality_pending}")

    unresolved_count = (
        len(jewelry.unresolved)
        + len(incomplete_branches)
        + len(missing_non_slottable)
        + len(missing_slottable)
        + (1 if cp_loadout_legality_pending else 0)
    )
    print(f"equipment_frontier_unresolved_count={unresolved_count}")
    if not cp_individual_branch_denominator_proven:
        print("NEXT_STEP=close remaining Health Recovery Champion Point branch grammars before loadout scoring")
        return 2
    if cp_loadout_legality_pending:
        print("NEXT_STEP=prove legal Champion Bar loadout dominance across Rejuvenation and the classified conditional recovery stars")
        return 2
    if unresolved_count:
        print("NEXT_STEP=close remaining equipment proof obligations")
        return 2
    print("NEXT_STEP=compose the ordinary Health Recovery incumbent from closed equipment, CP, class, race, consumable, and ordinary-set layers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
