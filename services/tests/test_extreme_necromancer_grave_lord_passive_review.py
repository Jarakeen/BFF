from __future__ import annotations

from services.extreme_necromancer_grave_lord_passive_review import (
    IRRELEVANT,
    ExtremeNecromancerGraveLordPassiveReview,
)


def test_grave_lord_review_covers_exact_live_u50_passive_roster() -> None:
    review = ExtremeNecromancerGraveLordPassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Reusable Parts",
        "Death Knell",
        "Dismember",
        "Rapid Rot",
    )
    assert len({row.passive_name for row in rows}) == 4
    assert review.complete


def test_grave_lord_passives_do_not_change_most_actual_heal_magnitude() -> None:
    rows = ExtremeNecromancerGraveLordPassiveReview().items()

    assert all(not row.objective_relevant for row in rows)
    assert all(row.coverage_status == IRRELEVANT for row in rows)


def test_death_knell_offensive_critical_chance_stays_out_of_critical_heal_size() -> None:
    row = next(
        row
        for row in ExtremeNecromancerGraveLordPassiveReview().items()
        if row.passive_name == "Death Knell"
    )

    assert "offensive Critical Strike Chance" in row.detail
    assert "not Critical Healing magnitude" in row.detail


def test_dismember_penetration_stays_out_of_heal_magnitude() -> None:
    row = next(
        row
        for row in ExtremeNecromancerGraveLordPassiveReview().items()
        if row.passive_name == "Dismember"
    )

    assert "Penetration" in row.detail
    assert "does not enlarge one healing event" in row.detail
