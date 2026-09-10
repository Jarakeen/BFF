from __future__ import annotations

from services.extreme_templar_aedric_spear_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeTemplarAedricSpearPassiveReview,
)


def test_aedric_spear_review_covers_exact_live_u50_passive_roster() -> None:
    review = ExtremeTemplarAedricSpearPassiveReview()
    rows = review.items()

    assert tuple(row.passive_name for row in rows) == (
        "Piercing Spear",
        "Spear Wall",
        "Burning Light",
        "Balanced Warrior",
    )
    assert review.complete


def test_balanced_warrior_is_the_only_most_actual_heal_relevant_passive() -> None:
    rows = {
        row.passive_name: row
        for row in ExtremeTemplarAedricSpearPassiveReview().items()
    }

    assert rows["Balanced Warrior"].objective_relevant
    assert rows["Balanced Warrior"].coverage_status == IMPLEMENTED
    assert "TemplarPassiveInputResolver" in rows["Balanced Warrior"].evidence
    assert "BuildCalculationContextFactory" in rows["Balanced Warrior"].evidence

    for name in ("Piercing Spear", "Spear Wall", "Burning Light"):
        assert not rows[name].objective_relevant
        assert rows[name].coverage_status == IRRELEVANT


def test_piercing_spear_review_does_not_conflate_critical_damage_and_healing() -> None:
    row = next(
        row
        for row in ExtremeTemplarAedricSpearPassiveReview().items()
        if row.passive_name == "Piercing Spear"
    )

    assert "Critical Damage" in row.detail
    assert "not Critical Healing" in row.detail
