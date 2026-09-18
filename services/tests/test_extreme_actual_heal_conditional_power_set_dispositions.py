from __future__ import annotations

import pytest

from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_gear_set_objective_service import (
    ExtremeGearSetObjectiveCandidate,
)


@pytest.mark.parametrize(
    ("set_name", "description"),
    (
        (
            "Briarheart",
            "(5 items) When you deal Critical Damage, you increase your Weapon and Spell Damage by 15-450 for 10 seconds. While this effect is active, dealing Critical Damage heals you for 95 Health. This effect can occur once every 15 seconds and the heal scales off the higher of your Max Magicka or Stamina.",
        ),
        (
            "Monolith of Storms",
            "(5 items) Dealing damage with a Storm Calling ability's initial hit or every 5th tick creates a Monolith near the enemy for 10 seconds, up to one every 1 second, up to 3 total. Your Monoliths within 28 meters of one another link together, dealing Shock Damage every 2 seconds. Each Monolith active grants you 100 Weapon and Spell Damage.",
        ),
        (
            "Moon Hunter",
            "(5 items) When your alchemical poison fires, increase your Weapon and Spell Damage by 12-547 for 8 seconds.",
        ),
        (
            "Moondancer",
            "(5 items) When you activate a synergy while in combat, you gain a shadow blessing that increases your Weapon and Spell Damage by 11-474 or a lunar blessing that increases your Magicka Recovery by 11-474 for 20 seconds.",
        ),
        (
            "Rallying Cry",
            "(5 items) When your healing critically strikes while Battle Spirit is active, you and group members within 12 meters of you gain Critical Resistance and Weapon and Spell Damage for 20 seconds.",
        ),
        (
            "Salvation",
            "(5 items) Reduces the cost of your Werewolf Transformation ability by 33%. While in Werewolf form, your Weapon and Spell Damage is increased by 5-150.",
        ),
        (
            "Scathing Mage",
            "(5 items) When you deal direct damage, you have a 20% chance to increase your Weapon and Spell Damage by 12-516 for 5 seconds.",
        ),
        (
            "Scorion's Feast",
            "(5 items) When you deal damage with a fully-charged Heavy Attack, you gain an Imbued Aura. If you deal damage with a fully-charged Heavy Attack with an Imbued Aura active, consume it and gain an Overflow Aura for 10 seconds, granting Weapon and Spell Damage.",
        ),
    ),
)
def test_reviewed_conditional_power_set_blockers_are_owned_by_runtime(
    set_name: str,
    description: str,
) -> None:
    blocker = (
        f"{set_name} (5): active set bonus is not yet mechanic-mapped: "
        f"{description}"
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name=set_name,
        category="Test",
        equipped_piece_count=5,
        objective_key="spell_damage",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    review = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert review.h1_mechanic_complete is True
    assert review.h1_positive_modifier_proven is True
    assert review.remaining_blockers == ()
    assert review.ignored_blockers == (blocker,)


def test_reviewed_conditional_power_set_mapping_is_objective_scoped() -> None:
    blocker = (
        "Briarheart (5): active set bonus is not yet mechanic-mapped: "
        "(5 items) When you deal Critical Damage, you increase your Weapon and Spell Damage "
        "by 450 for 10 seconds."
    )
    row = ExtremeGearSetObjectiveCandidate(
        set_id=1,
        set_name="Briarheart",
        category="Test",
        equipped_piece_count=5,
        objective_key="max_health",
        reviewed_delta=0.0,
        unresolved=(blocker,),
    )

    review = ExtremeActualHealGearSetCandidateService._h1_review(row)

    assert review.h1_mechanic_complete is False
    assert review.remaining_blockers == (blocker,)
