from __future__ import annotations

"""Inventory canonical Health Recovery equipment, jewelry, Mundus, and CP frontiers.

This is a proof-frontier audit, not whole-record scoring. It compares the reviewed
Heavy-Armor trait/Mundus states, resolves the strongest Health Recovery jewelry
glyph with Gold Infused scaling, and projects canonical Champion Point candidates.
Any unresolved CP mechanic remains explicit for objective-specific screening.
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


def main() -> int:
    args = _parser().parse_args()
    database = Path(args.database)

    print("EXTREME HEALTH RECOVERY EQUIPMENT FRONTIER")
    print(f"database={database}")
    print("mode=canonical_equipment_frontier_not_whole_record_scoring")
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
    print(f"non_slottable_candidates_reviewed={len(baseline.resolved_candidates) + len(baseline.unresolved_candidates)}")
    print(f"non_slottable_reviewed_lower_bound={baseline.reviewed_lower_bound:.3f}")
    print(f"non_slottable_unresolved={len(baseline.unresolved_candidates)}")
    for row in baseline.resolved_candidates:
        if float(row.reviewed_delta or 0.0) > 0.0:
            print(f"  non_slottable_positive: {row.name} delta={float(row.reviewed_delta):.3f}")
    for row in baseline.unresolved_candidates:
        print(f"  non_slottable_unresolved: {row.name}: {'; '.join(row.unresolved)}")
    print(f"slottable_candidates_reviewed={len(slottable)}")
    print(f"positive_slottable_candidates={len(positive_slottable)}")
    for row in positive_slottable:
        print(f"  slottable_positive: {row.name} delta={float(row.reviewed_delta):.3f}")
    print(f"slottable_unresolved={len(unresolved_slottable)}")
    for row in unresolved_slottable:
        print(f"  slottable_unresolved: {row.name}: {'; '.join(row.unresolved)}")
    print()

    unresolved_count = len(jewelry.unresolved) + len(baseline.unresolved_candidates) + len(unresolved_slottable)
    print(f"equipment_frontier_unresolved_count={unresolved_count}")
    if unresolved_count:
        print("NEXT_STEP=screen unresolved Champion Point mechanics for Health Recovery relevance, then close the ordinary equipment denominator")
        return 2
    print("NEXT_STEP=compose the ordinary Health Recovery incumbent from closed equipment, CP, class, race, consumable, and ordinary-set layers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
