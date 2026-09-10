from __future__ import annotations

from services.extreme_warden_green_balance_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeWardenGreenBalancePassiveReview,
)


def test_green_balance_review_is_exhaustive_and_complete() -> None:
    review = ExtremeWardenGreenBalancePassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Accelerated Growth",
        "Nature's Gift",
        "Emerald Moss",
        "Maturation",
    )
    assert review.complete


def test_green_balance_review_classifies_heal_size_vs_non_size_mechanics() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeWardenGreenBalancePassiveReview().items()
    }

    assert rows["Accelerated Growth"].objective_relevant
    assert rows["Accelerated Growth"].coverage_status == IMPLEMENTED
    assert rows["Emerald Moss"].objective_relevant
    assert rows["Emerald Moss"].coverage_status == IMPLEMENTED

    assert not rows["Nature's Gift"].objective_relevant
    assert rows["Nature's Gift"].coverage_status == IRRELEVANT
    assert "sustain" in rows["Nature's Gift"].detail.casefold()

    assert not rows["Maturation"].objective_relevant
    assert rows["Maturation"].coverage_status == IRRELEVANT
    assert "max health" in rows["Maturation"].detail.casefold()


def test_green_balance_relevant_passives_point_to_real_extreme_implementation_layers() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeWardenGreenBalancePassiveReview().items()
    }

    assert (
        rows["Accelerated Growth"].evidence
        == "ExtremeWardenAcceleratedGrowthCombatStateService"
    )
    assert rows["Emerald Moss"].evidence == "ExtremeWardenGreenBalanceHealingService"
