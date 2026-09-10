from __future__ import annotations

from services.extreme_warden_animal_companions_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeWardenAnimalCompanionsPassiveReview,
)


def test_animal_companions_review_covers_exact_live_u50_passive_roster() -> None:
    review = ExtremeWardenAnimalCompanionsPassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Bond with Nature",
        "Savage Beast",
        "Flourish",
        "Advanced Species",
    )
    assert review.complete


def test_bond_with_nature_is_the_healing_relevant_animal_companions_passive() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeWardenAnimalCompanionsPassiveReview().items()
    }

    assert rows["Bond with Nature"].objective_relevant
    assert rows["Bond with Nature"].coverage_status == IMPLEMENTED
    assert "ExtremeWardenBondWithNatureHealingEventService" in rows["Bond with Nature"].evidence


def test_other_animal_companions_passives_do_not_change_most_actual_heal_size() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeWardenAnimalCompanionsPassiveReview().items()
    }

    for name in ("Savage Beast", "Flourish", "Advanced Species"):
        assert not rows[name].objective_relevant
        assert rows[name].coverage_status == IRRELEVANT
