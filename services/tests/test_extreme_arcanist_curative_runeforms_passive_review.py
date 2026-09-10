from __future__ import annotations

from services.extreme_arcanist_curative_runeforms_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeArcanistCurativeRuneformsPassiveReview,
)


def test_curative_runeforms_review_has_exact_passive_roster_and_is_complete() -> None:
    review = ExtremeArcanistCurativeRuneformsPassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Healing Tides",
        "Hideous Clarity",
        "Erudition",
        "Intricate Runeforms",
    )
    assert review.complete


def test_curative_runeforms_review_classifies_only_healing_tides_as_heal_size_relevant() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeArcanistCurativeRuneformsPassiveReview().items()
    }

    assert rows["Healing Tides"].objective_relevant is True
    assert rows["Healing Tides"].coverage_status == IMPLEMENTED

    for passive_name in ("Hideous Clarity", "Erudition", "Intricate Runeforms"):
        assert rows[passive_name].objective_relevant is False
        assert rows[passive_name].coverage_status == IRRELEVANT

    assert "sustain" in rows["Hideous Clarity"].detail.casefold()
    assert "sustain" in rows["Erudition"].detail.casefold()
    assert "damage-shield" in rows["Intricate Runeforms"].detail.casefold()


def test_healing_tides_review_points_to_real_extreme_runtime_implementation() -> None:
    row = next(
        row
        for row in ExtremeArcanistCurativeRuneformsPassiveReview().items()
        if row.passive_name == "Healing Tides"
    )

    assert "ExtremeArcanistCurativeRuneformsHealingService" in row.evidence
    assert "ExtremeConditionalActualHealOptimizationService" in row.evidence
    assert "4%" in row.detail
    assert "Crux" in row.detail
