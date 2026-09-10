from __future__ import annotations

from services.extreme_necromancer_bone_tyrant_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeNecromancerBoneTyrantPassiveReview,
)


def test_bone_tyrant_review_covers_exact_four_passive_roster() -> None:
    review = ExtremeNecromancerBoneTyrantPassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Death Gleaning",
        "Disdain Harm",
        "Health Avarice",
        "Last Gasp",
    )
    assert len({row.passive_name for row in rows}) == 4
    assert review.complete


def test_bone_tyrant_review_marks_only_heal_size_passives_relevant() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeNecromancerBoneTyrantPassiveReview().items()
    }

    for name in ("Health Avarice", "Last Gasp"):
        assert rows[name].objective_relevant
        assert rows[name].coverage_status == IMPLEMENTED

    for name in ("Death Gleaning", "Disdain Harm"):
        assert not rows[name].objective_relevant
        assert rows[name].coverage_status == IRRELEVANT


def test_bone_tyrant_review_keeps_received_side_and_max_health_distinct() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeNecromancerBoneTyrantPassiveReview().items()
    }

    assert "Healing Received" in rows["Health Avarice"].detail
    assert "active bar" in rows["Health Avarice"].detail
    assert "Max Health" in rows["Last Gasp"].detail
    assert "before ESO rounding" in rows["Last Gasp"].detail
