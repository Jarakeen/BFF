from __future__ import annotations

from services.extreme_necromancer_living_death_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeNecromancerLivingDeathPassiveReview,
)


def test_living_death_review_covers_exact_four_passive_roster() -> None:
    review = ExtremeNecromancerLivingDeathPassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Curative Curse",
        "Near-Death Experience",
        "Corpse Consumption",
        "Undead Confederate",
    )
    assert len({row.passive_name for row in rows}) == 4
    assert review.complete


def test_living_death_review_only_curative_curse_changes_most_actual_heal_size() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeNecromancerLivingDeathPassiveReview().items()
    }

    assert rows["Curative Curse"].objective_relevant
    assert rows["Curative Curse"].coverage_status == IMPLEMENTED

    for name in (
        "Near-Death Experience",
        "Corpse Consumption",
        "Undead Confederate",
    ):
        assert not rows[name].objective_relevant
        assert rows[name].coverage_status == IRRELEVANT


def test_near_death_experience_stays_out_of_maximum_event_crit_size_math() -> None:
    row = next(
        row
        for row in ExtremeNecromancerLivingDeathPassiveReview().items()
        if row.passive_name == "Near-Death Experience"
    )

    assert "Critical Strike Chance" in row.detail
    assert "not the numeric size" in row.detail
