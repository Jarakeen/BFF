from __future__ import annotations

import pytest

from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_gear_set_objective_service import (
    ExtremeGearSetObjectiveCandidate,
)


@pytest.mark.parametrize(
    "objective",
    ("healing_done", "critical_healing", "spell_damage", "weapon_damage"),
)
def test_heartland_weapon_trait_effectiveness_is_h1_mechanic_complete(
    objective: str,
) -> None:
    blocker = (
        "Heartland Conqueror (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Increase the effectiveness of your Weapon Traits by 100%. "
        "This does not affect Ornate or Intricate traits."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Heartland Conqueror",
        category="Test",
        equipped_piece_count=5,
        objective_key=objective,
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    review = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert review.h1_mechanic_complete is True
    assert review.h1_positive_modifier_proven is True
    assert review.remaining_blockers == ()
    assert review.ignored_blockers == (blocker,)


def test_heartland_mapping_does_not_leak_to_resource_objectives() -> None:
    blocker = (
        "Heartland Conqueror (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) Increase the effectiveness of your Weapon Traits by 100%."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Heartland Conqueror",
        category="Test",
        equipped_piece_count=5,
        objective_key="max_magicka",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    review = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert review.h1_mechanic_complete is False
    assert review.remaining_blockers == (blocker,)
