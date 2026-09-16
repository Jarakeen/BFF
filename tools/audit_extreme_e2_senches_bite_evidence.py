from __future__ import annotations

"""Read-only evidence audit for Senche's Bite H1 denominator review."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.config import get_data_dir
from minmax.gear_set_repository import GearSetRepository
from services.extreme_actual_heal_gear_condition_relevance_service import (
    ExtremeActualHealGearConditionRelevanceService,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


SET_NAME = "Senche's Bite"
OBJECTIVES = ("critical_healing",)


def main() -> int:
    database = get_data_dir() / "eso.db"
    repository = GearSetRepository(database)
    repository.preload_all_static()

    gear_set = repository.get_set(SET_NAME)
    print("EXTREME E2 SENCHE'S BITE EVIDENCE AUDIT")
    print(f"database={database}")
    print(f"set_found={gear_set is not None}")
    if gear_set is None:
        return 1

    print(f"set_id={gear_set.id}")
    print(f"category={gear_set.category!r}")
    print(f"max_equip_count={gear_set.max_equip_count!r}")
    print("BONUSES")
    for bonus in repository.get_bonuses(gear_set.id):
        print(f"  {bonus.piece_count}pc: {bonus.description!r}")

    print("H1 OBJECTIVE ROWS")
    for objective in OBJECTIVES:
        row = ExtremeGearSetObjectiveService.candidate_for_set(
            repository,
            SET_NAME,
            objective,
        )
        review = ExtremeActualHealGearConditionRelevanceService.review(row)
        print(
            f"  objective={objective} reviewed_delta={row.reviewed_delta:.6f} "
            f"shared_mechanic_complete={row.mechanic_complete} "
            f"h1_mechanic_complete={review.h1_mechanic_complete} "
            f"h1_positive_modifier_proven={review.h1_positive_modifier_proven}"
        )
        print(f"    unresolved_count={len(row.unresolved)}")
        for index, message in enumerate(row.unresolved, start=1):
            print(f"    unresolved[{index}]={message!r}")
            print(f"      ignored_by_h1={message in review.ignored_blockers}")
            print(f"      remaining_in_h1={message in review.remaining_blockers}")
        for effect in row.source_effects:
            print(
                "    effect: "
                f"stat={getattr(effect.stat, 'value', effect.stat)} "
                f"operation={effect.operation.value} value={effect.value} "
                f"condition={effect.condition!r} source={effect.source!r}"
            )

    print(
        "NEXT_STEP=use the exact canonical blocker text above to tighten only Senche's Bite H1 review"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
