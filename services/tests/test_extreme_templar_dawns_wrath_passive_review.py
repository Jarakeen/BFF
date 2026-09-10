from __future__ import annotations

from services.extreme_templar_dawns_wrath_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeTemplarDawnsWrathPassiveReview,
)


def test_dawns_wrath_review_covers_exact_live_u50_passive_roster() -> None:
    review = ExtremeTemplarDawnsWrathPassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Enduring Rays",
        "Prism",
        "Illuminate",
        "Restoring Spirit",
    )
    assert review.complete


def test_illuminate_is_the_only_most_actual_heal_relevant_passive() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeTemplarDawnsWrathPassiveReview().items()
    }

    assert rows["Illuminate"].objective_relevant
    assert rows["Illuminate"].coverage_status == IMPLEMENTED
    assert "ExtremeTemplarIlluminateCombatStateService" in rows["Illuminate"].evidence
    assert "ExtremeTemplarConditionalActualHealService" in rows["Illuminate"].evidence

    for name in ("Enduring Rays", "Prism", "Restoring Spirit"):
        assert not rows[name].objective_relevant
        assert rows[name].coverage_status == IRRELEVANT


def test_restoring_spirit_review_keeps_sustain_out_of_event_magnitude() -> None:
    row = next(
        row
        for row in ExtremeTemplarDawnsWrathPassiveReview().items()
        if row.passive_name == "Restoring Spirit"
    )

    assert "cost" in row.detail.casefold()
    assert "do not change the size" in row.detail
