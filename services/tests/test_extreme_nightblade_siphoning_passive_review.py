from __future__ import annotations

from services.extreme_nightblade_siphoning_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeNightbladeSiphoningPassiveReview,
)


def test_siphoning_review_covers_exact_four_passive_roster() -> None:
    review = ExtremeNightbladeSiphoningPassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Catalyst",
        "Magicka Flood",
        "Soul Siphoner",
        "Transfer",
    )
    assert review.complete


def test_siphoning_review_marks_only_heal_size_passives_relevant() -> None:
    rows = {row.passive_name: row for row in ExtremeNightbladeSiphoningPassiveReview().items()}

    assert rows["Magicka Flood"].objective_relevant
    assert rows["Magicka Flood"].coverage_status == IMPLEMENTED
    assert "6% Max Magicka and Max Stamina" in rows["Magicka Flood"].detail

    assert rows["Soul Siphoner"].objective_relevant
    assert rows["Soul Siphoner"].coverage_status == IMPLEMENTED

    assert not rows["Catalyst"].objective_relevant
    assert rows["Catalyst"].coverage_status == IRRELEVANT
    assert not rows["Transfer"].objective_relevant
    assert rows["Transfer"].coverage_status == IRRELEVANT


def test_siphoning_review_preserves_resource_and_healing_done_layers() -> None:
    rows = {row.passive_name: row for row in ExtremeNightbladeSiphoningPassiveReview().items()}

    assert "NightbladePassiveInputResolver" in rows["Magicka Flood"].evidence
    assert "primary-resource" in rows["Magicka Flood"].detail
    assert "ExtremeNightbladeSiphoningHealingService" in rows["Soul Siphoner"].evidence
    assert "Healing Done" in rows["Soul Siphoner"].detail
