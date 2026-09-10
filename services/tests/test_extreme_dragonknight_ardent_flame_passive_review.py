from services.extreme_dragonknight_ardent_flame_passive_review import (
    IMPLEMENTED,
    INTEGRATION_PENDING,
    IRRELEVANT,
    ExtremeDragonknightArdentFlamePassiveReview,
)


def test_ardent_flame_review_covers_all_four_passives() -> None:
    rows = ExtremeDragonknightArdentFlamePassiveReview().items()

    assert [row.passive_name for row in rows] == [
        "Combustion",
        "Traumatic Burns",
        "Fan the Flames",
        "A Soul Ablaze",
    ]
    assert len({row.passive_name for row in rows}) == 4


def test_only_a_soul_ablaze_is_relevant_to_most_actual_heal() -> None:
    rows = ExtremeDragonknightArdentFlamePassiveReview().items()
    relevant = [row for row in rows if row.objective_relevant]

    assert [(row.passive_name, row.coverage_status) for row in relevant] == [
        ("A Soul Ablaze", INTEGRATION_PENDING),
    ]
    assert all(
        row.coverage_status == IRRELEVANT
        for row in rows
        if not row.objective_relevant
    )


def test_ardent_flame_review_remains_incomplete_until_context_wiring() -> None:
    review = ExtremeDragonknightArdentFlamePassiveReview()

    assert not review.complete
    assert all(
        row.coverage_status != IMPLEMENTED
        for row in review.items()
        if row.objective_relevant
    )
