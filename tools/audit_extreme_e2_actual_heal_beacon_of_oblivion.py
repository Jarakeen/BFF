from __future__ import annotations

"""Read-only canonical objective audit for Beacon of Oblivion."""

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


def main() -> int:
    database = get_data_dir() / "eso.db"
    repository = GearSetRepository(database)
    objective_row = ExtremeGearSetObjectiveService.candidate_for_set(
        repository,
        "Beacon of Oblivion",
        "healing_done",
    )
    h1_review = ExtremeActualHealGearConditionRelevanceService.review(objective_row)

    print("EXTREME E2 H1 BEACON OF OBLIVION OBJECTIVE AUDIT")
    print(f"database={database}")
    print(f"reviewed_delta={objective_row.reviewed_delta!r}")
    print(f"source_effect_count={len(objective_row.source_effects)}")
    for bonus in objective_row.source_bonuses:
        if int(bonus.piece_count) == 5:
            print(f"five_piece_description={str(bonus.description or '')!r}")
    for effect in objective_row.source_effects:
        stat = getattr(getattr(effect, "stat", None), "value", getattr(effect, "stat", None))
        operation = getattr(
            getattr(effect, "operation", None),
            "value",
            getattr(effect, "operation", None),
        )
        unit = getattr(getattr(effect, "unit", None), "value", getattr(effect, "unit", None))
        print(
            f"effect stat={stat!r} operation={operation!r} unit={unit!r} "
            f"value={effect.value!r} condition={effect.condition!r} source={effect.source!r}"
        )
    print(f"unresolved_count={len(objective_row.unresolved)}")
    for blocker in objective_row.unresolved:
        print(f"unresolved={blocker!r}")
    print(f"h1_mechanic_complete={h1_review.h1_mechanic_complete}")
    print(f"h1_positive_modifier_proven={h1_review.h1_positive_modifier_proven}")
    for blocker in h1_review.remaining_blockers:
        print(f"h1_remaining_blocker={blocker!r}")
    print(
        "NEXT_STEP=retain Beacon of Oblivion only with its explicit no-permanent-pet, "
        "Battle-Spirit-inactive H1 witness"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
