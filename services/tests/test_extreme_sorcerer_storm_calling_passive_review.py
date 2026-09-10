from services.extreme_sorcerer_storm_calling_passive_review import (
    IMPLEMENTED,
    IRRELEVANT,
    ExtremeSorcererStormCallingPassiveReview,
)


def test_storm_calling_review_covers_all_four_passives() -> None:
    review = ExtremeSorcererStormCallingPassiveReview()
    rows = review.items()

    assert [row.passive_name for row in rows] == [
        "Capacitor",
        "Energized",
        "Amplitude",
        "Expert Mage",
    ]
    assert review.complete


def test_only_expert_mage_is_relevant_to_most_actual_heal() -> None:
    rows = ExtremeSorcererStormCallingPassiveReview().items()
    relevant = [row for row in rows if row.objective_relevant]

    assert [(row.passive_name, row.coverage_status) for row in relevant] == [
        ("Expert Mage", IMPLEMENTED),
    ]
    assert all(
        row.coverage_status == IRRELEVANT
        for row in rows
        if not row.objective_relevant
    )


def test_expert_mage_review_points_to_canonical_power_pipeline() -> None:
    row = next(
        row
        for row in ExtremeSorcererStormCallingPassiveReview().items()
        if row.passive_name == "Expert Mage"
    )

    assert "SorcererPassiveInputResolver" in row.evidence
    assert "BuildCalculationContextFactory" in row.evidence
    assert "108 Weapon and Spell Damage" in row.detail
