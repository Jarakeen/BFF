from __future__ import annotations

"""Audit the current proof boundary for the next Extreme objective: Weapon Damage.

This deliberately reuses the existing canonical structural/global-search stack. It
reports the strongest currently executable lower bound and, more importantly, the
remaining deferred axes that prevent a global record claim. No new ESO math lives
here.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_record_result import ExtremeRecordProofStatus
from services.extreme_structural_core_stat_record_service import (
    ExtremeStructuralCoreStatRecordService,
)
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
)

OBJECTIVE = "weapon_damage"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def _print_record(label: str, record) -> None:
    print(label)
    print(f"proof_status={record.proof_status.value!r}")
    print(f"raw_value={record.raw_value!r}")
    print(f"globally_proven={record.globally_proven}")
    print(f"denominator_proven={record.search_coverage.denominator_proven}")
    print(f"candidates_screened={record.search_coverage.candidates_screened!r}")
    print(f"candidates_optimized={record.search_coverage.candidates_optimized!r}")
    print(f"searched_count={len(record.search_coverage.searched)}")
    for item in record.search_coverage.searched:
        print(f"  searched: {item}")
    print(f"omitted_count={len(record.search_coverage.omitted)}")
    for item in record.search_coverage.omitted:
        print(f"  omitted: {item}")
    print(f"unresolved_count={len(record.unresolved)}")
    for item in record.unresolved:
        print(f"  unresolved: {item}")
    print(f"ceiling_threat_count={len(record.ceiling_threats)}")
    for item in record.ceiling_threats:
        print(
            "  threat: "
            f"source={item.source!r} lower={item.lower_bound!r} "
            f"upper={item.upper_bound!r} reason={item.reason!r}"
        )
    build = record.winning_build
    if isinstance(build, dict):
        print(f"winner_race={build.get('race')!r}")
        print(f"winner_base_class={build.get('base_class')!r}")
        print(f"winner_class_skill_lines={tuple(build.get('class_skill_lines') or ())!r}")
        print(f"winner_active_bar={build.get('active_bar')!r}")
        print(f"winner_mundus={build.get('mundus')!r}")
        print(f"winner_food={build.get('food')!r}")
        print(f"winner_potion={build.get('potion')!r}")
        print(f"winner_active_buffs={tuple(build.get('active_buffs') or ())!r}")
        gear = build.get("named_gear") or build.get("gear") or build.get("named_sets")
        if gear is not None:
            print(f"winner_named_gear={gear!r}")
    print()


def main() -> int:
    database = Path(_parser().parse_args().database)

    structural = ExtremeStructuralCoreStatRecordService(database_path=database).record(OBJECTIVE)
    expanded = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        database_path=database
    ).record(OBJECTIVE)

    print("EXTREME WEAPON DAMAGE FOUNDATION AUDIT")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print()
    _print_record("STRUCTURAL LOWER BOUND", structural)
    _print_record("EXPANDED CURRENT FRONTIER", expanded)

    improvement = None
    if structural.raw_value is not None and expanded.raw_value is not None:
        improvement = float(expanded.raw_value) - float(structural.raw_value)
    print("FOUNDATION SUMMARY")
    print(f"expanded_over_structural_delta={improvement!r}")
    print(f"current_frontier_status={expanded.proof_status.value!r}")
    print(f"current_frontier_value={expanded.raw_value!r}")
    print(f"remaining_axis_count={len(expanded.search_coverage.omitted)}")
    print(f"unresolved_count={len(expanded.unresolved)}")
    print(f"ceiling_threat_count={len(expanded.ceiling_threats)}")
    foundation_ready = bool(
        expanded.raw_value is not None
        and expanded.proof_status in {
            ExtremeRecordProofStatus.LOWER_BOUND,
            ExtremeRecordProofStatus.CONDITIONAL,
            ExtremeRecordProofStatus.PROVEN,
        }
    )
    print(f"foundation_numeric_frontier_available={foundation_ready}")
    print(f"weapon_damage_record_closed={expanded.globally_proven}")
    print(
        "NEXT_STEP=close only the reported omitted/unresolved Weapon Damage axes; reuse shared power/runtime services before adding any new mechanic owner"
        if not expanded.globally_proven
        else "NEXT_STEP=publish the already closed Weapon Damage record"
    )
    return 0 if foundation_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
